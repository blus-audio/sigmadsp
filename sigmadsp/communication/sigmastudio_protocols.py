"""This module contains implementations for SigmaStudio TCPIP* protocol decoding.

These handle the packet decoding and conditioning, while actual communication happens upstream.

Protocol headers for ADAU144x/5x/6x are documented on the Analog Devices wiki at
https://wiki.analog.com/resources/tools-software/sigmastudio/usingsigmastudio/tcpipchannels

Protocol headers for ADAU1401/1701 are documented on the Analog Devices forum at
https://ez.analog.com/dsp/sigmadsp/f/q-a/163849/adau1401-adau1701-tcp-ip-documentation-unonficial-self-made
"""
import socket
from abc import ABC
from typing import Dict, Tuple, Type, Union

from sigmadsp.helper.conversion import bytes_to_int, int_to_bytes


class SigmaProtocolHeader(ABC):
    """Base class for protocol headers."""

    READ_REQUEST: int = 0x0A
    READ_RESPONSE: int = 0x0B
    WRITE: int = 0x09

    # field configuration
    fields: Dict[str, Tuple[int, int]]

    # field values
    field_values: Dict[str, int]

    def __init__(self):
        """Initialize field values."""
        self.field_values = {}
        for field in self.fields:
            self.field_values[field] = 0

    @property
    def length(self) -> int:
        """Get the total header size.

        Returns:
            int: The header size.
        """
        if not hasattr(self, "__length"):
            self.__length = sum([size for offset, size in self.fields.values()])

        return self.__length

    @property
    def has_payload(self) -> bool:
        """Whether this kind of packet carryies a payload.

        Returns:
            bool: True if this is a write / read response, False otherwise.
        """
        return self.field_values["operation"] in [self.WRITE, self.READ_RESPONSE]

    @property
    def is_write_request(self) -> bool:
        """Whether this is a write request.

        Returns:
            bool: True if this is a write.
        """
        return self.field_values["operation"] == self.WRITE

    @property
    def is_safeload(self) -> bool:
        """Whether this is a safeload write request.

        Returns:
            bool: True if this is a safeload request.
        """
        return self.field_values["operation"] == self.WRITE and self.field_values["safeload"] == 1

    @property
    def is_read_request(self) -> bool:
        """Whether this is a read request.

        Returns:
            bool: True if this is a read request.
        """
        return self.field_values["operation"] == self.READ_REQUEST

    @property
    def is_read_response(self) -> bool:
        """Whether this is a read response.

        Returns:
            bool: True if this is a read response.
        """
        return self.field_values["operation"] == self.READ_RESPONSE

    @property
    def as_bytes(self) -> bytearray:
        """Return the bytes representation of the current header.

        Returns:
            bytearray: the assembled header
        """
        buffer = bytearray(self.length)

        for name, (offset, size) in self.fields.items():
            int_to_bytes(self.field_values[name], buffer, offset, size)

        return buffer

    def parse(self, data: bytes):
        """Parse a header and populate field values.

        Args:
            data (bytes): The data to parse.
        """
        if len(data) != self.length:
            raise ValueError(f"Input data needs to be exactly {self.length} bytes long!")

        for name, (offset, size) in self.fields.items():
            self.field_values[name] = bytes_to_int(data, offset, size)

    def __setitem__(self, name: str, value: int):
        """Set a field value.

        Args:
            name (str): Field name.
            value (int): Field value.
        """
        valid_names = self.fields.keys()
        if name not in valid_names:
            raise ValueError(f"Invalid field name {name}; valid names are {', '.join(valid_names)}")

        self.field_values[name] = value

    def __getitem__(self, name: str) -> int:
        """Get a field value.

        Args:
            name (str): Field name.

        Returns:
            int: The field value.
        """
        return self.field_values[name]


_REGISTRY: Dict[int, Dict[str, Type[SigmaProtocolHeader]]] = {}


