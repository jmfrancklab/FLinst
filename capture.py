from Instruments import *
from pyspecdata import *
import time
from serial.tools.list_ports import comports
import serial
from scipy import signal
fl = figlist_var()

default = True
try:
    sys.argv[1]
    default = False 
except:
    sys.argv[0]
if default:
    ref_amp = 3.0
    volt_scale = 200e-3

datalist = []
print("about to load GDS")
#raw_input("Turn on RF amp") 

with GDS_scope() as g:
    raise ValueError("Don't forget to change the acquire_mode and timscal to what you want!!!")
    g.timscal(50e-6)  #set to 5 microsec/div
    for this_ch in range(2):
        g[this_ch].voltscal = volt_scale
    print("loaded GDS")
    g.acquire_mode('average',32)
    input("Wait for averaging to relax...")
    for j in range(n_captures):
        datalist.append(g.waveform(ch=0))
data = concat(datalist,'repeats').reorder('t')
j = 1
try_again = True
while try_again:
    data_name = 'capture%d'%j
    data.name(data_name)
    try:
        data.hdf5_write('201202_triwave_RMprobe_50ms.h5')
        try_again = False
    except Exception as e:
        print(e)
        print("name taken, trying again...")
        j += 1
        try_again = True
print(("name of data",data.name()))
print(("units should be",data.get_units('t')))
fl.next('Dual-channel data')
fl.plot(data)
fl.show()

