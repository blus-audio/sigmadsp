"""This module communicates with SigmaStudio.

It can receive read/write requests and return with read response packets.
"""
import logging
import socket
import socketserver
from multiprocessing import Queue
from typing import Tuple, Type

from sigmadsp.sigmastudio.common import (
    CONNECTION_CLOSED,
    ReadRequest,
    ReadResponse,
    SafeloadRequest,
    WriteRequest,
)

from .header import PacketHeader, PacketHeaderGenerator

# A logger for this module
logger = logging.getLogger(__name__)


class Packet:
    """A packet for data exchange with SigmaStudio."""

    def __init__(self, header: PacketHeader, payload: bytes = bytes()):
        """Initialize a new packet from a header and payload.

        Args:
            header (PacketHeader): The packet header object.
            payload (Union[None, bytes]): The optional payload.
        """
        self._header = header
        self.payload = payload

    @property
    def header(self) -> PacketHeader:
        """The header object of the packet."""
        return self._header

    @property
    def payload(self) -> bytes:
        """The packet payload."""
        return self._payload

    @payload.setter
    def payload(self, new_payload: bytes):
        if self.header["data_length"].value == 0:
            self._payload = new_payload
            self.header["data_length"].value = len(self._payload)

        else:
            assert (
                len(new_payload) == self.header["data_length"].value
            ), "Payload length does not match the expected length."
            self._payload = new_payload

    def as_bytes(self) -> bytes:
        """Get the full packet as a bytes object."""
        return self.header.as_bytes() + self.payload


class SigmaStudioTcpServer(socketserver.TCPServer):
    """The TCP server that is used for communicating with SigmaStudio."""

    allow_reuse_address = True

    def __init__(
        self,
        server_address: Tuple[str, int],
        request_handler_type: Type[socketserver.BaseRequestHandler],
        packet_header_generator: PacketHeaderGenerator,
        send_queue: Queue,
        receive_queue: Queue,
        bind_and_activate=True,
    ):
        """Initialize the ThreadedTCPServer with a Pipe for communicating with the TCP server worker thread.

        Args:
            server_address (Tuple[str, int]): The IP address and port of the server.
            request_handler_type (Type[socketserver.BaseRequestHandler]): The class that handles requests.
            packet_header_generator (PacketHeaderGenerator): A generator for packet headers.
            bind_and_activate (bool, optional): Whether to bind and activate the TCP server. Defaults to True.
            send_queue (Queue): The queue for data to send to SigmaStudio.
            receive_queue (Queue): The queue for data that was received by SigmaStudio.
        """
        self.send_queue = send_queue
        self.receive_queue = receive_queue
        self.packet_header_generator = packet_header_generator

        super().__init__(server_address, request_handler_type, bind_and_activate=bind_and_activate)


class SigmaStudioRequestHandler(socketserver.BaseRequestHandler):
    """Request handler for messages from SigmaStudio."""

    request: socket.socket
    server: SigmaStudioTcpServer

    def read(self, amount: int) -> bytes:
        """Reads the specified amount of data from the socket.

        Args:
            amount (int): The number of bytes to get.

        Returns:
            bytes: The received data.
        """
        data = bytearray()

        while amount > len(data):
            # Wait until the complete TCP payload was received.
            received = self.request.recv(amount - len(data))

            if 0 == len(received):
                # Give up, if no more data arrives.
                # Close the socket.
                self.request.shutdown(socket.SHUT_RDWR)
                self.request.close()

                raise ConnectionError

            data.extend(received)

        return bytes(data)

    def handle_write_request(self, packet: Packet):
        """Handle requests, where SigmaStudio wants to write to the DSP.

        Args:
            packet (Packet): The request packet object.
        """
        request: WriteRequest

        if packet.header.is_safeload:
            logger.debug(
                "[safeload] %s bytes to address 0x%04x",
                packet.header["data_length"].value,
                packet.header["address"].value,
            )
            request = SafeloadRequest(packet.header["address"].value, packet.payload)

        else:
            logger.debug(
                "[write] %s bytes to address 0x%04x", packet.header["data_length"].value, packet.header["address"].value
            )
            request = WriteRequest(packet.header["address"].value, packet.payload)

        self.server.receive_queue.put(request)

    def handle_read_request(self, packet: Packet):
        """Handle requests, where SigmaStudio wants to read from the DSP.

        Args:
            packet (Packet): The request header object.
        """
        logger.debug(
            "[read] %d bytes from address 0x%04x", packet.header["data_length"].value, packet.header["address"].value
        )

        # Notify application of read request
        self.server.receive_queue.put(ReadRequest(packet.header["address"].value, packet.header["data_length"].value))

        # Wait for payload data that goes into the read response
        read_response: ReadResponse = self.server.send_queue.get()

        response_packet = Packet(packet.header, read_response.data)
        response_packet.header["success"] = 0

        self.request.sendall(response_packet.as_bytes())

    def new_packet(self) -> Packet:
        """Create a new packet from a request."""
        # First, get the operation key. It is always the first received byte.
        operation_byte: bytes = self.read(1)
        header = self.server.packet_header_generator.new_header_from_operation_byte(operation_byte)

        # Read the rest of the header.
        remaining_header_bytes = self.read(header.size - 1)
        header.parse(operation_byte + remaining_header_bytes)

        payload: bytes = bytes()
        if header.carries_payload:
            payload = self.read(header["data_length"].value)

        return Packet(header, payload)

    def handle(self):
        """Called, when the TCP server has to handle a request.

        It never stops, except if the connection is reset.
        """
        while True:
            try:
                packet = self.new_packet()

                if packet.header.is_write_request:
                    self.handle_write_request(packet)

                elif packet.header.is_read_request:
                    self.handle_read_request(packet)

            except ConnectionError:
                self.server.receive_queue.put(CONNECTION_CLOSED)
                break


class SigmaStudioRawRequestHandler(SigmaStudioRequestHandler):
    """Raw request handler for messages from SigmaStudio.

    Outputs the raw requests in the shape of ``bytes``.
    """

    request: socket.socket
    server: SigmaStudioTcpServer

    def new_raw_packet(self) -> bytes:
        """Create a new packet from a request."""
        # First, get the operation key. It is always the first received byte.
        operation_byte: bytes = self.read(1)
        header = self.server.packet_header_generator.new_header_from_operation_byte(operation_byte)

        # Read the rest of the header.
        remaining_header_bytes = self.read(header.size - 1)
        header.parse(operation_byte + remaining_header_bytes)

        payload: bytes = bytes()
        if header.carries_payload:
            payload = self.read(header["data_length"].value)

        return operation_byte + remaining_header_bytes + payload

    def handle(self):
        """Called, when the TCP server has to handle a request.

        It never stops, except if the connection is reset.
        """
        while True:
            try:
                packet = self.new_raw_packet()
                self.server.receive_queue.put(packet)

            except ConnectionError:
                self.server.receive_queue.put(CONNECTION_CLOSED)
                break
