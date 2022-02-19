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

import argparse
import threading
import logging
import json
import rpyc
import sys

def load_from_settings(settings: dict, key: str, default: Any) -> Any:
    """Loads certain settings from the settings dictionary

    Args:
        settings (dict): Settings dictionary
        key (str): The key to look for
        default (Any): The default return value, if the key is not found

    Returns:
        Any: Setting for the key, if found, default otherwise.
    """
    if settings is not None:
        try:
            return settings[key]

        except KeyError:
            return default
             

class ConfigurationBackendService(rpyc.Service):
    """The configuration backend service that handles the underlying TCP server and SPI handler.
    This service also reacts to rpyc remote procedure calls, for performing actions with the DSP over SPI.
    """
    def __init__(self, settings: dict = None, parser: Parser = None):
        """Initialize service and start all relevant threads (TCP, SPI)

        Args:
            settings (dict, optional): The settings dictionary. Defaults to None.
            parser (Parser, optional): The parameter file parser. Defaults to None.
        """
        super().__init__()

        self.parser = parser

        # Load TCP server settings
        HOST = load_from_settings(settings, "host", "0.0.0.0")
        PORT = load_from_settings(settings, "port", 8087)
        
        # Create an SPI handler, along with its thread
        self.spi_handler = SpiHandler()

        # Create a SigmaTCPServer, along with its various threads
        self.sigma_tcp_server = SigmaTCPServer(HOST, PORT)
        logging.info(f"Sigma TCP server started on [{HOST}]:{PORT}.")

        # Create the worker thread for the handler itself
        worker_thread = threading.Thread(target=self.worker, name="Worker thread")
        worker_thread.daemon = True
        worker_thread.start()
        
        DSP_TYPE = load_from_settings(settings, "dsp_type", "adau14xx")
        logging.info(f"Specified DSP type is '{DSP_TYPE}'.")

        if DSP_TYPE == "adau14xx":
            self.dsp = Adau14xx(self.spi_handler)

        else:
            logging.error(f"DSP type '{DSP_TYPE}' is not known! Aborting.")
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
    If no file is provided, the default path is used for loading settings.

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
    """Loads parameter cells, accoring to the parameter file path that is defined in the settings dictionary

    Args:
        settings (dict): The settings dictionary

    Returns:
        List[Cell]: The cells that were found in the parameter file
    """
    if settings is not None:
        try:
            parameter_file_path = settings["parameter_file_path"]

        except KeyError:
            logging.info("No parameter file path was specified in the settings file.")

        else:
            parser = Parser()
            parser.run(parameter_file_path)
            return parser

    else:
        logging.info("No settings file was loaded, thus no parameter cells can be loaded.")
        return None


def launch(settings_file_path: str = None):
    """Launches the backend application

    Args:
        settings_file_path (str, optional): Settings file for the backend application. Defaults to None.
            If not specified, a default path is used for loading the settings.
    """
    settings = load_settings_file(settings_file_path)
    parser = load_parameters(settings)

    BACKEND_PORT = load_from_settings(settings, "backend_port", 18861)
        
    # Create the backend service, an rpyc handler
    configuration_backend_service = ConfigurationBackendService(settings, parser)
    threaded_server = ThreadedServer(configuration_backend_service, port=BACKEND_PORT)
    threaded_server.start()

def main():
    """Launch the backend with default settings
    """
    logging.basicConfig(level=logging.INFO)

    argument_parser = argparse.ArgumentParser()
    argument_parser.add_argument("-s", "--settings", required=False, help="specifies the settings file path for configuring the sigmadsp backend application")
    arguments = argument_parser.parse_args()

    launch(settings_file_path = arguments.settings)
    
if __name__ == "__main__":
    main()