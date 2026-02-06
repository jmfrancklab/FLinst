from pylab import *
from Instruments import Bridge12, prologix_connection, gigatronics
from Instruments.bridge12 import convert_to_power, convert_to_mv
from serial import Serial
import time
from itertools import cycle

meter_readings = []

run_bridge12 = True
if run_bridge12:
    with Bridge12() as b:
        b.set_wg(True)
        b.set_rf(True)
        b.set_amp(True)
    
        time.sleep(5)
        this_return = b.lock_on_dip(ini_range=(9.819e9,9.825e9))
        #with prologix_connection() as p
        #    with gigatronics(prologix_instance=p, address=7) as g:
        #        meter_readings.append(g.read_power())
        dip_f = this_return[2] 
        print(("Dip frequency"),dip_f)
        print(("Meter reading"),meter_readings)
        #for j in range(3):
        #    _,_,dip_f = b.zoom()
        b.set_freq(dip_f)
        b.set_power(13.0)
        input("Minimzie RX...") 
        b.set_power(16.0)
        input("Minimzie RX...")
        b.set_power(19.0)
        input("Minimzie RX...")
        #b.set_power(22.0)
        #input("Minimzie RX...")
        #b.set_power(25.0)
        #input("Minimzie RX...")
        #b.set_power(28.0)
        #input("Minimzie RX...")
        #b.set_power(31.0)
        #input("Minimzie RX...")
        #b.set_power(33.0)
        #input("Minimzie RX...")
        #b.set_power(34.0)
        #input("Minimzie RX...")
        #b.set_power(35.0)
        #input("Minimzie RX...")
        #b.set_power(36.0)
        #input("Minimzie RX...")
        #b.set_power(40.0)
        #input("Minimzie RX...")
        result = b.tuning_curve_data
        
        
        
        #fits = b.fit_data
save_data = False
if save_data:
    filename = '200301_terminator_1'
    np.savez(filename+'.npz', **result)

def plot_all(show_log_scale=True):
    figure()
    #thesecolors = cycle('bgrcmyk')
    powerlist = []
    powerlist = list(set((float(k.split('dBm')[0 ]) for k in list(result.keys()))))
    powerlist.sort()

    #print "powerlist is",powerlist
    for power in powerlist:
        if show_log_scale:
            fmt = convert_to_power
        else:
            fmt = lambda x: x
        #thiscolor = next(thesecolors())
        show_fits = False
        plotstyle = 'o-'
        if show_fits: plotstyle = 'o'
        plot(result['%ddBm_freq'%power],
             fmt(result['%ddBm_rx'%power]),
             plotstyle,label='%s'%power)
        ylabel('Power (dBm)')
        xlabel('Frequency (Hz)')
        if show_fits:
            if '%ddBm_range'%power in list(fits.keys()):
     #           print "plotting fit for",power
                f_range = fits['%ddBm_range'%power]
                f_axis = r_[f_range[0]:f_range[1]:100j]
                plot(f_axis,
                        fmt(fits['%ddBm_func'%power](f_axis)),
                        '-')

                        #color=thiscolor)
plot_all();legend()
show()
