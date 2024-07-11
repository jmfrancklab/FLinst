from pyspecdata import *
from Instruments.bridge12 import convert_to_power, convert_to_mv

response = input("1 for mV to dBm conversion, 2 for dBm to mV conversion: ")

if int(response) == 1:
    mV = input("Enter mV value: ")
    which_diode = input("1 for RX diode calibrated conversion, 2 for TX diode calibrated conversion: ")
    print("Calling convert_to_power function...")
    if int(which_diode) == 1:
        dBm = convert_to_power(float(mV),which_cal='Rx')
    if int(which_diode) == 2:
        dBm = convert_to_power(float(mV),which_cal='Tx')
    print("*** *** ***")
    print("CONVERTED",float(mV),"mV to",dBm,"dBm") 
    print("*** *** ***")

elif int(response) == 2:
    dBm = input("Enter dBm value: ")
    which_diode = input("1 for RX diode calibrated conversion, 2 for TX diode calibrated conversion: ")
    print("Calling convert_to_mv function...")
    if int(which_diode) == 1:
        mV = convert_to_mV(float(dBm),which_cal='Rx')
    if int(which_diode) == 2:
        mV = convert_to_mV(float(dBm),which_cal='Tx')
    print("*** *** ***")
    print("CONVERTED",float(dBm),"dBm to",mV,"mV") 
    print("*** *** ***")
    
else:
    print("I did not recognize your input variable.")

