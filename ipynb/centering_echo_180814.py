
# coding: utf-8

# 

get_ipython().magic(u'load_ext pyspecdata.ipy')
from pyspecdata.plot_funcs.image import imagehsv
import os
import sys
import matplotlib.style
import matplotlib as mpl

mpl.rcParams['image.cmap'] = 'jet'
fl = figlist_var()
gain_factor = sqrt(73503.77279)

max_window = 30e-6

carrier_f = 14.4289e6

for date,id_string,numchan,indirect_range in [
        #('180712','SE_exp',2)
        #('180712','SE_exp_2',2)
        #('180712','SE_exp_3',2)
        #('180713','SE_exp',2)
        #('180714','SE_exp',2), # 25 cycle measurement, B0 = 3395.75 G
        #('180714','SE_exp_offres',2) # 25 cycle measurement, B0 = 3585.85 G 
        #('180716','SE_test',2) # 1 cycle measurement with 8x GDS avg, B0 = 3395.75 G
        #('180716','SE_test_2',2) # 1 cycle measurement with 4x GDS avg, B0 = 3395.75 G
        #('180720','nutation_control',2)
        #('180723','nutation_control',2)
        #('180723','se_nutation',2,linspace(1.13e-6,6.13e-6,20))
        #('180723','se_nutation_2',2,linspace(1.5e-6,15e-6,40))
        #('180724','check_field',2,None),
        #('180724','check_field_2',2,None)
        #('180724','se_nutation',2,linspace(3.25e-6,15.25e-6,10))
        #('180724','90_nutation_control',2,linspace(1e-6,50e-6,5))
        #('180724','90_nutation',2,linspace(1e-6,50e-6,25)) # use -w 60e-6
        #('180725','90_nutation',2,linspace(1e-6,30e-6,30)) # use -w 60e-6
        #('180725','90_nutation_focused',2,linspace(6e-6,9e-6,30))
        ('180725','SE',2,None) # 3 cycles, 2x GDS avg, B0 = 3407.32 G, t90 = 7.45e-6 s
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

    s /= sqrt(gain_factor) 
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
        print ndshape(s)
        print ndshape(s_raw)
        subset = s['ch',1]['t':(1e-6,100e-6)]
        fl.next('raw data')
        if not single_90:
            fl.plot(s_raw['ch',1]['indirect',0]['ph2',0].reorder('t').real)
            onephase = subset.C.smoosh(['ph2','indirect'], noaxis = True, dimname='repeat').reorder('t')
            onephase_raw = s_raw['ch',1].C.smoosh(['ph2','indirect'], noaxis=True, dimname='repeat').reorder('t')
            print "dimensions of re-grouped raw data",ndshape(onephase_raw)
        if single_90:
            fl.plot(s_raw['ch',1]['indirect',-1].reorder('t').real)
            onephase = subset.C.reorder('t')
            onephase.rename('indirect','repeat')
            onephase_raw = s_raw['ch',1].C.reorder('t')
            onephase_raw.rename('indirect','repeat')
        colors = ['r','g','b','c']
        for k in xrange(ndshape(onephase)['ph1']):
            for j in xrange(ndshape(onephase)['repeat']):
                fl.next('compare rising edge')
                # need to define time slice for rising edge
                fl.plot(abs(onephase['repeat',j]['t':(26.2e-6,26.6e-6)]['ph1',k].C.reorder('t',first=True)),color=colors[k],alpha=0.3)
                fl.next('compar7e falling edge')
                # need to define time slice for falling edge
                fl.plot(abs(onephase['repeat',j]['t':(26.2e-6,26.6e-6)]['ph1',k].C.reorder('t',first=True)),color=colors[k],alpha=0.3)
                fl.next('compare rising edge, raw')
                fl.plot((onephase_raw['repeat',j]['t':(27.1e-6,27.9e-6)]['ph1',k].C.reorder('t',first=True)),color=colors[k],alpha=0.3)
                fl.next('compare falling edge, raw')
                fl.plot((onephase_raw['repeat',j]['t':(27.1e-6,27.9e-6)]['ph1',k].C.reorder('t',first=True)),color=colors[k],alpha=0.3)
        print ndshape(onephase)
        #}}}
    #{{{ shifting the axis so that 0 is centered on the pulses
    # before we even slice, we need an idea of where the pulse is
    def average_time(d):
        pulse_slice = d['ch',1].real
        normalization = (pulse_slice**2).integrate('t')
        return (pulse_slice**2 * pulse_slice.fromaxis('t')).integrate('t')/normalization
    if single_90:
        avg_t = average_time(s_raw['t':(0e-6,30e-6)]).data.mean()
    if not single_90:
        avg_t = average_time(s_raw['t':(6.5e-6,9.3e-6)]).data.mean()
    pulse_slice = s_raw['t':(avg_t-max_window/2,avg_t+max_window/2)]
    #{{{ NOTE: make sure that pulse_slice includes each pulse during a nutation measurement
        # you can test that with the following:
    #fl.image(pulse_slice)
    #fl.show();quit()
    #}}}
    avg_t = average_time(pulse_slice)
    print avg_t
    # this creates an nddata of the time averages for each 90 pulse
    logger.debug(strm('dimensions of average_time:',ndshape(avg_t)))
    # shift the time axis down by the average time, so that 90 is centered around t=0
    s_raw.setaxis('t', lambda t: t-avg_t.data.mean())
    #fl.next('check that this centers 90 around 0 on time axis')
    #fl.image(s_raw)
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
    fl.plot(abs(s_raw['indirect',0]['ph1',0]['ph2',0]['ch',1]), alpha=0.4,label='post phase adjustments')
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
        for k in xrange(ndshape(onephase_raw)['ph1']):
            for j in xrange(ndshape(onephase_raw)['repeat']):
                fl.next('compare rising edge: uncorrected')
                fl.plot((onephase_raw_shift['repeat',j]['ph1',k]['t':(-1.4e-6,-1.1e-6)].C.reorder('t',first=True)+2*k),color=colors[k],alpha=0.3)
                fl.next('compare falling edge: uncorrected')
                fl.plot((onephase_raw_shift['repeat',j]['ph1',k]['t':(1.0e-6,1.4e-6)].C.reorder('t',first=True)+2*k),color=colors[k],alpha=0.3)
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
        for k in xrange(ndshape(onephase_rawc)['ph1']):
            for j in xrange(ndshape(onephase_rawc)['repeat']):
                fl.next('compare rising edge: corrected')
                fl.plot(onephase_rawc['repeat',j]['ph1',k]['t':(-1.4e-6,-1.1e-6)].C.reorder('t',first=True),color=colors[k],alpha=0.3)
                fl.next('compare falling edge: corrected')
                fl.plot(onephase_rawc['repeat',j]['ph1',k]['t':(1.0e-6,1.4e-6)].C.reorder('t',first=True),color=colors[k],alpha=0.3)
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
    print ndshape(analytic)
    analytic.reorder(['indirect','t'], first=False)
    print ndshape(analytic)
    if not single_90:
        logging.debug('printing axis for ph1 and ph2')
        logging.debug(analytic.getaxis('ph1'))
        logging.debug(analytic.getaxis('ph2'))
        analytic.ift(['ph1','ph2'])
    if single_90:
        analytic.ft(['ph1'])
    fl.plot(abs(analytic['indirect',0]['ch',1]['ph1',-1]['ph2',0]), '--', alpha=0.4,label='before avg.: bandpass, phase adj, coh domain, post avg; 90 ch')
    analytic.mean('indirect',return_error=False)
    fl.plot(abs(analytic['ch',1]['ph1',-1]['ph2',0]), ':', alpha=0.4,label='bandpass, phase adj, coh domain, post avg; 90 ch')
    fl.plot(abs(analytic['ch',1]['ph1',0]['ph2',-1]), '.-', alpha=0.4,label='bandpass, phase adj, coh domain, post avg; 180 ch')
    analytic.set_units('V')
    fl.next('coherence, sig ch, t domain')
    fl.image(analytic['ch',0])
    print ndshape(analytic['ch',0])
    # now, pull the signal
    analytic = analytic['ch',0]['ph1',1]['ph2',0]
    analytic.name('Amplitude (Input-referred)')
    print ndshape(analytic)
    analytic = analytic['t':(0,None)]
    fl.next('Signal, with averaging')
    fl.plot(analytic.imag,alpha=0.4,label='imaginary')
    fl.plot(analytic.real,alpha=0.4,label='real')
    fl.plot(abs(analytic),color='k',alpha=0.4,label='abs')
    signal = analytic
fl.show()


# find the maximum, then center the maximum at t = 0

get_ipython().magic(u'matplotlib inline')

raw = signal.C 

max_index = abs(signal).argmax('t', raw_index=True).data
signal.setaxis('t', lambda x: x - signal.getaxis('t')[max_index])
span = 27 # max num of data points before reaching noise
display(abs(signal['t',max_index-span:max_index+span+1]))
display((signal['t',max_index-span:max_index+span+1]).real)
display((signal['t',max_index-span:max_index+span+1]).imag)
span_min = signal.getaxis('t')[max_index-span]
span_max = signal.getaxis('t')[max_index+span+1]
print span_min
print span_max

# 

get_ipython().magic(u'matplotlib inline')

signal = raw.C ## checkpoint

# 

figure('raw signal')
title('abs, raw signal')
plot(abs(signal))
axvline(span_min, c='k')
axvline(span_max, c='k')

# 

figure('before entering')
plot(abs(signal),c='k')
index_max = abs(signal).argmax('t',raw_index=True).data
signal.setaxis('t', lambda t: t - signal.getaxis('t')[index_max])
#figure('after centering')
plot(abs(signal),':')
gridandtick(gca())

def test_hermitian_symmetry(signal, signal_shift = r_[-6e-6:6e-6:500j]):
    rmsd = empty_like(signal_shift)
    for j,dt in enumerate(signal_shift):
        temp = signal.C
        temp.ft('t')
        # first order phase-shift, but implemented in time domain
        # time-shift in time domain is phase-shift in frequency domain
        temp *= exp(-1j*2*pi*dt*temp.fromaxis('t')) # time-shift 
        temp.ift('t')
        temp = temp['t',max_index-span:max_index+span+1]
        ph = temp.C.sum('t')
        ph /= abs(ph)
        # zeroth order phase-shift
        temp /= ph
        deviation = conj(temp.data[::-1]) - temp.data
        rmsd[j] = sum(abs(deviation)**2)
    rmsd_nd = nddata(rmsd,'dt').labels('dt',signal_shift).set_units('dt','s')
    rmsd_nd.name('RMSD')
    return rmsd_nd
rmsd_nd = test_hermitian_symmetry(signal)

# fit a polynomial in order to find the minimum more robustly

coeff,fit = rmsd_nd.polyfit('dt',order=5)
title(r'RMSD ($\Delta(t)$)')
plot(rmsd_nd)

interp_fit = fit.C.interp('dt',5000)
plot(interp_fit,alpha=0.5)
dt = interp_fit.C.argmin('dt').data.item()
zoomin = False # doesn't seem to help
if zoomin:
    slc = interp_fit.contiguous(lambda x: x<
                                min(r_[x['dt',-1].data.item(),x['dt',0].data.item()]))
    assert len(slc)==1,"no single minimum"
    rmsd_slc = rmsd_nd['dt':tuple(slc[0])]
    plot(rmsd_slc,alpha=0.3,linewidth=5)
    coeff,fit = rmsd_slc.polyfit('dt',order=5)
    interp_fit = fit.C.interp('dt',5000)
    plot(interp_fit,alpha=0.5)
    xlim(-1e-6,6e-6)

    figure()
    plot(rmsd_slc - fit)
print "dt is",dt

#  now, apply dt and compare to the original

with figlist_var() as fl:
    fl.next('plot comparison', legend=True)
    fl.plot(abs(signal)['t':(-20e06,20e-6)], label='before shift')
    signal.ft('t')
    signal *= exp(1j*2*pi*dt*signal.fromaxis('t'))
    signal.ift('t')
    fl.plot(abs(signal)['t':(-20e06,20e-6)], label='after shift')
    gridandtick(gca())
    rmsd = test_hermitian_symmetry(signal)
    # this is to check that we shifted the right way
    fl.next('check the rmsd from the hermitian test')
    fl.plot(rmsd)

# 

# With the max at t = 0, now select window of signal to use for phasing
ph_span = 45
max_index = abs(signal).argmax('t', raw_index=True).data
signal_slice = signal['t',max_index - ph_span : max_index + ph_span + 1]
span_min = signal.getaxis('t')[max_index-ph_span]
span_max = signal.getaxis('t')[max_index+ph_span+1]
plot(abs(signal))
plot(abs(signal_slice))
axvline(span_min, c='k')
axvline(span_max, c='k')
gridandtick(gca())


# span = 15

# 

proc_15 = raw.C
proc_15 = proc_15['t':(0,None)]
proc_15.ft('t')

# In[100]:

# span = 10

proc_10 = raw.C
proc_10 = proc_10['t':(0,None)]
proc_10.ft('t')

signal = scopy.C ## checkpoint

# span = 5

# 

proc_5 = raw.C
proc_5 = proc_5['t':(0,None)]
proc_5.ft('t')


signal_r = signal.C
signal_r = signal_r['t':(0,None)].C
signal_r['t', 0] /= 2.
signal_r.ft('t')
signal_r *= ph0
signal_r *= exp(ph1*signal_r.getaxis('t'))


# 

signal.ft('t')
signal *= ph0
signal *= exp(ph1*signal.fromaxis('t'))
signal.ift('t')
print "Done phasing"


# Absolute real method, cost function

signal_absreal = signal.C
signal_absreal = signal['t', lambda x: x >= 0].C
signal_absreal.data[0] /= 2.
signal_absreal.ft('t')
figure('abs real cost')
signal_absreal.data = abs(signal_absreal.data.real)
print ndshape(signal_absreal)

signal_absreal.sum('t')
print ndshape(signal_absreal)

# 

figure('hermitian cost')
signal_herm = signal.C
signal_herm.set_units('ph0','cyc')
signal_herm.set_units('ph1','s')
signal_herm.data -= conj(signal_herm.data[::-1])
signal_herm.data = abs(signal_herm.data)**2
signal_herm.sum('t')
image(signal_herm)


# 

signal = scopy.C ## checkpoint (reverse what was done to signal, so can apply desired changes)


# 

figure();title('Raw data')
plot(signal, c='violet')
plot(signal.real,':', c='k')
plot(signal.imag, c='cyan')
gridandtick(gca())
signal.ift('t')



raw_s = signal.C
raw_s = raw_s['t':(0,None)]
raw_s.ft('t')
#plot(raw_s.real, alpha=0.8)
plot(raw_s.imag, alpha=0.8)



# 

get_ipython().magic(u'matplotlib inline')


# 

figure('diff spans')
title('diff spans')

# 

figure('diff spans')
title('diff spans')

signal_absreal.meshplot(cmap=cm.viridis)



plot(proc_s.real, alpha=0.8, label = '%d'%ph_span)




plot(proc_s1.real, alpha=0.8, label = '%d'%ph_span)

# In[129]:

# 

get_ipython().magic(u'matplotlib notebook')


signal.ift('t')



plot(signal.real)
plot(signal.imag)

