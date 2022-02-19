import socketserver
from sigmadsp.helper.conversion import bytes_to_int8, bytes_to_int16, bytes_to_int32
from sigmadsp.helper.conversion import int8_to_bytes, int16_to_bytes, int32_to_bytes

class ThreadedSigmaTcpRequestHandler(socketserver.BaseRequestHandler):
    """
    Handling class for the Sigma TCP server
    """
    HEADER_LENGTH = 14
    COMMAND_WRITE = 0x09
    COMMAND_READ = 0x0a
    COMMAND_READ_RESPONSE = 0x0b

    def handle_write_data(self, data):
        """The WRITE command indicates that SigmaStudio intends to write a packet to the DSP.

        block_safeload write    This field indicates whether the packet is going to be a block write or a safeload write
        channel_number          This indicates the channel number
        total_length	        This indicates the total length of the write packet (uint32)
        chip_address	        The address of the chip to which the data has to be written
        payload_length	            The length of the data (uint32)
        address	                The address of the module whose data is being written to the DSP (uint16)
        payload	                The payload data to be written
        """

        block_safeload = bytes_to_int8(data, 1)
        channel_number = bytes_to_int8(data, 2)

        total_length = bytes_to_int32(data, 3)
        chip_address = bytes_to_int8(data, 7)
        payload_length = bytes_to_int32(data, 8)
        address = bytes_to_int16(data, 12)

        missing_payload_length = payload_length

        payload_data = bytearray()
        while missing_payload_length:
            # Wait until the complete TCP payload was received.
            received_data = self.request.recv(missing_payload_length)
            missing_payload_length -= len(received_data)

            payload_data += received_data

        self.server.queue.put("write")
        self.server.queue.put((address, payload_data))
        self.server.queue.join()

    def handle_read_request(self, data: bytes):
        """The READ command indicates that SigmaStudio intends to read a packet from the DSP.

        total_length	        This indicates the total length of the read packet (uint32)
        chip_address	        The address of the chip from which the data has to be read
        data_length	            The length of the data (uint32)
        address	                The address of the module whose data is being read from the DSP (uint16)
        """

        # Unpack received data
        total_length = bytes_to_int32(data, 1)
        chip_address = bytes_to_int8(data, 5)
        data_length = bytes_to_int32(data, 6)
        address = bytes_to_int16(data, 10)

        # Notify application of read request
        self.server.queue.put("read")
        self.server.queue.put((address, data_length))
        self.server.queue.join()

        # Wait for payload data that goes into the read response
        payload_data = self.server.queue.get()
        self.server.queue.task_done()

        # Build the read response packet, starting with length calculations ...
        total_transmit_length = ThreadedSigmaTcpRequestHandler.HEADER_LENGTH + data_length
        transmit_data = bytearray(total_transmit_length)

        # ... followed by populating the byte fields.
        int8_to_bytes(ThreadedSigmaTcpRequestHandler.COMMAND_READ_RESPONSE, transmit_data, 0)
        int32_to_bytes(total_transmit_length, transmit_data, 1)
        int8_to_bytes(chip_address, transmit_data, 5)
        int32_to_bytes(data_length, transmit_data, 6)
        int16_to_bytes(address, transmit_data, 10)

        # Success (0)/failure (1) byte at pos. 12. Always assume success.
        int16_to_bytes(0, transmit_data, 12)

        # Reserved zero byte at pos. 13
        int16_to_bytes(0, transmit_data, 13)

        transmit_data[ThreadedSigmaTcpRequestHandler.HEADER_LENGTH:] = payload_data

        self.request.sendall(transmit_data)

    def handle(self):
        """This method is called, when the TCP server receives new data for handling
        """
        while True:
            missing_header_length = ThreadedSigmaTcpRequestHandler.HEADER_LENGTH
            data = bytearray()

            while missing_header_length:
                # Wait until the complete TCP header was received.
                received_data = self.request.recv(missing_header_length)
                missing_header_length -= len(received_data)

                data += received_data
            
            command = data[0]

            if command == ThreadedSigmaTcpRequestHandler.COMMAND_WRITE:
                self.handle_write_data(data)

            elif command == ThreadedSigmaTcpRequestHandler.COMMAND_READ:
                self.handle_read_request(data)

            else:
                print(command)

class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True