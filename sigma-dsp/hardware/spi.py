import spidev
import threading
import multiprocessing
import logging

class SpiHandler():
    """Handles SPI transfers from and to SigmaDSP chipsets.
    Tested with ADAU145X
    """
    ADDRESS_LENGTH = 2
    HEADER_LENGTH = 3

    WRITE = 0
    READ = 1

    def __init__(self):
        """Initialize the SpiHandler thread
        """
        self._initialize_spi()
        self.thread = threading.Thread(target=self.serve_forever)
        self.thread.daemon = True
        self.thread.start()
        
        self.queue = multiprocessing.Queue()

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
        self.spi.max_speed_hz = 1000000

        # The SigmaDSP uses SPI mode 0 with 8 bits per word. Do not change.
        self.spi.mode = 0
        self.spi.bits_per_word = 8

    def serve_forever(self):
        """Handles incoming requests for writing or reading data over SPI
        """
        while True:
            mode = self.queue.get()

            if mode == "write":
                address, data = self.in_pipe.recv()
                self.write(address, data)

            if mode == "read":
                address, length = self.in_pipe.recv()
                data = self.read(address, length)
                
                self.queue.put(data)
                self.queue.join()

    def read(self, address: int, length: int) -> bytes:
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

        return bytes(spi_response[SpiHandler.HEADER_LENGTH:])

    def write(self, address: int, data: bytes) -> int:
        """Write data over the SPI port onto a SigmaDSP

        Args:
            address (int): Address to write to
            data (bytes): Data to write

        Returns:
            int: Number of bytes written
        """
        spi_request = bytearray(SpiHandler.HEADER_LENGTH)
        spi_request[0] = SpiHandler.WRITE
        spi_request[1:3] = address.to_bytes(SpiHandler.ADDRESS_LENGTH, "big")
        spi_request += data

        return self.spi.writebytes2(spi_request)
