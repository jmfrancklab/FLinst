from pyspecdata import *
#import winsound
#import logging
#init_logging(level=logging.DEBUG)
fl = figlist_var()

def process_series(date,id_string,V_AFG, pulse_threshold):
    """Process a series of pulse data.
    
    Lumping this as a function so we can do things like divide series, etc.

    Parameters
    ----------
    date: str
        date used in the filename
    id_string: str
        filename is called date_id_string
    V_AFG: array
        list of voltage settings used on the AFG 

    Returns
    -------
    V_anal: nddata
        The analytic signal, filtered to select the fundamental frequency (this is manually set).
    V_harmonic: nddata
        The analytic signal, filtered to set the second harmonic (this is manually set)
    V_pp: nddata
        After using the analytic signal to determine the extent of the pulse, find the min and max.
    """
    p_len = len(V_AFG)
    V_calib = 0.694*V_AFG
    fl.next('Channel 1, 1')
    for j in range(1,p_len+1):
        print "loading signal",j
        j_str = str(j)
        d = nddata_hdf5(date+'_'+id_string+'.h5/capture'+j_str+'_'+date,
                directory=getDATADIR(exp_type='test_equip'))
        d.set_units('t','s')
        if j == 1:
            raw_signal = (ndshape(d) + ('power',p_len)).alloc()
            raw_signal.setaxis('t',d.getaxis('t')).set_units('t','s')
            #gain = 10**5
            gain = 1
            raw_signal.setaxis('power',(gain)*((V_calib/2.0/sqrt(2))**2/50.))
        raw_signal['power',j-1] = d
        if j == 1:
            fl.next('Channel 1, 1')
            fl.plot(d['ch',0], alpha=0.5, label="label %s"%id_string)
        #if j == p_len:
        #    fl.next('channel 1, %d'%p_len)
        #    fl.plot(d['ch',0], alpha=0.5, label="label")
        d.ft('t',shift=True)
        plotdict = {1:"Fourier transform -- low power",
                p_len:"Fourier transform -- high power"}
        for whichp in [1,p_len]:
            fl.next(plotdict[whichp]) #this does not need to be here - empty plot
            if j == whichp:
                fl.plot(abs(d)['ch',0],alpha=0.2,label="FT %s"%id_string)
        d.ift('t')
        #for whichp in [1,p_len]:
        #    if j == whichp:
        #        fl.next('Channel 1, %d'%whichp)
        #        fl.plot(d['ch',0], alpha=0.5, label='FT and IFT')
        #        fl.plot(d['ch',0], alpha=0.5,label='raw data')
        # calculate the analytic signal
        d.ft('t')
        d = d['t':(0,None)]
        d_harmonic = d.copy()
        d['t':(33e6,None)] = 0
        d_harmonic['t':(0,33e6)] = 0
        d_harmonic['t':(60e6,None)] = 0
        #for whichp in [1,p_len]:
        #    fl.next(plotdict[whichp])
        #    if j == whichp:
        #        fl.plot(abs(d)['ch',0],alpha=0.15, label="used for analytic")
        #        fl.plot(abs(d_harmonic)['ch',0],alpha=0.15, label="used for harmonic")
        d.ift('t')
        d_harmonic.ift('t')
        d *= 2
        d_harmonic *= 2
        #for whichp in [1,p_len]:
        #    if j == whichp:
        #        fl.next('Channel 1, %d'%whichp)
        #        fl.plot(abs(d)['ch',0],alpha=0.5, label="analytic abs")
        #        fl.plot(abs(d_harmonic)['ch',0],alpha=0.5, label="harmonic abs")
        #        fl.plot(d['ch',0],alpha=0.5, label="analytic real")
        if j == 1:
            analytic_signal = (ndshape(d) + ('power',p_len)).alloc()
            analytic_signal.setaxis('t',d.getaxis('t')).set_units('t','s')
            analytic_signal.setaxis('power',(V_calib/2/sqrt(2))**2/50.)
            harmonic_signal = (ndshape(d_harmonic) + ('power',p_len)).alloc()
            harmonic_signal.setaxis('t',d_harmonic.getaxis('t')).set_units('t','s')
            harmonic_signal.setaxis('power',(V_calib/2/sqrt(2))**2/50.)
        analytic_signal['power',j-1] = d
        harmonic_signal['power',j-1] = d_harmonic
        #fl.next('analytic signal magnitude')
        #fl.plot(abs(analytic_signal['ch',0]),alpha=0.2,label="label")
    pulse_slice = abs(
            analytic_signal['ch',0]['power',-1]).contiguous(lambda x:
                    x>pulse_threshold*x.data.max())

    print "done loading all signals for %s"%id_string
    pulse_slice = pulse_slice[0,:]
    pulse_slice += r_[0.1e-6,-0.1e-6]
    V_anal = abs(analytic_signal['ch',0]['t':tuple(pulse_slice)]).mean('t')
    V_harmonic = abs(harmonic_signal['ch',0]['t':tuple(pulse_slice)]).mean('t')
    pulse_slice += r_[0.5e-6,-0.5e-6]
    V_pp = raw_signal['ch',0]['t':tuple(pulse_slice)].run(max,'t')
    V_pp -= raw_signal['ch',0]['t':tuple(pulse_slice)].run(min,'t')
    return V_anal, V_harmonic, V_pp

V_start = raw_input("Input start of sweep in Vpp: ")
V_start = float(V_start)
print V_start
V_stop = raw_input("Input stop of sweep in Vpp: ")
V_stop = float(V_stop)
print V_stop
V_step = raw_input("Input number of steps: ")
V_step = float(V_step)
print V_step

