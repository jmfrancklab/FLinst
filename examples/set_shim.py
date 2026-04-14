# TODO ☐: needs a docstring at the top.  All examples actually need a
#         docstring.  We are not actually building a sphinx gallery, but sphinx
#         gallery will actually fail if you don't have one.  (I think it
#         actually needs a title, as indicated by rst header.) So you could say
#         that all examples are *required* to have a docstring.

import sys
from Instruments import power_control
from SpinCore_pp import configuration

config_dict = configuration("active.ini")
# TODO ☐: especially since you can just gpt it, I would encourage you to use
#         argparser with named arguments here; this makes it more flexible.
with power_control() as p:
    if len(sys.argv) == 2:
        shim_name = str(sys.argv[1])
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
        p.shim_voltage[shim_name] = shim_voltage_V
    elif len(sys.argv) == 3:
        shim_name = str(sys.argv[1])
        shim_voltage_V = float(sys.argv[2])
        p.shim_voltage[shim_name] = shim_voltage_V
    else:
        raise ValueError("You entered an extra argument.")
    print(f"{shim_name}: {p.get_shims()[shim_name]}")
