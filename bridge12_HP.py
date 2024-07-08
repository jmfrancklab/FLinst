# -*- coding: utf-8 -*-
"""
Created on Mon Jul 29 20:52:43 2019

@author: aabeaton
"""

from pylab import *
from Instruments import Bridge12
from Instruments.bridge12 import convert_to_power, convert_to_mv
from serial import Serial
import time
from itertools import cycle

run_bridge12 = True
if run_bridge12:
    with Bridge12() as b:
        print("SETTING WAVEGUIDE SWITCH")
        b.set_wg(True)
        print("WAVEGUIDE SET")
        print("SETTING AMPLIFIER")
        b.set_amp(True)
        print("AMPLIFIER SET")
        
        print("SETTING FREQUENCY...")
        b.set_freq(9.851321e9)
      
        print("SETTING POWER...")
        b.set_power(10.0)
        input("Enter to exit...")
        print("EXITING.")