"""The backend application of sigmadsp.

This module includes the main application that provides an interface between the TCP server that faces SigmaStudio,
and an SPI handler that controls a DSP.

Commands from Sigma Studio are received, and translated to SPI read/write requests.
"""
import argparse
import logging
import sched
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import grpc
from retry import retry

import sigmadsp
from sigmadsp.communication.sigma_tcp_server import (
    ReadRequest,
    ReadResponse,
    SigmaStudioInterface,
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
from sigmadsp.hardware.dsp import ConfigurationError, SafetyCheckException
from sigmadsp.helper.settings import SigmadspSettings

# A logger for this module
logger = logging.getLogger(__name__)


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

        config = self.settings.config
        dsp_type = config["dsp"]["type"]
        dsp_protocol = config["dsp"].get("protocol", "spi")

        # Create a SigmaTCPServer, along with its various threads
        self.sigma_tcp_server = SigmaStudioInterface(
            config["host"]["ip"],
            config["host"]["port"],
        )
        logger.info("Sigma TCP server started on [%s]:%d.", config["host"]["ip"], config["host"]["port"])

        # Create a scheduler for recurring tasks
        self.scheduler = sched.scheduler(time.time, time.sleep)

        # Create the worker thread for the handler itself
        worker_thread = threading.Thread(target=self.worker, name="Backend service worker thread")
        worker_thread.daemon = True
        worker_thread.start()

        logger.info("Specified DSP type is '%s', using the '%s' protocol.", dsp_type, dsp_protocol)

        try:
            if dsp_type == "adau14xx":
                self.dsp = Adau14xx(self.settings.config)

            else:
                logger.error("DSP type '%s' is not known! Aborting.", dsp_type)
                sys.exit(1)

        except ConfigurationError:
            logger.error("DSP configuration is broken! Aborting")
            sys.exit(1)

        try:
            logger.info("Run startup safety check.")
            self.startup_safety_check()

        except SafetyCheckException:
            logger.warning("Startup safety check failed.")

    @retry(SafetyCheckException, 5, 5)
    def startup_safety_check(self) -> None:
        """Perform startup safety check, retrying a few times.

        The safety check might not be successful immediately after starting the DSP, so it is retried periodically.
        """
        self.safety_check()

    def safety_check(self) -> None:
        """Check a hash cell within the DSP's memory against a hash value from the parameter file.

        Only if they match, configuration of DSP parameters is allowed. Other operations (e.g. reset, or
        loading a new parameter file) are still allowed, even in a locked configuration state.
        """
        if not self.settings.parameter_parser:
            logger.warning("No parameter file was loaded! Configuration remains locked.")
            return

        safety_hash_cell = self.settings.parameter_parser.safety_hash_cell

        if safety_hash_cell is None:
            logger.warning("No safety hash cell exists in the DSP configuration! Configuration remains locked.")
            self.configuration_unlocked = False

        else:
            dsp_hash = self.dsp.get_parameter_value(safety_hash_cell.parameter_address, data_format="int")
            logger.info("Safety hash address: 0x%04x.", safety_hash_cell.parameter_address)

            if safety_hash_cell.parameter_value != dsp_hash:
                logger.warning(
                    "Safety hash cell content does not match! Expected %d, but read %d. Configuration remains locked.",
                    safety_hash_cell.parameter_value,
                    dsp_hash,
                )
                self.configuration_unlocked = False
                raise SafetyCheckException

            else:
                logger.info("Safety check successful. Configuration unlocked.")
                self.configuration_unlocked = True

    def worker(self):
        """Main worker functionality.

        Gets requests from the TCP server component and forwards them to the SPI handler.
        """
        while True:
            request = self.sigma_tcp_server.pipe_end_user.recv()

            if isinstance(request, WriteRequest):
                self.dsp.write(request.address, request.data)

            elif isinstance(request, ReadRequest):
                payload = self.dsp.read(request.address, request.length)

                self.sigma_tcp_server.pipe_end_user.send(ReadResponse(payload))

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

        if not self.settings.parameter_parser:
            response.message = "No parameters loaded, parameters cannot be changed."
            return response

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
            response.message = "Soft-reset DSP."
            response.success = True

        elif "hard_reset_dsp" == command:
            self.dsp.hard_reset()
            response.message = "Hard-reset DSP."
            response.success = True

        elif "load_parameters" == command:
            self.settings.store_parameters(list(request.load_parameters.content))

            # Repeat safety check after loading a new set of parameters
            try:
                self.safety_check()

            except SafetyCheckException:
                pass

            if self.configuration_unlocked:
                response.message = "Loaded parameters, control is unlocked."
                response.success = True

            else:
                response.message = "Safety check failed, parameters cannot be adjusted."
                response.success = False

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

    logger.info("Backend service started on %s", backend_address)

    grpc_server.wait_for_termination()


def main():
    """Launch the backend with default settings."""
    logging.basicConfig(level=logging.INFO)

    logger.info("Starting the sigmadsp backend, version %s.", sigmadsp.__version__)

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
