from pyspecdata import *
from numpy import *
import os
import sys
from Instruments import Bridge12,prologix_connection,gigatronics
from serial import Serial
import time

print "POWER TESTING DEMO"

indexing = r_[0:200:1]
meter_powers = zeros_like(indexing)

for j,this_power in enumerate(indexing):
    print "\n*** *** *** *** ***\n"
    print "ON INDEX NUMBER",this_power
    time.sleep(2)
    with prologix_connection() as p:
        with gigatronics(prologix_instance=p, address=7) as g:
            meter_powers[j] = g.read_power()
            print "POWER READING",meter_powers[j]
    print "\n*** *** *** *** ***\n"
print meter_powers
