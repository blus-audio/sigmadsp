"""Test script, for evaluating the Sigmadsp backend functionality."""
import logging

import rpyc

try:
    c = rpyc.connect("localhost", 18861)

except ConnectionRefusedError:
    logging.info("Sigmadsp backend is not running!")

else:
    c.root.reset()
    c.root.adjust_volume(-3, "adjustable_volume_main")
