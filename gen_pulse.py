from Instruments import *
from pyspecdata import *
import time
from timeit import default_timer as timer
from serial.tools.list_ports import comports
import serial
import pprint
from scipy import signal

#raw_input("Warning --> Detach from amplifier before proceeding further (set AFG before hooking up, since it generates cw)")
print("Starting timer...")
start = timer()
acquire = False

fl = figlist_var()

#{{{ This is where amplitude spacing is declared
amp_space = logspace(log10(0.01),log10(0.86),40)
acq_space = list(range(1,len(amp_space)+1)) #includes left, excludes right
acq_amp_dict = {}
for x,y in zip(acq_space,amp_space):
    temp=dict([(x,y)])
    acq_amp_dict.update(temp)
print("Capture number: amplitude in mVpp:")
pprint.pprint(acq_amp_dict)
#}}}

print("These are the instruments available:")
SerialInstrument(None)
print("done printing available instruments")

with SerialInstrument('GDS-3254') as s:
    print(s.respond('*idn?'))
    
with SerialInstrument('AFG-2225') as s:
    print(s.respond('*idn?'))

def acquire(x):
    datalist = []
    print("about to load GDS")
    num_averages = 16
    with GDS_scope() as g:
    #    g.timscal(5e-6)  #setting time scale to 500 ns/div
    #    g.voltscal(1,500e-3) #setting volt scale on channel 1 to 500 mV/div
        print("loaded GDS")
        ch1_waveform = g.waveform(ch=1)
        ch2_waveform = g.waveform(ch=2)
        for j in range(num_averages-1):
            print("average #",j)
            ch1_waveform += g.waveform(ch=1)
            ch2_waveform += g.waveform(ch=2)
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
    data_name = 'capture%d_180803'%x
    data.name(data_name)
    data.hdf5_write('180803_sweep_spec.h5')
    print("capture number",x)
    print("name of data",data.name())
    print("units should be",data.get_units('t'))
    print("shape of data",ndshape(data))
    fl.next('Dual-channel data')
    fl.plot(data)
    return

def gen_pulse(freq=14.8e6, width=4e-6, ch1_only=True):
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
            a.set_burst(per=100e-3) #effectively sets duty cycle (100msec b/w bursts)
            #set_amp = 1
            #for acq_no,set_amp in list(acq_amp_dict.items()):
            #   a[this_ch].ampl=set_amp
            #   input("Adjust scope settings, continue")
            #   acquire(acq_no)
print("Generating pulse...")
gen_pulse()
end = timer()
print("time:",(end-start),"s")

