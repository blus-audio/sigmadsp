"""Header generator for ADAU1x01 parts."""
from .header import Field, PacketHeader, PacketHeaderGenerator


class Adau1x01HeaderGenerator(PacketHeaderGenerator):
    """Header generator for ADAU1x01 parts."""

    @staticmethod
    def new_write_header() -> PacketHeader:
        """Generate a new header for a ADAU1x01 write packet."""
        return PacketHeader(
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

    @staticmethod
    def new_read_request_header() -> PacketHeader:
        """Generate a new header for a ADAU1x01 read request packet."""
        return PacketHeader(
            [
                Field("operation", 0, 1),
                Field("total_length", 1, 2),
                Field("chip_address", 3, 1),
                Field("data_length", 4, 2),
                Field("address", 6, 2),
            ]
        )

    @staticmethod
    def new_read_response_header() -> PacketHeader:
        """Generate a new header for a ADAU1x01 read response packet."""
        return PacketHeader(
            [
                Field("operation", 0, 1),
                Field("total_length", 1, 2),
                Field("address", 3, 1),
            ]
        )
