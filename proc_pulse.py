from pyspecdata import *
fl = figlist_var()
import os
import sys
import pprint
from collections import OrderedDict
#import winsound
#import logging
#init_logging(level=logging.DEBUG)
rms_method=True
#{{{ Choose parameter input (script or user) 
params_choice = int(sys.argv[1])
if params_choice == 0:
    print "Choosing script-defined parameters..."
    print "(make sure parameters are what you want)\n"
    V_start = 0.01
    V_stop = 0.01321941
    V_step = 5
    V_start_log = log10(V_start)
    V_stop_log = log10(V_stop)
    V_step_log = V_step
    V_AFG = logspace(V_start_log,V_stop_log,V_step)
    print "V_AFG(log10(%f),log10(%f),%f)"%(V_start,V_stop,V_step)
    print "V_AFG(%f,%f,%f)"%(log10(V_start),log10(V_stop),V_step)
    atten_p = 1
    atten_V = 1
    print "power, Voltage attenuation factors = %f, %f"%(atten_p,atten_V) 
    rms_method=True
    if rms_method:
        method = 'RMS'
    if not rms_method:
        method = 'PP'
    print "*** Processing method:",method,"***\n"
elif params_choice == 1:
    print "Requesting user input..."
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

    method_choice = raw_input("1 for PP method, 0 for RMS method: ")
    if method_choice == '1':
        rms_method = False
    elif method_chocie == '0':
        rms_method = True
    if rms_method:
        method = 'RMS'
    if not rms_method:
        method = 'PP'
    print "*** Processing method:",method,"***\n"
        # }}}
