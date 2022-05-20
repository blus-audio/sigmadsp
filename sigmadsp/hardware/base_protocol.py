"""This module implements the base class for I2C and SPI communication handlers."""
import logging
import threading
from abc import ABC, abstractmethod
from multiprocessing import Pipe

# A logger for this module
logger = logging.getLogger(__name__)


class BaseProtocol(ABC):
    """Base class for communication handlers talking to SigmaDSP chipsets."""

    def __init__(self, bus: int = 0, device: int = 0):
        """Initialize the communications thread.

        Args:
            bus (int, optional): Bus number. Defaults to 0.
            device (int, optional): Device number / address. Defaults to 0
        """
        self._initialize(bus, device)

        # Generate a Pipe, for communicating with the protocol handler thread within this class.
        self.pipe_end_owner, self.pipe_end_user = Pipe()

        protocol = self.__class__.__name__

        logger.info("Starting %s handling thread.", protocol)
        self.thread = threading.Thread(target=self.serve_forever, name=f"{protocol} handler thread", daemon=True)
        self.thread.start()

    def write(self, address: int, data: bytes):
        """Write data over the hardware interface via the pipe to the hardware thread.

        Args:
            address (int): DSP register address to write to
            data (bytes): Binary data to write
        """
        self.pipe_end_owner.send("write")
        self.pipe_end_owner.send((address, data))

    def read(self, address: int, length: int) -> bytes:
        """Read data from the hardware interface via the pipe to the hardware thread.

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
        """Handle incoming requests for writing or reading data."""
        while True:
            mode = self.pipe_end_user.recv()

            if mode == "write":
                address, data = self.pipe_end_user.recv()
                self._write(address, data)

            elif mode == "read":
                address, length = self.pipe_end_user.recv()
                data = self._read(address, length)
                self.pipe_end_user.send(data)

    @abstractmethod
    def _initialize(self, bus: int = 0, device: int = 0):
        """Initialize the hardware.

        Args:
            bus (int, optional): Bus number. Defaults to 0.
            device (int, optional): Device number / address. Defaults to 0
        """

    @abstractmethod
    def _read(self, address: int, length: int) -> bytes:
        """Read data from a SigmaDSP.

        Args:
            address (int): Address to read from
            length (int): Number of bytes to read

        Returns:
            bytes: Data that was read from the DSP
        """

    @abstractmethod
    def _write(self, address: int, data: bytes):
        """Write data onto a SigmaDSP.

        Args:
            address (int): Address to write to
            data (bytes): Data to write
        """
