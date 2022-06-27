"""A mockup for Sigma Studio, for testing the backend."""

import logging
import socket
import sys

logger = logging.getLogger(__name__)

READ_REQUEST: int = 0x0A
READ_RESPONSE: int = 0x0B
WRITE: int = 0x09


class SigmaTcpClient:
    def __init__(self, ip: str = "localhost", port: int = 8087):
        try:
            self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        except socket.error:
            logger.error("Failed to create socket.")
            sys.exit()

        try:
            self.s.connect((ip, port))

        except socket.error:
            logger.error("Could not connect to socket.")

    def read_request(self, payload: bytes) -> bytes:
        self.s.sendall(READ_REQUEST.to_bytes(1, "little"), payload)

        # Get response, and ignore it.
        self.s.recv(1)
        size = int.from_bytes(self.s.recv(4), "little")
        self.s.recv(size - 5)

    def write(self, payload: bytes):
        self.s.sendall(WRITE.to_bytes(1, "little"), payload)
