"""Set the magnet field using the instrument_control client.

Usage:
    1) "python set_field.py" sets the field according to
    the carrier frequency and gamma_eff in the active.ini.
    2) "python set_field.py 3500" sets the field to 3500 G
    3) "python set_field.py 0" ramps the field down to 0 and
    turns the PS off.
"""

import sys
from Instruments import instrument_control
from SpinCore_pp import configuration

config_dict = configuration("active.ini")
with instrument_control() as ic:
    if len(sys.argv) == 1:
        B_field = (
            config_dict["carrierFreq_MHz"] / config_dict["gamma_eff_MHz_G"]
        )
        print(
            "Your carrier frequency is "
            f"{config_dict['carrierFreq_MHz']} "
            "and I am setting the field to "
            f"{B_field} (based on γ_eff).\n\n"
            "NOTE: If you want to manually set a particular field "
            "(including 0 to turn off the magnet) you can specify "
            "as an argument on the command line)"
        )
        ic.set_field(B_field)
    elif len(sys.argv) == 2:
        B_field = float(sys.argv[1])
        ic.set_field(B_field)
    else:
        raise ValueError("You entered an extra argument.")
