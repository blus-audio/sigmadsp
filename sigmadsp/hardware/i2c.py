"""This module implements an I2C handler that talks to Sigma DSP devices."""
import logging
import threading
from multiprocessing import Pipe

from smbus2 import SMBus, i2c_msg

from sigmadsp.helper.conversion import int16_to_bytes

# A logger for this module
logger = logging.getLogger(__name__)


class I2cHandler:
    """Handle I2C transfers from and to SigmaDSP chipsets.

    Tested with ADAU1701
    """

    # Length of addresses (in bytes) for accessing registers
    ADDRESS_LENGTH = 2

    def __init__(self, i2c_bus: int = 1, i2c_addr: int = 0x34):
        """Initialize the I2cHandler thread."""
        self._initialize_i2c(i2c_bus, i2c_addr)

        # Generate a Pipe, for communicating with the I2C handler thread within this class.
        self.pipe_end_owner, self.pipe_end_user = Pipe()

        logger.info("Starting I2C handling thread.")
        self.thread = threading.Thread(target=self.serve_forever, name="I2C handler thread")
        self.thread.daemon = True
        self.thread.start()

    def _initialize_i2c(self, bus: int = 1, device: int = 0x34):
        """Initialize the I2C hardware.

        Bus will be 1 for RaspberryPi hardware.

        Args:
            bus (int, optional): Bus number. Defaults to 1.
            device (int, optional): Device number. Defaults to 0x34.
        """
        self.bus = SMBus(bus)
        self.i2c_addr = device

    def write(self, address: int, data: bytes):
        """Write data over the I2C interface via the pipe to the I2C thread.

        Args:
            address (int): DSP register address to write to
            data (bytes): Binary data to write
        """
        self.pipe_end_owner.send("write")
        self.pipe_end_owner.send((address, data))

    def read(self, address: int, length: int) -> bytes:
        """Read data from the I2C interface via the pipe to the I2C thread.

        Args:
            address (int): DSP register address to read from
            length (int): Number of bytes to read

        Returns:
            bytes: Register content
        """
        self.pipe_end_owner.send("read")
        self.pipe_end_owner.send((address, length))

        data = self.pipe_end_owner.recv()

        return data

    def serve_forever(self):
        """Handle incoming requests for writing or reading data over SPI."""
        while True:
            mode = self.pipe_end_user.recv()

            if mode == "write":
                address, data = self.pipe_end_user.recv()
                self._write_i2c(address, data)

            elif mode == "read":
                address, length = self.pipe_end_user.recv()
                data = self._read_i2c(address, length)
                self.pipe_end_user.send(data)

    def _read_i2c(self, address: int, length: int) -> bytes:
        """Read data over the i2c port from a SigmaDSP.

        Args:
            address (int): Address to read from
            length (int): Number of bytes to read

        Returns:
            bytes: Data that was read from the DSP
        """
        address_bytes = list(int16_to_bytes(address))

        msg_wr = i2c_msg.write(self.i2c_addr, address_bytes)
        msg_rd = i2c_msg.read(self.i2c_addr, length)

        self.bus.i2c_rdwr(msg_wr, msg_rd)
        rd_list = bytes(msg_rd)

        return rd_list

    def _write_i2c(self, address: int, data: bytes):
        """Write data over the I2C port onto a SigmaDSP.

        Args:
            address (int): Address to write to
            data (bytes): Data to write
        """
        wr_content = list(int16_to_bytes(address))
        wr_content.extend(list(data))

        msg_wr = i2c_msg.write(self.i2c_addr, wr_content)

        self.bus.i2c_rdwr(msg_wr)
