"""A mockup for Sigma Studio, for testing the backend."""

import logging
import socket
import sys
import time

logger = logging.getLogger(__name__)


class SigmaTcpClient:
    """Attempts to replicate the TCP client behavior of SigmaStudio."""

    def __init__(self, ip: str = "localhost", port: int = 8087):
        """Initialize the SigmaStudio TCP client.

        Args:
            ip (str, optional): The IP address to connect to. Defaults to "localhost".
            port (int, optional): The port to connect over. Defaults to 8087.
        """
        try:
            self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        except OSError:
            logger.error("Failed to create socket.")
            sys.exit()

        while True:
            try:
                self.s.connect((ip, port))

            except OSError:
                logger.warning("Could not connect to socket.")
                time.sleep(0.01)

            else:
                break

        logger.info("Connection established.")

    def write(self, payload: bytes):
        """Write payload to the socket.

        Args:
            payload (bytes): The payload to write.
        """
        self.s.sendall(payload)
