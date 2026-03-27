import sys
from Instruments import power_control
from SpinCore_pp import configuration

config_dict = configuration("active.ini")
with power_control() as p:
    if len(sys.argv) == 2:
        shim_name = str(sys.argv[1])
        channel = config_dict["shim_channels"][shim_name][1]
        shim_voltage_V = config_dict["shim_y_voltage_V"]
        print(
            "Your optial shim voltage is "
            f"{config_dict['shim_y_voltage_V']} "
            "and I am setting the field to "
            f"{shim_voltage_V}.\n\n"
            "NOTE: If you want to manually set a particular field "
            "(including 0 to turn off the shim) you can specify "
            "as an argument on the command line)"
        )
        p.set_shim_voltage(shim_voltage_V)
    elif len(sys.argv) == 3:
        shim_name = str(sys.argv[1])
        channel = config_dict["shim_channels"][shim_name][1]
        shim_voltage_V = float(sys.argv[2])
        p.set_shim_voltage(shim_voltage_V)
    else:
        raise ValueError("You entered an extra argument.")
