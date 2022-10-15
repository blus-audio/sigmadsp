"""Tests for the sigmastudio header generators."""
import pytest

from sigmadsp.helper.conversion import int8_to_bytes, int16_to_bytes
from sigmadsp.sigmastudio.adau1x01 import Adau1x01HeaderGenerator
from sigmadsp.sigmastudio.header import Field, OperationKey


def test_adau1x01_header_generator():
    """Test the adau1x01 write headers."""
    header_generator = Adau1x01HeaderGenerator()

    # Test the conversion of a binary header to an object-type header.
    payload = bytes(range(10))
    address = 8360
    data_length = len(payload)
    total_length = data_length + 10  # The header is 10 bytes long.

    header_message = (
        int8_to_bytes(OperationKey.WRITE_KEY.value)  # operation
        + b"\x01"  # safeload
        + b"\x01"  # channel
        + int16_to_bytes(total_length)  # total_length
        + b"\x0b"  # chip_address
        + int16_to_bytes(data_length)  # data_length
        + int16_to_bytes(address)  # address
    )

    write_header = header_generator.new_header_from_operation_key(OperationKey.WRITE_KEY)
    write_header.parse(header_message)

    assert write_header.is_continuous
    assert write_header.is_write_request
    assert write_header.is_safeload
    assert write_header.as_bytes() == header_message

    assert "operation" in write_header
    assert "not_in_there" not in write_header

    # Test the generation of headers from an operation byte.
    read_request_header = header_generator.new_header_from_operation_key(OperationKey.READ_REQUEST_KEY)
    assert read_request_header.is_read_request

    another_write_header = header_generator.new_header_from_operation_key(OperationKey.WRITE_KEY)
    assert another_write_header.is_write_request

    read_response_header = header_generator.new_header_from_operation_key(OperationKey.READ_RESPONSE_KEY)
    assert read_response_header.is_read_response


def test_field():
    """Test setting values in fields."""
    operation_field = Field("operation", 0, 1)

    with pytest.raises(AssertionError) as _:
        # Does not fit in one byte
        operation_field.value = b"\x1234"

    operation_field.value = b"\x90"

    with pytest.raises(AssertionError) as _:
        # 256 does not fit in one byte
        operation_field.value = 256

    operation_field.value = 10