# {{{ Signal processing function
def gen_power_data(date, id_string, V_AFG, rms_method=True,
        pulse_threshold=0.5):
    """Process a series of pulse data to produce output vs input power set
    ready for plotting.
    
    Lumping this as a function so we can do things like divide series, etc.

    Parameters
    ----------
    date: str
        date used in the filename
    id_string: str
        filename is called date_id_string
    V_AFG: array
        list of voltage settings used on the AFG 
    rms_method: boolean
        if True, calls rms_signal_to_power() which returns power of input data set 
        by subtracting V_RMS noise from V_RMS pulse and converting the difference to
        power.
        if False, calls pp_signal_to_power() which returns power of input data set
        by subtracting minimum V from maximum V within the pulse length, and converting
        the difference (V_PP) to power. Original method used for processing such data 
        sets until 06/2018.
    pulse_threshold: float 
        determines cut-off limit for calculating pulse power;
        this number is multiplied by the maximum V_{RMS} in the pulse width.

    Returns
    -------
    V_rms: nddata
        Generated from the analytic signal for each capture,
        has noise outside of pulse width subtracted out.
    """
    #{{{ RMS function: calculates power by subtracting RMS noise from RMS signal, both analytic
    def rms_signal_to_power(data,ch):
        "find the pulse, calculate the noise and signal powers and subtract them"
        pulse_slice = abs(data['power',-1]).contiguous(lambda x: x>pulse_threshold*x.data.max())
        pulse_slice = pulse_slice[0,:]
        pulse_limits = pulse_slice + r_[0.6e-6,-0.6e-6]
        noise_limits = pulse_slice - r_[0.6e-6,-0.6e-6]
        p_lim1,p_lim2 = pulse_limits
        n_lim1,n_lim2 = noise_limits
        Vn1_rms = sqrt((abs(data['t':(0,n_lim1)]
            )**2).mean('t',return_error=False))
        Vn2_rms = sqrt((abs(data['t':(0,n_lim2)]
            )**2).mean('t',return_error=False))
        Vn_rms = (Vn1_rms + Vn2_rms)/2.
        V_rms = sqrt((abs(data['t':tuple(pulse_slice)]
            )**2).mean('t',return_error=False))
        V_rms -= Vn_rms
        print 'CH',ch,'Noise limits in microsec: %f, %f'%(n_lim1/1e-6,n_lim2/1e-6)
        print 'CH',ch,'Pulse limits in microsec: %f, %f'%(p_lim1/1e-6,p_lim2/1e-6)
        return (V_rms)**2./50.
    #}}}
    #{{{ PP method: calculates power by subtract min from max analytic signal within pulse slice
    def pp_signal_to_power(data,ch):
        pulse_max = abs(data['power',-1].data.max())
        pulse_slice = abs(data['power',-1]).contiguous(lambda x: x>pulse_threshold*x.data.max())
        pulse_slice = pulse_slice[0,:]  
        pulse_slice += r_[0.6e-6,-0.6e-6]
        pulse_limits = tuple(pulse_slice)
        p_lim1,p_lim2 = pulse_limits
        print 'CH',ch,'Pulse limits in microsec: %f, %f'%(p_lim1/1e-6,p_lim2/1e-6)
        #Important point: Should this be modified to make it so that we are calculate V_pp from the
        #   raw data and not the analytic signal, as we had this method originally? 
        V_pp = data['t':tuple(pulse_slice)].run(max,'t')
        V_pp -= data['t':tuple(pulse_slice)].run(min,'t')
        return (V_pp)**2./50. 
    #}}}    
    p_len = len(V_AFG)
    V_calib = 0.694*V_AFG
    filename = date+'_'+id_string+'.h5'
    try:
        analytic_signal = nddata_hdf5(filename+'/accumulated_'+date,
                directory=getDATADIR(exp_type='test_equip'))
        analytic_signal.set_units('t','s')
    except:
        print "accumulated data was not found, pulling individual captures"
        for j in xrange(1,p_len+1):
            print "loading signal",j
            j_str = str(j)
            d = nddata_hdf5(filename+'/capture'+j_str+'_'+date,
                    directory=getDATADIR(exp_type='test_equip'))
            d.set_units('t','s')
            if j == 1:
                raw_signal = (ndshape(d) + ('power',p_len)).alloc()
                raw_signal.setaxis('t',d.getaxis('t')).set_units('t','s')
                raw_signal.setaxis('power',((V_calib/2.0/sqrt(2))**2/50.)).set_units('power','W')
            raw_signal['power',j-1] = d
            d.ft('t',shift=True)
            d = d['t':(0,None)]
            d['t':(0,5e6)] = 0
            d['t':(25e6,None)] = 0
            d.ift('t')
            d *= 2
            if j == 1:
                analytic_signal = (ndshape(d) + ('power',p_len)).alloc()
                analytic_signal.setaxis('t',d.getaxis('t')).set_units('t','s')
                analytic_signal.setaxis('power',(V_calib/2/sqrt(2))**2/50.)
            analytic_signal['power',j-1] = d
        analytic_signal.name('accumulated_'+date)
        analytic_signal.labels('ch',r_[1,2])
        analytic_signal.hdf5_write(filename,
                directory=getDATADIR(exp_type='test_equip'))
    fl.next('analytic')
    fl.plot(abs(analytic_signal['ch',0]['power',-1]),label=id_string)
    highest_power = abs(analytic_signal['power',-1])
    for ch in xrange(0,2):
        this_data = highest_power['ch',ch]
        pulse0_slice = this_data.contiguous(lambda x: x>pulse_threshold*x.data.max())
        pulse0_slice = tuple(pulse0_slice[0,:])
        fl.plot(this_data['t':pulse0_slice]['t',r_[0,-1]],'o',label='CH%s'%str(ch))
    print "Done loading signal for %s"%id_string 
    if rms_method:
        power0 = rms_signal_to_power(analytic_signal['ch',0],ch=1)
    if not rms_method:
        power0 = abs(pp_signal_to_power(analytic_signal['ch',0],ch=1))
    return_power = power0
    return_power.name('$P_{out}$')#.set_units('W')  #***IMPORTANT!***
    return return_power
