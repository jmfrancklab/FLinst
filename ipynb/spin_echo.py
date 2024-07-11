
# coding: utf-8

# In[ ]:

cd ..


# In[ ]:

from Instruments import *
from pyspecdata import *
import time
from timeit import default_timer as timer
from serial.tools.list_ports import comports
import serial
from scipy import signal


# In[ ]:

fl = figlist_var()


# In[ ]:

freq = 14.5e6
rate = freq*4
print rate,"MHz, rate"
max_width = 4097/rate
print max_width*1e6,u"\u03bcs max width"
width = 2.8e-6 + (2.8*2)*1e-6 + 50e-6
print width*1e6,u"\u03bcs this width"
this_samples = width*rate
this_samples_int4 = int(this_samples/4 + 0.5)*4
print this_samples_int4,"samples at this width"
total_samples = max_width*rate
print total_samples,"samples at max width"


# In[ ]:

time_spacing = (59.0e-6)/(3424.)
print time_spacing*1e6,u"\u03bcs between pts"
points_for_90 = (3e-6)/(time_spacing)
print points_for_90,u"pts needed for 90 pulse (i.e., that make up 2.8 \u03bcs)"
points_for_90_int4 = int(points_for_90/4 + 0.5)*4
print points_for_90_int4,"pts for 90, integer of 4"
points_for_deadtime = (50e-6)/(time_spacing)
print points_for_deadtime,u"pts needed for dead time (i.e., that make up 50 \u03bcs)"
points_for_deadtime_int4 = int(points_for_deadtime/4 + 0.5)*4
print points_for_deadtime_int4,"pts for deadtime, integer of 4"
points_for_180_int4 = points_for_90_int4*2
print points_for_180_int4,u"pts for 180, integer of 4 \u03bcs"

width = points_for_90_int4 + points_for_deadtime_int4 + points_for_180_int4
print '\n'
print width,"total number of points"
width_int4 = int(width/4 + 0.5)*4
print width_int4,"total number of points, integer of 4"


# In[ ]:

y = zeros(width_int4)
y[0::4] = 0
y[1::4] = 1
y[2::4] = 0
y[3::4] = -1
y[-1] = 0


# In[ ]:

#slice notation not inclusive of last index
# y[0:177] - this is the 90 pulse
y[177:3077] = 0
# width_int4 - points_for_180_int4 = 3077
# y[3077:3428] - this is the 180 pulse


# In[ ]:

start = timer()
with AFG() as a:
    a.reset()
    freq = 14.5e6
    rate = freq*4
    width = 58.4e-6
    total_samples = width*rate
    total_samples = int(total_samples/4 + 0.5)*4
    assert total_samples < 4097
    y = zeros(total_samples)
    y[0::4] = 0
    y[1::4] = 1
    y[2::4] = 0
    y[3::4] = -1
    y[-1] = 0
    y[177:3077] = 0
    ch_list = [0]
    for this_ch in ch_list:
        a[this_ch].digital_ndarray(y, rate=rate)
        a[this_ch].output=True
        a[this_ch].burst=True
        end = timer()


# In[ ]:

print end-start

