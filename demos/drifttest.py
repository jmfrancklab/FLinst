from pylab import *
from Instruments import Bridge12
from Instruments.bridge12 import convert_to_power, convert_to_mv
from serial import Serial
import time
from itertools import cycle
from pyspecdata import *

with Bridge12() as b:
    b.set_wg(True)
    b.set_rf(True)
    b.set_amp(True)
    b.set_power(10.0)
    b.freq_sweep(r_[9.81:9.83:20j]*1e9)
    b.lock_on_dip()
    for j in xrange(5):
        b.zoom(dBm_increment=3)
    #b.zoom(dBm_increment=2)
        
    result = b.tuning_curve_data
    
    f_axis = result['28dBm_freq']
    time_points = 5
    f_step = 2 # every other freq
    
    b.set_rf(False)
    time.sleep(2)
    
    rxpowers = ndshape([len(f_axis)/f_step,time_points],['freq','t_point']).alloc()
    rxpowers.setaxis('freq',f_axis[::2])
    rxpowers.setaxis('t_point',r_[0:time_points]) 
    for i,j in enumerate(r_[0:len(f_axis):2]): # good_freqs is highest power freq axis
        b.set_amp(True)
        b.set_rf(True)
        b.set_freq(f_axis[j])
        b.set_power(28)
        print "AT FREQUENCY NO. %d of %d"%(j,len(f_axis))
        # acquire 10 rxpower values 2 seconds apart (may need to adjust depending on length of DNP measurements to accuarately predict drift)
        for k in xrange(time_points):
            print "TIME POINT NO. %d"%k
            rxpowers['freq',i]['t_point',k] = b.rxpowermv_float()
            time.sleep(10)
        b.set_rf(False)
        time.sleep(2)
        
def plot_all():
    figure()
    powerlist = []
    thesecolors = cycle(list('bgrcmyk'))
    powerlist = list(set((float(k.split('dBm')[0 ]) for k in result.keys())))
    powerlist.sort()
    print "powerlist is",powerlist
    for power in powerlist:
        show_log_scale = True
        if show_log_scale:
            fmt = convert_to_power
        else:
            fmt = lambda x: x
        thiscolor = thesecolors.next()
        show_fits = False
        plotstyle = 'o-'
        if show_fits: plotstyle = 'o'
        plot(result['%ddBm_freq'%power],
             fmt(result['%ddBm_rx'%power]),
             plotstyle,
             color=thiscolor,
             label='%s'%power)
        if show_fits:
            if '%ddBm_range'%power in fits.keys():
                print "plotting fit for",power
                f_range = fits['%ddBm_range'%power]
                f_axis = r_[f_range[0]:f_range[1]:100j]
                plot(f_axis,
                        fmt(fits['%ddBm_func'%power](f_axis)),
                        '-',
                        color=thiscolor)
plot_all();legend()
  
