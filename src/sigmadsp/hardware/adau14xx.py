"""This module provides functionality for controlling SigmaDSP hardware, e.g.

- Changing parameter register contents
- Reading parameter registers
- Performing soft reset

For this, it uses the SpiHandler module, to interface to the DSP.
"""
import logging
from typing import Union

from sigmadsp.hardware.spi import SpiHandler
from sigmadsp.helper.conversion import (
    bytes_to_int32,
    clamp,
    db_to_linear,
    float_to_frac_8_24,
    frac_8_24_to_float,
    int16_to_bytes,
    int32_to_bytes,
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
        """Initialize the DSP with an SpiHandler that talks to it.

        Args:
            spi_handler (SpiHandler): The SpiHandler that communicates with the DSP.
        """
        self.spi_handler = spi_handler

    def soft_reset(self):
        """Soft reset the DSP.

        Set and release the corresponding register for resetting.
        """
        self.spi_handler.write(Adau14xx.RESET_REGISTER, int16_to_bytes(0))
        self.spi_handler.write(Adau14xx.RESET_REGISTER, int16_to_bytes(1))

    def get_parameter_value(self, address: int, data_format: str) -> Union[float, int, None]:
        """Get a parameter value from a chosen register address.

        Args:
            address (int): The address to look at.
            data_format (str): The data type to return the register in. Can be 'float' or 'int'.

        Returns:
            Union[float, int, None]: Representation of the register content in the specified format.
        """
        data_register = self.spi_handler.read(address, Adau14xx.FIXPOINT_REGISTER_LENGTH)
        data_integer = bytes_to_int32(data_register)

        if "int" == data_format:
            return data_integer

        elif "float" == data_format:
            return frac_8_24_to_float(data_integer)

        else:
            return None

    def set_parameter_value(self, value: Union[float, int], address: int) -> None:
        """Set a parameter value for a chosen register address.

        Args:
            value (float): The value to store in the register
            address (int): The target address
        """
        data_register: Union[bytes, None] = None

        if isinstance(value, float):
            data_register = int32_to_bytes(float_to_frac_8_24(value))

        elif isinstance(value, int):
            data_register = int32_to_bytes(value)

        if data_register is not None:
            self.spi_handler.write(address, data_register)

    def set_volume(self, value_db: float, address: int) -> float:
        """Set the volume register at the given address to a certain value in dB.

        Args:
            value_db (float): The volume setting in dB
            address (int): The volume adjustment register address

        Returns:
            float: The new volume in dB.
        """
        # Read current volume and apply adjustment
        value_linear = db_to_linear(value_db)

        # Clamp set volume to safe levels
        clamp(value_linear, 0, 1)

        self.set_parameter_value(value_linear, address)

        logging.info("Set volume to %.2f dB.", linear_to_db(value_linear))

        return linear_to_db(value_linear)

    def adjust_volume(self, adjustment_db: float, address: int) -> float:
        """Adjust the volume register at the given address by a certain value in dB.

        Args:
            adjustment_db (float): The volume adjustment in dB
            address (int): The volume adjustment register address

        Returns:
            float: The new volume in dB.
        """
        # Read current volume and apply adjustment
        current_volume = self.get_parameter_value(address, data_format="float")

        if not isinstance(current_volume, float):
            raise TypeError

        linear_adjustment = db_to_linear(adjustment_db)
        new_volume = current_volume * linear_adjustment

        # Clamp new volume to safe levels
        clamp(new_volume, 0, 1)

        self.set_parameter_value(new_volume, address)

        logging.info(
            "Adjusted volume from %.2f dB to %.2f dB.",
            linear_to_db(current_volume),
            linear_to_db(new_volume),
        )

        return linear_to_db(new_volume)
