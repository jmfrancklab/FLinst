from Instruments import *
from pyspecdata import *
import time
from serial.tools.list_ports import comports
import serial
from scipy import signal
from sys import argv

start = time.time()
fl = figlist_var()

args = sys.argv[1:]
filename = '210111_sqwv_cap_probe_2.h5'
if '-f' in args: 
    force_acq = True
    args.pop(args.index('-f'))
else:
    force_acq = False
datalist = []
print(("about to load datasets",args))
for j,dataset in enumerate(args):
    print(("acquiring/loading dataset",dataset))
    if force_acq and j==len(args)-1:
        print("Forcing acquisition of last dataset")
        _,thisnode = h5nodebypath('%s/%s'%(filename,dataset))
        thisnode._f_remove(recursive=True)
    try:
        data = nddata_hdf5('%s/%s'%(filename,dataset))
    except:
        print(("didn't find %s: about to load GDS"%dataset))
        with GDS_scope() as g:
            print("loaded GDS")
            for j in range(1,2):
                print(("trying to grab data from channel",j))
                datalist.append(g.waveform(ch=j))
            data = concat(datalist,'ch').reorder('t')
        j = 1
        data.name(dataset)
        data.hdf5_write(filename)
        print(("name of data", data.name()))
        print(("units should be",data.get_units('t')))
        print(("shape of data",ndshape(data)))
    fl.next('raw signal')
    fl.plot(data,alpha=0.5)
fl.show()    
                                

