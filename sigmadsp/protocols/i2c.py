"""This module implements an I2C handler that talks to Sigma DSP devices."""

import logging

from smbus2 import i2c_msg
from smbus2 import SMBus

from .common import DspProtocol
from sigmadsp.helper.conversion import int16_to_bytes

# A logger for this module
logger = logging.getLogger(__name__)


class I2cProtocol(DspProtocol):
    """Handle I2C transfers from and to SigmaDSP chipsets.

    Tested with ADAU1701
    """

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

        with SMBus(self._bus_id) as bus:
            bus.i2c_rdwr(write_message, read_message)

        return bytes(read_message)

    def _write(self, address: int, data: bytes) -> int:
        """Write data over the I2C port onto a SigmaDSP.

        Args:
            address (int): Address to write to.
            data (bytes): Data to write.

        Returns:
            int: Number of written bytes.
        """
        payload = list(int16_to_bytes(address))
        payload.extend(list(data))

        write_message = i2c_msg.write(self._device_address, payload)

        with SMBus(self._bus_id) as bus:
            bus.i2c_rdwr(write_message)

        return len(data)
