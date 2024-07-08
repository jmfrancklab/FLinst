from Instruments import *
from pyspecdata import *
import time
from timeit import default_timer as timer
from serial.tools.list_ports import comports
import serial
from scipy import signal

fl = figlist_var()
    
def collect(date,id_string,captures):
    cap_len = len(captures)
    datalist = []
    print("about to load GDS")
    with GDS_scope() as g:
        print("loaded GDS")
        start = time.time()
        for x in range(1,cap_len+1):
            print("entering capture",x)
            ch1_waveform = g.waveform(ch=1)
            ch2_waveform = g.waveform(ch=2)
            data = concat([ch1_waveform,ch2_waveform],'ch').reorder('t')
            if x == 1:
                channels = ((ndshape(data)) + ('capture',cap_len)).alloc()
                channels.setaxis('t',data.getaxis('t')).set_units('t','s')
                channels.setaxis('ch',data.getaxis('ch'))
            channels['capture',x-1] = data
        end = time.time()
    # {{{ in case it pulled from an inactive channel
    if not isfinite(data.getaxis('t')[0]):
        j = 0
        while not isfinite(data.getaxis('t')[0]):
            data.setaxis('t',datalist[j].getaxis('t'))
            j+=1
            if j == len(datalist):
                raise ValueError("None of the time axes returned by the scope are finite, which probably means no traces are active??")
    # }}}
    s = channels
    s.labels('capture',captures)
    s.name('accumulated_'+date)
    s.hdf5_write(date+'_'+id_string+'.h5')
    print("name of data",s.name())
    print("units should be",s.get_units('t'))
    print("shape of data",ndshape(s))
    print("TIME:",end-start)
    return

date = '190201'
id_string = 'SpinCore_pulses'
captures = linspace(1,300,300)
collect(date,id_string,captures) # as of now, last variable is node index
                                   # and this needs to be updated with run 
##{{{ this is code that can be used to generate all at once,
##       but personally feel uncomfortable with delay between writing to node
##       and continuing collection
#sweep_time = 3072 #[s] - get this from xepr parameters for current sweep
#capture_time = 1518 #[s] - approx, from timing captures for desired capture length 
#for x in xrange(sweep_time/capture_time):
#    # call acquire for as many times as needed for the sweep time, with
#    # each call containing its own index that gets incorporated into node name
#    acquire(date,id_string,captures,x)    
#    #}}}
