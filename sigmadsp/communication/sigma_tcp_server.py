"""This module communicates with SigmaStudio.

It can receive read/write requests and return with read response packets.
"""
import logging
import socket
import socketserver
import threading
from multiprocessing import Pipe
from typing import Type

from sigmadsp.communication.base import (
    ReadRequest,
    SafeloadRequest,
    ThreadedTCPServer,
    WriteRequest,
)
from sigmadsp.communication.sigmastudio_protocols import (
    SigmaProtocolHeader,
    SigmaProtocolPacket,
)

# A logger for this module
logger = logging.getLogger(__name__)


class SigmaStudioRequestHandler(socketserver.BaseRequestHandler):
    """Request handler for messages from SigmaStudio."""

    request: socket.socket
    server: ThreadedTCPServer
    dsp_type: str

    def read(self, amount: int) -> bytearray:
        """Reads the specified amount of data from the socket.

        Args:
            amount (int): The number of bytes to get.

        Returns:
            bytearray: The received data.
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

        return data

    def handle_write_data(self, packet: SigmaProtocolPacket):
        """Handle requests, where SigmaStudio wants to write to the DSP.

        Args:
            packet (SigmaProtocolPacket): The request packet object.
        """
        request: WriteRequest

        if packet.header.is_safeload:
            logger.info("[safeload] %s bytes to address 0x%04x", packet.header["data_length"], packet.header["address"])
            request = SafeloadRequest(packet.header["address"], packet.payload)
        else:
            logger.info("[write] %s bytes to address 0x%04x", packet.header["data_length"], packet.header["address"])
            request = WriteRequest(packet.header["address"], packet.payload)

        self.server.pipe_end_owner.send(request)

    def handle_read_request(self, packet: SigmaProtocolPacket):
        """Handle requests, where SigmaStudio wants to read from the DSP.

        Args:
            packet (SigmaProtocolPacket): The request header object.
        """
        logger.info("[read] %s bytes from address 0x%04x", packet.header["data_length"], packet.header["address"])

        # Notify application of read request
        self.server.pipe_end_owner.send(ReadRequest(packet.header["address"], packet.header["data_length"]))

        # Wait for payload data that goes into the read response
        read_response = self.server.pipe_end_owner.recv()

        header_defaults = packet.header.fields

        response_packet = SigmaProtocolPacket(self.dsp_type)
        response_packet.init_from_payload(SigmaProtocolHeader.READ_RESPONSE, read_response.data, header_defaults)
        response_packet.header["success"] = 0

        self.request.sendall(response_packet.as_bytes)

    def handle(self):
        """Call, when the TCP server receives new data for handling.

        It never stops, except if the connection is reset.
        """
        while True:
            try:
                packet: SigmaProtocolPacket = SigmaProtocolPacket(self.dsp_type)
                packet.init_from_network(self)

                if packet.header.is_write_request:
                    self.handle_write_data(packet)
                elif packet.header.is_read_request:
                    self.handle_read_request(packet)

            except ConnectionError:
                break


class Adau14xxRequestHandler(SigmaStudioRequestHandler):
    """ADAU144x/5x/6x request handler."""

    dsp_type = "adau14xx"


class Adau1701RequestHandler(SigmaStudioRequestHandler):
    """ADAU1701 request handler."""

    dsp_type = "adau1701"


class SigmaStudioInterface:
    """This is an interface class for communicating with SigmaStudio.

    It creates a TCP server, which SigmaStudio talks to.
    """

    def __init__(self, host: str, port: int, dsp_type: str):
        """Initialize the SigmaStudio interface.

        Starts the main TCP worker and initializes a pipe for communicating with the sigmadsp backend.

        Args:
            host (str): Listening IP address
            port (int): Port to listen at
            dsp_type (str): DSP type, used to select the relevant protocol handler
        """
        self.host = host
        self.port = port
        self.dsp_type = dsp_type

        # Generate a Pipe for communicating with the TCP server worker thread within this class.
        self.pipe_end_owner, self.pipe_end_user = Pipe()

        tcp_server_worker_thread = threading.Thread(target=self.tcp_server_worker, name="TCP server worker thread")
        tcp_server_worker_thread.daemon = True
        tcp_server_worker_thread.start()

    def tcp_server_worker(self):
        """The main worker for the TCP server."""
        protocol_handler: Type[SigmaStudioRequestHandler]

        if self.dsp_type == "adau14xx":
            protocol_handler = Adau14xxRequestHandler

        elif self.dsp_type == "adau1701":
            protocol_handler = Adau1701RequestHandler

        else:
            raise TypeError(f"The specified DSP type {self.dsp_type} is not supported.")

        tcp_server = ThreadedTCPServer((self.host, self.port), protocol_handler)

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
