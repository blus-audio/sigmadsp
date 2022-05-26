"""Tests for the communication.sigmastudio_protocols module."""
from sigmadsp.communication.sigmastudio_protocols import Adau1701WriteHeader


def test_adau1701_write_header():
    """Test the write headers."""
    header = Adau1701WriteHeader()

    payload = bytes(range(10))
    address = 8360
    data_length = len(payload)
    total_length = data_length + 10  # The header is 10 bytes long.

    header_message = (
        Adau1701WriteHeader.WRITE.to_bytes(1, "little")
        + b"\x01"
        + b"\x01"
        + total_length.to_bytes(2, "little")
        + b"\x0b"
        + data_length.to_bytes(2, "little")
        + address.to_bytes(2, "little")
    )

    header.parse(header_message)

    assert header.is_write_request
    assert header.is_safeload
    assert header.as_bytes() == header_message

    assert header.fields.has_field("operation")
    assert not header.fields.has_field("not_in_there")
