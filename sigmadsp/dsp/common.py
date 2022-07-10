"""General definitions for interfacing DSPs."""
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from math import nan
from typing import List, Literal, Union

import gpiozero

from sigmadsp.helper.conversion import (
    bytes_to_int32,
    clamp,
    db_to_linear,
    int32_to_bytes,
    linear_to_db,
)
from sigmadsp.protocols.common import DspProtocol
from sigmadsp.sigmastudio.header import PacketHeaderGenerator

# A logger for this module
logger = logging.getLogger(__name__)

ParameterType = Literal["float", "int"]


class SafetyCheckError(Exception):
    """Custom exception for failed DSP safety checks."""


class ConfigurationError(Exception):
    """Custom exception for an invalid DSP configuration."""


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


# see https://github.com/python/mypy/issues/5374
@dataclass  # type: ignore
class Dsp(ABC):
    """A generic DSP class, to be extended by child classes."""

    use_safeload: bool
    dsp_protocol: DspProtocol
    pins: List[Pin] = field(default_factory=list)

    # All fixpoint (parameter) registers are four bytes long
    FIXPOINT_REGISTER_LENGTH = 4

    @property
    @abstractmethod
    def header_generator(self) -> PacketHeaderGenerator:
        """The packet header generator of the DSP."""

    @staticmethod
    @abstractmethod
    def float_to_frac(value: float) -> int:
        """The method that converts floating-point values to fractional integers on this Dsp."""

    @staticmethod
    @abstractmethod
    def frac_to_float(value: int) -> float:
        """The method that converts fractional integers to floating-point values on this Dsp."""

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

        if pin:
            logger.info("Hard-resetting the DSP.")

            pin.control.on()
            time.sleep(delay)
            pin.control.off()

        else:
            logger.warning("No hard-reset pin is defined, not resetting.")

        # Soft-reset in the end, for flushing registers.
        self.soft_reset()

    def write(self, address: int, data: bytes):
        """Write data to the DSP using the configured communication handler.

        Args:
            address (int): Address to write to
            data (bytes): Data to write
        """
        assert address >= 0

        self.dsp_protocol.write(address, data)

    def read(self, address: int, length: int) -> bytes:
        """Write data to the DSP using the configured communication handler.

        Args:
            address (int): Address to write to
            length (int): Number of bytes to read
        """
        assert address >= 0
        assert length > 0

        return self.dsp_protocol.read(address, length)

    def set_volume(self, volume_db: float, address: int, relative: bool = False) -> float:
        """Set the volume register at the given address to a certain value in dB.

        Args:
            volume_db (float): The volume setting in dB
            address (int): The volume adjustment register address
            relative (bool): If True, the current DSP register value is changed by ``volume_db``. If False, it is set.

        Returns:
            float: The new volume in dB.
        """
        # Read current volume first
        current_volume_linear = self.get_parameter_value(address, data_format="float")

        if not isinstance(current_volume_linear, float):
            raise TypeError(f"Current volume readout has incorrect type {type(current_volume_linear)}.")

        current_volume_db = linear_to_db(current_volume_linear)

        if volume_db is nan:
            logger.info("Volume value is nan.")
            return current_volume_db

        if relative:
            new_volume_value_db = volume_db + current_volume_db

        else:
            new_volume_value_db = volume_db

        try:
            # Clamp set volume to safe levels
            new_volume_value_linear = clamp(db_to_linear(new_volume_value_db), 0, 1)

        except OverflowError:
            logger.info("Volume adjustment was too large, ignoring.")
            return current_volume_db

        try:
            self.set_parameter_value(new_volume_value_linear, address, data_format="float")

        except ValueError:
            # Parameter conversion failed.
            return current_volume_db

        logger.info("Set volume to %.2f dB.", linear_to_db(new_volume_value_linear))

        # Read back current volume and verify.
        new_volume_value_linear_from_dsp = self.get_parameter_value(address, data_format="float")

        if not isinstance(new_volume_value_linear_from_dsp, float):
            raise TypeError(f"New volume readout has incorrect type {type(new_volume_value_linear_from_dsp)}.")

        return linear_to_db(new_volume_value_linear_from_dsp)

    def adjust_volume(self, adjustment_db: float, address: int) -> float:
        """Adjust the volume register at the given address by a certain value in dB.

        Args:
            adjustment_db (float): The volume adjustment in dB
            address (int): The volume adjustment register address

        Returns:
            float: The new volume in dB.
        """
        return self.set_volume(adjustment_db, address, relative=True)

    @abstractmethod
    def soft_reset(self):
        """Soft reset the DSP."""

    @abstractmethod
    def safeload(self, address: int, data: bytes):
        """Write data to the chip using chip-specific safeload.

        Args:
            address (int): Address to write to
            data (bytes): Data to write
        """

    def set_parameter_value(self, value: Union[float, int], address: int, data_format: ParameterType) -> None:
        """Set a parameter value for a chosen register address. Registers are 32 bits wide.

        Args:
            value (float): The value to store in the register
            address (int): The target address
            data_format (PARAMETER_TYPE): The data type of value. Can be ``float`` or ``int``.
        """
        data_register: Union[bytes, None] = None

        if data_format == "float":
            data_register = int32_to_bytes(self.float_to_frac(value))

        elif data_format == "int":
            data_register = int32_to_bytes(value)

        if data_register is not None:
            if self.use_safeload:
                self.safeload(address, data_register)

            else:
                self.write(address, data_register)

    def get_parameter_value(self, address: int, data_format: Literal["int", "float"]) -> Union[float, int, None]:
        """Get a parameter value from a chosen register address.

        Args:
            address (int): The address to look at.
            data_format (Literal["int", "float"]): The data type to return the register in. Can be ``float`` or ``int``.

        Returns:
            Union[float, int, None]: Representation of the register content in the specified format.
        """
        data_register = self.read(address, Dsp.FIXPOINT_REGISTER_LENGTH)
        data_integer = bytes_to_int32(data_register)

        if "int" == data_format:
            return data_integer

        elif "float" == data_format:
            return self.frac_to_float(data_integer)

        else:
            return None
