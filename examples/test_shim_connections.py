"""
HP Shim Power Supply
====================

Just go through and set the voltage on a bunch of shim coils, and verify
that the power supply believes that the currents have been changed."""

from pylab import *
from Instruments import HP6623A, prologix_connection, gigatronics
from Instruments.bridge12 import convert_to_power, convert_to_mv
from serial import Serial

# voltage_array = r_[0.:1.:0.025]
HP1 = 2
HP2 = 3
HP_list = [
    (HP1, 1, 1.0),  # B0 shim
    (HP1, 2, 1.0),  # Z1 shim
    (HP2, 1, 0.0),  # Z2 shim
    (HP2, 2, 0.0),  # X shim
    (HP2, 3, 0.0),  # Y shim
]
print(HP_list[:][-1])


# {{{
def set_shims(HP_list, output=False):
    # pass a list of the HP sources, we either have 1 or 2
    B0_shim = HP_list[0]
    Z1_shim = HP_list[1]
    Z2_shim = HP_list[2]
    X_shim = HP_list[3]
    Y_shim = HP_list[4]
    if output:
        for index in range(len(HP_list)):
            this_shim = HP_list[index]
            this_shim[0].set_voltage(this_shim[1], this_shim[-1])
        for index in range(len(HP_list)):
            this_shim = HP_list[index]
            if this_shim[-1] == 0.0:
                print("zero")
                this_shim[0].output(this_shim[1], False)
            else:
                this_shim[0].output(this_shim[1], True)
        curr_list = []
        volt_list = []
        for index in range(len(HP_list)):
            this_shim = HP_list[index]
            curr_list.append(this_shim[0].get_current(this_shim[1]))
            volt_list.append(this_shim[0].get_voltage(this_shim[1]))
        print("CURRENT LIST", curr_list)
        print("VOLTAGE LIST", volt_list)
        return curr_list, volt_list
    else:
        for index in range(len(HP_list)):
            this_shim = HP_list[index]
            this_shim[0].output(this_shim[1], False)
        curr_list = []
        volt_list = []
        for index in range(len(HP_list)):
            this_shim = HP_list[index]
            curr_list.append(this_shim[0].get_current(this_shim[1]))
            volt_list.append(this_shim[0].get_voltage(this_shim[1]))
        print("CURRENT LIST", curr_list)
        print("VOLTAGE LIST", volt_list)
        return curr_list, volt_list


# }}}

with prologix_connection() as p:
    with HP6623A(prologix_instance=p, address=3) as HP1:
        with HP6623A(prologix_instance=p, address=5) as HP2:
            print("*** *** ***")
            HP_list = [
                (HP1, 1, 0.0),  # X shim
                (HP1, 2, 0.0),  # Z2 shim
                (HP2, 1, 0.0),  # B0 shim
                (HP2, 2, 0.1),  # Y shim
                (HP2, 3, 0.03),  # Z1 shim
            ]
            set_shims(HP_list, True)
            input()
            print("DONE")
            print("* * *")
            set_shims(HP_list, False)
quit()
