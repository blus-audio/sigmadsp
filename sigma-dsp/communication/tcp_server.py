import socketserver

class ThreadedSigmaTcpRequestHandler(socketserver.BaseRequestHandler):
    """
    Handling class for the Sigma TCP server
    """
    HEADER_LENGTH = 14
    COMMAND_WRITE = 0x09
    COMMAND_READ = 0x0a
    COMMAND_READ_RESPONSE = 0x0b

    def bytes_to_int(self, data: bytes, offset: int, length: int = 1) -> int:
        """Convertes a number of bytes to their integer representation.
        Uses "length" bytes from the "data" input, starting at "offset".

        Args:
            data (bytes): Input bytes
            offset (int): Offset in number of bytes, from the beginning of the data buffer
            length (int, optional): Number of bytes to convert. Defaults to 1.

        Returns:
            int: Integer representation of the input data stream
        """
        return int.from_bytes(data[offset:offset+length], byteorder='big')

    def bytes_to_int8(self, data: bytes, offset: int) -> int:
        """Converts one byte to an 8 bit integer value.

        Args:
            data (bytes): Input byte
            offset (int): Offset in number of bytes, from the beginning of the data buffer

        Returns:
            int: 8 bit integer representation of the input data stream
        """
        return self.bytes_to_int(data, offset, length = 1)

    def bytes_to_int16(self, data: bytes, offset: int) -> int:
        """Converts one byte to a 16 bit integer value.

        Args:
            data (bytes): Input bytes
            offset (int): Offset in number of bytes, from the beginning of the data buffer

        Returns:
            int: 16 bit integer representation of the input data stream
        """
        return self.bytes_to_int(data, offset, length = 2)

    def bytes_to_int32(self, data: bytes, offset: int) -> int:
        """Converts one byte to a 32 bit integer value.

        Args:
            data (bytes): Input bytes
            offset (int): Offset in number of bytes, from the beginning of the data buffer

        Returns:
            int: 32 bit integer representation of the input data stream
        """
        return self.bytes_to_int(data, offset, length = 4)

    def int_to_bytes(self, buffer: bytearray, value: int, offset: int, length: int = 1):
        """Fill a buffer with values

        Args:
            buffer (bytearray): The buffer to fill
            value (int): The value to pack into the buffer
            offset (int): Offset in number of bytes, from the beginning of the data buffer
            length (int): Number of bytes to be written
        """
        buffer[offset:offset+length] = value.to_bytes(length, byteorder='big')

    def int8_to_bytes(self, buffer, value, offset):
        """Fill a buffer with an 8 bit value (1 byte)

        Args:
            buffer (bytearray): The buffer to fill
            value (int): The value to pack into the buffer
            offset (int): Offset in number of bytes, from the beginning of the data buffer
            length (int): Number of bytes to be written
        """
        self.int_to_bytes(buffer, value, offset, length = 1)

    def int16_to_bytes(self, buffer, value, offset):
        """Fill a buffer with a 16 bit value (2 bytes)

        Args:
            buffer (bytearray): The buffer to fill
            value (int): The value to pack into the buffer
            offset (int): Offset in number of bytes, from the beginning of the data buffer
            length (int): Number of bytes to be written
        """
        self.int_to_bytes(buffer, value, offset, length = 2)

    def int32_to_bytes(self, buffer, value, offset):
        """Fill a buffer with a 32 bit value (4 bytes)

        Args:
            buffer (bytearray): The buffer to fill
            value (int): The value to pack into the buffer
            offset (int): Offset in number of bytes, from the beginning of the data buffer
            length (int): Number of bytes to be written
        """
        self.int_to_bytes(buffer, value, offset, length = 4)

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

        block_safeload = self.bytes_to_int8(data, 1)
        channel_number = self.bytes_to_int8(data, 2)

        total_length = self.bytes_to_int32(data, 3)
        chip_address = self.bytes_to_int8(data, 7)
        payload_length = self.bytes_to_int32(data, 8)
        address = self.bytes_to_int16(data, 12)

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
        total_length = self.bytes_to_int32(data, 1)
        chip_address = self.bytes_to_int8(data, 5)
        data_length = self.bytes_to_int32(data, 6)
        address = self.bytes_to_int16(data, 10)

        # Notify application of read request
        self.server.queue.put("read")
        self.server.queue.put((address, data_length))
        self.server.queue.join()

        # Wait for payload data that goes into the read response
        payload_data = self.server.queue.get()

        # Build the read response packet, starting with length calculations ...
        total_transmit_length = ThreadedSigmaTcpRequestHandler.HEADER_LENGTH + data_length
        transmit_data = bytearray(total_transmit_length)

        # ... followed by populating the byte fields.
        self.int8_to_bytes(transmit_data, ThreadedSigmaTcpRequestHandler.COMMAND_READ_RESPONSE, 0)
        self.int32_to_bytes(transmit_data, total_transmit_length, 1)
        self.int8_to_bytes(transmit_data, chip_address, 5)
        self.int32_to_bytes(transmit_data, data_length, 6)
        self.int16_to_bytes(transmit_data, address, 10)

        # Success (0)/failure (1) byte at pos. 12. Always assume success.
        self.int16_to_bytes(transmit_data, 0, 12)

        # Reserved zero byte at pos. 13
        self.int16_to_bytes(transmit_data, 0, 13)

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