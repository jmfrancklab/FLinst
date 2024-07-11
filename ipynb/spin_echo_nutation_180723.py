
# coding: utf-8

# In[1]:

cd ..


# In[2]:

from Instruments import *
from pyspecdata import *
import time
from timeit import default_timer as timer
from serial.tools.list_ports import comports
import serial
from scipy import signal


# In[5]:

get_ipython().magic(u'pylab inline')


# In[ ]:

get_ipython().magic(u'matplotlib notebook')


# In[6]:

fl = figlist_var()


# In[14]:

freq = 14.4289e6
T1 = 200e-3
t_90_range  = linspace(1.5e-6,6.0e-6,3) # range of 90 times
d_interseq = 5*T1       #[sec] time between sequence trigger 
freq_carrier = freq     #[Hz] rf pulse frequency
points_total = 4096     #[pts] total points, property of AFG
rate = freq_carrier*4   #[pts/sec] AFG requires for arb waveform
time_spacing = 1/rate   
time_total = time_spacing * points_total 
t_90 = t_90_range[-1]    
t_180 = 2*t_90          
# ***
t_tau = time_total - t_90 - t_180    # this must be held constant
t_correction = (2*t_90/pi) + (t_180/2)
t_interpulse = t_tau - t_correction    # decrease this until tau = constant
print t_tau
print t_correction
print t_interpulse
# ***

points_90 = t_90/time_spacing
points_180 = t_180/time_spacing 
points_tau = t_tau/time_spacing
points_correction = t_correction/time_spacing
points_interpulse = t_interpulse/time_spacing
print points_tau
print points_correction
print points_interpulse

time_sequence = t_90 + t_interpulse + t_180
points_sequence = points_90 + points_interpulse + points_180
print time_sequence
print points_sequence # needs to be less than 4097
assert (points_sequence < 4097)

# I think this is the correct pulse sequence to vary with a constant tau as defined in Cavanagh
for i,t_90 in enumerate(t_90_range):
    print "*** *** ENTERING INDEX %d *** ***"%i
    t_90 = t_90
    t_180 = 2*t_90
    t_correction = ((2/pi)*t_90) + 0.5*t_180
    t_interpulse = t_tau - t_correction
    t_total = t_90 + t_interpulse + t_180
    print "LENGTH OF 90 PULSE:",t_90
    print "LENGTH OF 180 PULSE:",t_180
    print "LEGNTH OF DELAY:",t_interpulse
    print "LENGTH OF TAU:",t_tau
    print "LENGTH OF PULSE SEQUENCE:",t_total
    points_90 = t_90/time_spacing
    points_interpulse = t_interpulse/time_spacing
    points_180 = t_180/time_spacing
    points_seq = points_90 + points_interpulse + points_180
    print "POINTS IN 90 PULSE",points_90
    print "POINTS IN 180 PULSE",points_180
    print "POINTS IN DELAY",points_interpulse
    print "POINTS IN TAU",points_interpulse+t_correction/time_spacing
    print "POINTS IN SEQUENCE:",points_seq
    print "*** *** GENERATING ARB WAVEFORM *** ***"
   #generating the arbitrary waveformM
    t = r_[0 : int(points_seq)]
    freq_sampling = 0.25
    y = exp(1j*2*pi*t[1 : -1]*freq_sampling)
    y[int(points_90) : int(points_90+points_interpulse)] = 0
    y[0] = 0
    y[-1] = 0
    figsize(14,14)
    plot(y+1*i,alpha=0.3)

