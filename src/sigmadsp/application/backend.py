"""This module includes the main application that provides an interface between
the TCP server that faces SigmaStudio, and an SPI handler that controls a DSP.

Commands from Sigma Studio are received, and translated to SPI
read/write requests.
"""
import argparse
import logging
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import List

import grpc
import yaml

from sigmadsp.communication.sigma_tcp_server import (
    ReadRequest,
    ReadResponse,
    SigmaTCPServer,
    WriteRequest,
)
from sigmadsp.generated.backend_service.control_pb2 import (
    ControlRequest,
    ControlResponse,
)
from sigmadsp.generated.backend_service.control_pb2_grpc import (
    BackendServicer,
    add_BackendServicer_to_server,
)
from sigmadsp.hardware.adau14xx import Adau14xx
from sigmadsp.hardware.spi import SpiHandler
from sigmadsp.helper.parser import Cell, Parser


class SigmadspSettings:
    """This class holds and manages settings for the SigmaDSP application."""

    default_config_path = "/var/lib/sigmadsp/config.yaml"

    def __init__(self, config_path: str = None):
        """Loads a config file in *.yaml format from a specified path. If no
        file is provided, the default path is used for loading settings.

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
            logging.error(
                "Settings file not found at %s. Aborting.", config_path
            )
            raise

        self.load_parameters()

    def load_parameters(self) -> List[Cell]:
        """Loads parameter cells, according to the parameter file path that is
        defined in the settings object.

        Returns:
            List[Cell]: The cells that were found in the parameter file
        """
        parser = Parser()
        parser.run(self.config["parameters"]["path"])

        self.parameter_parser = parser

    def store_parameters(self, lines: List[str]):
        """Stores parameters to the parameter file.

        Args:
            lines (List[str]): [description]
        """
        with open(
            self.config["parameters"]["path"], "w", encoding="UTF8"
        ) as parameter_file:
            parameter_file.writelines(lines)

        self.load_parameters()


class BackendService(BackendServicer):
    """The backend service that handles the underlying TCP server and SPI
    handler.

    This service also reacts to rpyc remote procedure calls, for
    performing actions with the DSP over SPI.
    """

    def __init__(self, settings: SigmadspSettings = None):
        """Initialize service and start all relevant threads (TCP, SPI)

        Args:
            settings (SigmadspSettings, optional): The settings object.
                Defaults to None.
        """
        super().__init__()

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
        worker_thread = threading.Thread(
            target=self.worker, name="Worker thread"
        )
        worker_thread.daemon = True
        worker_thread.start()

        logging.info(
            "Specified DSP type is '%s'.", self.settings.config["dsp"]["type"]
        )

        if self.settings.config["dsp"]["type"] == "adau14xx":
            self.dsp = Adau14xx(self.spi_handler)

        else:
            logging.error(
                "DSP type '%s' is not known! Aborting.",
                self.config["dsp"]["type"],
            )
            sys.exit(0)

    def worker(self):
        """Main worker functionality.

        Gets requests from the TCP server component and forwards them to
        the SPI handler.
        """
        while True:
            request = self.sigma_tcp_server.get_request()

            if isinstance(request, WriteRequest):
                self.spi_handler.write(request.address, request.data)

            elif isinstance(request, ReadRequest):
                payload = self.spi_handler.read(request.address, request.length)

                self.sigma_tcp_server.put_request(ReadResponse(payload))

    def control(self, request: ControlRequest, context):
        """Main backend entry point for control messages.

        Args:
            request (ControlRequest): The request that the backend shall handle.
            context (Any): The context within which to handle the request (unused).

        Returns:
            ControlResponse: A control response message, returned to the caller.
        """
        response = ControlResponse()
        response.success = True

        # Determine the type of control request.
        command = request.WhichOneof("command")

        if "reset_dsp" == command:
            self.dsp.soft_reset()
            response.message = "Reset DSP."

        elif "change_volume" == command:
            for volume_cell in self.settings.parameter_parser.volume_cells:
                if volume_cell.name == request.change_volume.cell_name:

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

                    response.message = (
                        f"Set volume of '{request.change_volume.cell_name}' ",
                        f"to {new_volume_db:.2f} dB.",
                    )

                    break

        elif "load_parameters" == command:
            self.settings.store_parameters(request.load_parameters.content)
            response.message = "Loaded parameters"

        return response


def launch(settings: SigmadspSettings):
    """Launches the backend application.

    Args:
        config_path (str, optional): Settings file for the backend application.
            Defaults to None. If not specified, a default path is used
            for loading the settings.
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
