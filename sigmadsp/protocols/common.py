"""This module implements the base class for I2C and SPI communication handlers."""

import logging
import threading
from abc import ABC, abstractmethod
from collections.abc import Generator
from multiprocessing import Queue
from typing import Any

from sigmadsp.sigmastudio.common import ReadRequest, WriteRequest

# A logger for this module
logger = logging.getLogger(__name__)


class DspProtocol(ABC):
    """Base class for communication handlers talking to SigmaDSP chipsets."""

    # Length of addresses (in bytes) for accessing DSP registers
    ADDRESS_LENGTH = 2

    transmit_queue: Queue
    receive_queue: Queue

    def run(self):
        """Start the DSP protocol thread."""
        # Generate queues, for communicating with the protocol handler thread within this class.
        self.transmit_queue = Queue()
        self.receive_queue = Queue()

        protocol = self.__class__.__name__

        logger.info("Starting %s handling thread.", protocol)
        self.thread = threading.Thread(target=self.serve_forever, name=f"{protocol} handler thread", daemon=True)
        self.thread.start()

    def writable_data(
        self, address: int, data: bytes, max_payload_size_word: int
    ) -> Generator[tuple[int, bytes], Any, None]:
        """Yields chunks of writable data, according to the interface's capabilities.

        Args:
            address (int): Address to write to.
            data (bytes): Data to write.
            max_payload_size_word (int): The number of words (32 bit) that the interface can transfer at once.

        Returns:
            Generator[tuple[int, bytes], Any, None]: The generator over writable chunks of data.
                Gives tuples of DSP register address and writable binary data.
        """
        remaining_data_size = len(data)
        current_address = address
        current_data = data

        max_payload_size_byte = max_payload_size_word * 4

        while remaining_data_size > 0:
            # There is data remaining for writing

            if remaining_data_size >= max_payload_size_byte:
                # Packet has to be split into smaller chunks,
                # where the write address is advanced accordingly.
                # DSP register addresses are counted in words (32 bit per increment).
                yield current_address, current_data[:max_payload_size_byte]

                # Update address, data counter, and the binary data buffer
                current_address += max_payload_size_word
                remaining_data_size -= max_payload_size_byte
                current_data = current_data[max_payload_size_byte:]

            else:
                # The packet fits into one transmission.
                yield current_address, current_data
                remaining_data_size = 0

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
            address (int): Address to read from.
            length (int): Number of bytes to read.

        Returns:
            bytes: Data that was read from the DSP.
        """

    @abstractmethod
    def _write(self, address: int, data: bytes):
        """Write data onto a SigmaDSP.

        Args:
            address (int): Address to write to.
            data (bytes): Data to write.
        """
