"""This module implements an SPI handler that talks to Sigma DSP devices."""
import logging

import spidev  # type: ignore

from .common import DspProtocol

# A logger for this module
logger = logging.getLogger(__name__)


def build_spi_frame(address: int, data: bytes) -> bytearray:
    """Build an SPI frame that is later written to the DSP.

    Args:
        address (int): The register address that the data is written to
        data (bytes): The register content

    Returns:
        bytearray: The complete SPI frame buffer
    """
    frame = bytearray(SpiProtocol.HEADER_LENGTH)
    frame[0] = SpiProtocol.WRITE
    frame[1:3] = address.to_bytes(SpiProtocol.ADDRESS_LENGTH, "big")
    frame += data

    return frame


class SpiProtocol(DspProtocol):
    """Handle SPI transfers from and to SigmaDSP chipsets.

    Tested with ADAU145X
    """

    # Length of addresses (in bytes) for accessing registers
    ADDRESS_LENGTH = 2

    # Length of the SPI header for communicating with SigmaDSP chipsets
    HEADER_LENGTH = 3

    # Maximum number of bytes per SPI transfer
    MAX_SPI_BYTES = 4096

    # Maximum number of words (32 bit) that can be transferred with the
    # maximum number of allowed bytes per SPI transfer
    MAX_PAYLOAD_WORDS = int((MAX_SPI_BYTES - HEADER_LENGTH) / 4)

    # Derive maximum payload (bytes) from number of maximum words
    MAX_PAYLOAD_BYTES = MAX_PAYLOAD_WORDS * 4

    WRITE = 0
    READ = 1

    def __init__(self, bus: int = 0, device: int = 0):
        """Initialize the SPI hardware.

        Bus and device numbers shall be kept at (0, 0) for RaspberryPi hardware.
        The RaspberryPi only has one SPI peripheral.

        Args:
            bus (int, optional): Bus number. Defaults to 0.
            device (int, optional): Device number. Defaults to 0.
        """
        self._spi = spidev.SpiDev()
        self._spi.open(bus, device)

        # The SigmaDSP allows a maximum SPI transfer speed of 20 MHz.
        # Raspberry Pi hardware allows binary steps (1 MHz, 2 MHz, ...)
        self._spi.max_speed_hz = 16000000

        # The SigmaDSP uses SPI mode 0 with 8 bits per word. Do not change.
        self._spi.mode = 0
        self._spi.bits_per_word = 8

        self.run()

    def _read(self, address: int, length: int) -> bytes:
        """Read data over the SPI port from a SigmaDSP.

        Args:
            address (int): Address to read from
            length (int): Number of bytes to read

        Returns:
            bytes: Data that was read from the DSP
        """
        spi_request = bytearray(length + SpiProtocol.HEADER_LENGTH)
        spi_request[0] = SpiProtocol.READ
        spi_request[1:3] = address.to_bytes(SpiProtocol.ADDRESS_LENGTH, "big")

        # Read, by writing zeros
        spi_response = self._spi.xfer(spi_request)

        return bytes(spi_response[SpiProtocol.HEADER_LENGTH :])

    def _write(self, address: int, data: bytes):
        """Write data over the SPI port onto a SigmaDSP.

        Args:
            address (int): Address to write to
            data (bytes): Data to write
        """
        remaining_data_length = len(data)
        current_address = address
        current_data = data

        while remaining_data_length > 0:
            # There is data remaining for writing

            if remaining_data_length >= SpiProtocol.MAX_PAYLOAD_BYTES:
                # Packet has to be split into smaller chunks,
                # where the write address is advanced accordingly.
                # DSP register addresses are counted in words (32 bit per increment).

                # Build the frame from a subset of the input data, and write it
                frame = build_spi_frame(
                    current_address,
                    current_data[: SpiProtocol.MAX_PAYLOAD_BYTES],
                )
                self._spi.writebytes(frame)

                # Update address, data counter, and the binary data buffer
                current_address += SpiProtocol.MAX_PAYLOAD_WORDS
                remaining_data_length -= SpiProtocol.MAX_PAYLOAD_BYTES
                current_data = current_data[SpiProtocol.MAX_PAYLOAD_BYTES :]

            else:
                # The packet fits into one transmission.
                frame = build_spi_frame(current_address, current_data)
                self._spi.writebytes(frame)
                remaining_data_length = 0