axis_spacing = raw_input("1 for log scale, 0 for linear scale: ")
if axis_spacing == '1':
    V_start_log = log10(V_start)
    V_stop_log = log10(V_stop)
    V_AFG = logspace(V_start_log,V_stop_log,V_step)
    print "V_AFG(log10(%f),log10(%f),%f)"%(V_start,V_stop,V_step)
    print "V_AFG(%f,%f,%f)"%(log10(V_start),log10(V_stop),V_step)
    print V_AFG
elif axis_spacing == '0':
    V_AFG = linspace(V_start,V_stop,V_step)
    print "V_AFG(%f,%f,%f)"%(V_start,V_stop,V_step)
    print V_AFG

atten_choice = raw_input("1 for attenuation, 0 for no attenuation: ")
if atten_choice == '1':
    atten_p = 10**(-40./10.)
    atten_V = 10**(-40./20.)
elif atten_choice == '0':
    atten_p = 1
    atten_V = 1
print "power, Voltage attenuation factors = %f, %f"%(atten_p,atten_V) 

for date,id_string in [
#        ('180514','sweep_high_control'),
#        ('180515','sweep10_high_control'),
#        ('180515','sweep10_high_duplexer_2piTL_2'),
#        ('180514','sweep_high_duplexer_2piTL')
#        ('180514','sweep_high_duplexer_2piTL')
        ('180514','sweep_control'),
        ('180514','sweep_duplexer_2piTL'),
        ('180514','sweep_duplexer_2piTL_2'),
        ('180531','sweep_pomona_dpx'),
#        ('180531','sweep_pomona_dpx_testing'),
#        ('180531','sweep_pomona_dpx_testing2'),
#        ('180531','sweep_pomona_dpx_testing3'),
#        ('180601','sweep_pomona_dpx_testing'),
#        ('180601','sweep_pomona_dpx_testing2'),
#        ('180601','sweep_pomona_dpx_testing3'),
#        ('180601','sweep_pomona_dpx_testing4'),
        ('180601','sweep_pomona_dpx'),
#        ('180514','sweep_control'),
#        ('180514','sweep_duplexer_2piTL'),
#        ('180514','sweep_duplexer_2piTL_2'),
#        ('180503','sweep_high_control'),
#        ('180513','sweep_high_control'),
#        ('180503','sweep_high_duplexer_2pi'),
#        ('180513','sweep_high_duplexer_2piTL'),
#        ('180502','sweep_control'),
#        ('180503','sweep_duplexer_2pi'),
#        ('180513','sweep_duplexer_2piTLnoD'),
#        ('180513','sweep_duplexer_2piTL'),
#       ('180510','sweep_low_control'),
#       ('180503','sweep_low_duplexer_2pi'),
#       ('180513','sweep_low_duplexer_2piTLnoD'),
#       ('180513','sweep_low_duplexer_2piTL'),
        ]:
    if date == '180514' and id_string == 'sweep_control':
        label='control'
    elif date == '180514' and id_string == 'sweep_duplexer_2piTL':
        label = 'previous duplexer'
    elif date == '180514' and id_string == 'sweep_duplexer_2piTL_2':
        label = 'previous duplexer 2'
    elif date == '180531' and id_string == 'sweep_pomona_dpx':
        label = 'pomona duplexer'
    elif date == '180531' and id_string == 'sweep_pomona_dpx_testing':
        label = 'Trial 2'
    elif date == '180531' and id_string == 'sweep_pomona_dpx_testing2':
        label = 'Trial 3'
    elif date == '180531' and id_string == 'sweep_pomona_dpx_testing3':
        label = 'Trial 4'
    elif date == '180601' and id_string == 'sweep_pomona_dpx_testing':
        label = 'Trial 5'
    elif date == '180601' and id_string == 'sweep_pomona_dpx_testing2':
        label = 'Trial 6'
    elif date == '180601' and id_string == 'sweep_pomona_dpx_testing3':
        label = 'Trial 7'
    elif date == '180601' and id_string == 'sweep_pomona_dpx_testing4':
        label = 'Trial 8'
    elif date == '180601' and id_string == 'sweep_pomona_dpx':
        label = 'current pomona duplexer'

    V_anal, V_harmonic, V_pp = process_series(date,id_string,V_AFG, pulse_threshold=0.1)
#    fl.next('V_analytic: P vs P')
#    fl.plot((V_anal/sqrt(2))**2/50./atten_p, label="%s $V_{analytic}$"%label) 
#    fl.next('V_harmonic: P vs P')
#    fl.plot((V_harmonic/sqrt(2))**2/50./atten_p, label="%s $V_{harmonic}$"%label) 
    fl.next('Output vs Input: Intermediate power, loglog')
    V_pp.rename('power','$P_{in}$').set_units('$P_{in}$','W')
    V_pp.name('$P_{out}$').set_units('W')
    fl.plot((V_pp/sqrt(2)/2.0)**2/50./atten_p,'.',alpha=0.65,plottype='loglog',label="%s"%label) 
    fl.next('log($P_{out}$) vs. log($V^{PP}_{in}$)')
    val = V_pp/atten_V
    val.rename('$P_{in}$','setting').setaxis('setting',V_AFG).set_units('setting','Vpp')
    fl.plot(val,'.',plottype='loglog',label="%s $V_{pp}$"%label)
    fl.next('log($V^{PP}_{out}$) vs. log($V^{PP}_{in}$)')
    fl.plot(val,'.',plottype='loglog',label="%s $V{pp}$"%label)

fl.show()

