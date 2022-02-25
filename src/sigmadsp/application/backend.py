"""The backend application of sigmadsp.

This module includes the main application that provides an interface between the TCP server that faces SigmaStudio,
and an SPI handler that controls a DSP.

Commands from Sigma Studio are received, and translated to SPI read/write requests.
"""
import argparse
import logging
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import List

import grpc
import yaml

import sigmadsp
from sigmadsp.communication.sigma_tcp_server import (
    ReadRequest,
    ReadResponse,
    SigmaTCPServer,
    WriteRequest,
)
from sigmadsp.generated.backend_service.control_pb2 import (
    ControlParameterRequest,
    ControlRequest,
    ControlResponse,
)
from sigmadsp.generated.backend_service.control_pb2_grpc import (
    BackendServicer,
    add_BackendServicer_to_server,
)
from sigmadsp.hardware.adau14xx import Adau14xx
from sigmadsp.hardware.spi import SpiHandler
from sigmadsp.helper.parser import Parser


class SigmadspSettings:
    """This class holds and manages settings for the SigmaDSP application."""

    default_config_path = "/var/lib/sigmadsp/config.yaml"

    def __init__(self, config_path: str = None):
        """Load a config file in *.yaml format from a specified path.

        If no file is provided, the default path is used for loading settings.

        Args:
            config_path (str, optional): The input path of the settings file.
                Defaults to None.
        """
        if config_path is None:
            config_path = SigmadspSettings.default_config_path

        try:
            # Open settings file, in order to configure the application
            with open(config_path, "r", encoding="utf8") as settings_file:
                self.config = yaml.safe_load(settings_file)
                logging.info("Settings file %s was loaded.", config_path)

        except FileNotFoundError:
            logging.error("Settings file not found at %s. Aborting.", config_path)
            raise

        self.load_parameters()

    def load_parameters(self) -> None:
        """Load parameter cells, according to the parameter file path that is defined in the settings object."""
        parser = Parser()
        parser.run(self.config["parameters"]["path"])

        self.parameter_parser = parser

    def store_parameters(self, lines: List[str]):
        """Store parameters to the parameter file.

        Args:
            lines (List[str]): [description]
        """
        with open(self.config["parameters"]["path"], "w", encoding="UTF8") as parameter_file:
            parameter_file.writelines(lines)

        self.load_parameters()


