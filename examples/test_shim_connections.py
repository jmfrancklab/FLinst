"""
HP Shim Power Supply
====================

Just go through and set the voltage on a bunch of shim coils, and verify
that the power supply believes that the currents have been changed."""
from pylab import *
from Instruments import HP6623A, prologix_connection, gigatronics
from Instruments.bridge12 import convert_to_power, convert_to_mv
from serial import Serial

with prologix_connection() as p:
        with HP6623A(prologix_instance=p, address=3) as HP:
            print("*** *** ***")
            HP.set_current(2,0.4)
            print("Current on channel 1 is",HP.get_current(2))
            HP.set_voltage(2,0.2)
            print("Voltage on channel 1 is",HP.get_voltage(2))
            print(HP.output(1,0))
            print(HP.output(2,0))
            print(HP.output(3,0))
            print(HP.check_output(1))
            print(HP.check_output(2))
            print(HP.check_output(3))
            print(HP.output(1,True))
            print(HP.output(2,1))
            print(HP.output(3,True))
            print(HP.check_output(1))
            print(HP.check_output(2))
            print(HP.check_output(3))
            print(HP.output(1,False))
            print(HP.output(2,0))
            print(HP.output(3,0))
            print(HP.check_output(1))
            print(HP.check_output(2))
            print(HP.check_output(3))
            print("*** *** ***")
