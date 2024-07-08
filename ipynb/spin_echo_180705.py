
# coding: utf-8

# In[ ]:

cd ..

from Instruments import *
from pyspecdata import *
import time
from timeit import default_timer as timer
from serial.tools.list_ports import comports
import serial
from scipy import signal

#%matplotlib notebook

fl = figlist_var()


# In[ ]:

#timing and setting up parameters for arbitrary wavefunction output


# In[ ]:

freq_carrier = 14.445e6 #[Hz] rf pulse
points_total = 4096 # maximum points allowed
t_90 = 2.27e-6 #[s] 90 time 
t_180 = 2*t_90 #[s] 180 time
t_d1 = 40e-6 #[s] delay between 90 and 180

t_sp = (t_90+t_180+t_d1)/points_total
print t_sp

# these point values, I can use to set the delay to 0
points_90 = t_90/t_sp
print points_90
points_180 = t_180/t_sp
print points_180
# to maximize d1, do the following
points_d1 = points_total - points_90 - points_180
print points_d1

points_seq = points_90 + points_180 + points_d1
print points_seq
assert points_seq < 4097


# In[ ]:

#Here is a functioning version of generating spin echo sequence with exponential array
#and a change in phase


# In[ ]:

start = timer()
with AFG() as a:
    a.reset()
    freq_carrier = 14.445e6 #[Hz] rf pulse
    rate = 4*freq_carrier # parameter needed for AFG
    t = r_[0:4096]
    freq = 0.25
    y = 0*t
    y = exp(1j*2*pi*t[1:-2]*freq)
    y[int(points_90):int(points_90+points_d1)] = 0
    y[int(points_90+points_d1+1)] = 0 # this is so p180 has same phase as p90
    # I do not think that it matters with phase cycling, but just to be safe...
    
    y_ph = y.copy()
    ph1=1
    y_ph[1:int(points_90)] *= exp(1j*pi/2*ph1)
    #y[int(points_90+points_d1+1)] = *= exp(1j*pi/2*ph2)
    
    ch_list = [0]
    for this_ch in ch_list:
        start1 = timer()
        a[this_ch].ampl = 10.
        a[this_ch].digital_ndarray(y, rate=rate)
        a[this_ch].output = True
        a[this_ch].burst = True
        a.set_burst(per=1) #per=T2 of sample
    end1 = timer()
    with GDS_scope() as g:
        ch1_waveform = g.waveform(ch=1)
        data1 = ch1_waveform.reorder('t')
        channels = ((ndshape(data1))).alloc()
        channels.setaxis('t',data.getaxis('t')).set_units('t','s')
        print "I have captured"
    for this_ch in ch_list:
        start2 = timer()
        a[this_ch].digital_ndarray(y_ph, rate=rate)
        #a[this_ch].output = True
        a[this_ch].burst = True
        # do not need to set output or the burst period, since AFG has not been reset
    with GDS_scope() as g:
        ch1_waveform = g.waveform(ch=1)
        data2 = ch1_waveform.reorder('t')
        channels = ((ndshape(data2))).alloc()
        channels.setaxis('t',data.getaxis('t')).set_units('t','s')
        print "I have captured"
    end2 = timer()

print end1 - start1
print end2 - start2


# In[ ]:

#This is a functioning version of a phase cycled sequence


# In[ ]:

start = timer()
data_list = {}