def _register(operation: int, chip_type: str, header_class: Type[SigmaProtocolHeader]):
    """Add a class to the header registry for the given operation and chip type.

    Args:
        operation (int): The operation code.
        chip_type (str): Chip type.
        header_class (Type[SigmaProtocolHeader]): Header class.
    """
    if operation not in _REGISTRY:
        _REGISTRY[operation] = {}

    _REGISTRY[operation][chip_type] = header_class


def _get_header(dsp_type: str, operation: int) -> SigmaProtocolHeader:
    """Select the appropriate header class for the chip type and operation requested.

    Args:
        dsp_type (str): One of the supported DSP types.
        operation (int): The operation code.

    Returns:
        SigmaProtocolHeader: The header object.
    """
    if operation not in _REGISTRY:
        valid_opcodes = ", ".join([f"0x{op:02x}" for op in _REGISTRY])
        raise ValueError(f"Invalid operation 0x{operation:02x}; valid operations are {valid_opcodes}.")

    if dsp_type not in _REGISTRY[operation]:
        raise ValueError(f"DSP type {dsp_type} is not supported.")

    header = _REGISTRY[operation][dsp_type]()
    header["operation"] = operation
    return header


class Adau1701WriteHeader(SigmaProtocolHeader):
    """Write header for the TCPIP1701 protocol.

    This is used for ADAU1701 and ADAU1401.
    """

    fields = {
        "operation": (0, 1),
        "safeload": (1, 1),
        "channel": (2, 1),
        "total_length": (3, 2),
        "chip_address": (5, 1),
        "data_length": (6, 2),
        "address": (8, 2),
    }


class Adau1701ReadRequestHeader(SigmaProtocolHeader):
    """Read request header for the TCPIP1701 protocol.

    This is used for ADAU1701 and ADAU1401 chips.
    """

    fields = {
        "operation": (0, 1),
        "total_length": (1, 2),
        "chip_address": (3, 1),
        "data_length": (4, 2),
        "address": (6, 2),
    }


class Adau1701ReadResponseHeader(SigmaProtocolHeader):
    """Read response header for the TCPIP1701 protocol.

    This is used for ADAU1701 and ADAU1401.
    """

    fields = {
        "operation": (0, 1),
        "total_length": (1, 2),
        "success": (3, 1),
    }


_register(SigmaProtocolHeader.WRITE, "adau1701", Adau1701WriteHeader)
_register(SigmaProtocolHeader.READ_REQUEST, "adau1701", Adau1701ReadRequestHeader)
_register(SigmaProtocolHeader.READ_RESPONSE, "adau1701", Adau1701ReadResponseHeader)


class Adau145xWriteHeader(SigmaProtocolHeader):
    """Write header for the TCPIPADAU144x/5x/6x protocols.

    This is presumably used for ADAU144x, ADAU145x and ADAU146x chips.
    """

    fields = {
        "operation": (0, 1),
        "safeload": (1, 1),
        "channel": (2, 1),
        "total_length": (3, 4),
        "chip_address": (7, 1),
        "data_length": (8, 4),
        "address": (12, 2),
    }


class Adau145xReadRequestHeader(SigmaProtocolHeader):
    """Read request header for the TCPIPADAU144x/5x/6x protocols.

    This is presumably used for ADAU144x, ADAU145x and ADAU146x chips.
    """

    fields = {
        "operation": (0, 1),
        "total_length": (1, 4),
        "chip_address": (5, 1),
        "data_length": (6, 4),
        "address": (10, 2),
        "reserved": (12, 2),
    }


class Adau145xReadResponseHeader(SigmaProtocolHeader):
    """Read response header for the TCPIPADAU144x/5x/6x protocols.

    This is presumably used for ADAU144x, ADAU145x and ADAU146x chips.
    """

    fields = {
        "operation": (0, 1),
        "total_length": (1, 4),
        "chip_address": (5, 1),
        "data_length": (6, 4),
        "address": (10, 2),
        "success": (12, 1),
        "reserved": (13, 1),
    }