#}}}
# {{{ Call files
for date,id_string in [
#        ('180514','sweep_high_control'),
#        ('180514','sweep_high_duplexer_2piTL')
        ('180514','sweep_control'),
#        ('180514','sweep_duplexer_2piTL'),
#        ('180531','sweep_pomona_dpx_testing'),
#        ('180531','sweep_pomona_dpx_testing2'),
#        ('180531','sweep_pomona_dpx_testing3'),
#        ('180601','sweep_pomona_dpx_testing'),
#        ('180601','sweep_pomona_dpx_testing2'),
#        ('180601','sweep_pomona_dpx_testing3'),
        ('180601','sweep_pomona_dpx_testing4'),
#        ('180607','sweep_pomona_dpx_5steps'),
#        ('180607','sweep_pomona_dpx_5steps_2'),
#        ('180607','sweep_pomona_dpx_5steps_3'),
#        ('180607','sweep_pomona_dpx_5steps_4'),
#        ('180607','sweep_pomona_dpx_5steps_5'),
#        ('180607','sweep_pomona_dpx_5steps_6'),
#        ('180607','sweep_pomona_dpx_5steps_8'),
        ('180601','sweep_pomona_dpx'),
        ('180607','sweep_pomona_dpx_5steps_9'),
        ('180607','sweep_pomona_dpx_5steps_9_2'),
        ('180607','sweep_pomona_dpx_5steps_9_3'),
##        ('180607','sweep_pomona_dpx_5steps_7'),
##        ('180607','sweep_pomona_dpx_5steps_7_2'),
##        ('180607','sweep_pomona_dpx_5steps_7_3'),
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
# }}}
# {{{ Assign plot labels based on file name
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
    elif date == '180607' and id_string == 'sweep_pomona_dpx_5steps_7':
        label = 'current pomona duplexer_rerun1'
    elif date == '180607' and id_string == 'sweep_pomona_dpx_5steps_7_2':
        label = 'current pomona duplexer_rerun2'
    elif date == '180607' and id_string == 'sweep_pomona_dpx_5steps_7_3':
        label = 'current pomona duplexer_rerun3'
    elif date == '180607' and id_string == 'sweep_pomona_dpx_5steps_9':
        label = 'Trial 8_rerun1'
    elif date == '180607' and id_string == 'sweep_pomona_dpx_5steps_9_2':
        label = 'Trial 8_rerun2'
    elif date == '180607' and id_string == 'sweep_pomona_dpx_5steps_9_3':
        label = 'Trial 8_rerun3'
    else:
        label = id_string
# }}}
    power_plot = gen_power_data(date,id_string,V_AFG/atten_V,rms_method)
    fl.next('Troubleshooting Shielded Duplexer at Low Power, loglog (%s method)'%method)
    power_plot.rename('power','$P_{in}$ $(W)$')#.set_units('$P_{in}$','W')
    power_plot.name('$P_{out}$ $(W)$')#.set_units('W')
    fl.plot(power_plot,'-o',alpha=0.65,plottype='loglog',label="%s"%label) 
#{{{ Relative dB calculations
    dB_value =  10*log10(power_plot.mean())
    print 'Calculating dB for',id_string,':',dB_value.data
    if date+id_string == '180514sweep_control':
        k=0
        dbdict = {}
        temp = []
        ord_dbdictlist = []
    dict_db = dict([(date+'_'+id_string,dB_value.data)])
    dbdict.update(dict_db)
    k += 1
print "***dB values***"
ord_dbdict = OrderedDict(sorted(dbdict.items(), key=lambda t: t[1]))
for name,db in ord_dbdict.iteritems():
    temp = [name,db]
    ord_dbdictlist.append(temp)
print "Non-relative dB:"
pprint.pprint(ord_dbdictlist)
r_db = array(ord_dbdictlist) 
print "Relative dB:"
for q in xrange(0,k):
    val = float(r_db[q][1])-float(r_db[-1][1])
    print r_db[q][0],'=',val
#}}}
fl.show()
