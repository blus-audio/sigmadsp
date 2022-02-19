"""This module includes the main application that provides an interface between the TCP server that faces
Sigma Studio, and the SPI handler that controls the DSP.

Commands from Sigma Studio are received, and translated to SPI read/write requests.
"""
from sigmadsp.hardware.adau14xx import Adau14xx
from sigmadsp.communication.sigma_tcp_server import SigmaTCPServer, WriteRequest, ReadRequest, ReadResponse
from sigmadsp.hardware.spi import SpiHandler
from sigmadsp.helper.parser import Parser, Cell
from rpyc.utils.server import ThreadedServer
from typing import Any, List

import threading
import logging
import json
import rpyc


class ConfigurationBackendService(rpyc.Service):
    def __init__(self, settings: dict = None, parser: Parser = None):
        super().__init__()

        self.parser = parser

        if settings is not None:
            try:
                HOST = settings["host"]

            except KeyError:
                HOST = "0.0.0.0"
            
            try:
                PORT = settings["port"]

            except KeyError:
                PORT = 8087

        # Generate TCP server
        if HOST == "0.0.0.0":
            logging.info(f"Starting a TCP server, for listening on any IP address on port {PORT}.")
        
        else:
            logging.info(f"Starting a TCP server, for listening on {HOST}:{PORT}.")

        # Generate an SPI handler, along with its thread
        self.spi_handler = SpiHandler()

        # Generate a SigmaTCPServer, along with its thread
        self.sigma_tcp_server = SigmaTCPServer()

        worker_thread = threading.Thread(target=self.worker, name="Worker thread")
        worker_thread.daemon = True
        worker_thread.start()

        self.dsp = Adau14xx(self.spi_handler)

    def worker(self):
        while True:
            request = self.sigma_tcp_server.get_request()

            if isinstance(request, WriteRequest):
                self.spi_handler.write(request.address, request.data)

            elif isinstance(request, ReadRequest):
                payload = self.spi_handler.read(request.address, request.length)

                self.sigma_tcp_server.put_request(ReadResponse(payload))

    def exposed_reset_dsp(self):
        """Soft resets the DSP
        """
        self.dsp.soft_reset()

    def exposed_adjust_volume(self, adjustment_db: float, cell_name: str):
        """Adjusts the volume of a specified volume cell

        Args:
            adjustment_db (float): The adjustment in dB for the volume cell
            cell_name (str): The name of the cell to adjust
        """
        for volume_cell in self.parser.volume_cells:
            if volume_cell.name == cell_name:
                self.dsp.adjust_volume(adjustment_db, volume_cell.parameter_address)

    def on_connect(self, conn):
        # code that runs when a connection is created
        # (to init the service, if needed)
        del conn

    def on_disconnect(self, conn):
        # code that runs after the connection has already closed
        # (to finalize the service, if needed)
        del conn


def load_settings_file(settings_file_path: str) -> Any:
    """Loads a settings file in .json format from a specified path and returns a settings dictionary.

    Args:
        settings_file_path (str): The input path

    Returns:
        Any: The settings dictionary
    """ 
    if settings_file_path is None:
        settings_file_path = "/etc/sigmatcp/sigmatcp.json"

    try:
        # Open settings file, in order to configure the application
        with open(settings_file_path, "r") as settings_file:
            settings = json.load(settings_file)
            logging.info(f"Settings file {settings_file_path} was loaded.")
    
    except FileNotFoundError:
        logging.info("Settings file not found. Using default values.")
        settings = None

    return settings


def load_parameters(settings: dict) -> List[Cell]:
    if settings is not None:
        try:
            parameter_file_path = settings["parameter_file_path"]

        except KeyError:
            logging.info("No parameter file path was specified.")

        else:
            parser = Parser()
            parser.run(parameter_file_path)
            return parser

    else:
        return None


def launch(settings_file_path: str = None):
    settings = load_settings_file(settings_file_path)
    parser = load_parameters(settings)
    
    configuration_backend_service = ConfigurationBackendService(settings, parser)
    t = ThreadedServer(configuration_backend_service, port=18861)
    t.start()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    launch()
    