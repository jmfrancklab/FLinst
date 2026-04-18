"""Set a shim channel to its configured or user-specified voltage.

Usage in a terminal:
    python set_shim.py SHIM_NAME
    python set_shim.py SHIM_NAME --voltage VOLTAGE

Examples:
    python set_shim.py y
    python set_shim.py y --voltage 0.25
"""

import argparse
from Instruments import instrument_control
from SpinCore_pp import configuration

config_dict = configuration("active.ini")
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("shim_name", help="Shim channel name to set.")
parser.add_argument(
    "-v",
    "--voltage",
    type=float,
    help="Explicit shim voltage in volts. Defaults to the configured value.",
)
args = parser.parse_args()

with instrument_control() as ic:
    shim_name = str(args.shim_name)
    if args.voltage is None:
        shim_voltage_V = config_dict["shim_y_voltage_V"]
        print(
            "Your previous optimal shim voltage is "
            f"{config_dict['shim_y_voltage_V']} "
            f"and I am setting shim {shim_name} to "
            f"{shim_voltage_V}.\n\n"
            "NOTE: If you want to manually set a particular shim voltage "
            "(including 0 to turn off the shim) you can specify "
            "as an argument on the command line)"
        )
        ic.shim_voltage[shim_name] = shim_voltage_V
    else:
        shim_voltage_V = args.voltage
        ic.shim_voltage[shim_name] = shim_voltage_V
    print(f"{shim_name}: {ic.get_shims()[shim_name]}")
