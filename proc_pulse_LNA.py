from pyspecdata import *
fl = figlist_var()
import os
import sys
#{{{ Functions for plotting different captures of one data set
def gen_plotdict(capture_list,plot_str):
    plotdict = {}
    for n in range(len(capture_list)):
        cap_no = capture_list[n]
        dict_n = dict([(cap_no,'CAPTURE %d %s'%(cap_no,plot_str))])
        plotdict.update(dict_n)
    return plotdict

def plot_captures(capture_list,plot_str,current_j,data,how_many_ch):
    plotdict = gen_plotdict(capture_list,plot_str)
    for whichp in capture_list:
        fl.next(plotdict[whichp])
        if current_j == whichp:
            for ch_no in range(how_many_ch):
                k = ch_no + 1
                fl.plot(data['ch',ch_no],alpha=0.2,label='CH%d'%k)
    return
#}}}
#{{{ Choose parameter input (script=0 or user=1) 
params_choice = int(sys.argv[1])
if params_choice == 0:
    print("Choosing script-defined parameters...")
    print("(make sure parameters are what you want)\n")
    V_start = 0.01
    V_stop = 0.86
    V_step = 40 
    V_start_log = log10(V_start)
    V_stop_log = log10(V_stop)
    V_step_log = V_step
    V_AFG = logspace(V_start_log,V_stop_log,V_step)
    print("V_AFG(log10(%f),log10(%f),%f)"%(V_start,V_stop,V_step))
    print("V_AFG(%f,%f,%f)"%(log10(V_start),log10(V_stop),V_step))

    rms_method=True
    if rms_method:
        method = 'RMS'
    if not rms_method:
        method = 'PP'
    print("*** Processing method:",method,"***\n")
elif params_choice == 1:
    print("Requesting user input...")
    V_start = input("Input start of sweep in Vpp: ")
    V_start = float(V_start)
    print(V_start)
    V_stop = input("Input stop of sweep in Vpp: ")
    V_stop = float(V_stop)
    print(V_stop)
    V_step = input("Input number of steps: ")
    V_step = float(V_step)
    print(V_step)

    axis_spacing = input("1 for log scale, 0 for linear scale: ")
    if axis_spacing == '1':
        V_start_log = log10(V_start)
        V_stop_log = log10(V_stop)
        V_AFG = logspace(V_start_log,V_stop_log,V_step)
        print("V_AFG(log10(%f),log10(%f),%f)"%(V_start,V_stop,V_step))
        print("V_AFG(%f,%f,%f)"%(log10(V_start),log10(V_stop),V_step))
        print(V_AFG)
    elif axis_spacing == '0':
        V_AFG = linspace(V_start,V_stop,V_step)
        print("V_AFG(%f,%f,%f)"%(V_start,V_stop,V_step))
        print(V_AFG)
    
    method_choice = input("1 for PP method, 0 for RMS method: ")
    if method_choice == '1':
        rms_method = False
    elif method_choice == '0':
        rms_method = True
    if rms_method:
        method = 'RMS'
    if not rms_method:
        method = 'PP'
    print("*** Processing method:",method,"***\n")
        # }}}
