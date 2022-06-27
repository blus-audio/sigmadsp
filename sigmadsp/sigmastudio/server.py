"""This module communicates with SigmaStudio.

It can receive read/write requests and return with read response packets.
"""
import logging
import socket
import socketserver
import threading
from multiprocessing import Pipe
from typing import Tuple, Type

from sigmadsp.sigmastudio.common import (
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
        return self._payload

    @payload.setter
    def payload(self, new_payload: bytes):
        if self.header["data_length"] == 0:
            self._payload = new_payload
            self.header["data_length"] = len(self._payload)

        else:
            assert len(new_payload) == self.header["data_length"], "Payload length does not match the expected length."
            self._payload = new_payload

    def as_bytes(self) -> bytes:
        """Get the full packet as a bytes object."""
        return self.header.as_bytes() + self.payload


class ThreadedTCPServer(socketserver.ThreadingTCPServer):
    """The threaded TCP server that is used for communicating with SigmaStudio.

    It will be instantiated by SigmaStudioInterface. General server settings can be adjusted below.
    """

    allow_reuse_address = True

    def __init__(
        self,
        server_address: Tuple[str, int],
        request_handler_type: Type[socketserver.BaseRequestHandler],
        packet_header_generator: PacketHeaderGenerator,
        bind_and_activate=True,
    ):
        """Initialize the ThreadedTCPServer with a Pipe for communicating with the TCP server worker thread.

        Args:
            server_address (Tuple[str, int]): The IP address and port of the server.
            request_handler_type (Type[socketserver.BaseRequestHandler]): The class that
            packet_header_generator (PacketHeaderGenerator): A generator for packet headers
            bind_and_activate (bool, optional): Whether to bind and activate the TCP server. Defaults to True.
        """
        self.pipe_end_owner, self.pipe_end_user = Pipe()
        self.packet_header_generator = packet_header_generator

        super().__init__(server_address, request_handler_type, bind_and_activate=bind_and_activate)


class SigmaStudioTcpServer:
    """This is an interface class for communicating with SigmaStudio.

    It creates a TCP server, which SigmaStudio talks to. This server uses a SigmaStudio specific request handler.
    """

    def __init__(self, host: str, port: int, packet_header_generator: PacketHeaderGenerator):
        """Initialize the SigmaStudio interface.

        Starts the main TCP worker and initializes a pipe for communicating with the sigmadsp backend.

        Args:
            host (str): Listening IP address
            port (int): Port to listen at
            packet_header_generator (PacketHeaderGenerator): The packet header generator that is used for generating message headers.
        """
        self.host = host
        self.port = port
        self.packet_header_generator = packet_header_generator

        # Generate a Pipe for communicating with the TCP server worker thread within this class.
        self.pipe_end_owner, self.pipe_end_user = Pipe()

        tcp_server_worker_thread = threading.Thread(target=self.tcp_server_worker, name="TCP server worker thread")
        tcp_server_worker_thread.daemon = True
        tcp_server_worker_thread.start()

    def tcp_server_worker(self):
        """The main worker for the TCP server."""
        tcp_server = ThreadedTCPServer((self.host, self.port), RequestHandler, self.packet_header_generator)

        with tcp_server:
            # Base TCP server thread
            # This initial thread starts one more thread for each request.
            tcp_server_thread = threading.Thread(target=tcp_server.serve_forever, name="TCP server thread")
            tcp_server_thread.daemon = True
            tcp_server_thread.start()

            while True:
                # Wait for a request from the TCP server
                request = tcp_server.pipe_end_user.recv()

                if isinstance(request, WriteRequest):
                    # Write request received, don't do anything else
                    self.pipe_end_owner.send(request)

                elif isinstance(request, SafeloadRequest):
                    # Safeload request received, don't do anything else
                    self.pipe_end_owner.send(request)

                elif isinstance(request, ReadRequest):
                    # Read request received, wait for data to send to PC application
                    self.pipe_end_owner.send(request)

                    read_response = self.pipe_end_owner.recv()

                    # Send read response
                    tcp_server.pipe_end_user.send(read_response)


class RequestHandler(socketserver.BaseRequestHandler):
    """Request handler for messages from SigmaStudio."""

    request: socket.socket
    server: ThreadedTCPServer

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
            logger.info("[safeload] %s bytes to address 0x%04x", packet.header["data_length"], packet.header["address"])
            request = SafeloadRequest(packet.header["address"].value, packet.payload)

        else:
            logger.info("[write] %s bytes to address 0x%04x", packet.header["data_length"], packet.header["address"])
            request = WriteRequest(packet.header["address"].value, packet.payload)

        self.server.pipe_end_owner.send(request)

    def handle_read_request(self, packet: Packet):
        """Handle requests, where SigmaStudio wants to read from the DSP.

        Args:
            packet (Packet): The request header object.
        """
        logger.info(
            "[read] %d bytes from address 0x%04x", packet.header["data_length"].value, packet.header["address"].value
        )

        # Notify application of read request
        self.server.pipe_end_owner.send(ReadRequest(packet.header["address"].value, packet.header["data_length"].value))

        # Wait for payload data that goes into the read response
        read_response: ReadResponse = self.server.pipe_end_owner.recv()

        response_packet = Packet(packet.header, read_response.data)
        response_packet.header["success"] = 0

        self.request.sendall(response_packet.as_bytes())

    def new_packet_from_request(self) -> Packet:
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
                packet = self.new_packet_from_request()

                if packet.header.is_write_request:
                    self.handle_write_request(packet)

                elif packet.header.is_read_request:
                    self.handle_read_request(packet)

            except ConnectionError:
                break
