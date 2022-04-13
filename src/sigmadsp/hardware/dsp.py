"""General definitions for interfacing DSPs."""
import logging
import time
from abc import abstractmethod
from dataclasses import dataclass
from typing import List, Union

import gpiozero

from sigmadsp.hardware.spi import SpiHandler

# A logger for this module
logger = logging.getLogger(__name__)


class SafetyCheckException(Exception):
    """Custom exception for failed DSP safety checks."""


@dataclass
class Pin:
    """A class that describes a general DSP pin."""

    name: str
    number: int

    def __post_init__(self):
        """Initialize the generic device, based on the configured parameters."""
        self.control = gpiozero.GPIODevice(self.number)


@dataclass
class InputPin(Pin):
    """A class that describes a DSP input pin."""

    pull_up: bool
    active_state: bool
    bounce_time: Union[float, None]

    def __post_init__(self):
        """Initialize the input device, based on the configured parameters."""
        self.control = gpiozero.DigitalInputDevice(self.number, self.pull_up, self.active_state, self.bounce_time)


@dataclass
class OutputPin(Pin):
    """A class that describes a DSP output pin."""

    initial_value: bool
    active_high: bool

    def __post_init__(self):
        """Initialize the output device, based on the configured parameters."""
        self.control = gpiozero.DigitalOutputDevice(self.number, self.active_high, self.initial_value)


class Dsp:
    """A generic DSP class, to be extended by child classes."""

    def __init__(self, config: dict, spi_handler: SpiHandler):
        """Initialize the DSP with an SpiHandler that talks to it.

        Args:
            config (dict): Configuration settings, from the general configuration file.
            spi_handler (SpiHandler): The SpiHandler that communicates with the DSP.
        """
        self.config = config
        self.pins: List[Pin] = []
        self.parse_config()

        self.spi_handler = spi_handler
        self.hard_reset()

    def parse_config(self):
        """Parse the configuration file and extract relevant information."""
        try:
            for pin_definition_key in self.config["dsp"]["pins"]:
                pin_definition = self.config["dsp"]["pins"][pin_definition_key]

                if pin_definition["mode"] == "output":
                    output_pin = OutputPin(
                        pin_definition_key,
                        pin_definition["number"],
                        pin_definition["initial_state"],
                        pin_definition["active_high"],
                    )

                    self.add_pin(output_pin)

                elif pin_definition["mode"] == "input":
                    input_pin = InputPin(
                        pin_definition_key,
                        pin_definition["number"],
                        pin_definition["pull_up"],
                        pin_definition["active_state"],
                        pin_definition["bounce_time"],
                    )

                    self.add_pin(input_pin)

        except (KeyError, TypeError):
            logger.info("No DSP pin definitions were found in the configuration file.")

    def get_pin_by_name(self, name: str) -> Union[Pin, None]:
        """Get a pin by its name.

        Args:
            name (str): The name of the pin.

        Returns:
            Union[Pin, None]: The pin, if one matches, None otherwise.
        """
        for pin in self.pins:
            if pin.name == name:
                return pin

        return None

    def has_pin(self, pin: Pin) -> bool:
        """Check, if a pin is known in the list of pins.

        Args:
            pin (Pin): The pin to look for.

        Returns:
            bool: True, if the pin is known, False otherwise.
        """
        return bool(self.get_pin_by_name(pin.name) is not None)

    def add_pin(self, pin: Pin):
        """Add a pin to the list of pins, if it doesn't exist yet.

        Args:
            pin (Pin): The pin to add.
        """
        if not self.has_pin(pin):
            logger.info("Found DSP pin definition '%s' (%d)", pin.name, pin.number)
            self.pins.append(pin)

    def remove_pin_by_name(self, name: str):
        """Remove a pin, based on its name.

        Args:
            name (str): The pin name.
        """
        pin = self.get_pin_by_name(name)

        if pin:
            self.pins.remove(pin)

    def hard_reset(self, delay: float = 0):
        """Hard reset the DSP.

        Set and release the corresponding pin for resetting.
        """
        pin = self.get_pin_by_name("reset")

        if not pin:
            logger.info("Falling back to soft-resetting the DSP, no hard-reset pin is defined.")
            self.soft_reset()
            return

        logger.info("Hard-resetting the DSP.")

        pin.control.on()
        time.sleep(delay)
        pin.control.off()

    @abstractmethod
    def soft_reset(self):
        """Soft reset the DSP."""
