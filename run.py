from sigmadsp import application
from sigmadsp.hardware.adau14xx import Adau14xx

adau14xx = Adau14xx()
adau14xx.soft_reset()

application.main()