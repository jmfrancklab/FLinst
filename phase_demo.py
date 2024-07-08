from pyspecdata import *
# if we are on resonance, the Hermitian test is a good test of ph0, but not really ph1
# the sum abs real test is a good test of how to phase an FID, but doesn't work
# if you start to include the FID mirror when doing an echo
with figlist_var() as fl:
    N = 50 # size of the phase "correction" dimensions
    dw_width = 30 # width of the ph1 window, in dwell times
    echo_used = False # a default, do not set here
    generate_echo = True
    construct_freq_domain = False
    gaussian_inhomog = False
    w = 10.
    if construct_freq_domain:
        # {{{ construct in frequency domain
        SW = 100.
        t = r_[-SW/2:SW/2:501j]
        d = nddata(w/(1j*2*pi*t+w),['t']).labels('t',t)
        # }}}
        fl.next('show time domain')
        d.set_ft_prop('t',['time','not','aliased'],True)
        d.ift('t')
        fl.plot(d)
        d.ft('t')
    else:
        # {{{ construct in time domain
        offset = 0.
        if generate_echo:
            echo_used = True
        if echo_used:
            d = nddata(r_[-5:5:1001j],'t')
            if gaussian_inhomog:
                d = exp(-abs(d)**2*(w*3)**2+1j*2*pi*offset*d.fromaxis('t'))
            else:
                d = exp(-abs(d)*w+1j*2*pi*offset*d.fromaxis('t'))
        else:
            d = nddata(r_[0:5.:501j],'t')
            d = exp(-d*w+1j*2*pi*offset*d.fromaxis('t'))
            d['t',0] /= 2 # comes from the definition of a discrete heaviside
            #                checked that this is not pyspecdata-specific
            #                without this, I get a baseline
        fl.next('show FID')
        fl.plot(d)
        SW = 1./diff(d.getaxis('t')[r_[0,1]]).item()
        d.ft('t',shift=True)
        # }}}
    fl.next('show frequency')
    fl.plot(d.real)
    fl.plot(d.imag)
    # {{{ construct the phases that we use to mess things up
    x = nddata(r_[-0.5:0.5:N*1j],'ph0').set_units('ph0','cyc')
    ph0 = exp(1j*2*pi*x)
    x = nddata(r_[-dw_width/SW/2:dw_width/SW/2:N*1j],'ph1').set_units('ph1','s')
    ph1 = 1j*2*pi*x
    if echo_used:
        d_rightside = d.C
        d_rightside.ift('t')
        d_rightside = d_rightside['t':(0.02,None)].C
        d_rightside['t',0] /= 2.
        d_rightside.ft('t')
        d_rightside *= ph0
        d_rightside *= exp(ph1*d_rightside.fromaxis('t'))
    d *= ph0
    d *= exp(ph1*d.fromaxis('t'))
    # }}}
    d.ift('t')
    # in the following, a None slice drops the last point, which is problematic!
    d_absreal = d.C
    if echo_used:
        d_absreal = d['t',lambda x: x>=0].C
        d_absreal.data[0] /= 2
    d_absreal.ft('t')
    fl.next('abs real cost')
    d_absreal.data = abs(d_absreal.data.real)
    d_absreal.sum('t')
    fl.image(d_absreal)
    if echo_used:
        fl.next('abs real cost -- starting from 0.02')
        d_rightside.data = abs(d_rightside.data.real)
        d_rightside.sum('t')
        fl.image(d_rightside)
    if echo_used:# only the time-domain construction is symmetric
        fl.next('hermitian cost')
        d_herm = d.C
        d_herm.data -= conj(d_herm.data[::-1])
        d_herm.data = abs(d_herm.data)**2
        d_herm.sum('t')
        fl.image(d_herm)
