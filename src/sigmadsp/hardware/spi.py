"""This module implements an SPI handler that talks to Sigma DSP devices
"""
import logging
import multiprocessing
import threading

import spidev


class SpiHandler:
    """Handles SPI transfers from and to SigmaDSP chipsets.
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

    def __init__(self):
        """Initialize the SpiHandler thread"""
        self._initialize_spi()

        self.queue = multiprocessing.JoinableQueue()

        logging.info("Starting SPI handling thread.")
        self.thread = threading.Thread(target=self.serve_forever, name="SPIHandlerThread")
        self.thread.daemon = True
        self.thread.start()

    def _initialize_spi(self, bus: int = 0, device: int = 0):
        """Initialize the SPI hardware.

        Bus and device numbers shall be kept at (0, 0) for RaspberryPi hardware.
        The RaspberryPi only has one SPI peripheral.

        Args:
            bus (int, optional): Bus number. Defaults to 0.
            device (int, optional): Device number. Defaults to 0.
        """
        self.spi = spidev.SpiDev()
        self.spi.open(bus, device)

        # The SigmaDSP allows a maximum SPI transfer speed of 20 MHz.
        # Raspberry Pi hardware allows binary steps (1 MHz, 2 MHz, ...)
        self.spi.max_speed_hz = 16000000

        # The SigmaDSP uses SPI mode 0 with 8 bits per word. Do not change.
        self.spi.mode = 0
        self.spi.bits_per_word = 8

    def write(self, address: int, data: bytes):
        """Write data over the SPI interface via the queue to the SPI thread.

        Args:
            address (int): DSP register address to write to
            data (bytes): Binary data to write
        """
        self.queue.put("write")
        self.queue.put((address, data))
        self.queue.join()

    def read(self, address: int, length: int) -> bytes:
        """Read data from the SPI interface via the queue to the SPI thread.

        Args:
            address (int): DSP register address to read from
            length (int): Number of bytes to read

        Returns:
            bytes: Register content
        """
        self.queue.put("read")
        self.queue.put((address, length))
        self.queue.join()

        data = self.queue.get()
        self.queue.task_done()

        return data

    def serve_forever(self):
        """Handles incoming requests for writing or reading data over SPI"""
        while True:
            mode = self.queue.get()
            self.queue.task_done()

            if mode == "write":
                address, data = self.queue.get()
                self.queue.task_done()

                self._write_spi(address, data)

            elif mode == "read":
                address, length = self.queue.get()
                self.queue.task_done()

                data = self._read_spi(address, length)

                self.queue.put(data)
                self.queue.join()

    def _read_spi(self, address: int, length: int) -> bytes:
        """Read data over the SPI port from a SigmaDSP

        Args:
            address (int): Address to read from
            length (int): Number of bytes to read

        Returns:
            bytes: Data that was read from the DSP
        """
        spi_request = bytearray(length + SpiHandler.HEADER_LENGTH)
        spi_request[0] = SpiHandler.READ
        spi_request[1:3] = address.to_bytes(SpiHandler.ADDRESS_LENGTH, "big")

        # Read, by writing zeros
        spi_response = self.spi.xfer(spi_request)

        return bytes(spi_response[SpiHandler.HEADER_LENGTH :])

    def _build_spi_frame(self, address: int, data: bytes) -> bytearray:
        """Builds an SPI frame that is going to be written to the DSP

        Args:
            address (int): The register address that the data is written to
            data (bytes): The register content

        Returns:
            bytearray: The complete SPI frame buffer
        """
        frame = bytearray(SpiHandler.HEADER_LENGTH)
        frame[0] = SpiHandler.WRITE
        frame[1:3] = address.to_bytes(SpiHandler.ADDRESS_LENGTH, "big")
        frame += data

        return frame

    def _write_spi(self, address: int, data: bytes):
        """Write data over the SPI port onto a SigmaDSP

        Args:
            address (int): Address to write to
            data (bytes): Data to write

        Returns:
            int: Number of bytes written
        """
        remaining_data_length = len(data)
        current_address = address
        current_data = data

        while remaining_data_length > 0:
            # There is data remaining for writing

            if remaining_data_length >= SpiHandler.MAX_PAYLOAD_BYTES:
                # Packet has to be split into smaller chunks, where the write address is advanced accordingly.
                # DSP register addresses are counted in words (32 bit per increment).

                # Build the frame from a subset of the input data, and write it
                frame = self._build_spi_frame(current_address, current_data[: SpiHandler.MAX_PAYLOAD_BYTES])
                self.spi.writebytes(frame)

                # Update address, data counter, and the binary data buffer
                current_address += SpiHandler.MAX_PAYLOAD_WORDS
                remaining_data_length -= SpiHandler.MAX_PAYLOAD_BYTES
                current_data = current_data[SpiHandler.MAX_PAYLOAD_BYTES :]

            else:
                # The packet fits into one transmission.
                frame = self._build_spi_frame(current_address, current_data)
                self.spi.writebytes(frame)
                remaining_data_length = 0
