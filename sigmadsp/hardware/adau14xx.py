import time
from sigmadsp.hardware.spi import SpiHandler
from sigmadsp.helper.conversion import bytes_to_int8, bytes_to_int16, bytes_to_int32
from sigmadsp.helper.conversion import int8_to_bytes, int16_to_bytes, int32_to_bytes

class Adau14xx:
    RESET_REGISTER = 0xF890
    RESET_REGISTER_LENGTH = 2

    def __init__(self):
        self.spi_handler = SpiHandler()

    def soft_reset(self):
        SpiHandler.write(self.spi_handler, Adau14xx.RESET_REGISTER, int16_to_bytes(0))
        time.sleep(1)
        SpiHandler.write(self.spi_handler, Adau14xx.RESET_REGISTER, int16_to_bytes(1))

    def get_volume(self):
        pass

    def set_volume(self):
        pass