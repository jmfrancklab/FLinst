from pyspecdata import *
from pyspecdata.plot_funcs.image import imagehsv
import os
import sys
import matplotlib.style
import matplotlib as mpl
import argparse
#import logging

mpl.rcParams['image.cmap'] = 'jet'
fl = figlist_var()
#init_logging(level='debug')
parser = argparse.ArgumentParser(description='basic command-line options')
parser.add_argument('--window', '-w',
        help='the maximum size of the window that encompasses all the pulses',
        default=15e-6,
        type=float,
        dest='max_window')
parser.add_argument('--carrier', '-c',
        help='the carrier frequency',
        default=14.46e6,
        type=float,
        dest='carrier_f')
args = parser.parse_args(sys.argv[1:])
#print args.max_window # this would work
globals().update(vars(args)) # this directly inserts the info above into
#                              namespace of global variables

for date,id_string,numchan,indirect_range in [
        ('181003','spin_echo',2,None) # spin echo, B0 = 3403
        ]:
    filename = date+'_'+id_string+'.h5'
    nodename = 'this_capture'

    s = nddata_hdf5(filename+'/'+nodename,
            directory = getDATADIR(exp_type='test_equip'))
    s.set_units('t','s')
    logger.debug(strm('dimensions are:',ndshape(s)))
    is_nutation = False
    if 't_90' in s.dimlabels:
        s.rename('t_90','indirect')
        is_nutation = True
        logger.info('This is a nutation curve')
    if 'full_cyc' in s.dimlabels:
        s.rename('full_cyc','indirect')
    if 'average' in s.dimlabels:
        s.rename('average','indirect')
    logger.info("*** Code for phase cycling based on 'fix_phase_cycling_180712.py' ***")
    logger.info("WARNING: Need to define time slices for pulses on a by-dataset basis ***")

    this_gain = 73503.77279 # gain factor
    s /= sqrt(this_gain) 
    #s.set_units('V')
    s.labels('ph1',r_[0:4]/4.)
    s.labels( 'ph2',r_[0:4:2]/4. )
    fl.next('following ref ch pulses')
    fl.plot(s['indirect',0]['ph1',0]['ph2',0]['ch',1],label='raw')
    s_raw = s.C.reorder('t',first=False)
    s.ft('t',shift=True)
    s = s['t':(0,None)]
    s.setaxis('t',lambda f: f-carrier_f)
    s.ift('t')
    s = s*2
    single_90 = False 
    confirm_triggers = False 
    #{{{ confirm that different phases trigger differently due to differing rising edges
    if confirm_triggers:
        print(ndshape(s))
        print(ndshape(s_raw))
        subset = s['ch',1]['t':(1e-6,100e-6)]
        fl.next('raw data')
        if not single_90:
            fl.plot(s_raw['ch',1]['indirect',0]['ph2',0].reorder('t').real)
            onephase = subset.C.smoosh(['ph2','indirect'], noaxis = True, dimname='repeat').reorder('t')
            onephase_raw = s_raw['ch',1].C.smoosh(['ph2','indirect'], noaxis=True, dimname='repeat').reorder('t')
            print("dimensions of re-grouped raw data",ndshape(onephase_raw))
        if single_90:
            fl.plot(s_raw['ch',1]['indirect',-1].reorder('t').real)
            onephase = subset.C.reorder('t')
            onephase.rename('indirect','repeat')
            onephase_raw = s_raw['ch',1].C.reorder('t')
            onephase_raw.rename('indirect','repeat')
        colors = ['r','g','b','c']
        for k in range(ndshape(onephase)['ph1']):
            for j in range(ndshape(onephase)['repeat']):
                fl.next('compare rising edge')
                # need to define time slice for rising edge
                fl.plot(abs(onephase['repeat',j]['t':(6e-6,6.9e-6)]['ph1',k].C.reorder('t',first=True)),color=colors[k],alpha=0.3)
                fl.next('compare falling edge')
                # need to define time slice for falling edge
                fl.plot(abs(onephase['repeat',j]['t':(7.5e-6,8e-6)]['ph1',k].C.reorder('t',first=True)),color=colors[k],alpha=0.3)
                fl.next('compare rising edge, raw')
                fl.plot((onephase_raw['repeat',j]['t':(6e-6,6.9e-6)]['ph1',k].C.reorder('t',first=True)),color=colors[k],alpha=0.3)
                fl.next('compare falling edge, raw')
                fl.plot((onephase_raw['repeat',j]['t':(7.5e-6,8e-6)]['ph1',k].C.reorder('t',first=True)),color=colors[k],alpha=0.3)
        print(ndshape(onephase))
        #}}}
    #{{{ shifting the axis so that 0 is centered on the pulses
    # before we even slice, we need an idea of where the pulse is
    def average_time(d):
        pulse_slice = d['ch',1].real
        normalization = (pulse_slice**2).integrate('t')
        return (pulse_slice**2 * pulse_slice.fromaxis('t')).integrate('t')/normalization
    if single_90:
        avg_t = average_time(s_raw['t':(4e-6,14e-6)]).data.mean()
    if not single_90:
        avg_t = average_time(s_raw['t':(7.5e-6,9.5e-6)]).data.mean()
    pulse_slice = s_raw['t':(avg_t-max_window/2,avg_t+max_window/2)]
    #{{{ NOTE: make sure that pulse_slice includes each pulse during a nutation measurement
        # you can test that with the following:
    #fl.next('image for nutation')
    #fl.image(pulse_slice)
    #fl.show();quit()
    #}}}
    avg_t = average_time(pulse_slice)
    print(avg_t)
    # this creates an nddata of the time averages for each 90 pulse
    logger.debug(strm('dimensions of average_time:',ndshape(avg_t)))
    # shift the time axis down by the average time, so that 90 is centered around t=0
    s_raw.setaxis('t', lambda t: t-avg_t.data.mean())
    fl.next('check that this centers 90 around 0 on time axis')
    fl.image(s_raw)
    #}}}
    # {{{ now, go ahead and shift each indirect data element relative to the
    # others, so their pulses line up
    # I'm going to do this twice, for maximum accuracy
    # notice that a lot of the code that was
    # here before is gathered into the "average_time" function above
    avg_t = average_time(s_raw['t':(-max_window/2,max_window/2)])
    # the first time I do this, just do it on the raw data
    s_raw.ft('t',shift=True)
    phase_factor = s_raw.fromaxis('t',lambda x: 1j*2*pi*x)
    phase_factor *= avg_t
    s_raw *= exp(phase_factor)
    s_raw.ift('t')
    # }}}
    # {{{ now that my rms noise average will be more balanced,
    #     redetermine the center here, and reshift the pulses next
    avg_t = average_time(s_raw['t':(-max_window/2,max_window/2)])
    s_raw.setaxis('t', lambda t: t-avg_t.data.mean())
    fl.next('following ref ch pulses')
    fl.plot(abs(s_raw)['indirect',0]['ph1',0]['ph2',0]['ch',1],alpha=0.4,label='post phase adjustments')
    # }}}
    # {{{ since this is the last step, take the analytic signal
    #     and then apply the relative shifts again
    analytic = s_raw.C.ft('t')['t':(13e6,16e6)].ift('t')*2 # 2 for the analytic signal
    analytic.ft('t')
    analytic.setaxis('t',lambda f: f-carrier_f)
    analytic.set_units('indirect','s')
    phase_factor = analytic.fromaxis('t',lambda x: 1j*2*pi*x)
    phase_factor *= avg_t
    #     this time, optionally include the Cavanagh shifts
    if is_nutation:
        logger.debug(strm('the nutation axis is',analytic.getaxis('indirect')))
        # we want to move forward by (2/pi-1/2)*t90
        logger.debug(strm('correction before pulse shift',phase_factor))
        if not single_90:
            phase_factor += -1j*2*pi*(2/pi-0.5)*analytic.fromaxis('indirect')*analytic.fromaxis('t')
            logger.debug(strm('and after pulse shift',phase_factor))
    analytic *= exp(phase_factor)
    analytic.ift('t')
    # }}}
    #{{{ checking phase shifted trigger
    if confirm_triggers:
        if not single_90:
            onephase_raw_shift = s_raw['ch',1].C.smoosh(['ph2','indirect'],noaxis=True,dimname='repeat').reorder('t')
            onephase_raw_shift.name('Amplitude').set_units('V')
        if single_90:
            onephase_raw_shift = s_raw['ch',1].C.reorder('t')
            onephase_raw_shift.rename('indirect','repeat')
        for k in range(ndshape(onephase_raw)['ph1']):
            for j in range(ndshape(onephase_raw)['repeat']):
                fl.next('compare rising edge: uncorrected')
                fl.plot((onephase_raw_shift['repeat',j]['ph1',k]['t':(-0.6e-6,-0.35e-6)].C.reorder('t',first=True)+2*k),color=colors[k],alpha=0.3)
                fl.next('compare falling edge: uncorrected')
                fl.plot((onephase_raw_shift['repeat',j]['ph1',k]['t':(0.35e-6,0.6e-6)].C.reorder('t',first=True)+2*k),color=colors[k],alpha=0.3)
        raw_corr = s_raw.C.ft('t')
        phase_factor = raw_corr.fromaxis('t',lambda x: 1j*2*pi*x)
        phase_factor *= avg_t
        raw_corr *= exp(phase_factor)
        raw_corr.ift('t',pad=30*1024)
        if not single_90:
            onephase_rawc = raw_corr['ch',1].C.smoosh(['ph2','indirect'],noaxis=True, dimname='repeat').reorder('t')
        if single_90:
            onephase_rawc = raw_corr['ch',1].C.reorder('t')
            onephase_rawc.rename('indirect','repeat')
        for k in range(ndshape(onephase_rawc)['ph1']):
            for j in range(ndshape(onephase_rawc)['repeat']):
                fl.next('compare rising edge: corrected')
                fl.plot(onephase_rawc['repeat',j]['ph1',k]['t':(-0.6e-6,-0.35e-6)].C.reorder('t',first=True),color=colors[k],alpha=0.3)
                fl.next('compare falling edge: corrected')
                fl.plot(onephase_rawc['repeat',j]['ph1',k]['t':(0.35e-6,0.6e-6)].C.reorder('t',first=True),color=colors[k],alpha=0.3)
     #}}}
    # with time-shifted, phase corrected raw data, now take analytic
    # measured phase is phase of each 90 after time-shifting and phase correcting
    # set the phase of the 90 pulse for EACH INDIVIDUAL SCAN to make sure it's correct
    measured_phase = analytic['t':(-max_window/2,max_window/2)].mean('t',return_error=False)
    measured_phase /= abs(measured_phase)
    logger.info(strm("measured phase",measured_phase))
    # expected phase is how we expect the phases to cycle, and how it is programmed in the pulse sequence
    expected_phase = nddata(exp(r_[0,1,2,3]*pi/2*1j),[4],['ph1'])
    # phase correcting analytic signal by difference between expected and measured phases
    analytic *= expected_phase/measured_phase
    analytic.ft('t')
    analytic *= exp(1j*1.28*pi/8.)
    analytic.ift('t')
    analytic.reorder(['indirect','t'], first=False)
    fl.next('analytic signal, ref ch')
    fl.image(analytic['ch',1])
    analytic = analytic['indirect',0]['ch',0]['ph1',0]['ph2',0]
    analytic.set_units('V')
    analytic.name('Amplitude (Input-referred)')
    analytic = analytic['t':(108.5e-6,None)]
    fl.next('One transient, time domain')
    fl.plot(analytic.real, alpha=0.6, color='red',label='real')
    fl.plot(analytic.imag, alpha=0.6, color='blue', label='imag')
    fl.plot(abs(analytic), alpha=0.6, color='gray', label='abs')
    axhline(0, linestyle=':', color='black')
    axvline(127.0, linestyle=':', color='black')
    analytic.ft('t')
    fl.next('One transient, frequency domain')
    fl.plot(abs(analytic), alpha=0.6, color='black', label='abs')
    fl.show();quit()
    fl.next('coherence domain, ref ch')
    if not single_90:
        analytic.ift(['ph1','ph2'])
    if single_90:
        analytic.ift(['ph1'])
    fl.image(analytic['ch',1])
    fl.next('following ref ch pulses')
    fl.plot(abs(analytic)['indirect',0]['ch',1]['ph1',-1]['ph2',0], '--', alpha=0.4,label='before avg.: bandpass, phase adj, coh domain, post avg; 90 ch')
    #if not is_nutation:
    #    analytic.mean('indirect',return_error=False)
    fl.plot(abs(analytic)['indirect',0]['ch',1]['ph1',-1]['ph2',0], ':', alpha=0.4,label='bandpass, phase adj, coh domain, post avg; 90 ch')
    fl.plot(abs(analytic)['indirect',0]['ch',1]['ph1',0]['ph2',-1], '.-', alpha=0.4,label='bandpass, phase adj, coh domain, post avg; 180 ch')
    analytic.set_units('V')
    fl.next('coherence, sig ch, t domain')
    fl.image(analytic['ch',0])
    fl.next('coherence, sig ch, t slice')
    fl.image(analytic['t':(105.e-6,None)])
    analytic = analytic['ch',0]['ph1',1]['ph2',0] # pulling signal
    analytic.name('Amplitude (Input-referred)')
    analytic = analytic['t':(108.5e-6,None)]
    fl.next('Signal, time domain')
    fl.plot(analytic.real, alpha=0.6, color='red',label='real')
    fl.plot(analytic.imag, alpha=0.6, color='blue', label='imag')
    fl.plot(abs(analytic), alpha=0.6, color='gray', label='abs')
    axhline(0, linestyle=':', color='black')
    axvline(127.0, linestyle=':', color='black')
    analytic.ft('t')
    fl.next('Signal, frequency domain')
    fl.plot(abs(analytic), alpha=0.6, color='black', label='abs')
    fl.show();quit()
    s_analytic.set_units('V')
    if not single_90:
        signal = s_analytic['ph1',1]['ph2',0]
    if single_90:
        signal = analytic['ch',0]['ph1',1]['ph2',0]
        fl.next('signal, t domain')
        fl.image(signal)
        fl.next('signal slice, t domain')
        fl.image(signal['t':(30e-6,None)])
        fl.next('signal, t domain')
        fl.image(abs(signal))
        fl.next('abs signal slice, t domain')
        fl.image(abs(signal['t':(30e-6,None)]))
    print(ndshape(signal))
    if is_nutation:
        fl.next('image: signal, t domain')
        fl.image(signal)
        fl.next('image: abs signal, t domain')
        fl.image(abs(signal))
        cropped_signal = signal.C.cropped_log()
        fl.next('image: signal, t domain, cropped')
        fl.image(cropped_signal)
        fl.next('image: abs(signal), t domain, cropped')
        fl.image(abs(cropped_signal))
        fl.show();quit()
    #{{{ for measuring offset
    # plot abs value of signal along offset axis to determine
    # adjustment needed on the magnet (B0)
    for_offset = signal.C.ft('t')
    for_offset.name('Amplitude')
    for_offset.setaxis('t', lambda x: x/(2*pi*gammabar_H)*1e4)
    for_offset.set_units('t','G')
    for_offset.rename('t',r'$\frac{\Omega}{2 \pi \gamma_{H}}$')
    fl.next('signal, offset')
    fl.plot(abs(for_offset))
    #}}}
    #{{{ for plotting signal(t) 
    signal.name('Amplitude')
    #{{{ for checking each coherence pathway
    #for ph2 in xrange(ndshape(s_analytic)['ph2']):
    #    for ph1 in xrange(ndshape(s_analytic)['ph1']):
    #        fl.next(r'$\Delta_{c_{1}}$ = %d, $\Delta_{c_{2}}$ = %d'%(ph1,ph2))
    #        fl.plot(s_analytic['ph1',ph1]['ph2',ph2],alpha=0.4) # in order to see units
    #        #xlim(100,None) #units of 1e-6 seconds
    #}}}
    #for x in xrange(ndshape(signal)['indirect']):
    #    fl.plot(signal['indirect',x],alpha=0.4) # in order to see units
    #fl.plot(signal,alpha=0.45)
    signal = signal['t':(100e-6,None)]
    fl.next(r'$\Delta_{c_{1}}$ = -1, $\Delta_{c_{2}}$ = 0,$\pm 2$')
    fl.plot(signal.real,alpha=0.4,label='real')
    fl.plot(signal.imag,alpha=0.4,label='imag')
    fl.plot(abs(signal),':',c='k',alpha=0.15,label='abs')
    axhline(0,linestyle=':',c='gray')
    fl.show();quit()
    #xlim(105,None) #units of 1e-6 seconds
    #}}}

fl.show()
