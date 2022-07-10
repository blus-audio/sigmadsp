"""This module implements the base class for I2C and SPI communication handlers."""
import logging
import threading
from abc import ABC, abstractmethod
from multiprocessing import Queue

from sigmadsp.sigmastudio.common import ReadRequest, WriteRequest

# A logger for this module
logger = logging.getLogger(__name__)


class DspProtocol(ABC):
    """Base class for communication handlers talking to SigmaDSP chipsets."""

    def run(self):
        """Start the DSP protocol thread."""
        # Generate queues, for communicating with the protocol handler thread within this class.
        self.transmit_queue = Queue()
        self.receive_queue = Queue()

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
        self.transmit_queue.put(WriteRequest(address, data))

    def read(self, address: int, length: int) -> bytes:
        """Read data from the hardware interface via the pipe to the hardware thread.

        Args:
            address (int): DSP register address to read from
            length (int): Number of bytes to read

        Returns:
            bytes: Register content
        """
        self.transmit_queue.put(ReadRequest(address, length))
        return self.receive_queue.get()

    def serve_forever(self):
        """Handle incoming requests for writing or reading data."""
        while True:
            try:
                request = self.transmit_queue.get()

            except EOFError:
                break

            if isinstance(request, WriteRequest):
                self._write(request.address, request.data)

            elif isinstance(request, ReadRequest):
                data = self._read(request.address, request.length)

                try:
                    self.receive_queue.put(data)

                except EOFError:
                    break

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
    def _write(self, address: int, data: bytes) -> int:
        """Write data onto a SigmaDSP.

        Args:
            address (int): Address to write to
            data (bytes): Data to write

        Returns:
            int: Number of written bytes.
        """
