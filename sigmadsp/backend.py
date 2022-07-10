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
from multiprocessing import Queue
from typing import Callable, Dict

import grpc
from retry.api import retry_call

import sigmadsp
from sigmadsp.dsp.common import ConfigurationError, Dsp, SafetyCheckError
from sigmadsp.dsp.factory import dsp_from_config
from sigmadsp.generated.backend_service.control_pb2 import (
    ControlParameterRequest,
    ControlRequest,
    ControlResponse,
)
from sigmadsp.generated.backend_service.control_pb2_grpc import (
    BackendServicer,
    add_BackendServicer_to_server,
)
from sigmadsp.helper.settings import SigmadspSettings
from sigmadsp.sigmastudio.common import (
    CONNECTION_CLOSED,
    ReadRequest,
    ReadResponse,
    SafeloadRequest,
    WriteRequest,
)
from sigmadsp.sigmastudio.server import SigmaStudioRequestHandler, SigmaStudioTcpServer

# A logger for this module
logger = logging.getLogger(__name__)


class BackendService(BackendServicer):
    """The backend service that handles the underlying TCP server and SPI handler.

    This service also reacts to rpyc remote procedure calls, for performing actions with the DSP over SPI.
    """

    dsp: Dsp
    send_queue: Queue
    receive_queue: Queue

    def __init__(self, settings: SigmadspSettings, dsp_from_config_fn: Callable[[Dict], Dsp] = dsp_from_config):
        """Initialize service and start all relevant threads (TCP, SPI).

        Args:
            settings (SigmadspSettings): The settings object.
            dsp_from_config_fn (Callable[[Dict], Dsp]): The function to use for generating new Dsp objects
                from a config.
        """
        super().__init__()

        self._active = True

        self.send_queue = Queue()
        self.receive_queue = Queue()

        # If configuration_unlocked is False, no DSP parameters can be changed.
        self.configuration_unlocked: bool = False

        self.settings = settings
        self.config = self.settings.config

        # Create a scheduler for recurring tasks
        self.scheduler = sched.scheduler(time.time, time.sleep)

        try:
            self.dsp = dsp_from_config_fn(self.config)

        except ConfigurationError:
            logger.error("DSP configuration is broken! Aborting")
            sys.exit(1)

        logger.info(
            "Specified DSP type is '%s', using the '%s' protocol.",
            type(self.dsp).__name__,
            type(self.dsp.dsp_protocol).__name__,
        )

        # Create the startup thread
        startup_worker_thread = threading.Thread(target=self.startup_worker, name="Startup worker", daemon=True)
        startup_worker_thread.start()

    def startup_worker(self):
        """A thread that performs a startup check and then starts the rest of the threads."""
        # Reset the DSP first.
        self.dsp.hard_reset()

        try:
            logger.info("Run startup safety check.")
            self.retry_safety_check()

        except SafetyCheckError:
            logger.warning("Startup safety check failed.")

        logger.info("Startup finished.")

        # Create a SigmaTCPServer and run it.
        self.sigma_tcp_server = SigmaStudioTcpServer(
            (self.config["host"]["ip"], self.config["host"]["port"]),
            SigmaStudioRequestHandler,
            self.dsp.header_generator,
            self.send_queue,
            self.receive_queue,
        )

        self.sigma_tcp_server_worker_thread = threading.Thread(
            target=self.sigma_tcp_server_worker, daemon=True, name="Sigma TCP server worker"
        )
        self.sigma_tcp_server_worker_thread.start()

        logger.info("Sigma TCP server started on [%s]:%d.", self.config["host"]["ip"], self.config["host"]["port"])

        # Create the request worker thread.
        self.sigma_studio_worker_thread = threading.Thread(
            target=self.sigma_studio_worker, name="SigmaStudio worker", daemon=True
        )
        self.sigma_studio_worker_thread.start()

    def trigger_retry_safety_check(self):
        """Runs the safety check in a new thread."""
        safety_check_thread = threading.Thread(target=self.retry_safety_check, daemon=True)
        safety_check_thread.start()

    def retry_safety_check(self) -> None:
        """The ``safety_check``, but with retries."""
        retry_call(self.safety_check, exceptions=SafetyCheckError, tries=5, delay=5)

    def safety_check(self) -> None:
        """Check a hash cell within the DSP's memory against a hash value from the parameter file.

        Only if they match, configuration of DSP parameters is allowed. Other operations (e.g. reset, or
        loading a new parameter file) are still allowed, even in a locked configuration state.
        """
        self.configuration_unlocked = False

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
                raise SafetyCheckError

            else:
                logger.info("Safety check successful. Configuration unlocked.")
                self.configuration_unlocked = True

    def close(self):
        """Close the backend service and terminate its threads."""
        self._active = False

        self.send_queue.close()
        self.receive_queue.close()

        self.sigma_studio_worker_thread.join()

        self.sigma_tcp_server.shutdown()
        self.sigma_tcp_server_worker_thread.join()

    def sigma_tcp_server_worker(self):
        """Sigma TCP server worker.

        Simply runs the TCP server.
        """
        with self.sigma_tcp_server:
            self.sigma_tcp_server.serve_forever()

        logger.info("Sigma TCP server worker terminated.")

    def sigma_studio_worker(self):
        """Sigma studio worker.

        Gets requests from the TCP server component and forwards them to the SPI handler.
        """
        with self.sigma_tcp_server:
            while self._active:
                try:
                    request = self.receive_queue.get()

                    if request is CONNECTION_CLOSED:
                        ...

                    elif isinstance(request, WriteRequest):
                        self.dsp.write(request.address, request.data)

                    elif isinstance(request, SafeloadRequest):
                        self.dsp.safeload(request.address, request.data)

                    elif isinstance(request, ReadRequest):
                        payload = self.dsp.read(request.address, request.length)
                        self.send_queue.put(ReadResponse(payload))

                    else:
                        raise TypeError(f"Unknown command type {type(request)}.")

                except EOFError:
                    # Access to one of the queues failed, terminate the worker.
                    break

        logger.info("Sigma studio worker terminated.")

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
            response.message = "No parameters were loaded, parameters cannot be changed."
            return response

        if not self.configuration_unlocked:
            # Do not allow to change parameters.
            response.message = "Configuration is currently locked, parameters cannot be changed."
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
            self.trigger_retry_safety_check()

            response.message = "Soft-reset DSP."
            response.success = True

        elif "hard_reset_dsp" == command:
            self.dsp.hard_reset()
            self.trigger_retry_safety_check()

            response.message = "Hard-reset DSP."
            response.success = True

        elif "load_parameters" == command:
            self.settings.store_parameters(list(request.load_parameters.content))

            # Repeat safety check after loading a new set of parameters
            try:
                self.safety_check()

            except SafetyCheckError:
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
