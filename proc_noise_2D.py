from pyspecdata import *
fl = figlist_var()
import os
import sys
import matplotlib.style
import matplotlib as mpl

mpl.rcParams['image.cmap'] = 'jet'

def load_noise(date,id_string,captures):
    cap_len = len(captures)
    filename = date+'_'+id_string+'.h5'
    try:
        s = nddata_hdf5(filename+'/accumulated_'+date,
                directory=getDATADIR(exp_type='test_equip'))
        s.set_units('t','s')
    except:
        print("accumulated data was not found, pulling individual captures")
        for j in range(1,cap_len+1):
            j_str = str(j)
            d = nddata_hdf5(filename+'/capture'+j_str+'_'+date,
                directory=getDATADIR(exp_type='test_equip'))
            d.set_units('t','s')
            if j == 1:
                channels = ((ndshape(d)) + ('capture',cap_len)).alloc()
                channels.setaxis('t',d.getaxis('t')).set_units('t','s')
                channels.setaxis('ch',d.getaxis('ch'))
            print("loading signal %s into capture %s "%(j_str,j_str))
            channels['capture',j-1]=d        
        s = channels
        s.labels('capture',captures)
        s.name('accumulated_'+date)
        s.hdf5_write(filename,
                directory=getDATADIR(exp_type='test_equip'))
    return s


gain_factor_dcasc12 = 114008.55204672
gain_factor = 1
captures = linspace(1,100,100)
for date,id_string,numchan,gain_factor in [
#        ('180627','test_se_amp_4',2,gain_factor),
#        ('180628','test_se_amp',2,gain_factor),     #d_interseq = 5*100e-3
#        ('180628','test_se_amp_2',2,gain_factor),   #d_interseq = 100e-3
#        ('180628','test_se_amp_3',2,gain_factor),    #trig_mod = normal, trig = ch1  
#        ('180628','test_se_amp_4',2,gain_factor),      
#        ('180628','test_se_amp_5',2,gain_factor),    #50 MSamples/sec  
#        ('180628','test_se_amp_6',2,gain_factor),    #100 MSamples/sec  
#        ('180628','test_se_amp_7',2,gain_factor),    #100 MSamples/sec adjusting position
#        ('180628','test_se_amp_8',2,gain_factor),    #100 MSamples/sec adjusting position again
#        ('180628','test_se_amp_9',2,gain_factor),    #100 MSamples/sec adjusting position again; no capture ch2
#        ('180628','test_se_amp_10',2,gain_factor),    #100 MSamples/sec adjusting position again; no capture ch2
#        ('180628','test_se_amp_11',2,gain_factor),    #probe in magnet, with my sample, magnetic field going - just test
#        ('180628','test_se_amp_12',2,gain_factor),   #made some adjustments to pulse timing, specifically position in the capture
        ('180628','spin_echo_exp',1,gain_factor),    
        ('180628','spin_echo_exp2_cont',1,gain_factor),    
        ('180628','spin_echo_exp2_cont2',1,gain_factor),    
#        ('180628','noise_AFG_off_amp_off_sample_in_magnet_on',1,gain_factor_dcasc12),
#        ('180628','noise_AFG_off_amp_off_sample_in_magnet_off',1,gain_factor_dcasc12),
        ]:
    s = load_noise(date,id_string,captures)['ch',0]['capture':(0,10000)]
    s.ft('t',shift=True)
#    fl.next('plot')
#    fl.plot(s)
    s = abs(s['t':(0,30e6)]).run(log10)
#    width = 0.01e6
#    im.convolve('t',width)
    fl.next('%s'%id_string)
    fl.image(s.real,interpolation='bicubic')
#    s.ift('t')
#    fl.next('analytic, low-pass (t) %s'%id_string)
#    fl.plot(s)
    
fl.show()
