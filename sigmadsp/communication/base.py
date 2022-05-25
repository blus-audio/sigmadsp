"""This module contains the base classes for SigmaStudio protocol handling."""
import socketserver
from dataclasses import dataclass
from multiprocessing import Pipe


@dataclass(frozen=True)
class WriteRequest:
    """SigmaStudio requests to write data to the DSP."""

    address: int
    data: bytes


class SafeloadRequest(WriteRequest):
    """SigmaStudio requests to write data to the DSP using safeload."""


@dataclass(frozen=True)
class ReadRequest:
    """SigmaStudio requests to read data from the DSP."""

    address: int
    length: int


@dataclass(frozen=True)
class ReadResponse:
    """SigmaStudio is sent a response to its ReadRequest."""

    data: bytes


class ThreadedTCPServer(socketserver.ThreadingTCPServer):
    """The threaded TCP server that is used for communicating with SigmaStudio.

    It will be instantiated by SigmaStudioInterface. General server settings can be adjusted below.
    """

    allow_reuse_address = True

    def __init__(self, *args, **kwargs):
        """Initialize the ThreadedTCPServer with a Pipe for communicating with the TCP server worker thread."""
        self.pipe_end_owner, self.pipe_end_user = Pipe()

        super().__init__(*args, **kwargs)
