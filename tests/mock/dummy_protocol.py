"""This module implements a dummy protocol handler for testing purposes."""
import logging

from sigmadsp.protocols.common import DspProtocol
from sigmadsp.sigmastudio.common import ReadRequest
from sigmadsp.sigmastudio.common import WriteRequest

# A logger for this module
logger = logging.getLogger(__name__)


class DummyProtocol(DspProtocol):
    """Handle dummy transfers."""

    _write_requests: list[WriteRequest]
    _read_requests: list[ReadRequest]

    def __init__(self):
        """Initialize the Dummy protocol."""
        self.reset()
        self.run()

    def reset(self) -> None:
        """Empty all recorded data."""
        self._memory: dict[int, bytes] = {}
        self._write_requests = []
        self._read_requests = []

    def _read(self, address: int, length: int) -> bytes:
        """Read dummy data from the internal memory.

        Args:
            address (int): Address to read from
            length (int): Number of bytes to read

        Returns:
            bytes: Data with the required length.
        """
        self._read_requests.append(ReadRequest(address, length))

        try:
            data = self._memory[address]

        except KeyError:
            return bytes(length)

        else:
            return data[:length]

    def _write(self, address: int, data: bytes):
        """Write dummy data.

        Args:
            address (int): Address to write to
            data (bytes): Data to write
        """
        self._write_requests.append(WriteRequest(address, data))
        self._memory[address] = data

    @property
    def read_requests(self) -> list[ReadRequest]:
        """All read requests that were handled."""
        return self._read_requests

    @property
    def write_requests(self) -> list[WriteRequest]:
        """All write requests that were handled."""
        return self._write_requests
