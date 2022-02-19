"""This module includes the main application that provides an interface between the TCP server that faces
Sigma Studio, and the SPI handler that controls the DSP.

Commands from Sigma Studio are received, and translated to SPI read/write requests.
"""
import argparse
import json
import logging
import sys
import threading
from typing import Any, List

import rpyc
from rpyc.utils.server import ThreadedServer

from sigmadsp.communication.sigma_tcp_server import (
    ReadRequest,
    ReadResponse,
    SigmaTCPServer,
    WriteRequest,
)
from sigmadsp.hardware.adau14xx import Adau14xx
from sigmadsp.hardware.spi import SpiHandler
from sigmadsp.helper.parser import Cell, Parser


class SigmadspSettings:
    default_settings_file_path = "/var/lib/sigmadsp/sigmadsp.json"

    def __init__(self, settings_file_path: str = None):
        """Loads a settings file in .json format from a specified path.
        If no file is provided, the default path is used for loading settings.

        Args:
            settings_file_path (str, optional): The input path of the settings file.
                Defaults to None.
        """
        if settings_file_path is None:
            settings_file_path = SigmadspSettings.default_settings_file_path

        try:
            # Open settings file, in order to configure the application
            with open(settings_file_path, "r", encoding="utf8") as settings_file:
                self.settings = json.load(settings_file)
                logging.info("Settings file %s was loaded.", settings_file_path)

        except FileNotFoundError:
            logging.info("Settings file not found. Using default values.")
            self.settings = None

        self.parameter_parser = self.load_parameters()

    def load_parameters(self) -> List[Cell]:
        """Loads parameter cells, according to the parameter file path
        that is defined in the settings object.

        Returns:
            List[Cell]: The cells that were found in the parameter file
        """
        parameter_file_path = self.parameter_file_path

        parser = Parser()
        parser.run(parameter_file_path)
        return parser

    def store_parameters(self, lines: List[str]):
        """Stores parameters to the parameter file.

        Args:
            lines (List[str]): [description]
        """
        with open(self.parameter_file_path, "w", encoding="UTF8") as parameter_file:
            parameter_file.writelines(lines)

        self.load_parameters()

    def get_setting(self, key: str, default_setting: Any = None) -> Any:
        """Loads certain settings from the settings dictionary

        Args:
            key (str): The key to look for
            default_setting (Any): The default return value, if the key is not found

        Returns:
            Any: Setting for the key, if found, default_setting otherwise.
        """
        setting = default_setting

        if self.settings is not None:
            try:
                setting = self.settings[key]

            except KeyError:
                pass

        return setting

    @property
    def host(self) -> str:
        return self.get_setting("host", "0.0.0.0")

    @property
    def port(self) -> int:
        return self.get_setting("port", 8087)

    @property
    def backend_port(self) -> int:
        return self.get_setting("backend_port", 18861)

    @property
    def dsp_type(self) -> str:
        return self.get_setting("dsp_type", "adau14xx")

    @property
    def parameter_file_path(self) -> str:
        return self.get_setting("parameter_file_path", "/var/lib/sigmadsp/current.params")


class ConfigurationBackendService(rpyc.Service):
    """The configuration backend service that handles the underlying TCP server and SPI handler.
    This service also reacts to rpyc remote procedure calls, for performing actions with the DSP over SPI.
    """

    def __init__(self, settings: SigmadspSettings = None):
        """Initialize service and start all relevant threads (TCP, SPI)

        Args:
            settings (SigmadspSettings, optional): The settings object. Defaults to None.
        """
        super().__init__()

        self.settings = settings

        # Create an SPI handler, along with its thread
        self.spi_handler = SpiHandler()

        # Create a SigmaTCPServer, along with its various threads
        self.sigma_tcp_server = SigmaTCPServer(settings.host, settings.port)
        logging.info("Sigma TCP server started on [%s]:%d.", settings.host, settings.port)

        # Create the worker thread for the handler itself
        worker_thread = threading.Thread(target=self.worker, name="Worker thread")
        worker_thread.daemon = True
        worker_thread.start()

        logging.info("Specified DSP type is '%s'.", settings.dsp_type)

        if settings.dsp_type == "adau14xx":
            self.dsp = Adau14xx(self.spi_handler)

        else:
            logging.error("DSP type '%s' is not known! Aborting.", settings.dsp_type)
            sys.exit(0)

    def worker(self):
        """Main worker functionality. Gets requests from the TCP server component
        and forwards them to the SPI handler.
        """
        while True:
            request = self.sigma_tcp_server.get_request()

            if isinstance(request, WriteRequest):
                self.spi_handler.write(request.address, request.data)

            elif isinstance(request, ReadRequest):
                payload = self.spi_handler.read(request.address, request.length)

                self.sigma_tcp_server.put_request(ReadResponse(payload))

    def exposed_reset_dsp(self):
        """Soft resets the DSP"""
        self.dsp.soft_reset()

    def exposed_adjust_volume(self, adjustment_db: float, cell_name: str):
        """Adjusts the volume of a specified volume cell

        Args:
            adjustment_db (float): The adjustment in dB for the volume cell
            cell_name (str): The name of the cell to adjust
        """
        for volume_cell in self.settings.parameter_parser.volume_cells:
            if volume_cell.name == cell_name:
                self.dsp.adjust_volume(adjustment_db, volume_cell.parameter_address)

    def exposed_load_parameter_file(self, lines: List[str]):
        """Store a new parameter file locally"""
        self.settings.store_parameters(lines)

    def on_connect(self, conn):
        # code that runs when a connection is created
        # (to init the service, if needed)
        del conn

    def on_disconnect(self, conn):
        # code that runs after the connection has already closed
        # (to finalize the service, if needed)
        del conn


def launch(settings: SigmadspSettings):
    """Launches the backend application

    Args:
        settings_file_path (str, optional): Settings file for the backend application. Defaults to None.
            If not specified, a default path is used for loading the settings.
    """
    BACKEND_PORT = settings.backend_port

    # Create the backend service, an rpyc handler
    configuration_backend_service = ConfigurationBackendService(settings)
    threaded_server = ThreadedServer(configuration_backend_service, port=BACKEND_PORT)
    threaded_server.start()


def main():
    """Launch the backend with default settings"""
    logging.basicConfig(level=logging.INFO)

    argument_parser = argparse.ArgumentParser()
    argument_parser.add_argument(
        "-s",
        "--settings",
        required=False,
        help="specifies the settings file path for configuring the sigmadsp backend application",
    )
    arguments = argument_parser.parse_args()

    settings = SigmadspSettings(arguments.settings)
    launch(settings)


if __name__ == "__main__":
    main()