# {{{ Signal processing function
def gen_power_data(date, id_string, V_AFG, rms_method,
        pulse_threshold=0.5):
    # {{{ documentation
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
    return_power : nddata
        output power (y-axis) vs input power (x-axis) for each capture
    """
    #}}}
    #{{{ RMS function: calculates power by subtracting RMS noise from RMS signal, both analytic
    def rms_signal_to_power(data,ch):
        "find the pulse, calculate the noise and signal powers and subtract them"
        pulse0_slice = abs(data['power',-1]).contiguous(lambda x: x>pulse_threshold*x.data.max())
        pulse0_slice = pulse0_slice[0,:]
        pulse_limits = pulse0_slice + r_[0.6e-6,-0.6e-6]
        noise_limits = pulse0_slice - r_[0.6e-6,-0.6e-6]
        p0_lim1,p0_lim2 = pulse_limits
        n0_lim1,n0_lim2 = noise_limits
        Vn1_rms0 = sqrt((abs(data['t':(0,n0_lim1)]
            )**2).mean('t',return_error=False))
        Vn2_rms0 = sqrt((abs(data['t':(0,n0_lim2)]
            )**2).mean('t',return_error=False))
        Vn_rms0 = (Vn1_rms0 + Vn2_rms0)/2.
        V_rms0 = sqrt((abs(data['t':tuple(pulse0_slice)]
            )**2).mean('t',return_error=False))
        V_rms0 -= Vn_rms0
        print('CH',ch,'Noise limits in microsec: %f, %f'%(n0_lim1/1e-6,n0_lim2/1e-6))
        print('CH',ch,'Pulse limits in microsec: %f, %f'%(p0_lim1/1e-6,p0_lim2/1e-6))
        return (V_rms0)**2./50.
    #}}}
    #{{{ PP method: calculates power by subtract min from max analytic signal within pulse slice
    def pp_signal_to_power(data,ch):
        pulse_max = abs(data['power',-1].data.max())
        pulse_slice = abs(data['power',-1]).contiguous(lambda x: x>pulse_threshold*x.data.max())
        pulse_slice = pulse_slice[0,:]  
        pulse_slice += r_[0.6e-6,-0.6e-6]
        pulse_limits = tuple(pulse_slice)
        p_lim1,p_lim2 = pulse_limits
        print('CH',ch,'Pulse limits in microsec: %f, %f'%(p_lim1/1e-6,p_lim2/1e-6))
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
        print("accumulated data was not found, pulling individual captures")
        for j in range(1,p_len+1):
            print("loading signal",j)
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
        #{{{Optional - plots analytic pulse cut off 
    fl.next('Lowest power, analytic')
    fl.plot(abs(analytic_signal['ch',0]['power',0]),label=id_string)
    fl.plot(abs(analytic_signal['ch',1]['power',0]),label=id_string)
    lowest_power = abs(analytic_signal['power',0])
    for ch in range(0,2):
        this_data = lowest_power['ch',ch]
        pulse0_slice = this_data.contiguous(lambda x: x>pulse_threshold*x.data.max())
        pulse0_slice = tuple(pulse0_slice[0,:])
        fl.plot(this_data['t':pulse0_slice]['t',r_[0,-1]],'o',label='CH%s'%str(ch))
    fl.next('Highest power, analytic')
    fl.plot(abs(analytic_signal['ch',0]['power',-1]),label=id_string)
    fl.plot(abs(analytic_signal['ch',1]['power',-1]),label=id_string)
    highest_power = abs(analytic_signal['power',-1])
    for ch in range(0,2):
        this_data = highest_power['ch',ch]
        pulse0_slice = this_data.contiguous(lambda x: x>pulse_threshold*x.data.max())
        pulse0_slice = tuple(pulse0_slice[0,:])
        fl.plot(this_data['t':pulse0_slice]['t',r_[0,-1]],'o',label='CH%s'%str(ch))
        #}}}
    print("DATA: %s"%id_string) 
    #{{{ NOTE: ASSUMES CH1=REFERENCE AND CH2=DUT
    if rms_method:
        power0 = rms_signal_to_power(analytic_signal['ch',0],ch=1)
        power0 *= atten_factor
        power1 = rms_signal_to_power(analytic_signal['ch',1],ch=2)
    if not rms_method:
        power0 = abs(pp_signal_to_power(analytic_signal['ch',0],ch=1))
        power0 *= atten_factor
        power1 = abs(pp_signal_to_power(analytic_signal['ch',1],ch=2))
        #}}}
    return_power = power1
    return_power.name('$P_{out}  (W)$')#.set_units('W')
    return_power.rename('power','$P_{in}  (W)$').setaxis('$P_{in}  (W)$',power0.data)#.set_units('$P_{in}$','W')
    return return_power
#}}}
atten_factor = 7.056e-5
for date,id_string in [
        #('180610','sweep_LNA1'),
        #('180610','sweep_pmdpx_LNA1'),
        #('180610','sweep_LNA2'),
        #('180610','sweep_pmdpx_LNA2'),
        #('180610','sweep_casc12'),
        ('180610','sweep_pmdpx_casc12'),
        ('180803','sweep_dcasc'),
        ('180803','sweep_spec'),
        ]:
    # {{{ plot labels
    if id_string == 'sweep_LNA1':
        label = 'LNA #1'
    elif id_string == 'sweep_pmdpx_LNA1':
        label = 'LNA #1 + Duplexer'
    elif id_string == 'sweep_LNA2':
        label = 'LNA #2'
    elif id_string == 'sweep_pmdpx_LNA2':
        label = 'LNA #2 + Duplexer'
    elif id_string == 'sweep_casc12':
        label = 'Cascade (#1,#2)'
    elif id_string == 'sweep_pmdpx_casc12':
        label = 'Cascade + Duplexer (June)'
    elif id_string == 'sweep_spec':
        label = 'Spectrometer setup'
    elif id_string == 'sweep_dcasc':
        label = 'Cascade + Duplexer'
    else :
        label = '%s'%id_string
        #}}}
    power_plot = gen_power_data(date,id_string,V_AFG,rms_method)
#    truncate_LNAp = LNA_power['$P_{in}$':((1e2*1e-12),None)]
    fl.next('Determining gain factors (%s method)'%method)
    fl.plot(power_plot,'.',label='%s'%label,plottype='loglog',)
    c,result = power_plot.polyfit('$P_{in}  (W)$',force_y_intercept=0)
    fl.plot(result,label='gain = %0.2f'%(c[0][1]),alpha=0.6,plottype='loglog')
    print("Fit parameters for",id_string)
    print(c,'\n')
fl.show()


