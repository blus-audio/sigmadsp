"""This module provides functionality for controlling SigmaDSP ADAU1x01 hardware."""

from __future__ import annotations

import logging
import math

from sigmadsp.dsp.common import Dsp
from sigmadsp.helper.conversion import bytes_to_int16
from sigmadsp.helper.conversion import float_to_frac_5_23
from sigmadsp.helper.conversion import frac_5_23_to_float
from sigmadsp.helper.conversion import int16_to_bytes
from sigmadsp.sigmastudio.adau1x01 import Adau1x01HeaderGenerator

# A logger for this module
logger = logging.getLogger(__name__)


class Adau1x0x(Dsp):
    """A class for controlling functionality of Analog Devices Sigma DSPs, especially ADAU1x01 series parts."""

    # Addresses and sizes of important registers
    DSP_CORE_CONTROL_REGISTER = 0x081C
    DSP_CORE_CONTROL_REGISTER_LENGTH = 2

    DSP_CORE_CONTROL_REGISTER_IST_POS = 5
    DSP_CORE_CONTROL_REGISTER_IST_MASK = 1 << DSP_CORE_CONTROL_REGISTER_IST_POS

    # Safeload registers (address, data)
    SAFELOAD_REGISTERS: list[tuple[int, int]] = [
        (0x0815, 0x810),
        (0x0816, 0x811),
        (0x0815, 0x812),
        (0x0818, 0x813),
        (0x0819, 0x814),
    ]

    # Safeload register length
    SAFELOAD_ADDRESS_REGISTER_LENGTH = 2
    SAFELOAD_DATA_REGISTER_LENGTH = 5

    header_generator = Adau1x01HeaderGenerator()

    @staticmethod
    def float_to_frac(value: float) -> int:
        """The method that converts floating-point values to fractional integers on the Adau1x01.

        Args:
            value (float): The floating-point value.

        Returns:
            float: The fractional value.
        """
        return float_to_frac_5_23(value)

    @staticmethod
    def frac_to_float(value: int) -> float:
        """The method that converts fractional integers to floating-point values on the Adau1x01.

        Args:
            value (float): The fractional value.

        Returns:
            float: The float value.
        """
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
            address_register, data_register = Adau1x0x.SAFELOAD_REGISTERS[sd]
            address_bytes = int16_to_bytes(address)
            data_buf = bytearray(Adau1x0x.SAFELOAD_DATA_REGISTER_LENGTH)

            data_buf[1:] = data[sd * Adau1x0x.FIXPOINT_REGISTER_LENGTH : (sd + 1) * Adau1x0x.FIXPOINT_REGISTER_LENGTH]

            self.write(address_register, address_bytes)
            self.write(data_register, data_buf)

        control_bytes = self.read(Adau1x0x.DSP_CORE_CONTROL_REGISTER, Adau1x0x.DSP_CORE_CONTROL_REGISTER_LENGTH)
        control_reg = bytes_to_int16(control_bytes)

        control_reg |= Adau1x0x.DSP_CORE_CONTROL_REGISTER_IST_MASK

        # start safe load
        self.write(Adau1x0x.DSP_CORE_CONTROL_REGISTER, int16_to_bytes(control_reg))
