"""This module communicates with SigmaStudio.
It can receive read/write requests and return with read response packets.
"""
import multiprocessing
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


@dataclass
class WriteRequest:
    """Helper class for defining a write request.
    A write request consists of a target address and data."""

    address: int
    data: bytes


@dataclass
class ReadRequest:
    """Helper class for defining a read request.
    A read request consists of a read address, and a field length."""

    address: int
    length: int


@dataclass
class ReadResponse:
    """Helper class for defining a read response.
    A read response only contains the data that was read from the read address."""

    data: bytes


class ThreadedSigmaTcpRequestHandler(socketserver.BaseRequestHandler):
    """
    Handling class for the Sigma TCP server
    """

    HEADER_LENGTH = 14
    COMMAND_WRITE = 0x09
    COMMAND_READ = 0x0A
    COMMAND_READ_RESPONSE = 0x0B

    def handle_write_data(self, data):
        """The WRITE command indicates that SigmaStudio intends to write a packet to the DSP.

        block_safeload write    This field indicates whether the packet is a block write or a safeload write
        channel_number          This indicates the channel number
        total_length	        This indicates the total length of the write packet (uint32)
        chip_address	        The address of the chip to which the data has to be written
        payload_length	        The length of the data (uint32)
        address	                The address of the module whose data is being written to the DSP (uint16)
        payload	                The payload data to be written
        """

        # These fields are currently unused
        block_safeload = bytes_to_int8(data, 1)
        channel_number = bytes_to_int8(data, 2)
        total_length = bytes_to_int32(data, 3)
        del block_safeload
        del channel_number
        del total_length

        # The chip address is appended by the read/write bit. Shifting right by one bit removes it.
        # This field is currently unused
        chip_address = bytes_to_int8(data, 7) >> 1
        del chip_address

        payload_length = bytes_to_int32(data, 8)
        address = bytes_to_int16(data, 12)

        missing_payload_length = payload_length

        payload_data = bytearray()
        while missing_payload_length:
            # Wait until the complete TCP payload was received.
            received_data = self.request.recv(missing_payload_length)
            missing_payload_length -= len(received_data)

            payload_data += received_data

        self.server.queue.put(WriteRequest(address, payload_data))

    def handle_read_request(self, data: bytes):
        """The READ command indicates that SigmaStudio intends to read a packet from the DSP.

        total_length	        This indicates the total length of the read packet (uint32)
        chip_address	        The address of the chip from which the data has to be read
        data_length	            The length of the data (uint32)
        address	                The address of the module whose data is being read from the DSP (uint16)
        """

        # Unpack received data
        total_length = bytes_to_int32(data, 1)
        del total_length

        chip_address = bytes_to_int8(data, 5)
        data_length = bytes_to_int32(data, 6)
        address = bytes_to_int16(data, 10)

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
        """This method is called, when the TCP server receives new data for handling. It never stops,
        except if the connection is reset.
        """
        while True:
            missing_header_length = ThreadedSigmaTcpRequestHandler.HEADER_LENGTH
            received_data = bytearray()

            while missing_header_length:
                # Wait until the complete TCP header was received.
                received_data += self.request.recv(missing_header_length)
                missing_header_length -= len(received_data)

            command = received_data[0]

            if command == ThreadedSigmaTcpRequestHandler.COMMAND_WRITE:
                self.handle_write_data(received_data)

            elif command == ThreadedSigmaTcpRequestHandler.COMMAND_READ:
                self.handle_read_request(received_data)

            else:
                print(command)


class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    """The threaded TCP server that is used for communicating with SigmaStudio.
    Here, general server settings can be adjusted."""

    allow_reuse_address = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.queue = multiprocessing.JoinableQueue()


class SigmaTCPServer:
    """This is a helper class for easily filling the queue to the TCP server and reading from it."""

    def __init__(self, host: str, port: int):
        """Initialize the Sigma TCP server. Starts the main TCP worker and initializes a queue for communicating
        with other threads.

        Args:
            host (str): Listening IP address
            port (int): Port to listen at
        """
        self.host = host
        self.port = port
        self.queue = multiprocessing.JoinableQueue()

        tcp_server_worker_thread = threading.Thread(target=self.tcp_server_worker, name="TCP server worker thread")
        tcp_server_worker_thread.daemon = True
        tcp_server_worker_thread.start()

    def get_request(self) -> Union[ReadRequest, WriteRequest]:
        """Get an item from the queue

        Returns:
            Union[ReadRequest, WriteRequest]: The item that was returned from the queue
        """
        request = self.queue.get()
        self.queue.task_done()

        return request

    def put_request(self, request: ReadResponse):
        """Put an item into the queue: blocks, until released with 'task_done()',
        which is called by 'get_request()'.

        Args:
            request (ReadResponse): The request to put into the queue
        """
        self.queue.put(request)
        self.queue.join()

    def tcp_server_worker(self):
        """The main worker for the TCP server"""
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
