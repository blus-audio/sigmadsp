"""This module implements a dummy protocol handler for testing purposes."""
import logging
from typing import Dict, List

from sigmadsp.protocols.common import DspProtocol
from sigmadsp.sigmastudio.common import WriteRequest

# A logger for this module
logger = logging.getLogger(__name__)


class DummyProtocol(DspProtocol):
    """Handle dummy transfers."""

    _write_requests: List[WriteRequest]

    def __init__(self):
        """Initialize the Dummy protocol."""
        self.reset()
        self.run()

    def reset(self):
        """Empty all recorded data."""
        self._memory: Dict[int, bytes] = {}
        self._write_requests: List[WriteRequest] = []

    def _read(self, address: int, length: int) -> bytes:
        """Read dummy data from the internal memory.

        Args:
            address (int): Address to read from
            length (int): Number of bytes to read

        Returns:
            bytes: Data with the required length.
        """
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
        self._memory[address] = data
        self._write_requests.append(WriteRequest(address, data))

    @property
    def write_requests(self) -> List[WriteRequest]:
        """All write requests that were handled."""
        return self._write_requests
