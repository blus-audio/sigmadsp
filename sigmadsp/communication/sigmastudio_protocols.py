"""This module contains implementations for SigmaStudio TCPIP* protocol decoding.

These handle the packet decoding and conditioning, while actual communication happens upstream.

Protocol headers for ADAU144x/5x/6x are documented on the Analog Devices wiki at
https://wiki.analog.com/resources/tools-software/sigmastudio/usingsigmastudio/tcpipchannels

Protocol headers for ADAU1401/1701 are documented on the Analog Devices forum at
https://ez.analog.com/dsp/sigmadsp/f/q-a/163849/adau1401-adau1701-tcp-ip-documentation-unonficial-self-made
"""
from abc import ABC
from collections import OrderedDict
from dataclasses import dataclass
from typing import TYPE_CHECKING, Dict, Iterator, List, Type, Union

from sigmadsp.helper.conversion import bytes_to_int, int_to_bytes

if TYPE_CHECKING:
    # avoid circular import
    from sigmadsp.communication.sigma_tcp_server import SigmaStudioRequestHandler


@dataclass
class Field:
    """A class that represents a field in a protocol header."""

    # The name of the field, e.g. "operation", "safeload", "channel".
    name: str

    # The offset of the field in bytes from the start of the header.
    offset: int

    # The size of the field in bytes.
    size: int

    # The stored value.
    value: int = 0

    def __post_init__(self):
        """Perform sanity checks on the field properties."""
        if self.size < 0:
            raise ValueError("Field size must be a positive integer.")

        if self.offset < 0:
            raise ValueError("Field offset must be a positive integer.")

        # The last byte index that is occupied by this field.
        self.end = self.offset + self.size - 1

    def __hash__(self) -> int:
        """Hash functionality."""
        return hash((self.name, self.offset, self.size))


class Fields:
    """An iterable collection of Field objects."""

    def __init__(self, fields: List[Field]):
        """Initialize the header fields. Add more fields to it by means of `add()`.

        Instantiate via:
        Fields(
            [
                Field("field_name", 0, 4),
                Field("next_field_name", 4, 1),
                # ...
            ]
        )

        Args:
            fields (List[Field]): The list of fields to add initially.
        """
        self._fields: OrderedDict[str, Field] = OrderedDict()  # pylint: disable=E1136

        for field in fields:
            self.add_field(field)

    @property
    def size(self) -> int:
        """The total size of the header in bytes."""
        return sum([field.size for field in self])

    @property
    def is_continuous(self) -> bool:
        """Whether or not there are spaces in the header that are not defined."""
        fields_entries = self.as_list()

        for field, next_field in zip(fields_entries, fields_entries[1:]):
            if (field.end + 1) != next_field.offset:
                return False

        return True

    def _check_for_overlaps(self):
        """Check for overlapping fields.

        Raises:
            MemoryError: If overlapping fields are found.
        """
        fields_entries = self.as_list()

        # Check for overlapping fields, which are sorted by their offset.
        for field, next_field in zip(fields_entries, fields_entries[1:]):
            if not field.end <= next_field.offset:
                raise MemoryError("Fields {field.name} and {next_field.name} overlap.")

    def _sort_fields_by_offset(self):
        """Sorts the fields in this header by their offset."""
        self._fields = OrderedDict(sorted(self._fields.items(), key=lambda item: item[1].offset))

    def add_field(self, field: Field):
        """Add a new field. Duplicates are ignored.

        Args:
            field (Field): The field to add.
        """
        if field not in self:
            self._fields[field.name] = field

            self._sort_fields_by_offset()
            self._check_for_overlaps()

    def as_bytes(self) -> bytes:
        """Get the full header as a bytes object."""
        buffer = bytearray()

        for field in self:
            int_to_bytes(field.value, buffer, field.offset, field.size)

        return bytes(buffer)

    def as_list(self) -> List[Field]:
        """The fields as a list.

        Returns:
            List[Field]: The list of fields.
        """
        return list(self._fields.values())

    def __iter__(self) -> Iterator[Field]:
        """The iterator for fields."""
        for item in self._fields.values():
            yield item

    def __getitem__(self, name: str) -> Field:
        """Get a field by its name.

        Args:
            name (str): The name of the field.

        Returns:
            Union[Field, None]: The field, or None, if no field was found.

        Raises:
            IndexError: If the field does not exist.
        """
        return self._fields[name]

    def __contains__(self, name: str) -> bool:
        """Magic methods for using `in`.

        Args:
            name (str): The name to look for in the fields.

        Returns:
            bool: True, if a field with the given name exists.
        """
        return name in self._fields


