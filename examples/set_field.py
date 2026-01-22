"""Set the magnet field using the power_control client.

Usage:
    1) "python set_field.py" sets the field according to
    the carrier frequency and gamma_eff in the active.ini.
    2) "python set_field.py 3500" sets the field to 3500 G
    3) "pyhton set_field.py 0" ramps the field down to 0 and
    turns the PS off.
"""

import sys
from Instruments import power_control
from SpinCore_pp import configuration

config_dict = configuration("active.ini")
with power_control() as p:
    if len(sys.argv) == 1:
        B_field = (
            config_dict["carrierFreq_MHz"] / config_dict["gamma_eff_MHz_G"]
        )
        print(
            "Your carrier freqency is "
            f"{config_dict['carrierFreq_MHz']} "
            "and I am setting the field to "
            f"{B_field}"
        )
        p.set_field(B_field)

    if len(sys.argv) == 2:
        B_field = float(sys.argv[1])
        p.set_field(B_field)
    else:
        raise ValueError("You entered an extra argument.")
