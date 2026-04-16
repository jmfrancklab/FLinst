"""
HP Shim Power Supply
====================

Test control over the shims via the server.
"""

from Instruments import instrument_control


with instrument_control() as ic:
    shim_names = list(ic.get_shims().keys())
    print("initial shim readback:", ic.get_shims())
    print("\nVoltage test")
    ic.shim_voltage[:] = 0.0
    ic.shim_current[:] = 1.5
    print("device readback after voltage/current setup:", ic.get_shims())
    first_shim = shim_names[0]
    ic.shim_voltage[first_shim] = 1.5
    print(
        "device read voltage for",
        first_shim,
        "after named-shim set to 1.5 V:",
        ic.get_shims()[first_shim][0],
    )
    ic.shim_voltage[:] = [2.0] * len(shim_names)
    print(
        "device read voltages after bulk set to 2.0 V:",
        {shim_name: ic.get_shims()[shim_name][0] for shim_name in shim_names},
    )
    ic.shim_voltage[:] = 0.0
    ic.shim_current[:] = 0.0
    print("device readback after voltage test shutdown:", ic.get_shims())

    print("\nCurrent test")
    ic.shim_current[:] = 0.0
    ic.shim_voltage[:] = 15.0
    print("device readback after current/voltage setup:", ic.get_shims())
    ic.shim_current[first_shim] = 0.5
    print(
        "device read current for",
        first_shim,
        "after float set to 0.5 A:",
        ic.get_shims()[first_shim][1],
    )
    ic.shim_current[:] = [0.7] * len(shim_names)
    print(
        "device read currents after array set to 0.7 A:",
        {shim_name: ic.get_shims()[shim_name][1] for shim_name in shim_names},
    )
    ic.shim_current[:] = 0.0
    ic.shim_voltage[:] = 0.0
    print("device readback after current test shutdown:", ic.get_shims())
