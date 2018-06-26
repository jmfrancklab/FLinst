from Instruments import *
from pyspecdata import *
import time
from timeit import default_timer as timer
from serial.tools.list_ports import comports
import serial
from scipy import signal

acquire = False
fl = figlist_var()

print "These are the instruments available:"
SerialInstrument(None)
print "done printing available instruments"

with SerialInstrument('GDS-3254') as s:
    print s.respond('*idn?')
    
def collect(date,id_string,captures):
    capture_length = len(captures)
    start = timer()
    datalist = []
    print "about to load GDS"
    with GDS_scope() as g:
        print "loaded GDS"
        for x in xrange(1,capture_length+1):
            print "entering capture",x
            ch1_waveform = g.waveform(ch=1)
            ch2_waveform = g.waveform(ch=2)
            data = concat([ch1_waveform,ch2_waveform],'ch').reorder('t')
            if x == 1:
                channels = ((ndshape(data)) + ('capture',capture_length)).alloc()
                channels.setaxis('t',data.getaxis('t')).set_units('t','s')
                channels.setaxis('ch',data.getaxis('ch'))
            channels['capture',x-1] = data
            #{{{ in case pulled from inactive channel
            if not isfinite(data.getaxis('t')[0]):
                j = 0
                while not isfinite(data.getaxis('t')[0]):
                    data.setaxis('t',datalist[j].getaxis('t'))
                    j+=1
                    if j == len(datalist):
                        raise ValueError("None of the time axes returned by the scope are finite, which probably means no traces are active??")
            #}}}
    s = channels
    s.labels('capture',captures)
    s.name('accumulated_'+date)
    s.hdf5_write(date+'_'+id_string+'.h5')
    print "name of data",s.name()
    print "units should be",s.get_units('t')
    print "shape of data",ndshape(s)
    return start

date = '180625'
id_string = 'network_22MHz_pulse_noise_2'
captures = linspace(1,100,100)

print "Starting collection..."
start = collect(date,id_string,captures)
end = timer()
print "Collection time:",(end-start),"s"
