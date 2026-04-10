"""
HP Shim Power Supply
====================

Test control over the shims via the server.
"""

from Instruments import power_control


with power_control() as p:
    shim_names = list(p.get_shims().keys())
    print("initial shim readback:", p.get_shims())
    print("\nVoltage test")
    p.shim_voltage[:] = 0.0
    p.shim_current[:] = 1.5
    print("device readback after voltage/current setup:", p.get_shims())
    # TODO ☐: I don't really understand this.  (1) the server rounds for
    #         you, so why do that here? (2) why is there a loop? You set
    #         up the properties as dict properties, so you should be able
    #         to set them to a vector if you like.
    #         This is an example, so you want to be showing you how
    #         acctually expect people to interact with the module.
    for shim_name in shim_names:
        rounded_voltage = p.round_shim_voltage(shim_name, 1.5)
        print(
            "rounded float voltage for",
            shim_name,
            "from 1.5 V to:",
            rounded_voltage,
        )
        p.shim_voltage[shim_name] = rounded_voltage
        print(
            "device read voltage for",
            shim_name,
            "after float set:",
            p.get_shims()[shim_name][0],
        )
    rounded_voltage_arrays = {
        shim_name: p.round_shim_voltage(shim_name, [2.0, 2.0])
        for shim_name in shim_names
    }
    print(
        "rounded array voltages from 2.0 V request:",
        rounded_voltage_arrays,
    )
    rounded_voltages = [
        rounded_voltage_arrays[shim_name][0] for shim_name in shim_names
    ]
    p.shim_voltage[:] = rounded_voltages
    print(
        "device read voltages after array set:",
        {shim_name: p.get_shims()[shim_name][0] for shim_name in shim_names},
    )
    p.shim_voltage[:] = 0.0
    p.shim_current[:] = 0.0
    print("device readback after voltage test shutdown:", p.get_shims())

    print("\nCurrent test")
    p.shim_current[:] = 0.0
    p.shim_voltage[:] = 15.0
    print("device readback after current/voltage setup:", p.get_shims())
    for shim_name in shim_names:
        p.shim_current[shim_name] = 0.5
        print(
            "device read current for",
            shim_name,
            "after float set to 0.5 A:",
            p.get_shims()[shim_name][1],
        )
    p.shim_current[:] = [0.7] * len(shim_names)
    print(
        "device read currents after array set to 0.7 A:",
        {shim_name: p.get_shims()[shim_name][1] for shim_name in shim_names},
    )
    p.shim_current[:] = 0.0
    p.shim_voltage[:] = 0.0
    print("device readback after current test shutdown:", p.get_shims())
