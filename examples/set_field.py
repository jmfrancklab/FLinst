#!/usr/bin/env python3
"""Set the magnet field using the power_control client.

Usage:
    python Instruments/set_field.py 3500 --ip 127.0.0.1 --port 6002
"""

from Instruments import power_control
from SpinCore_pp import configuration

config_dict = config_dict = configuration("active.ini")
with power_control as p:
    if len(sys.argv) < 2:
        B_field = (
            onfig_dict["carrierFreq_MHz"] / config_dict["gamma_eff_MHz_G"]
        )
        print(
            f"Your carrier freqency is {
                config_dict['carrierFreq_MHz']
            } and I am setting the field to {
                config_dict['carrierFreq_MHz'] / config_dict['gamma_eff_MHz_G']
            }"
        )
        p.set_field(B_field)

    else:
        B_field = float(sys.argv[1]) * config_dict["current_v_field_A_G"]
        p.set_field(B_field)
