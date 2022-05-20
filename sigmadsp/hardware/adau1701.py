"""This module provides functionality for controlling SigmaDSP hardware, e.g.

- Deploying programs
- Changing parameter register contents
- Reading parameter registers
"""
import logging
from typing import Union

from sigmadsp.hardware.dsp import Dsp
from sigmadsp.helper.conversion import (
    bytes_to_int16,
    bytes_to_int32,
    float_to_frac_5_23,
    frac_5_23_to_float,
    int16_to_bytes,
    int32_to_bytes,
)

# A logger for this module
logger = logging.getLogger(__name__)


class Adau1701(Dsp):
    """A class for controlling functionality of Analog Devices Sigma DSPs, especially ADAU1701 series parts."""

    # Addresses and sizes of important registers
    CONTROL_REGISTER = 0x081C
    CONTROL_REGISTER_LENGTH = 2

    # All fixpoint (parameter) registers are four bytes long
    FIXPOINT_REGISTER_LENGTH = 4

    # Safeload registers (address, data)
    SAFELOAD_REGISTERS = [
        (0x0815, 0x810),
        (0x0816, 0x811),
        (0x0815, 0x812),
        (0x0818, 0x813),
        (0x0819, 0x814),
    ]

    # Safeload register length
    SAFELOAD_SA_LENGTH = 2
    SAFELOAD_SD_LENGTH = 5

    def soft_reset(self):
        """Soft reset the DSP.

        Not available on ADAU1701
        """
        logger.info("Soft-resetting the DSP is not available on ADAU1701")

    def get_parameter_value(self, address: int, data_format: str) -> Union[float, int, None]:
        """Get a parameter value from a chosen register address.

        Args:
            address (int): The address to look at.
            data_format (str): The data type to return the register in. Can be 'float' or 'int'.

        Returns:
            Union[float, int, None]: Representation of the register content in the specified format.
        """
        data_register = self.read(address, Adau1701.FIXPOINT_REGISTER_LENGTH)
        data_integer = bytes_to_int32(data_register)

        float_value = frac_5_23_to_float(data_integer)

        if "int" == data_format:
            return int(float_value)

        elif "float" == data_format:
            return float_value

        else:
            return None

    def set_parameter_value(self, value: Union[float, int], address: int) -> None:
        """Set a parameter value for a chosen register address.

        Args:
            value (float): The value to store in the register
            address (int): The target address
        """
        data_register: Union[bytes, None] = None
        data_register = int32_to_bytes(float_to_frac_5_23(value))

        if data_register is not None:
            self.safeload(address, data_register)

    def safeload(self, address: int, data: bytes, count: int = 1):
        """Write data to the chip using hardware safeload.

        Args:
            address (int): Address to write to
            data (bytes): Data to write; multiple words should be concatenated
            count (int): number of words to write (max. 5)
        """
        # load up the address and data in safeload registers
        for sd in range(0, count):
            address_register, data_register = Adau1701.SAFELOAD_REGISTERS[sd]
            address_bytes = int16_to_bytes(address)
            data_buf = bytearray(Adau1701.SAFELOAD_SD_LENGTH)

            data_buf[1:] = data[sd * Adau1701.FIXPOINT_REGISTER_LENGTH : (sd + 1) * Adau1701.FIXPOINT_REGISTER_LENGTH]

            self.write(address_register, address_bytes)
            self.write(data_register, data_buf)

        control_bytes = self.read(Adau1701.CONTROL_REGISTER, Adau1701.CONTROL_REGISTER_LENGTH)
        control_reg = bytes_to_int16(control_bytes)

        ist_mask = 1 << 5

        control_reg |= ist_mask

        # start safe load
        self.write(Adau1701.CONTROL_REGISTER, int16_to_bytes(control_reg))
