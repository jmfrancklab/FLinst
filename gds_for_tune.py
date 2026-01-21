# note -- this was the original copy -- please see the spincore repo for the up to date version that calls tune, as well
#from Instruments import *
from pyspecdata import *
import time
#from serial.tools.list_ports import comports
#import serial
from scipy import signal
from FLInst import GDS_scope

fl = figlist_var()

print("These are the instruments available:")
SerialInstrument(None)
print("done printing available instruments")

with GDS_scope() as g:
    g.reset()
    g.CH1.disp=True
    g.CH2.disp=True
    g.write(':CHAN1:DISP ON')
    g.write(':CHAN2:DISP ON')
    g.write(':CHAN3:DISP OFF')
    g.write(':CHAN4:DISP OFF')
    g.CH1.voltscal=100E-3
    g.CH2.voltscal=50E-3
    g.timscal(500e-9, pos=2.325e-6)
    g.write(':CHAN1:IMP 5.0E+1')
    g.write(':CHAN2:IMP 5.0E+1')
    g.write(':TRIG:SOUR CH1') 
    g.write(':TRIG:MOD NORMAL')
    g.write(':TRIG:HLEV 7.5E-2')
