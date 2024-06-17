"""This module implements an I2C handler that talks to Sigma DSP devices."""

from __future__ import annotations

import logging

from smbus2 import SMBus, i2c_msg

from sigmadsp.helper.conversion import int16_to_bytes

from .common import DspProtocol

# A logger for this module
logger = logging.getLogger(__name__)


class I2cProtocol(DspProtocol):
    """Handle I2C transfers from and to SigmaDSP chipsets.

    Tested with ADAU1701
    """

    # Length of the I2C header for communicating with SigmaDSP chipsets
    HEADER_LENGTH = DspProtocol.ADDRESS_LENGTH

    # Maximum number of bytes per I2C transfer
    MAX_I2C_BYTES = 1024

    # Maximum number of words (32 bit) that can be transferred with the
    # maximum number of allowed bytes per SPI transfer
    MAX_PAYLOAD_WORDS = int((MAX_I2C_BYTES - HEADER_LENGTH) / 4)

    def __init__(self, bus_id: int = 1, device_address: int = 0x38):
        """Initialize the I2C hardware.

        Bus will be 1 for RaspberryPi hardware.

        Args:
            bus_id (int, optional): Bus identifier. Defaults to 1.
            device_address (int, optional): Device address. Defaults to 0x38 (ADAU145x default address).
        """
        self._bus_id = bus_id
        self._device_address = device_address

        self.run()

    def _read_write_i2c(self, write_message: i2c_msg, read_message: i2c_msg | None = None):
        """Low-level read-write function for I2C.

        Args:
            write_message (i2c_msg): The message to write.
            read_message (i2c_msg | None, optional): The message to read. Defaults to None (no message read).
        """
        try:
            with SMBus(self._bus_id) as bus:
                if read_message is None:
                    bus.i2c_rdwr(write_message)

                else:
                    bus.i2c_rdwr(write_message, read_message)

        except OSError as e:
            if read_message is None:
                logger.error("I2C failed to write message %s with error: %s", str(write_message.buf), str(e))

            else:
                logger.error(
                    "I2C failed to write message %s and read message %s with error: %s",
                    str(write_message.buf),
                    str(read_message.buf),
                    str(e),
                )

    def _read(self, address: int, length: int) -> bytes:
        """Read data over the I2C port from a SigmaDSP.

        Args:
            address (int): Address to read from.
            length (int): Number of bytes to read.

        Returns:
            bytes: Data that was read from the DSP.
        """
        address_bytes = list(int16_to_bytes(address))

        write_message = i2c_msg.write(self._device_address, address_bytes)
        read_message = i2c_msg.read(self._device_address, length)
        self._read_write_i2c(write_message, read_message)

        return bytes(read_message)

    def _write(self, address: int, data: bytes):
        """Write data over the I2C port onto a SigmaDSP.

        Args:
            address (int): Address to write to.
            data (bytes): Data to write.
        """
        for chunk_address, chunk_data in self.writable_data(address, data, self.MAX_PAYLOAD_WORDS):
            payload = list(int16_to_bytes(chunk_address))
            payload.extend(list(chunk_data))
            write_message = i2c_msg.write(self._device_address, payload)
            self._read_write_i2c(write_message)
