"""This module provides functionality for controlling SigmaDSP hardware, e.g.
- Changing parameter register contents
- Reading parameter registers
- Performing soft reset

For this, it uses the SpiHandler module, to interface to the DSP.
"""
import logging

from sigmadsp.hardware.spi import SpiHandler
from sigmadsp.helper.conversion import (
    int16_to_bytes,
    int32_to_bytes,
    bytes_to_int32,
    db_to_linear,
    linear_to_db,
)


class Adau14xx:
    """A class for controlling functionality of Analog Devices Sigma DSPs, especially ADAU14xx series parts."""

    # Addresses and sizes of important registers
    RESET_REGISTER = 0xF890
    RESET_REGISTER_LENGTH = 2

    # All fixpoint (parameter) registers are four bytes long
    FIXPOINT_REGISTER_LENGTH = 4

    def __init__(self, spi_handler: SpiHandler):
        self.spi_handler = spi_handler

    def fixpoint_to_float(self, value: int) -> float:
        """Converts a value in the DSPs fixpoint representation to float.
        32 bit values consist of 8 integer and 24 fractional bits. They are signed.

        Args:
            value (int): Fixpoint value to convert

        Returns:
            float: Output in float format
        """
        return value / 2 ** 24

    def float_to_fixpoint(self, value: float) -> int:
        """Converts a float value to the DSPs fixpoint representation.
        32 bit values consist of 8 integer and 24 fractional bits. They are signed.

        Args:
            value (float): Float value to convert

        Returns:
            int: Output in DSP fixpoint format
        """
        return int(value * 2 ** 24)

    def soft_reset(self):
        """Soft resets the DSP by writing the reset register twice."""
        self.spi_handler.write(Adau14xx.RESET_REGISTER, int16_to_bytes(0))
        self.spi_handler.write(Adau14xx.RESET_REGISTER, int16_to_bytes(1))

    def get_parameter_value(self, address: int) -> float:
        """Gets a parameter value from a chosen register address

        Args:
            address (int): The address to look at

        Returns:
            float: Float representation of the register content
        """

        data_register = self.spi_handler.read(
            address, Adau14xx.FIXPOINT_REGISTER_LENGTH
        )
        data_integer = bytes_to_int32(data_register)
        data_float = self.fixpoint_to_float(data_integer)
        return data_float

    def set_parameter_value(self, value: float, address: int):
        """Sets a parameter value for a chosen register address

        Args:
            value (float): The value to store in the register
            address (int): The target address
        """
        data_integer = self.float_to_fixpoint(value)
        data_register = int32_to_bytes(data_integer)
        self.spi_handler.write(address, data_register)

    def adjust_volume(self, adjustment_db: float, address: int):
        """Adjust the volume register at the given address by a certain value in dB.

        Args:
            adjustment_db (float): The volume adjustment in dB
            address (int): The volume adjustment register address
        """
        # Read current volume and apply adjustment
        current_volume = self.get_parameter_value(address)
        linear_adjustment = db_to_linear(adjustment_db)
        new_volume = current_volume * linear_adjustment

        # Clamp volume to safe levels
        if new_volume >= 1:
            new_volume = 1

        elif new_volume <= 0:
            new_volume = 0

        self.set_parameter_value(new_volume, address)

        logging.info(
            f"Adjusted volume from {linear_to_db(current_volume):.2f} dB to {linear_to_db(new_volume):.2f} dB."
        )
