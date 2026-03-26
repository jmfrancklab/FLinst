import sys
from Instruments import power_control
from SpinCore_pp import configuration

config_dict = configuration("active.ini")
with power_control() as p:
    if len(sys.argv) == 1:
        shim_current_A = config_dict["shim_y_current_A"]
        print(
            "Your optial shim current is "
            f"{config_dict['shim_y_current_A']} "
            "and I am setting the field to "
            f"{shim_current_A}.\n\n"
            "NOTE: If you want to manually set a particular field "
            "(including 0 to turn off the shim) you can specify "
            "as an argument on the command line)"
        )
        p.set_shim_current(shim_current_A)
    elif len(sys.argv) == 2:
        shim_current_A = float(sys.argv[1])
        p.set_shim_current(shim_current_A)
    else:
        raise ValueError("You entered an extra argument.")
