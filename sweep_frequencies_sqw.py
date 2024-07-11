from Instruments import *
from pyspecdata import *
import time
import os
from serial.tools.list_ports import comports
import serial
from scipy import signal

fl = figlist_var()

print("These are the instruments available:")
SerialInstrument(None)
print("done printing available instruments")

with SerialInstrument('GDS-3254') as s:
    print(s.respond('*idn?'))
    
with SerialInstrument('AFG-2225') as s:
    print(s.respond('*idn?'))

with AFG() as a:
    a.reset()
    x = r_[-6:6:200j]
    y = zeros_like(x)
    y[0::4]=0
    y[1::4]=1
    y[2::4]=0
    y[3::4]=-1
    y[-1]=0
    for this_ch in range(2):
        print("Sending CH%d arbitrary waveform to AFG"%(this_ch+1))
        a[this_ch].digital_ndarray(y)
    for set_f in linspace(100e3,500e3,100):
        for this_ch in range(2):
            print("Now setting frequency to ",(set_f))
            a[this_ch].freq=set_f
            #print "Thus CH",(this_ch+1),"array freq is",set_f,"Hz"
            #print "CH%d burst set to"%(this_ch+1),a[this_ch].burst
            #print "Now turning CH%d output on..."%(this_ch+1)
            a[this_ch].output = True
        for this_ch in range(2):
            a[this_ch].burst = True
            #if we run a.check_idn() here, it pops out of burst mode
            datalist = []
        print("Now loading GDS...")
        with GDS_scope() as g:
            g.timscal(2e-6)  
            if set_f < 350e3:
                ch1vs = 1E0
            else:
                ch1vs = 500E-3
            if set_f < 320e3:
                ch2vs = 1E0
            else:
                ch2vs = 500E-3
            g.CH1.voltscal=ch1vs
            g.CH2.voltscal=ch2vs
            print("loaded GDS")
            for j in range(1,3):
                print("trying to grab data from channel",j)
                datalist.append(g.waveform(ch=j))
        data = concat(datalist,'ch').reorder('t')
        # {{{ use integer j to make a unique dataset name
        j = 1
        try_again = True
        while try_again:
            data_name = 'capture%d_F%04.3fMHz'%(j,(set_f*50)/1e6)
            data.name(data_name)
            try:
                data.hdf5_write('171229_series.h5',
                        directory=getDATADIR(exp_type='test_equip'))
                try_again = False
            except:
                print("name taken, trying again...")
                j += 1
                try_again = True
        # }}}
        print("name of data",data.name())
        print("units should be",data.get_units('t'))
        print("shape of data",ndshape(data))
        fl.next('Dual-channel data %4.3fMHz'%((set_f*50)/1e6))
        fl.plot(data, alpha=0.5)
    fl.show()