with AFG() as a:
    a.reset()
    freq_carrier = 14.445e6 #[Hz] rf pulse
    rate = 4*freq_carrier # parameter needed for AFG
    t = r_[0:4096]
    freq = 0.25
    y = 0*t
    y = exp(1j*2*pi*t[1:-2]*freq)
    y[int(points_90):int(points_90+points_d1)] = 0
    y[int(points_90+points_d1+1)] = 0 # this is so p180 has same phase as p90
    y_ph = y.copy()
    
    #ph1=1
    #y_ph[1:int(points_90)] *= exp(1j*pi/2*ph1)
    #y[int(points_90+points_d1+1)] = *= exp(1j*pi/2*ph2)
    
    ch_list = [0]
    for this_ch in ch_list:
        start_cycle = timer()
        a[this_ch].ampl = 10.
        a[this_ch].digital_ndarray(y, rate=rate)
        a[this_ch].output = True
        a[this_ch].burst = True
        a.set_burst(per=1) #cycling period = T2 of sample
        for ph2 in xrange(0,4,2):
            figure()
            print "Phasing 180 by ph2=",ph2,"..."
            y_ph[int(points_90+points_d1+1):-2] *= exp(1j*pi/2*ph2)
            print "Phased 180 by ph2=",ph2
            for ph1 in xrange(4):
                y_ph[1:int(points_90)] *= exp(1j*pi/2*ph1)
                print "Phasing 90 by ph1=",ph1,"..."
                a[this_ch].digital_ndarray(y_ph, rate=rate)
                a[this_ch].burst = True
                print "Phased 90 by ph1=",ph1
                with GDS_scope() as g:
                    print "Attempting to capture"
                    ch1_waveform = g.waveform(ch=1)
                    data = ch1_waveform.reorder('t')
                    plot(data)
                    show()
                    print "Exiting capture"
    end_cycle = timer()

print end_cycle - start_cycle


# In[ ]:

#Trying to implement averaging on scope before capture, attempt 1


# In[ ]:

start = timer()
data_list = {}

with AFG() as a:
    a.reset()
    freq_carrier = 14.445e6 #[Hz] rf pulse
    rate = 4*freq_carrier # parameter needed for AFG
    t = r_[0:4096]
    freq = 0.25
    y = 0*t
    y = exp(1j*2*pi*t[1:-2]*freq)
    y[int(points_90):int(points_90+points_d1)] = 0
    y[int(points_90+points_d1+1)] = 0 # this is so p180 has same phase as p90
    y_ph = y.copy()
    
    #ph1=1
    #y_ph[1:int(points_90)] *= exp(1j*pi/2*ph1)
    #y[int(points_90+points_d1+1)] = *= exp(1j*pi/2*ph2)
    
    ch_list = [0]
    for this_ch in ch_list:
        start_cycle = timer()
        a[this_ch].ampl = 10.
        a[this_ch].digital_ndarray(y, rate=rate)
        a[this_ch].output = True
        a[this_ch].burst = True
        a.set_burst(per=1) #cycling period = T2 of sample
        for ph2 in xrange(0,4,2):
            figure()
            print "Phasing 180 by ph2=",ph2,"..."
            y_ph[int(points_90+points_d1+1):-2] *= exp(1j*pi/2*ph2)
            print "Phased 180 by ph2=",ph2
            for ph1 in xrange(4):
                y_ph[1:int(points_90)] *= exp(1j*pi/2*ph1)
                print "Phasing 90 by ph1=",ph1,"..."
                a[this_ch].digital_ndarray(y_ph, rate=rate)
                a[this_ch].burst = True
                print "Phased 90 by ph1=",ph1
                with GDS_scope() as g:
                    print "Attempting to capture"
                    ch1_waveform = g.waveform(ch=1)
                    data = ch1_waveform.reorder('t')
                    plot(data)
                    show()
                    print "Exiting capture"
    end_cycle = timer()

print end_cycle - start_cycle


# In[ ]:

#Trying to implement averaging on scope before capture, attempt 2


# In[ ]:

start = timer()
data_list = {}

