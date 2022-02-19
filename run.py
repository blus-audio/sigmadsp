from sigmadsp.hardware.adau14xx import Adau14xx
from sigmadsp.application import main

adau14xx = Adau14xx()
adau14xx.soft_reset()

main()