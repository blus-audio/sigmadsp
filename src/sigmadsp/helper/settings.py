"""This module contains a class that handles settings for this application."""
import logging
from typing import List, Union

import yaml

from sigmadsp.helper.parser import Parser

# A logger for this module
logger = logging.getLogger(__name__)


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
                logger.info("Settings file %s was loaded.", config_path)

        except FileNotFoundError:
            logger.error("Settings file not found at %s. Aborting.", config_path)
            raise

        # A parser for parameters, defined in the config file.
        self.parameter_parser: Union[Parser, None] = None

        self.load_parameters()

    def load_parameters(self) -> None:
        """Load parameter cells, according to the parameter file path that is defined in the settings object."""
        try:
            parser = Parser()
            parser.run(self.config["parameters"]["path"])

            self.parameter_parser = parser

        except (IndexError, TypeError):
            logger.info("No parameter path was defined in the configuration file.")

    def store_parameters(self, lines: List[str]):
        """Store parameters to the parameter file.

        Args:
            lines (List[str]): [description]
        """
        with open(self.config["parameters"]["path"], "w", encoding="UTF8") as parameter_file:
            parameter_file.writelines(lines)

        self.load_parameters()
