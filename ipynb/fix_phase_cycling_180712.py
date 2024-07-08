
# coding: utf-8

# In[1]:

get_ipython().magic(u'load_ext pyspecdata.ipy')


# In[218]:

# grab the data -- this is mandatory

d = nddata_hdf5('180711_SE_phcyc_control.h5/this_capture',
                directory=getDATADIR(exp_type='test_equip_shared'))
d.set_units('t','s')
d_raw = d.C.reorder('t',first=False)


# In[215]:

fl=figlist_var()
fl.next('raw data',figsize=(14,28))
fl.plot(d_raw['ch',1]['average',0]['ph2',0]['t':(24e-6,30e-6)].reorder('t').real)


# In[55]:

ndshape(d)
d.ft('t',shift=True)
d = d['t':(0,None)]
d.setaxis('t',lambda x: x-14.43e6)
d.ift('t')


# In[56]:

fl=figlist_var()
fl.next('phcyc',figsize=(14,14))
subset = d['ch',1]['t':(20e-6,100e-6)]
fl.image(subset,black=True)


# In[90]:

# sort into groups with the same ph1 value
onephase = subset.C.smoosh(['ph2','average'], noaxis=True, dimname='repeat').reorder('t')
ndshape(onephase)


# In[92]:

# plot each group of same ph1 value with a different color
fl=figlist_var()
colors = ['r','g','b','c']
for k in range(ndshape(onephase)['ph1']):
    for j in range(ndshape(onephase)['repeat']):
        fl.next('compare rising edge')
        fl.plot(abs(onephase['repeat',j]['t':(24.85e-6,25e-6)]['ph1',k].C.reorder('t',first=True)),color=colors[k],alpha=0.3)
        fl.next('compare falling edge')
        fl.plot(abs(onephase['repeat',j]['t':(27.4e-6,27.8e-6)]['ph1',k].C.reorder('t',first=True)),color=colors[k],alpha=0.3)


# In[94]:

# so, this looks like it's triggering differently for different phases.  We think we know why this is, but plot the raw voltage to be sure
fl=figlist_var()
fl.next('compare raw trigger')
onephase = d_raw['ch',1].C.smoosh(['ph2','average'], noaxis=True, dimname='repeat').reorder('t')
ndshape(onephase)
colors = ['r','g','b','c']
for k in range(ndshape(onephase)['ph1']):
    for j in range(ndshape(onephase)['repeat']):
        fl.next('compare rising edge')
        fl.plot(onephase['repeat',j]['t':(24.85e-6,25e-6)]['ph1',k].C.reorder('t',first=True),color=colors[k],alpha=0.3)
        fl.next('compare falling edge')
        fl.plot(onephase['repeat',j]['t':(27.4e-6,27.8e-6)]['ph1',k].C.reorder('t',first=True),color=colors[k],alpha=0.3)


# In[219]:

# so, we're happy that we know exactly what's hapenning -- find the average pulse centers.  This is mandatory for the steps below: I want to start over and relabel my x axis in a more convenient way, so that below I'm not shifting my pulses by a massive amount so that they alias over

pulse_slice = d_raw['t':(24.8e-6,27.6e-6)]['ch',1].real
normalization = (pulse_slice**2).integrate('t')
average_time = (pulse_slice**2 * pulse_slice.fromaxis('t')).integrate('t')/normalization
average_time.reorder('average',first=False)
d_raw.setaxis('t', lambda x: x-average_time.data.mean())


# In[220]:

# on the new axis, redetermine the pulse center -- mandatory for steps below
pulse_slice = d_raw['t':(-1.6e-6,1.6e-6)]['ch',1].real
normalization = (pulse_slice**2).integrate('t')
average_time = (pulse_slice**2 * pulse_slice.fromaxis('t')).integrate('t')/normalization
average_time.reorder('average',first=False)


# In[161]:

print average_time


# In[164]:

# now generate corrected analytic signal
analytic = d_raw.C.ft('t', shift=True)['t':(0,None)]
analytic.setaxis('t',lambda x: x-14.43e6)
phase_factor = analytic.fromaxis('t',lambda x: 1j*2*pi*x)
phase_factor *= average_time
phase_factor.run(lambda x: exp(x))
analytic *= phase_factor
analytic.ift('t')


# In[221]:

# apply the time-shift correction to the raw data, and see what it looks like.  This is the first step in the correction
fl=figlist_var()
onephase = d_raw['ch',1].C.smoosh(['ph2','average'], noaxis=True, dimname='repeat').reorder('t')
for k in range(ndshape(onephase)['ph1']):
    for j in range(ndshape(onephase)['repeat']):
        fl.next('compare rising edge: uncorrected')
        fl.plot(onephase['repeat',j]['ph1',k]['t':(-1.5e-6,-1.1e-6)].C.reorder('t',first=True)+2*k,color=colors[k],alpha=0.3)
        fl.next('compare falling edge: uncorrected')
        fl.plot(onephase['repeat',j]['ph1',k]['t':(1.1e-6,1.5e-6)].C.reorder('t',first=True)+2*k,color=colors[k],alpha=0.3)
raw_corr = d_raw.C.ft('t',shift=True)
phase_factor = raw_corr.fromaxis('t',lambda x: 1j*2*pi*x)
phase_factor *= average_time
phase_factor.run(lambda x: exp(x))
raw_corr *= phase_factor
raw_corr.ift('t',pad=30*1024)
onephase = raw_corr['ch',1].C.smoosh(['ph2','average'], noaxis=True, dimname='repeat').reorder('t')
ndshape(onephase)
colors = ['r','g','b','c']
for k in range(ndshape(onephase)['ph1']):
    for j in range(ndshape(onephase)['repeat']):
        fl.next('compare rising edge')
        fl.plot(onephase['repeat',j]['ph1',k]['t':(-1.5e-6,-1.1e-6)].C.reorder('t',first=True),color=colors[k],alpha=0.3)
        fl.next('compare falling edge')
        fl.plot(onephase['repeat',j]['ph1',k]['t':(1.1e-6,1.5e-6)].C.reorder('t',first=True),color=colors[k],alpha=0.3)


# In[227]:

# Take this corrected raw data, and convert to filtered analytic signal.  Then, adjust the zero-order phase so that each step of the 90 cycle matches its known value.
analytic = raw_corr['ch',1].C.ft('t')['t':(0,15.5e6)].setaxis('t',lambda x: x-14.43e6).ift('t').reorder(['average','t'],first=False)
fl=figlist_var()
measured_phase = analytic['t':(-2e-6,2e-6)].mean('t',return_error=False).mean('ph2',return_error=True).mean('average',return_error=True)
measured_phase /= abs(measured_phase)
known_phase = nddata(exp(r_[0,1,2,3]*pi/2*1j),[4],['ph1'])
analytic *= known_phase/measured_phase
fl.next('analytic signal',figsize=(14,28))
fl.image(analytic['t':(-2e-6,75e-6)])


# In[228]:

fl = figlist_var()
fl.next('switch to coherence domain', figsize=(14,28)) # and verify ift vs. ft
coh_domain = analytic.C.ift(['ph1','ph2'])
fl.image(coh_domain['t':(-2e-6,75e-6)])


# In[ ]:



