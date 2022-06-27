"""This module implements an I2C handler that talks to Sigma DSP devices."""
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

    def __init__(self, bus: int = 1, device: int = 0x38):
        """Initialize the I2C hardware.

        Bus will be 1 for RaspberryPi hardware.

        Args:
            bus (int, optional): Bus number. Defaults to 1.
            device (int, optional): Device number. Defaults to 0x38. (ADAU145x default address)
        """
        self._bus = SMBus(bus)
        self._i2c_addr = device

        self.run()

    def _read(self, address: int, length: int) -> bytes:
        """Read data over the i2c port from a SigmaDSP.

        Args:
            address (int): Address to read from
            length (int): Number of bytes to read

        Returns:
            bytes: Data that was read from the DSP
        """
        address_bytes = list(int16_to_bytes(address))

        msg_wr = i2c_msg.write(self._i2c_addr, address_bytes)
        msg_rd = i2c_msg.read(self._i2c_addr, length)

        self._bus.i2c_rdwr(msg_wr, msg_rd)
        rd_list = bytes(msg_rd)

        return rd_list

    def _write(self, address: int, data: bytes):
        """Write data over the I2C port onto a SigmaDSP.

        Args:
            address (int): Address to write to
            data (bytes): Data to write
        """
        wr_content = list(int16_to_bytes(address))
        wr_content.extend(list(data))

        msg_wr = i2c_msg.write(self._i2c_addr, wr_content)

        self._bus.i2c_rdwr(msg_wr)
