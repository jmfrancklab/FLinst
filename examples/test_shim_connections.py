"""
HP Shim Power Supply
====================

This script provides a small shim-mapping layer for two HP6623A supplies.
Named shim channels (e.g., Z0, Z1, Z2, X, Y) are mapped to a specific
instrument and output channel, and the helper function applies a current
limit, voltage limit, and output on/off state in one call.
"""

from Instruments import HP6623A, prologix_connection
import logging

# Initialize the two HP6623A instances and create a dictionary of shim names.
HP1 = HP6623A(gpibaddr=3)
HP2 = HP6623A(gpibaddr=5)
shim_dict = {
    "Z0": (HP1, 0),
    "Y": (HP1, 1),
    "Z1": (HP2, 0),
    "Z2": (HP2, 1),
    "X": (HP2, 2),
}


def shim_setter(which_shim, value, v_limit=15.0):
    """Set current and output state for a named shim."""
    hp_inst, ch = shim_dict[which_shim]
    if value == 0.0:
        hp_inst.I_limit[ch] = 0.0
        hp_inst.V_limit[ch] = 0.0
        hp_inst.output[ch] = False
        logging.info(f"Shim {which_shim} is turned off")
    else:
        hp_inst.V_limit[ch] = v_limit
        hp_inst.I_limit[ch] = value
        hp_inst.output[ch] = True
        logging.info(f"Shim {which_shim} is on with current set to {value}.")


with prologix_connection() as p:
    with HP6623A(prologix_instance=p, address=3) as HP1:
        with HP6623A(prologix_instance=p, address=5) as HP2:
            HP1.safe_current_on_enable = 1.8
            HP2.safe_current_on_enable = 1.8

            for inst, ch in shim_dict.values():
                inst.set_overvoltage(ch, 15)

            shim_setter("Z0", 1.0)
            shim_setter("Y", 1.0)
            shim_setter("Z1", 0.0)
            shim_setter("Z2", 0.0)
            shim_setter("X", 0.0)

            input()
            for shim in shim_dict:
                shim_setter(shim, 0.0)
