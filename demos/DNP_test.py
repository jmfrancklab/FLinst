from pylab import *
from Instruments import Bridge12
from Instruments.bridge12 import convert_to_power, convert_to_mv
from serial import Serial
import time
from itertools import cycle
# {{{ determine the list of power settings
powers = r_[1e-3:2.0:20j]
dB_settings = round_(2*log10(powers/1e-3)*10.)/2
dB_settings = unique(dB_settings)
def check_for_3dB_step(x):
    assert len(x.shape) == 1
    if any(diff(x)>3.0):
        idx = nonzero(diff(x) > 3)[0][0] # pull the first one
        x = insert(x,idx+1,r_[x[idx]:x[idx+1]:3.0][1:]) # insert an array spaced by 3dB
        x = check_for_3dB_step(x)
        return x
    else:
        return x
ini_len = len(dB_settings)
dB_settings = check_for_3dB_step(dB_settings)
print "adjusted my power list by",len(dB_settings)-len(powers),"to satisfy the 3dB step requirement and the 0.5 dB resolution"
powers = 1e-3*10**(dB_settings/10.)
# }}}

with Bridge12() as b:
    b.set_wg(True)
    b.set_rf(True)
    b.set_amp(True)
    this_return = b.lock_on_dip(ini_range=(9.81e9,9.83e9))
    print "Frequency",dip_f
    dip_f = this_return[2]
    b.set_freq(dip_f)
    for j,this_power in enumerate(dB_settings):
        print "\n*** *** *** *** ***\n"
        print "SETTING THIS POWER",this_power,"(",powers[j],"W)"
        b.set_power(this_power)
        time.sleep(5)

    #rx_array = zeros_like(dB_settings)
    #tx_array = zeros_like(dB_settings)
    #for j,this_power in enumerate(dB_settings):
    #    print "Setting",this_power,"which is",powers[j],"W"
    #    b.set_power(this_power)
    #    if this_power >= 24.0:
    #        raw_input("Minimzie RX...")
    #        print "Accepted."
    #    rx_array[j] = b.rxpowermv_float()
    #    tx_array[j] = b.txpowermv_float()
        

        #if this_power < 29.0:
        #    time.sleep(10)
        #elif this_power > 29.0:
        #    time.sleep(2)
        result = b.tuning_curve_data
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