"""This module contains the common classes for SigmaStudio protocol handling."""
from dataclasses import dataclass


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


# SigmaStudio disconnected from the server.
CONNECTION_CLOSED = None
