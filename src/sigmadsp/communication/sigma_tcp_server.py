"""This module communicates with SigmaStudio.

It can receive read/write requests and return with read response packets.
"""
import logging
import multiprocessing
import socket
import socketserver
import threading
from dataclasses import dataclass
from typing import Union

from sigmadsp.helper.conversion import (
    bytes_to_int8,
    bytes_to_int16,
    bytes_to_int32,
    int8_to_bytes,
    int16_to_bytes,
    int32_to_bytes,
)


@dataclass(frozen=True)
class WriteRequest:
    """SigmaStudio requests to write data to the DSP."""

    address: int
    data: bytes


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

    It will be instantiated by SigmaTCPServer. Here, general server settings can be adjusted.
    """

    allow_reuse_address = True

    def __init__(self, *args, **kwargs):
        """Initialize the ThreadedTCPServer."""
        self.queue: multiprocessing.JoinableQueue = multiprocessing.JoinableQueue()

        super().__init__(*args, **kwargs)


class ThreadedSigmaTcpRequestHandler(socketserver.BaseRequestHandler):
    """Handling class for the Sigma TCP server."""

    request: socket.socket
    server: ThreadedTCPServer

    HEADER_LENGTH: int = 14
    COMMAND_WRITE: int = 0x09
    COMMAND_READ: int = 0x0A
    COMMAND_READ_RESPONSE: int = 0x0B

    def receive_amount(self, total_size: int) -> bytearray:
        """Receives data from a request, until the desired size is reached.

        Args:
            total_size (int): The payload size in bytes to get.

        Returns:
            bytearray: The received data.
        """
        payload_data = bytearray()

        while total_size > len(payload_data):
            # Wait until the complete TCP payload was received.
            received = self.request.recv(total_size - len(payload_data))

            if 0 == len(received):
                # Give up, if no more data arrives.
                # Close the socket.
                self.request.shutdown(socket.SHUT_RDWR)
                self.request.close()

                raise ConnectionError

            payload_data.extend(received)

        return payload_data

    def handle_write_data(self, packet_header: bytes):
        """Handle requests, where SigmaStudio wants to write to the DSP.

        Args:
            packet_header (bytes): The binary request header, as received from SigmaStudio.
        """
        # This field indicates whether the packet is a block write or a safeload write.
        # TODO: This field is currently unused.
        block_safeload = bytes_to_int8(packet_header, 1)
        del block_safeload

        # This indicates the channel number.
        # TODO: This field is currently unused.
        channel_number = bytes_to_int8(packet_header, 2)
        del channel_number

        # This indicates the total length of the write packet (uint32).
        # This field is currently unused.
        total_length = bytes_to_int32(packet_header, 3)
        del total_length

        # The address of the chip to which the data has to be written.
        # The chip address is appended by the read/write bit: shifting right by one bit removes it.
        # TODO: This field is currently unused.
        chip_address = bytes_to_int8(packet_header, 7) >> 1
        del chip_address

        # The length of the data (uint32).
        total_payload_size = bytes_to_int32(packet_header, 8)

        # The address of the module whose data is being written to the DSP (uint16).
        address = bytes_to_int16(packet_header, 12)

        payload_data = self.receive_amount(total_payload_size)

        self.server.queue.put(WriteRequest(address, payload_data))

    def handle_read_request(self, packet_header: bytes):
        """Handle requests, where SigmaStudio wants to read from the DSP.

        Args:
            packet_header (bytes): The binary request header, as received from SigmaStudio.
        """
        # This indicates the total length of the read packet (uint32)
        total_length = bytes_to_int32(packet_header, 1)
        del total_length

        # The address of the chip from which the data has to be read
        chip_address = bytes_to_int8(packet_header, 5)

        # The length of the data (uint32)
        data_length = bytes_to_int32(packet_header, 6)

        # The address of the module whose data is being read from the DSP (uint16)
        address = bytes_to_int16(packet_header, 10)

        # Notify application of read request
        self.server.queue.put(ReadRequest(address, data_length))
        self.server.queue.join()

        # Wait for payload data that goes into the read response
        read_response = self.server.queue.get()

        payload_data = read_response.data

        # Build the read response packet, starting with length calculations ...
        total_transmit_length = ThreadedSigmaTcpRequestHandler.HEADER_LENGTH + data_length
        transmit_data = bytearray(total_transmit_length)

        # ... followed by populating the byte fields.
        int8_to_bytes(
            ThreadedSigmaTcpRequestHandler.COMMAND_READ_RESPONSE,
            transmit_data,
            0,
        )
        int32_to_bytes(total_transmit_length, transmit_data, 1)
        int8_to_bytes(chip_address, transmit_data, 5)
        int32_to_bytes(data_length, transmit_data, 6)
        int16_to_bytes(address, transmit_data, 10)

        # Success (0)/failure (1) byte at pos. 12. Always assume success.
        int16_to_bytes(0, transmit_data, 12)

        # Reserved zero byte at pos. 13
        int16_to_bytes(0, transmit_data, 13)

        transmit_data[ThreadedSigmaTcpRequestHandler.HEADER_LENGTH :] = payload_data

        self.request.sendall(transmit_data)
        self.server.queue.task_done()

    def handle(self):
        """Call, when the TCP server receives new data for handling.

        It never stops, except if the connection is reset.
        """
        while True:
            try:
                # Receive the packet header in the beginning.
                packet_header = self.receive_amount(ThreadedSigmaTcpRequestHandler.HEADER_LENGTH)

                # The first byte of the header contains the command from SigmaStudio.
                command = packet_header[0]

                if command == ThreadedSigmaTcpRequestHandler.COMMAND_WRITE:
                    self.handle_write_data(packet_header)

                elif command == ThreadedSigmaTcpRequestHandler.COMMAND_READ:
                    self.handle_read_request(packet_header)

                else:
                    logging.info("Received an unknown command code '%s'.", hex(command))

            except ConnectionError:
                break


class SigmaTCPServer:
    """This is a helper class for easily filling the queue to the TCP server and reading from it."""

    def __init__(self, host: str, port: int):
        """Initialize the Sigma TCP server.

        Starts the main TCP worker and initializes a queue for communicating to other threads.

        Args:
            host (str): Listening IP address
            port (int): Port to listen at
        """
        self.host = host
        self.port = port
        self.queue: multiprocessing.JoinableQueue = multiprocessing.JoinableQueue()

        tcp_server_worker_thread = threading.Thread(target=self.tcp_server_worker, name="TCP server worker thread")
        tcp_server_worker_thread.daemon = True
        tcp_server_worker_thread.start()

    def get_request(self) -> Union[ReadRequest, WriteRequest]:
        """Get an item from the queue.

        Returns:
            Union[ReadRequest, WriteRequest]: The item that was returned from the queue
        """
        request = self.queue.get()
        self.queue.task_done()

        return request

    def put_request(self, request: ReadResponse):
        """Put an item into the queue: blocks, until released with 'task_done()', which is called by 'get_request()'.

        Args:
            request (ReadResponse): The request to put into the queue
        """
        self.queue.put(request)
        self.queue.join()

    def tcp_server_worker(self):
        """The main worker for the TCP server."""
        tcp_server = ThreadedTCPServer((self.host, self.port), ThreadedSigmaTcpRequestHandler)

        with tcp_server:
            # Base TCP server thread
            # This initial thread starts one more thread for each request.
            tcp_server_thread = threading.Thread(target=tcp_server.serve_forever, name="TCP server thread")
            tcp_server_thread.daemon = True
            tcp_server_thread.start()

            while True:
                # Wait for a request from the TCP server
                request = tcp_server.queue.get()
                tcp_server.queue.task_done()

                if isinstance(request, WriteRequest):
                    # Write request received, don't do anything else
                    self.queue.put(request)
                    self.queue.join()

                elif isinstance(request, ReadRequest):
                    # Read request received, wait for data to send to PC application
                    self.queue.put(request)
                    self.queue.join()

                    read_response = self.queue.get()
                    self.queue.task_done()

                    # Send read response
                    tcp_server.queue.put(read_response)
                    tcp_server.queue.join()
