"""This module provides functionality for controlling SigmaDSP ADAU14xx hardware."""
import logging
import math

from sigmadsp.dsp.common import Dsp
from sigmadsp.helper.conversion import (
    float_to_frac_8_24,
    frac_8_24_to_float,
    int16_to_bytes,
    int32_to_bytes,
)
from sigmadsp.sigmastudio.adau14xx import Adau14xxHeaderGenerator

# A logger for this module
logger = logging.getLogger(__name__)


class Adau14xx(Dsp):
    """A class for controlling functionality of Analog Devices Sigma DSPs, especially ADAU14xx series parts."""

    # Addresses and sizes of important registers
    RESET_REGISTER = 0xF890
    RESET_REGISTER_LENGTH = 2

    # safeload registers - SigmaStudio 3.14 and newer
    SAFELOAD_DATA_REGISTERS = [0x6000, 0x6001, 0x6002, 0x6003, 0x6004]
    SAFELOAD_ADDRESS_REGISTER = 0x6005
    SAFELOAD_COUNT_REGISTER = 0x6006
    SAFELOAD_DATA_REGISTER_LENGTH = 4

    header_generator = Adau14xxHeaderGenerator()

    @staticmethod
    def float_to_frac(value: float) -> int:
        """The method that converts floating-point values to fractional integers on the Adau14xx."""
        return float_to_frac_8_24(value)

    @staticmethod
    def frac_to_float(value: int) -> float:
        """The method that converts fractional integers to floating-point values on the Adau14xx."""
        return frac_8_24_to_float(value)

    def soft_reset(self):
        """Soft reset the DSP.

        Set and release the corresponding register for resetting.
        """
        self.write(Adau14xx.RESET_REGISTER, int16_to_bytes(0))
        self.write(Adau14xx.RESET_REGISTER, int16_to_bytes(1))
        logger.info("Soft-resetting the DSP.")

    def safeload(self, address: int, data: bytes):
        """Write data to the chip using software safeload.

        Args:
            address (int): Address to write to
            data (bytes): Data to write; multiple parameters should be concatenated
        """
        # Number of words with length FIXPOINT_REGISTER_LENGTH in data.
        word_count = math.ceil(len(data) / self.FIXPOINT_REGISTER_LENGTH)

        assert address >= 0

        if word_count > len(Adau14xx.SAFELOAD_DATA_REGISTERS):
            raise IndexError(
                f"Cannot write {word_count * self.FIXPOINT_REGISTER_LENGTH} bytes by means of software safeload, "
                f"the maximum is {len(Adau14xx.SAFELOAD_DATA_REGISTERS) * self.FIXPOINT_REGISTER_LENGTH} bytes."
            )
        for register_index, register_address in zip(range(word_count), Adau14xx.SAFELOAD_DATA_REGISTERS):
            data_buf = data[
                register_index * self.FIXPOINT_REGISTER_LENGTH : (register_index + 1) * self.FIXPOINT_REGISTER_LENGTH
            ]
            self.write(register_address, data_buf)

        # TODO: test if the address is supposed to be shifted down by 1 as old forum posts suggest
        self.write(self.SAFELOAD_ADDRESS_REGISTER, int32_to_bytes(address))
        self.write(self.SAFELOAD_COUNT_REGISTER, int32_to_bytes(word_count))
