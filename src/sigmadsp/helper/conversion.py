"""This module includes many conversion functions that can be used for different purposes.

- Conversion between linear and dB-scale values
- Conversion from bytes-like objects of varying length to integers
- Conversion from integers to bytes-like objects of specified length
"""
import math


def clamp(value: float, min_value: float, max_value: float) -> float:
    """Clamps a value to a specified range.

    Args:
        value (float): The value to clamp.
        min_value (float): Lower clamping boundary.
        max_value (float): Upper clamping boundary.

    Returns:
        float: The clamped value.
    """
    if value >= max_value:
        value = max_value

    elif value <= min_value:
        value = min_value

    return value


def frac_8_24_to_float(value: int) -> float:
    """Convert a value in the DSPs fractional representation to float.

    32 bit values consist of 8 integer and 24 fractional bits and are signed.

    Args:
        value (int): Fractional value to convert

    Returns:
        float: Output in float format
    """
    return value / 2**24


def float_to_frac_8_24(value: float) -> int:
    """Convert a float value to the DSPs fractional representation.

    32 bit values consist of 8 integer and 24 fractional bits and are signed.

    Args:
        value (float): Float value to convert

    Returns:
        int: Output in DSP fractional format
    """
    return int(value * 2**24)


def db_to_linear(value_db: float) -> float:
    """Convert a dB-scale value (e.g. voltage) to a linear-scale value.

    Args:
        value (float): Input dB value

    Returns:
        float: Output linear value
    """
    return 10 ** (value_db / 20)


def linear_to_db(value_linear: float) -> float:
    """Convert a linear-scale value to a dB-scale value (e.g. voltage).

    Args:
        value_linear (float): The linear input value

    Returns:
        float: Output in dB scale
    """
    return 20 * math.log10(value_linear)


def bytes_to_int(data: bytes, offset: int = 0, length: int = 1) -> int:
    """Convert a number of bytes to their integer representation.

    Uses "length" bytes from the "data" input, starting at "offset".

    Args:
        data (bytes): Input bytes
        offset (int, optional): Offset in number of bytes, from the beginning of the data buffer
        length (int, optional): Number of bytes to convert. Defaults to 1.

    Returns:
        int: Integer representation of the input data stream
    """
    return int.from_bytes(data[offset : offset + length], byteorder="big")


def bytes_to_int8(data: bytes, offset: int = 0) -> int:
    """Convert one byte to an 8 bit integer value.

    Args:
        data (bytes): Input byte
        offset (int, optional): Offset in number of bytes, from the beginning of the data buffer

    Returns:
        int: 8 bit integer representation of the input data stream
    """
    return bytes_to_int(data, offset, length=1)


def bytes_to_int16(data: bytes, offset: int = 0) -> int:
    """Convert two bytes to a 16 bit integer value.

    Args:
        data (bytes): Input bytes
        offset (int, optional): Offset in number of bytes, from the beginning of the data buffer

    Returns:
        int: 16 bit integer representation of the input data stream
    """
    return bytes_to_int(data, offset, length=2)


def bytes_to_int32(data: bytes, offset: int = 0) -> int:
    """Convert four bytes to a 32 bit integer value.

    Args:
        data (bytes): Input bytes
        offset (int, optional): Offset in number of bytes, from the beginning of the data buffer

    Returns:
        int: 32 bit integer representation of the input data stream
    """
    return bytes_to_int(data, offset, length=4)


def int_to_bytes(value: int, buffer: bytearray = None, offset: int = 0, length: int = 1):
    """Fill a buffer with values. If no buffer is provided, a new one is created.

    Args:
        buffer (bytearray): The buffer to fill
        value (int): The value to pack into the buffer
        offset (int, optional): Offset in number of bytes, from the beginning of the data buffer
        length (int): Number of bytes to be written
    """
    if buffer is None:
        buffer = bytearray(length + offset)

    buffer[offset : offset + length] = value.to_bytes(length, byteorder="big")

    return buffer


def int8_to_bytes(value, buffer=None, offset=0):
    """Fill a buffer with an 8 bit value (1 byte). If no buffer is provided, a new one is created.

    Args:
        buffer (bytearray): The buffer to fill
        value (int): The value to pack into the buffer
        offset (int, optional): Offset in number of bytes, from the beginning of the data buffer
    """
    return int_to_bytes(value, buffer, offset=offset, length=1)


def int16_to_bytes(value, buffer=None, offset=0):
    """Fill a buffer with a 16 bit value (2 bytes). If no buffer is provided, a new one is created.

    Args:
        value (int): The value to pack into the buffer
        buffer (bytearray, optional): The buffer to fill
        offset (int, optional): Offset in number of bytes, from the beginning of the data buffer
    """
    return int_to_bytes(value, buffer, offset=offset, length=2)


def int32_to_bytes(value, buffer=None, offset=0) -> bytearray:
    """Fill a buffer with a 32 bit value (4 bytes). If no buffer is provided, a new one is created.

    Args:
        buffer (bytearray): The buffer to fill
        value (int): The value to pack into the buffer
        offset (int, optional): Offset in number of bytes, from the beginning of the data buffer
    """
    return int_to_bytes(value, buffer, offset=offset, length=4)
