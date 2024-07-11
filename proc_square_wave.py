from pyspecdata import *
fl = figlist_var()

d = nddata_hdf5('scope_data.h5/capture3_171109')
d.set_units('t','s')
fl.next('Dual-channel d')
fl.plot(d, alpha=0.5)
fl.next('Fourier transform',figsize=(12,6))
d.ft('t',shift=True)
fl.plot(d, alpha=0.5)
fl.next('Zoom In',figsize=(12,6))
d = d['t':(0,40e6)]
fl.plot(abs(d), alpha=0.5)
fl.next('Analytic Signal Magnitude',
        figsize=(12,6))
d.ift('t')
fl.plot(abs(d),
        alpha=0.5)
fl.next('Analytic Signal Phase -- mixed down 15 MHz',
        figsize=(12,6))
d *= d.fromaxis('t',
        lambda x: exp(-1j*2*pi*15e6*x))
fl.plot(d.angle, '.')
fl.next('Analytic Signal Phase Difference',
        figsize=(12,6))
d_diff = d['ch',1]/d['ch',0]
d_diff.set_units(r'rad/$\pi$')
fl.plot(d_diff.angle/pi, '.')
fl.show()
