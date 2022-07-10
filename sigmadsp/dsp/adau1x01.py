"""This module provides functionality for controlling SigmaDSP ADAU1x01 hardware."""
import logging
import math
from typing import List, Tuple

from sigmadsp.dsp.common import Dsp
from sigmadsp.helper.conversion import (
    bytes_to_int16,
    float_to_frac_5_23,
    frac_5_23_to_float,
    int16_to_bytes,
)
from sigmadsp.sigmastudio.adau1x01 import Adau1x01HeaderGenerator

# A logger for this module
logger = logging.getLogger(__name__)


class Adau1x01(Dsp):
    """A class for controlling functionality of Analog Devices Sigma DSPs, especially ADAU1x01 series parts."""

    # Addresses and sizes of important registers
    CONTROL_REGISTER = 0x081C
    CONTROL_REGISTER_LENGTH = 2

    # Safeload registers (address, data)
    SAFELOAD_REGISTERS: List[Tuple[int, int]] = [
        (0x0815, 0x810),
        (0x0816, 0x811),
        (0x0815, 0x812),
        (0x0818, 0x813),
        (0x0819, 0x814),
    ]

    # Safeload register length
    SAFELOAD_SA_LENGTH = 2
    SAFELOAD_SD_LENGTH = 5

    header_generator = Adau1x01HeaderGenerator()

    @staticmethod
    def float_to_frac(value: float) -> int:
        """The method that converts floating-point values to fractional integers on the Adau1x01."""
        return float_to_frac_5_23(value)

    @staticmethod
    def frac_to_float(value: int) -> float:
        """The method that converts fractional integers to floating-point values on the Adau1x01."""
        return frac_5_23_to_float(value)

    def soft_reset(self):
        """Soft reset the DSP.

        Not available on ADAU1x01
        """
        logger.info("Soft-reset is not available on ADAU1x01")

    def safeload(self, address: int, data: bytes):
        """Write data to the chip using hardware safeload.

        Args:
            address (int): Address to write to
            data (bytes): Data to write; multiple words should be concatenated.
        """
        # Number of words with length FIXPOINT_REGISTER_LENGTH in data.
        word_count = math.ceil(len(data) / self.FIXPOINT_REGISTER_LENGTH)

        assert address >= 0

        # load up the address and data in safeload registers
        for sd in range(0, word_count):
            address_register, data_register = Adau1x01.SAFELOAD_REGISTERS[sd]
            address_bytes = int16_to_bytes(address)
            data_buf = bytearray(Adau1x01.SAFELOAD_SD_LENGTH)

            data_buf[1:] = data[sd * Adau1x01.FIXPOINT_REGISTER_LENGTH : (sd + 1) * Adau1x01.FIXPOINT_REGISTER_LENGTH]

            self.write(address_register, address_bytes)
            self.write(data_register, data_buf)

        control_bytes = self.read(Adau1x01.CONTROL_REGISTER, Adau1x01.CONTROL_REGISTER_LENGTH)
        control_reg = bytes_to_int16(control_bytes)

        ist_mask = 1 << 5

        control_reg |= ist_mask

        # start safe load
        self.write(Adau1x01.CONTROL_REGISTER, int16_to_bytes(control_reg))