class SigmaProtocolHeader(ABC):
    """Base class for protocol headers."""

    READ_REQUEST: int = 0x0A
    READ_RESPONSE: int = 0x0B
    WRITE: int = 0x09

    @property
    def fields(self) -> Fields:
        """Fields of the header."""

    @property
    def has_payload(self) -> bool:
        """Whether this kind of packet carries a payload.

        Returns:
            bool: True if this is a write / read response, False otherwise.
        """
        return self.fields["operation"].value in [self.WRITE, self.READ_RESPONSE]

    @property
    def is_write_request(self) -> bool:
        """Whether this is a write request.

        Returns:
            bool: True if this is a write.
        """
        return self.fields["operation"].value == self.WRITE

    @property
    def is_safeload(self) -> bool:
        """Whether this is a safeload write request.

        Returns:
            bool: True if this is a safeload request.
        """
        return self.fields["operation"].value == self.WRITE and self.fields["safeload"].value == 1

    @property
    def is_read_request(self) -> bool:
        """Whether this is a read request.

        Returns:
            bool: True if this is a read request.
        """
        return self.fields["operation"].value == self.READ_REQUEST

    @property
    def is_read_response(self) -> bool:
        """Whether this is a read response.

        Returns:
            bool: True if this is a read response.
        """
        return self.fields["operation"].value == self.READ_RESPONSE

    def as_bytes(self) -> bytes:
        """Return the bytes representation of the current header.

        Returns:
            bytes: the assembled header
        """
        return self.fields.as_bytes()

    def parse(self, data: bytes):
        """Parse a header and populate field values.

        Args:
            data (bytes): The data to parse.
        """
        if len(data) != self.fields.size:
            raise ValueError(f"Input data needs to be exactly {self.fields.size} bytes long!")

        for field in self.fields:
            field.value = bytes_to_int(data, field.offset, field.size)

    def __setitem__(self, name: str, value: int):
        """Set a field value.

        Args:
            name (str): Field name.
            value (int): Field value.
        """
        valid_names = [field.name for field in self.fields]

        if name not in valid_names:
            raise ValueError(f"Invalid field name {name}; valid names are {', '.join(valid_names)}")

        self.fields[name].value = value

    def __getitem__(self, name: str) -> int:
        """Get a field value.

        Args:
            name (str): Field name.

        Returns:
            int: The field value.
        """
        return self.fields[name].value


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

    fields = Fields(
        [
            Field("operation", 0, 1),
            Field("safeload", 1, 1),
            Field("channel", 2, 1),
            Field("total_length", 3, 2),
            Field("chip_address", 5, 1),
            Field("data_length", 6, 2),
            Field("address", 8, 2),
        ]
    )


class Adau1701ReadRequestHeader(SigmaProtocolHeader):
    """Read request header for the TCPIP1701 protocol.

    This is used for ADAU1701 and ADAU1401 chips.
    """

    fields = Fields(
        [
            Field("operation", 0, 1),
            Field("total_length", 1, 2),
            Field("chip_address", 3, 1),
            Field("data_length", 4, 2),
            Field("address", 6, 2),
        ]
    )


class Adau1701ReadResponseHeader(SigmaProtocolHeader):
    """Read response header for the TCPIP1701 protocol.

    This is used for ADAU1701 and ADAU1401.
    """

    fields = Fields(
        [
            Field("operation", 0, 1),
            Field("total_length", 1, 2),
            Field("address", 3, 1),
        ]
    )


