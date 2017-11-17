from pyspecdata import *

mixdown = 15e6
capture_num = 1
f_axis = linspace(100e3,500e3,100) # must match sweep_frequencies_sqw

for j,thisfreq in enumerate(f_axis):
    data_name = 'capture%d_F%04.3fMHz'%(capture_num,(thisfreq*50)/1e6)
    d = nddata_hdf5(
            '171116_100fsweep.h5/%s'%data_name,
            directory=getDATADIR(exp_type='test_equip')
            ).set_units('t','s') # why are units not already set?
    d.ft('t',shift=True)
    d = d['t':(0,40e6)] # throw out negative frequencies and low-pass
    if j == 0:
        collated = ndshape(d)
        collated += ('f_pulse',len(f_axis))
        collated = collated.alloc(format=None)
        # {{{ note to self: this should NOT be required
        #     need to add/move labels to ndshape
        collated.setaxis('t', d.getaxis('t')).setaxis(
                'ch', d.getaxis('t')).setaxis(
                        'f_pulse', f_axis)
        collated.set_units('t','Hz').set_units('f_pulse','Hz')
        #collated.set_ft_prop('t') #shouldn't be required
        # }}}
    # we should really do a lot of the above inside the acquisition routine
    collated['f_pulse',j] = d
with figlist_var(filename='sweep_171116.pdf') as fl:
    collated.reorder('ch') # move ch first (outside)
    collated.ift('t')
    collated *= collated.fromaxis('t',
            lambda x: exp(-1j*2*pi*mixdown*x))
    fl.next('analytic signal, raw')
    fl.image(collated)
    ratio = collated['ch',1]/collated['ch',0]
    fl.next('ratio ch2 to ch1')
    fl.image(ratio)
    fl.next('ratio, abs over safe range')
    fl.image(abs(ratio['t':(11.6e-6,13e-6)]))
    fl.next('ratio, sum over safe range')
    avg_over_t = ratio['t':(11.6e-6,13e-6)].runcopy(mean,'t')
    fl.plot(abs(avg_over_t))
    ylim(0,1)
    ylabel('amplitude (solid line)')
    fl.next('ratio, sum over safe range', twinx=1)
    fl.plot(avg_over_t.angle/pi,'.')
    ylabel('phase (dots)')
    # {{{ because I have amplitudes that blow up, do the following:
    #     (maybe I should be dividing in the frequency domain?
    ratio /= abs(ratio)
    ratio *= abs(collated['ch',1])
    # }}}
    fl.next('phase difference ch2 to ch1')
    fl.image(ratio)
