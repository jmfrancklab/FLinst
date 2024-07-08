from pyspecdata import *
import os
import sys
import matplotlib.style
import matplotlib as mpl
#from logging import DEBUG

#init_logging(level=DEBUG)

mpl.rcParams['image.cmap'] = 'jet'
fl = figlist_var()
# for JF - how can I pull the dimension of just one axis of an nddata?

average = False #Make true to calculate average in time domain 
reference = False #For calculating carrier frequency from reference channel
for date,id_string,numchan,gain_factor,captures in [
        #{{{ test for signal on 180630
    ('180630','spin_echo_exp_block1',2,1,6000), 
    #('180630','spin_echo_exp_block2',2,1,6000), 
    #('180630','spin_echo_exp_block3',2,1,500), 
    #('180630','spin_echo_exp_block4',2,1,300)
    #}}}
        #{{{ test for signal on 180628
    #('180628','spin_echo_exp2',2,1), 
    #('180628','spin_echo_exp2_cont',2,1), 
    #('180628','spin_echo_exp2_cont2',2,1), 
    #}}}
    ]:
    filename = date+'_'+id_string+'.h5'
    nodename = "accumulated_"+date
    ## {{{ to store a truncated file
    #filename = date+'_'+id_string+'.h5'
    #s = nddata_hdf5(filename+'/'+nodename,
    #        directory=getDATADIR(exp_type='test_equip'))['capture',0:100]
    #s.set_units('t','s')
    #s.name('test')
    #s.hdf5_write('test_data_180629.h5',
    #        directory=getDATADIR(exp_type='test_equip'))
    #exit()
    ## }}}
    if reference:
        #{{{ not finished -- for calculating carrier frequency
        s = nddata_hdf5(filename+'/'+nodename,
            directory=getDATADIR(exp_type='test_equip'))['ch',1]
        s.set_units('t','s')
        s.name('Volts')
        fl.next('Spin Echo')
        fl.plot(s['capture',1],alpha=0.3)
        fl.show()
        quit()
        pulse_threshold = 0.5
        pulse_slice = (s['capture',-1]).contiguous(lambda x: x>pulse_threshold*x.data.max())
        pulse_slice = pulse_slice[0,:]
        pulse_limits = pulse_slice + r_[0.6e-6,-0.6e-6]
        p_lim1,p_lim2 = pulse_limits
        fl.next('f plot')
        fl.plot(s['t':(p_lim1,p_lim2)])
        fl.show()
        quit()
        s.ft('t',shift=True)
        s['t':(None,5e5)] = 0
        s['t':(20e5,None)] = 0
        s.ift('t')
        #avg_f = s.mean('capture',return_error=False)
        #print "for: ",date+id_string,"average frequency\t",avg_f
        #}}}
    if not reference:
        s = nddata_hdf5(filename+'/'+nodename,
            directory=getDATADIR(exp_type='test_equip'))['ch',0]
        s.set_units('t','s')
        if average:
        #{{{ for averaging captures in time domain
        #q = s.mean('capture',return_error=False)
            q = s.sum('capture')
            q /= captures
            q.name('Volts')
            fl.next('Averaged signal, real')
            fl.plot(q.real,alpha=0.25,label=id_string)
            fl.next('Averaged signal, imaginary')
            fl.plot(q.imag,alpha=0.25,label=id_string)
        #}}}
        if not average:
            print("print 1")
            print(ndshape(s))
            s.ft('t',shift=True)
            s = s['t':(0,15.5e6)]
            print("print 2")
            print(ndshape(s))
            s.setaxis('t',lambda x: x - 14.5e6 - 16.95e3)
            #fl.next('FT of raw signal')
            #fl.image(abs(s))
            s_filt = s.C
            s_filt['t':(None,-1e6)] = 0
            print("print 3")
            print(ndshape(s_filt))
            s.ift('t')
            s_filt.ift('t')
            print("print 4")
            print(ndshape(s_filt))
            #s *= s.fromaxis('t',lambda x: exp(-1j*2*pi*resonance_freq))
            #fl.next('Raw signal')
            #fl.image(s)
            #logger.info('plotted raw signal')
            #fl.next('Filtered')
            #fl.image(s_filt)
            #logger.info('plotted filtered signal')
            #fl.next('filtered, cropped log')
            #fl.image(s_filt.C.cropped_log())
            #logger.info('plotted cropped log signal')
fl.show()