with AFG() as a:
    a.reset()
    freq_carrier = 14.445e6 #[Hz] rf pulse
    rate = 4*freq_carrier # parameter needed for AFG
    t = r_[0:4096]
    freq = 0.25
    y = 0*t
    y = exp(1j*2*pi*t[1:-2]*freq)
    y[int(points_90):int(points_90+points_d1)] = 0
    y[int(points_90+points_d1+1)] = 0 # this is so p180 has same phase as p90
    y_ph = y.copy()
    
    #ph1=1
    #y_ph[1:int(points_90)] *= exp(1j*pi/2*ph1)
    #y[int(points_90+points_d1+1)] = *= exp(1j*pi/2*ph2)
    
    ch_list = [0]
    for this_ch in ch_list:
        start_cycle = timer()
        a[this_ch].ampl = 10.
        a[this_ch].digital_ndarray(y, rate=rate)
        a[this_ch].output = True
        a[this_ch].burst = True
        a.set_burst(per=1) #cycling period = T2 of sample
        for ph2 in xrange(0,4,2):
            figure()
            print "Phasing 180 by ph2=",ph2,"..."
            y_ph[int(points_90+points_d1+1):-2] *= exp(1j*pi/2*ph2)
            print "Phased 180 by ph2=",ph2
            for ph1 in xrange(4):
                y_ph[1:int(points_90)] *= exp(1j*pi/2*ph1)
                print "Phasing 90 by ph1=",ph1,"..."
                a[this_ch].digital_ndarray(y_ph, rate=rate)
                a[this_ch].burst = True
                print "Phased 90 by ph1=",ph1
                with GDS_scope() as g:
                    print "Attempting to capture"
                    print "Waiting..."
                    time.sleep(10)
                    print "Done waiting"
                    ch1_waveform = g.waveform(ch=1)
                    data = ch1_waveform.reorder('t')
                    plot(data)
                    show()
                    print "Exiting capture"
    end_cycle = timer()

print end_cycle - start_cycle


# In[ ]:

#Implemting averaging after capturing (not using scope averaging)


# In[ ]:

start = timer()
num_averages = 64

with AFG() as a:
    a.reset()
    freq_carrier = 14.445e6 #[Hz] rf pulse
    rate = 4*freq_carrier # parameter needed for AFG
    t = r_[0:4096]
    freq = 0.25
    y = 0*t
    y = exp(1j*2*pi*t[1:-2]*freq)
    y[int(points_90):int(points_90+points_d1)] = 0
    y[int(points_90+points_d1+1)] = 0 # this is so p180 has same phase as p90
    y_ph = y.copy()
    
    #ph1=1
    #y_ph[1:int(points_90)] *= exp(1j*pi/2*ph1)
    #y[int(points_90+points_d1+1)] = *= exp(1j*pi/2*ph2)
    
    ch_list = [0]
    for this_ch in ch_list:
        start_cycle = timer()
        a[this_ch].ampl = 10.
        a[this_ch].digital_ndarray(y, rate=rate)
        a[this_ch].output = True
        a[this_ch].burst = True
        a.set_burst(per=1) #cycling period = T2 of sample
        for ph2 in xrange(0,4,2):
            figure()
            print "Phasing 180 by ph2=",ph2,"..."
            y_ph[int(points_90+points_d1+1):-2] *= exp(1j*pi/2*ph2)
            print "Phased 180 by ph2=",ph2
            for ph1 in xrange(4):
                y_ph[1:int(points_90)] *= exp(1j*pi/2*ph1)
                print "Phasing 90 by ph1=",ph1,"..."
                a[this_ch].digital_ndarray(y_ph, rate=rate)
                a[this_ch].burst = True
                print "Phased 90 by ph1=",ph1
                with GDS_scope() as g:
                    print "Attempting to capture"
                    ch1_waveform = g.waveform(ch=1)
                    print "Beginning to average"
                    for u in xrange(num_averages-1):
                        ch1_waveform += g.waveform(ch=1)
                    data = ch1_waveform.reorder('t')
                    data /= num_averages
                    print "Finished avearaging"
                    plot(data)
                    show()
                    print "Exiting capture"
    end_cycle = timer()

print end_cycle - start_cycle