class BackendService(BackendServicer):
    """The backend service that handles the underlying TCP server and SPI handler.

    This service also reacts to rpyc remote procedure calls, for performing actions with the DSP over SPI.
    """

    def __init__(self, settings: SigmadspSettings):
        """Initialize service and start all relevant threads (TCP, SPI).

        Args:
            settings (SigmadspSettings): The settings object.
        """
        super().__init__()

        # If configuration_unlocked is False, no DSP parameters can be changed.
        self.configuration_unlocked: bool = False

        self.settings = settings

        # Create an SPI handler, along with its thread
        self.spi_handler = SpiHandler()

        # Create a SigmaTCPServer, along with its various threads
        self.sigma_tcp_server = SigmaTCPServer(
            self.settings.config["host"]["ip"],
            self.settings.config["host"]["port"],
        )
        logging.info(
            "Sigma TCP server started on [%s]:%d.",
            self.settings.config["host"]["ip"],
            self.settings.config["host"]["port"],
        )

        # Create the worker thread for the handler itself
        worker_thread = threading.Thread(target=self.worker, name="Backend service worker thread")
        worker_thread.daemon = True
        worker_thread.start()

        logging.info("Specified DSP type is '%s'.", self.settings.config["dsp"]["type"])

        if self.settings.config["dsp"]["type"] == "adau14xx":
            self.dsp = Adau14xx(self.spi_handler)

        else:
            logging.error(
                "DSP type '%s' is not known! Aborting.",
                self.settings.config["dsp"]["type"],
            )
            sys.exit(0)

        self.safety_check()

    def safety_check(self) -> None:
        """Check a hash cell within the DSP's memory against a hash value from the parameter file.

        Only if they match, configuration of DSP parameters is allowed. Other operations (e.g. reset, or
        loading a new parameter file) are still allowed, even in a locked configuration state.
        """
        safety_hash_cell = self.settings.parameter_parser.safety_hash_cell

        if safety_hash_cell is None:
            logging.warning("Safety hash in cell not present! Configuration locked.")
            self.configuration_unlocked = False

        else:
            dsp_hash = self.dsp.get_parameter_value(safety_hash_cell.parameter_address, data_format="int")

            if safety_hash_cell.parameter_value != dsp_hash:
                logging.warning("Safety hash in cell does not match! Configuration locked.")
                self.configuration_unlocked = False

            else:
                logging.info("Safety check successful. Configuration unlocked.")
                self.configuration_unlocked = True

    def worker(self):
        """Main worker functionality.

        Gets requests from the TCP server component and forwards them to the SPI handler.
        """
        while True:
            request = self.sigma_tcp_server.get_request()

            if isinstance(request, WriteRequest):
                self.spi_handler.write(request.address, request.data)

            elif isinstance(request, ReadRequest):
                payload = self.spi_handler.read(request.address, request.length)

                self.sigma_tcp_server.put_request(ReadResponse(payload))

    def control_parameter(self, request: ControlParameterRequest, context):
        """Main backend entry point for control messages that change or read parameters.

        Here, the configuration has to be in an unlocked state, which requires a hash number in the DSP firmware to
        match the hash number that is provided in the parameter file.

        Args:
            request (ControlParameterRequest): The request that the backend shall handle.
            context (Any): The context within which to handle the request (unused).

        Returns:
            ControlResponse: A control response message, returned to the caller.
        """
        response = ControlResponse()

        # Determine the type of control request.
        command = request.WhichOneof("command")
        response.success = False

        if not self.configuration_unlocked:
            # Do not allow to change parameters.
            response.message = "Configuration locked, parameters cannot be changed."
            return response

        if "change_volume" == command:
            volume_cells_to_adjust = self.settings.parameter_parser.get_matching_cells_by_name_tokens(
                self.settings.parameter_parser.volume_cells, list(request.change_volume.name_tokens)
            )

            if not volume_cells_to_adjust:
                response.message = (
                    f"No volume cell identified by {request.change_volume.name_tokens} was found."
                    "Available controls are "
                    f"{([cell.name_tokens for cell in self.settings.parameter_parser.volume_cells])}."
                )

            for volume_cell in volume_cells_to_adjust:
                if request.change_volume.relative:
                    new_volume_db = self.dsp.adjust_volume(
                        request.change_volume.value,
                        volume_cell.parameter_address,
                    )

                elif not request.change_volume.relative:
                    new_volume_db = self.dsp.set_volume(
                        request.change_volume.value,
                        volume_cell.parameter_address,
                    )

                response.message = f"Set volume of cell '{volume_cell.full_name}' to {new_volume_db:.2f} dB."

        response.success = True
        return response

    def control(self, request: ControlRequest, context):
        """Main backend entry point for control messages.

        Args:
            request (ControlRequest): The request that the backend shall handle.
            context (Any): The context within which to handle the request (unused).

        Returns:
            ControlResponse: A control response message, returned to the caller.
        """
        response = ControlResponse()

        # Determine the type of control request.
        command = request.WhichOneof("command")

        if "reset_dsp" == command:
            self.dsp.soft_reset()
            response.message = "Reset DSP."

        elif "load_parameters" == command:
            self.settings.store_parameters(list(request.load_parameters.content))

            # Repeat safety check after loading a new set of parameters
            self.safety_check()

            if self.configuration_unlocked:
                response.message = "Loaded parameters, control is unlocked."

            else:
                response.message = "Safety check failed, parameters cannot be adjusted."

        response.success = True
        return response


def launch(settings: SigmadspSettings):
    """Launch the backend application.

    Args:
        settings (SigmadspSettings): Settings object for the backend application.
    """
    # Create the backend service, a grpc service
    grpc_server = grpc.server(ThreadPoolExecutor(max_workers=10))

    backend_port = settings.config["backend"]["port"]
    backend_address = f"[::]:{backend_port}"

    add_BackendServicer_to_server(BackendService(settings), grpc_server)
    grpc_server.add_insecure_port(backend_address)
    grpc_server.start()

    logging.info("Backend service started on %s", backend_address)

    grpc_server.wait_for_termination()


def main():
    """Launch the backend with default settings."""
    logging.basicConfig(level=logging.INFO)

    logging.info("Starting the sigmadsp backend, version %s.", sigmadsp.__version__)

    argument_parser = argparse.ArgumentParser()
    argument_parser.add_argument(
        "-s",
        "--settings",
        required=False,
        help=(
            "specifies the settings file path for configuring ",
            "the sigmadsp backend application",
        ),
    )
    arguments = argument_parser.parse_args()

    settings = SigmadspSettings(arguments.settings)
    launch(settings)


if __name__ == "__main__":
    main()
