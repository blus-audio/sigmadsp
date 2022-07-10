"""This module describes the header of a packet that is exchanged with SigmaStudio.

Headers contain individual fields that follow each other in a certain sequence.
"""

from abc import ABC, abstractmethod
from collections import OrderedDict
from dataclasses import dataclass
from enum import Enum
from typing import Iterator, List, Literal, Union

from sigmadsp.helper.conversion import bytes_to_int, int_to_bytes


class OperationKey(Enum):
    """Possible operation keys that are exchanged with SigmaStudio."""

    READ_REQUEST_KEY = 0x0A
    READ_RESPONSE_KEY = 0x0B
    WRITE_KEY = 0x09


ValidFieldNames = Literal[
    "operation", "safeload", "channel", "total_length", "chip_address", "data_length", "address", "success", "reserved"
]


@dataclass
class Field:
    """A class that represents a single field in the header."""

    # The name of the field.
    name: ValidFieldNames

    # The offset of the field in bytes from the start of the header.
    offset: int

    # The size of the field in bytes.
    size: int

    @property
    def value(self) -> int:
        """The stored value."""
        return self._value

    @value.setter
    def value(self, new_value: Union[int, bytes, bytearray]):
        """Store a new value and convert it before storage, if required.

        Args:
            new_value (Union[int, bytes, bytearray]): The new value to set. If ``int``, it is stored without conversion.
                If ``bytes`` or ``bytearray``, it is first converted to int.

        Raises:
            TypeError: If the value type is not supported.
        """
        if isinstance(new_value, bytearray):
            new_value = bytes(new_value)

        if isinstance(new_value, bytes):
            assert len(new_value) == self.size
            self._value = bytes_to_int(new_value, 0)

        elif isinstance(new_value, int):
            assert new_value.bit_length() <= self.size * 8
            self._value = new_value

        else:
            raise TypeError(f"Unsupported value type {type(new_value)} for the field value.")

    def __post_init__(self):
        """Perform sanity checks on the field properties."""
        self.value = 0

        if self.size < 0:
            raise ValueError("Field size must be a positive integer.")

        if self.offset < 0:
            raise ValueError("Field offset must be a positive integer.")

        # The last byte index that is occupied by this field.
        self.end = self.offset + self.size - 1

    def __hash__(self) -> int:
        """Hash functionality."""
        return hash((self.name, self.offset, self.size))


class PacketHeader:
    """An iterable collection of Field objects that forms the packet header."""

    def __init__(self, fields: List[Field]):
        """Initialize the header fields. Add more fields to it by means of ``add()``.

        Instantiate via:
        PacketHeader(
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
        return sum((field.size for field in self))

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

    def add(self, name: ValidFieldNames, offset: int, size: int):
        """Create and add a new field.

        Args:
            name (ValidFieldNames): The name of the field.
            offset (int): The field offset in number of bytes.
            size (int): The size of the field in bytes.
        """
        field = Field(name, offset, size)
        self.add_field(field)

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

    def parse(self, data: bytes):
        """Parse a header and populate field values.

        Args:
            data (bytes): The data to parse.
        """
        if len(data) != self.size:
            raise ValueError(f"Input data needs to be exactly {self.size} bytes long!")

        for field in self:
            field.value = bytes_to_int(data, field.offset, field.size)

    @property
    def is_write_request(self) -> bool:
        """Whether this is a write request."""
        return self._fields["operation"].value == OperationKey.WRITE_KEY.value

    @property
    def is_read_request(self) -> bool:
        """Whether this is a read request."""
        return self._fields["operation"].value == OperationKey.READ_REQUEST_KEY.value

    @property
    def is_read_response(self) -> bool:
        """Whether this is a read response."""
        return self._fields["operation"].value == OperationKey.READ_RESPONSE_KEY.value

    @property
    def is_safeload(self) -> bool:
        """Whether this is a software-safeload write request."""
        return self.is_write_request and self._fields["safeload"].value == 1

    @property
    def carries_payload(self) -> bool:
        """Whether the corresponding packet carries a payload."""
        return self.is_write_request or self.is_read_response

    @property
    def names(self) -> List[str]:
        """All field names in a list."""
        return [field.name for field in self]

    def __iter__(self) -> Iterator[Field]:
        """The iterator for fields."""
        for item in self._fields.values():
            yield item

    def __setitem__(self, name: ValidFieldNames, value: Union[int, bytes, bytearray]):
        """Set a field value.

        Args:
            name (ValidFieldNames): Field name.
            value (Union[int, bytes, bytearray]): Field value.
        """
        if name not in self.names:
            raise ValueError(f"Invalid field name {name}; valid names are {', '.join(self.names)}")

        # FIXME: Type is correct, see https://github.com/python/mypy/issues/3004.
        self._fields[name].value = value  # type: ignore

    def __getitem__(self, name: ValidFieldNames) -> Field:
        """Get a field by its name.

        Args:
            name (ValidFieldNames): The name of the field.

        Returns:
            Union[Field, None]: The field, or None, if no field was found.

        Raises:
            IndexError: If the field does not exist.
        """
        return self._fields[name]

    def __contains__(self, name: ValidFieldNames) -> bool:
        """Magic methods for using ``in``.

        Args:
            name (ValidFieldNames): The name to look for in the fields.

        Returns:
            bool: True, if a field with the given name exists.
        """
        return name in self._fields


class PacketHeaderGenerator(ABC):
    """Generic generator for packet headers."""

    @staticmethod
    @abstractmethod
    def new_write_header() -> PacketHeader:
        """Generate a new header for a write packet."""

    @staticmethod
    @abstractmethod
    def new_read_request_header() -> PacketHeader:
        """Generate a new header for a read request packet."""

    @staticmethod
    @abstractmethod
    def new_read_response_header() -> PacketHeader:
        """Generate a new header for a read response packet."""

    def new_header_from_operation_byte(self, operation_byte: bytes) -> PacketHeader:
        """Generate a header from an operation byte.

        Args:
            operation_byte (bytes): The operation byte to decide on the header.

        Raises:
            ValueError: If the operation key, extracted from the operation byte, is not known.

        Returns:
            PacketHeader: A new packet header.
        """
        assert len(operation_byte) == 1, "Operation byte must have a length of 1."

        operation_key = OperationKey(bytes_to_int(operation_byte, offset=0, length=1))

        header: PacketHeader
        if operation_key == OperationKey.READ_REQUEST_KEY:
            header = self.new_read_request_header()

        elif operation_key == OperationKey.READ_RESPONSE_KEY:
            header = self.new_read_response_header()

        elif operation_key == OperationKey.WRITE_KEY:
            header = self.new_write_header()

        else:
            raise ValueError(f"Unknown operation key {operation_key}.")

        header["operation"] = operation_byte
        return header
