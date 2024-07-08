from Instruments import *
from pyspecdata import *
import time
from serial.tools.list_ports import comports
import serial
from scipy import signal

input("Warning --> Detach from amplifier before proceeding further (set AFG before hooking up, since it generates cw)")

acquire = False

fl = figlist_var()

print("These are the instruments available:")
SerialInstrument(None)
print("done printing available instruments")

with SerialInstrument('GDS-3254') as s:
    print(s.respond('*idn?'))
    
with SerialInstrument('AFG-2225') as s:
    print(s.respond('*idn?'))

def acquire():
    datalist = []
    print("about to load GDS")
    num_averages = 16
    with GDS_scope() as g:
    #    g.timscal(5e-6)  #setting time scale to 500 ns/div
    #    g.voltscal(1,500e-3) #setting volt scale on channel 1 to 500 mV/div
        print("loaded GDS")
        ch1_waveform = g.waveform(ch=1)
        ch2_waveform = g.waveform(ch=1)
        for j in range(num_averages-1):
            print("average #",j)
            ch1_waveform += g.waveform(ch=1)
            ch2_waveform += g.waveform(ch=1)
    data = concat([ch1_waveform,ch2_waveform],'ch').reorder('t')
    data /= num_averages
    # {{{ in case it pulled from an inactive channel
    if not isfinite(data.getaxis('t')[0]):
        j = 0
        while not isfinite(data.getaxis('t')[0]):
            data.setaxis('t',datalist[j].getaxis('t'))
            j+=1
            if j == len(datalist):
                raise ValueError("None of the time axes returned by the scope are finite, which probably means no traces are active??")
    # }}}
    j = 1
    try_again = True
    while try_again:
        data_name = 'capture%d_180320'%j
        data.name(data_name)
        try:
            data.hdf5_write('180320_test.h5')
            try_again = False
            print("capture number",j)
        except:
            print("name taken, trying again...")
            j += 1
            try_again = True
    print("name of data",data.name())
    print("units should be",data.get_units('t'))
    print("shape of data",ndshape(data))
    fl.next('Dual-channel data')
    fl.plot(data)
    

def gen_pulse(freq=14.5e6, width=4e-6, ch1_only=True):
    with AFG() as a:
        a.reset()
        rate = freq*4
        total_samples = width*rate
        total_samples = int(total_samples/4 + 0.5)*4 # convert to multiple of 4
        assert total_samples < 4097, "Your pattern length (%d) exceeds the max (4096 samples at %g MHz)"%(total_samples,rate)
        y = zeros(total_samples)
        y[0::4]=0
        y[1::4]=1
        y[2::4]=0
        y[3::4]=-1
        y[-1]=0
        if ch1_only:
            ch_list = [0]
        else:
            ch_list = [0,1]
        for this_ch in ch_list:
            a[this_ch].digital_ndarray(y, rate=rate)
            print("now, output on")
            a[this_ch].output = True
        for this_ch in range(1):
            a[this_ch].burst = True
            a.set_burst(per=500e-6)
            for set_amp in linspace(25e-3,2.5,50):
                a[this_ch].ampl=set_amp
                input("Stopping at 25mVpp.")
                acquire()
gen_pulse()