_register(SigmaProtocolHeader.WRITE, "adau144x", Adau145xWriteHeader)
_register(SigmaProtocolHeader.READ_REQUEST, "adau144x", Adau145xReadRequestHeader)
_register(SigmaProtocolHeader.READ_RESPONSE, "adau144x", Adau145xReadResponseHeader)
_register(SigmaProtocolHeader.WRITE, "adau145x", Adau145xWriteHeader)
_register(SigmaProtocolHeader.READ_REQUEST, "adau145x", Adau145xReadRequestHeader)
_register(SigmaProtocolHeader.READ_RESPONSE, "adau145x", Adau145xReadResponseHeader)
_register(SigmaProtocolHeader.WRITE, "adau146x", Adau145xWriteHeader)
_register(SigmaProtocolHeader.READ_REQUEST, "adau146x", Adau145xReadRequestHeader)
_register(SigmaProtocolHeader.READ_RESPONSE, "adau146x", Adau145xReadResponseHeader)


class SigmaProtocolPacket:
    """Communication packet for talking to SigmaStudio.

    This class handles all of the payload decoding / encoding.
    """

    dsp_type: str
    header: SigmaProtocolHeader
    payload: bytearray

    def __init__(self, dsp_type):
        """Initialize the packet.

        Args:
            dsp_type (str): DSP type.
        """
        self.dsp_type = dsp_type

    def init_from_payload(self, operation: int, payload: bytearray, header_defaults: Union[dict, None] = None):
        """Initialize the packet with a new header and the provided payload.

        Args:
            operation (int): Operation code; most often SigmaStudioPacket.READ_RESPONSE
            payload (bytearray): Payload.
            header_defaults (dict): Default values for header fields; useful when setting chip address, etc. from the
                                    request headers
        """
        self.header = _get_header(self.dsp_type, operation)
        self.payload = payload
        self.header["total_length"] = self.header.length + len(payload)

        # adau145x and friends have some additional response fields
        if "data_length" in self.header.fields:
            self.header["data_length"] = len(payload)

        if header_defaults is None:
            return

        for field in self.header.fields:
            if field in ["operation", "total_length", "data_length", "success"]:
                continue

            self.header[field] = header_defaults.get(field, 0)

    def init_from_network(self, connection: socket.socket):
        """Fetch data from a socket.

        Args:
            connection (socket): Socket to use.
        """
        # first get the operation code
        header_bytes: bytearray = self.read(connection, 1)

        # get the appropriate header object
        self.header = _get_header(self.dsp_type, header_bytes[0])

        # finally, read the rest of the header and parse it
        header_bytes.extend(self.read(connection, self.header.length - 1))
        self.header.parse(header_bytes)

        if self.header.is_write_request:
            # we have a payload
            self.payload = self.read(connection, self.header["data_length"])

    def read(self, connection: socket.socket, amount: int) -> bytearray:
        """Reads the specified amount of data from the socket.

        Args:
            connection (socket.socket): Communication socket for fetching the header data / payload.
            amount (int): The number of bytes to get.

        Returns:
            bytearray: The received data.
        """
        data = bytearray()

        while amount > len(data):
            # Wait until the complete TCP payload was received.
            received = connection.recv(amount - len(data))

            if 0 == len(received):
                # Give up, if no more data arrives.
                # Close the socket.
                connection.shutdown(socket.SHUT_RDWR)
                connection.close()

                raise ConnectionError

            data.extend(received)

        return data

    @property
    def as_bytes(self) -> bytearray:
        """Return the whole packet as a bytearray, ready for sending over the network.

        This also handles all of the math involved in setting up the header.

        Returns:
            bytearray: header and payload combined
        """
        buffer = self.header.as_bytes
        buffer.extend(self.payload)
        return buffer
