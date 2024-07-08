from pyspecdata import *
from pyspecdata.plot_funcs.image import imagehsv
import os
import sys
import matplotlib.style
import matplotlib as mpl

mpl.rcParams['image.cmap'] = 'jet'
fl = figlist_var()

carrier_f = 14.4289e6

for date,id_string,numchan,t_90_range, in [
        ('180720','nutation_control',2,linspace(1.5e-6,6.0e-6,3))
        ]:
    filename = date+'_'+id_string+'.h5'
    nodename = 'this_capture'
    s = nddata_hdf5(filename+'/'+nodename,
            directory = getDATADIR(exp_type='test_equip'))
    s.set_units('t','s')
    s.setaxis('ph1', r_[0:4]*0.25)
    s.setaxis('ph2', r_[0:4:2]*0.25)
    s_raw = s.C.reorder('t',first=False)
    #for i,t_90 in enumerate(t_90_range):
    #    fl.next('raw data %d'%i) 
    #    fl.plot(s_raw['ch',1]['t_90',i]['ph2',0].reorder('t').real,alpha=0.2)
    slice_90_range = [(12.49e-6,14.2e-6),(12.49e-6,16.38e-6),(12.49e-6,18.65e-6)]
    for i,slice_90 in enumerate(slice_90_range):
        pulse_slice = s_raw['t_90',i]['t':slice_90]['ch',1].real
        normalization = (pulse_slice**2).integrate('t')
        average_time = (pulse_slice**2 * pulse_slice.fromaxis('t')).integrate('t')/normalization
        s_raw['t_90',i].setaxis('t', lambda t: t-average_time.data.mean())
    s_raw.setaxis('t', lambda t: t+30e-6)
    fl.next('time-shifted data')
    fl.image(s_raw)
    s_raw_corr = s_raw.C
    s_raw_corr.ft('t',shift=True)
    f = s_raw_corr.fromaxis('t')
    t_90 = s_raw_corr.fromaxis('t_90')
    ph_shift = exp(1j*2*pi*f*t_90*(0.5-2/pi))
    ph_shift.run(lambda x: exp(x))
    s_raw_corr *= ph_shift
    s_raw_corr.setaxis('t',lambda f: f-carrier_f)
    s_raw_corr.ift('t')
    fl.next('phase adjusting')
    fl.image(s_raw_corr)
    analytic = s['ch',1].C.ft('t',shift=True)['t':(0,16e6)].setaxis('t',lambda f: f-carrier_f).ift('t')
    fl.next('analytic')
    fl.image(analytic)
    analytic *= ph_shift
    measured_phase = analytic['t':slice_90_range[0]].mean('t',return_error=False).mean('ph2',return_error=True)
    measured_phase / abs(measured_phase)
    expected_phase = nddata(exp(r_[0,1,2,3]*pi/2*1j),[4],['ph1'])
    analytic *= expected_phase/measured_phase
    fl.next('after overall ph correction')
    fl.image(analytic)
    fl.show()
    quit()
