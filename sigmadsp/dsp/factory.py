"""Factory module for generating DSP objects."""
import logging
from typing import Dict
from typing import Type
from typing import Union

from .adau14xx import Adau14xx
from .adau1x01 import Adau1x0x
from .common import ConfigurationError
from .common import Dsp
from .common import InputPin
from .common import OutputPin
from sigmadsp.protocols.i2c import I2cProtocol
from sigmadsp.protocols.spi import SpiProtocol

logger = logging.getLogger(__name__)

ADAU_14XX = "adau14xx"
ADAU_1X0X = "adau1x0x"


def dsp_factory(dsp_type_name: str) -> Type[Dsp]:
    """Creates Dsp objects, based on the name of the DSP.

    Args:
        dsp_type_name (str): The name of the DSP.

    Returns:
        Type[Dsp]: The matching DSP class.
    """
    if dsp_type_name == ADAU_14XX:
        return Adau14xx

    elif dsp_type_name == ADAU_1X0X:
        return Adau1x0x

    else:
        raise TypeError("DSP type {dsp_type} is not known.")


def dsp_from_config(config: Dict) -> Dsp:
    """Parse a configuration dictionary and create a new DSP from it.

    Args:
        config (dict): The configuration dictionary.

    Returns:
        Dsp: The created DSP object.
    """
    dsp: Dsp

    try:
        dsp_protocol_name: str = config["dsp"]["protocol"].lower()
        dsp_type_name: str = config["dsp"]["type"].lower()
        bus = int(config["dsp"]["bus_number"])
        device = int(config["dsp"]["device_address"])

    except KeyError as e:
        logger.error("Key %s missing from the DSP configuration.", e.args[0])
        raise ConfigurationError from e

    else:
        # Generate the protocol first (e.g. SPI or I2C).
        dsp_protocol: Union[SpiProtocol, I2cProtocol]

        if dsp_protocol_name == "spi":
            dsp_protocol = SpiProtocol(bus=bus, device=device)

        elif dsp_protocol_name == "i2c":
            dsp_protocol = I2cProtocol(bus=bus, device=device)

        else:
            raise TypeError(f"Unknown DSP protocol {dsp_protocol_name}.")

        # Then, generate the dsp itself.
        dsp_type: Type[Dsp] = dsp_factory(dsp_type_name)

        # Use safeload by default.
        dsp = dsp_type(True, dsp_protocol)

    try:
        # Parse the configuration for pin definitions.
        for pin_definition_key in config["dsp"]["pins"]:
            pin_definition = config["dsp"]["pins"][pin_definition_key]

            if pin_definition["mode"] == "output":
                output_pin = OutputPin(
                    pin_definition_key,
                    pin_definition["number"],
                    pin_definition["initial_state"],
                    pin_definition["active_high"],
                )

                dsp.add_pin(output_pin)

            elif pin_definition["mode"] == "input":
                input_pin = InputPin(
                    pin_definition_key,
                    pin_definition["number"],
                    pin_definition["pull_up"],
                    pin_definition["active_state"],
                    pin_definition["bounce_time"],
                )

                dsp.add_pin(input_pin)

    except (KeyError, TypeError):
        logger.info("No DSP pin definitions were found in the configuration file.")

    return dsp