_register(SigmaProtocolHeader.WRITE, "adau1701", Adau1701WriteHeader)
_register(SigmaProtocolHeader.READ_REQUEST, "adau1701", Adau1701ReadRequestHeader)
_register(SigmaProtocolHeader.READ_RESPONSE, "adau1701", Adau1701ReadResponseHeader)


class Adau145xWriteHeader(SigmaProtocolHeader):
    """Write header for the TCPIPADAU144x/5x/6x protocols.

    This is presumably used for ADAU144x, ADAU145x and ADAU146x chips.
    """

    fields = Fields(
        [
            Field("operation", 0, 1),
            Field("safeload", 1, 1),
            Field("channel", 2, 1),
            Field("total_length", 3, 4),
            Field("chip_address", 7, 1),
            Field("data_length", 8, 4),
            Field("address", 12, 2),
        ]
    )


class Adau145xReadRequestHeader(SigmaProtocolHeader):
    """Read request header for the TCPIPADAU144x/5x/6x protocols.

    This is presumably used for ADAU144x, ADAU145x and ADAU146x chips.
    """

    fields = Fields(
        [
            Field("operation", 0, 1),
            Field("total_length", 1, 4),
            Field("chip_address", 5, 1),
            Field("data_length", 6, 4),
            Field("address", 10, 2),
            Field("reserved", 12, 2),
        ]
    )


class Adau145xReadResponseHeader(SigmaProtocolHeader):
    """Read response header for the TCPIPADAU144x/5x/6x protocols.

    This is presumably used for ADAU144x, ADAU145x and ADAU146x chips.
    """

    fields = Fields(
        [
            Field("operation", 0, 1),
            Field("total_length", 1, 4),
            Field("chip_address", 5, 1),
            Field("data_length", 6, 4),
            Field("address", 10, 2),
            Field("success", 12, 1),
            Field("reserved", 13, 1),
        ]
    )


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

    def __init__(self, dsp_type: str):
        """Initialize the packet.

        Args:
            dsp_type (str): DSP type.
        """
        self.dsp_type = dsp_type

    def init_from_payload(self, operation: int, payload: bytearray, header_defaults: Union[Fields, None] = None):
        """Initialize the packet with a new header and the provided payload.

        Args:
            operation (int): Operation code; most often SigmaStudioPacket.READ_RESPONSE
            payload (bytearray): Payload.
            header_defaults (Union[Fields, None]): Default values for header fields; useful when setting chip address,
                etc. from therequest headers
        """
        self.header = _get_header(self.dsp_type, operation)
        self.payload = payload
        self.header["total_length"] = self.header.fields.size + len(payload)

        # adau145x and friends have some additional response fields
        if "data_length" in self.header.fields:
            self.header["data_length"] = len(payload)

        if header_defaults is None:
            return

        for field in self.header.fields:
            if field.name in ["operation", "total_length", "data_length", "success"]:
                continue

            if field.name in header_defaults:
                self.header.fields[field.name].value = header_defaults[field.name].value

    def init_from_network(self, request_handler: "SigmaStudioRequestHandler"):
        """Fetch data from the request handler.

        Args:
            request_handler (SigmaStudioRequestHandler): The request handler that deals with the network.
        """
        # first get the operation code
        header_bytes: bytearray = request_handler.read(1)

        # get the appropriate header object
        self.header = _get_header(self.dsp_type, header_bytes[0])

        # finally, read the rest of the header and parse it
        header_bytes.extend(request_handler.read(self.header.fields.size - 1))
        self.header.parse(header_bytes)

        if self.header.is_write_request:
            # we have a payload
            self.payload = request_handler.read(self.header["data_length"])

    @property
    def as_bytes(self) -> bytes:
        """Return the whole packet as bytes, ready for sending over the network.

        This also handles all of the math involved in setting up the header.

        Returns:
            bytes: header and payload combined
        """
        buffer = bytearray(self.header.as_bytes())

        buffer.extend(self.payload)

        return bytes(buffer)
