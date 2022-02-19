def bytes_to_int(data: bytes, offset: int, length: int = 1) -> int:
    """Convertes a number of bytes to their integer representation.
    Uses "length" bytes from the "data" input, starting at "offset".

    Args:
        data (bytes): Input bytes
        offset (int, optional): Offset in number of bytes, from the beginning of the data buffer
        length (int, optional): Number of bytes to convert. Defaults to 1.

    Returns:
        int: Integer representation of the input data stream
    """
    return int.from_bytes(data[offset:offset+length], byteorder='big')

def bytes_to_int8(data: bytes, offset: int) -> int:
    """Converts one byte to an 8 bit integer value.

    Args:
        data (bytes): Input byte
        offset (int, optional): Offset in number of bytes, from the beginning of the data buffer

    Returns:
        int: 8 bit integer representation of the input data stream
    """
    return bytes_to_int(data, offset, length = 1)

def bytes_to_int16(data: bytes, offset: int) -> int:
    """Converts one byte to a 16 bit integer value.

    Args:
        data (bytes): Input bytes
        offset (int, optional): Offset in number of bytes, from the beginning of the data buffer

    Returns:
        int: 16 bit integer representation of the input data stream
    """
    return bytes_to_int(data, offset, length = 2)

def bytes_to_int32(data: bytes, offset: int) -> int:
    """Converts one byte to a 32 bit integer value.

    Args:
        data (bytes): Input bytes
        offset (int, optional): Offset in number of bytes, from the beginning of the data buffer

    Returns:
        int: 32 bit integer representation of the input data stream
    """
    return bytes_to_int(data, offset, length = 4)

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

    buffer[offset:offset+length] = value.to_bytes(length, byteorder='big')

    return buffer

def int8_to_bytes(value, buffer = None, offset = 0):
    """Fill a buffer with an 8 bit value (1 byte). If no buffer is provided, a new one is created.

    Args:
        buffer (bytearray): The buffer to fill
        value (int): The value to pack into the buffer
        offset (int, optional): Offset in number of bytes, from the beginning of the data buffer
    """
    return int_to_bytes(value, buffer, offset = offset, length = 1)

def int16_to_bytes(value, buffer = None, offset = 0):
    """Fill a buffer with a 16 bit value (2 bytes). If no buffer is provided, a new one is created.

    Args:
        value (int): The value to pack into the buffer
        buffer (bytearray, optional): The buffer to fill
        offset (int, optional): Offset in number of bytes, from the beginning of the data buffer
    """
    return int_to_bytes(value, buffer, offset = offset, length = 2)

def int32_to_bytes(value, buffer = None, offset = 0) -> bytearray:
    """Fill a buffer with a 32 bit value (4 bytes). If no buffer is provided, a new one is created.

    Args:
        buffer (bytearray): The buffer to fill
        value (int): The value to pack into the buffer
        offset (int, optional): Offset in number of bytes, from the beginning of the data buffer
    """
    return int_to_bytes(value, buffer, offset = offset, length = 4)
