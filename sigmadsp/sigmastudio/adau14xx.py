"""Header generator for ADAU14xx parts."""
from .header import Field, PacketHeader, PacketHeaderGenerator


class Adau14xxHeaderGenerator(PacketHeaderGenerator):
    """Header generator for ADAU14xx parts."""

    @staticmethod
    def new_write_header() -> PacketHeader:
        """Generate a new header for a ADAU14xx write packet."""
        return PacketHeader(
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

    @staticmethod
    def new_read_request_header() -> PacketHeader:
        """Generate a new header for a ADAU14xx read request packet."""
        return PacketHeader(
            [
                Field("operation", 0, 1),
                Field("total_length", 1, 4),
                Field("chip_address", 5, 1),
                Field("data_length", 6, 4),
                Field("address", 10, 2),
                Field("reserved", 12, 2),
            ]
        )

    @staticmethod
    def new_read_response_header() -> PacketHeader:
        """Generate a new header for a ADAU14xx read response packet."""
        return PacketHeader(
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
