#{{{ Program doc
r'''Use this program to capture a single S11 (reflection) measurement
    Must use the appropriate set up of the power splitter (PS) and
    reference channel (CH1). Set up as follows (also see AAB-2, 7/12/2018
    yellow tab):
    CH1 (AFG) -*ref*-> CH1 (GDS) *Use coax labeled 'REF'
    CH2 (AFG) --> PS (PORT 1) --> PS (S) --> DUT --> PS (2) --> CH2 (GDS)
    Sends out programmed waveform on both channels of the AFG, with
    the option to correct for amplitude variation (due to use of
    the power splitter), so that the reflection is calculated
    correctly (using *proc_chirp.py*)
    There are two options for a programmed waveform:
        (1) A proper chirp from 5 to 25 MHz,
    and (2) A pulse of a specified frequency
    These options are chosen by the :pulse_90: boolean,
    where True is (2) and False is (1).

    ALTERNATIVELY, use this program to capture and save scope display.
    Note that if you have multi_channel set to True, and only
    have CH 1 on (i.e., CH 2 is turned off or not active), then
    your collected data will appear to be empty. This is
    because you cannot capture an inactive channel.
    Multi_channel right now is set to capture only CH1 and CH2
    - you could alter this to accept 3 and 4 as well.
'''
#}}}
from Instruments import *
from pyspecdata import *
import time
from serial.tools.list_ports import comports
import serial
from scipy import signal

start = time.time()
fl = figlist_var()
multi_channel = False
datalist = []
print("about to load GDS")
with GDS_scope() as g:
    print("loaded GDS")
    #g.acquire_mode('average',32)
    input("Enter once signal has reached steady-state...")
    if multi_channel:
        for j in range(1,3):
            print("trying to grab data from channel",j)
            datalist.append(g.waveform(ch=j))
    else:
        print("trying to grab data from channel 1")
        datalist.append(g.waveform(ch=1))
data = concat(datalist,'ch').reorder('t')
j = 1
try_again = True
while try_again:
    data_name = 'capture%d'%j
    data.name(data_name)
    try:
        data.hdf5_write('200820_pulse.h5')
        try_again = False
    except Exception as e:
        print(e)
        print("name taken, trying again...")
        j += 1
        try_again = True
print("name of data",data.name())
print("units should be",data.get_units('t'))
print("shape of data",ndshape(data))
end = time.time()
if multi_channel:
    fl.next('Dual-channel data')
else:
    fl.next('Single-channel data')
fl.plot(data)
fl.show()
#
