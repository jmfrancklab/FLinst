from pyspecdata import *
fl = figlist_var()
import os
import sys
#4096 points
# {{{ constants measured elsewhere
gain_factor_amp1 = 525.94786172         #LNA 2
gain_factor_amp2 = 531.84920761         #LNA 1
gain_factor_casc12 = 171428.95568926    #cascade (1 then 2)
gain_factor_damp1 = 318.5103874         #duplexer,LNA 1 
gain_factor_damp2 = 325.65682308        #duplexer,LNA 2 
gain_factor_dcasc12 = 114008.55204672   #duplexer,cascade(1,2)
gain_factor_pdcasc12 =45514.53212012    #probe,duplexer,cascade

#gain_factor_amp1 = 521.27172202                         #LNA1 gain factor
#gain_factor_amp2 = 529.98023528                        #LNA2 gain factor
#gain_factor_amp3 = 523.73589899                        #LNA3 gain factor
##gain_factor_casc12_ = 203383.76725939914
##gain_factor_casc12 = 174549.75561175 
#gain_factor_casc12 = 193879.86939256                  #LNA1,LNA2 gain factor
#gain_factor_dpx_ = 0.6141065062411988
#gain_factor_dpx = 0.7156772659294433                  #Duplexer gain factor
##gain_factor_tot = 113984.00001949
#gain_factor_tot = 120618.95681133 
scope_noise = 4.4578468934e-19                         # pulled from the gain=1.0 calculation of the
                                                        # scope noise, below
atten_factor = 7.056e-5
T = 273.15 + 20.
power_signal_AFG = ((50.e-3)/(sqrt(2)*2))**2./50.
test_signal_power = power_signal_AFG * atten_factor
# }}}
    # {{{ command line arguments for integration interval 
default = True
try:
    sys.argv[1]
    default = False
except:
    sys.argv[0]
if default:
    integration = False
if not default:
    integration = True
    width_choice = int(sys.argv[1])
    if width_choice == 1:
        integration_center = 1.45e7
        integration_width = 2.2e6
    elif width_choice == 2:
        integration_center = 1.452e7
        integration_width = 2.42e5
    elif width_choice == 3:
        integration_center = 14.5e6 
        integration_width = 5.7e6
    elif width_choice == 4:
        integration_center = 1.45e7
        integration_width = 6.28e6
    elif width_choice == 5:
        integration_center = 1.45e7
        integration_width = 8.11e5
    elif width_choice == 20:
        integration_center = 20.e6 
        integration_width = 6.4e6
    elif width_choice == 25:
        integration_center = 25.e6 
        integration_width = 6.3e6
    elif width_choice == 43:
        integration_center = 43.47655e6 
        integration_width = 15.14685e6
    elif width_choice == 55:
        integration_center = 55.e6 
        integration_width = 10.e6
    else:
        print("Unrecognized width choice")
        integration_center = 14.5e6 
        integration_width = 2.e6
    # }}}
#{{{ loads noise into accumulated data file for faster processing
def load_noise(date,id_string,captures):
    cap_len = len(captures)
    filename = date+'_'+id_string+'.h5'
    try:
        s = nddata_hdf5(filename+'/accumulated_'+date,
                directory=getDATADIR(exp_type='test_equip'))
        s.set_units('t','s')
    except:
        print("accumulated data was not found, pulling individual captures")
        for j in range(1,cap_len+1):
            j_str = str(j)
            d = nddata_hdf5(filename+'/capture'+j_str+'_'+date,
                directory=getDATADIR(exp_type='test_equip'))
            d.set_units('t','s')
            if j == 1:
                channels = ((ndshape(d)) + ('capture',cap_len)).alloc()
                channels.setaxis('t',d.getaxis('t')).set_units('t','s')
                channels.setaxis('ch',d.getaxis('ch'))
            print("loading signal %s into capture %s "%(j_str,j_str))
            channels['capture',j-1]=d        
        s = channels
        s.labels('capture',captures)
        s.name('accumulated_'+date)
        s.hdf5_write(filename,
                directory=getDATADIR(exp_type='test_equip'))
    return s
#}}}
    #{{{ generate power spectral density function 
def generate_psd(data,acq_time,gain_factor):
    data.ft('t')
    data = abs(data)**2         #mod square
    data.mean('capture', return_error=False)
    width = 1e6
    data.convolve('t',width)
    data /= 50.              # divide by resistance, gives units: W*s, or W/Hz
    data /= acq_time         # divide by acquisition time
    data *= 2                # because the power is split over negative and positive frequencies
#     if gain_factor != 1: # if we're not talking about the scope noise
#         s -= scope_noise
    data /= gain_factor      # divide by gain factor, found from power curve -->
    return data,width
    # }}}

captures = linspace(0,100,100)
power_dens_CH1_dict = {}
power_dens_CH2_dict = {}
for date,id_string,numchan,gain_factor in [
#        ('180626','network_22MHz_pulse_noise',2,gain_factor_dcasc12),
#        ('180626','network_22MHz_pulse_noise_atten_250M_2',2,gain_factor_dcasc12),
#            ('180626','network_22MHz_pulse_noise_atten2_100M',2,gain_factor_dcasc12),
#            ('180626','network_22MHz_pulse_noise_atten2_2_100M',2,gain_factor_dcasc12),
#            ('180626','network_22MHz_pulse_noise_atten2_3_100M',2,gain_factor_dcasc12),
#            ('180626','network_22MHz_pulse_noise_atten3_100M',2,gain_factor_dcasc12),
#            ('180626','network_22MHz_pulse_noise_atten3_2_100M',2,gain_factor_dcasc12),
#            ('180626','network_22MHz_pulse_noise_atten3_3_100M',2,gain_factor_dcasc12),
            ('180626','network_22MHz_pulse_noise_atten3_4_100M',2,gain_factor_dcasc12),
            ('180709','network_9_3',2,gain_factor_dcasc12),
#            ('180626','network_22MHz_pulse_noise_atten3_5_100M',2,gain_factor_dcasc12),
#            ('180627','test_se_amp_3',2,gain_factor_dcasc12),
#            ('180627','test_se_amp_4',2,gain_factor_dcasc12),
#            ('180627','test_se_amp_5',2,gain_factor_dcasc12),
#            ('180627','test_se_amp_6',2,gain_factor_dcasc12),
#            ('180628','test_se_amp_4',2,gain_factor_dcasc12),
#            ('180628','test_se_amp_5',2,gain_factor_dcasc12),
#            ('180628','test_se_amp_11',2,gain_factor_dcasc12),
            #('180628','test_se_amp_12',2,gain_factor_dcasc12), 
            #('180628','spin_echo_exp',2,gain_factor_dcasc12), 
            #('180630','spin_echo_exp_block2',2,gain_factor_dcasc12), 
    ]:
    label = date+'_'+id_string
    print("\n*** LOADING:",id_string,"***")
    d = load_noise(date,id_string,captures)['ch',0]
    print(ndshape(d))
    # Preliminary processing, from gen_power_data()
    raw_signal = (ndshape(d)).alloc()
    raw_signal.setaxis('t',d.getaxis('t')).set_units('t','s')
    raw_signal.setaxis('capture',d.getaxis('capture'))
    d.ft('t',shift=True)
    d = d['t':(0,None)]
    d['t':(20e6,None)] = 0
    d['t':(0,10e6)] = 0
    d.ift('t')
    noise_slice = (161e-6,250e-6)
    d = d['t':noise_slice]
    acq_time = diff(d.getaxis('t')[r_[0,-1]])[0]
    print(acq_time) 
    print(ndshape(d))
#    d.ift('t')
#    y = d['capture',1]
#    y.name('Volts')
#    fl.next('Processed, 14.5 MHz pulse')
#    fl.plot(y,alpha=0.5,label='without 5 MHz high pass')
#    y.ft('t')
#    y.ift('t')
#    fl.plot(y,alpha=0.5,label='with 5 MHz high pass')
#    fl.plot(y['t':noise_slice]['t',r_[0,-1]],'o',color='black',alpha=0.4,label='noise slice')
#    dt_power_density,width = generate_psd(deadtime,acq_time,gain_factor)
#    fl.next('Processed, 14.5 MHz pulse')
#    fl.plot(y,alpha=0.3)
    #fl.next('after deadtime %s'%id_string)
    #fl.plot(after_deadtime)
    dt_power_density,width = generate_psd(d,acq_time,gain_factor)
    #{{{ processing without integration over frequency band
    if not integration:
        fl.next('Power Spectral Density (Input-referred)')
        dt_power_density.name('$S_{xx}(\\nu)$').set_units('W/Hz')
        fl.plot(dt_power_density, alpha=0.35, label='%s'%label, plottype='semilogy' )
        axhline(y=k_B*T/1e-12, alpha=0.9, color='purple') # 1e-12 b/c the axis is given in pW
            #}}}
    #{{{ processing with integration over frequency bands
    if integration:
        interval = tuple(integration_center+r_[-1,1]*integration_width)
        startf,stopf = tuple(interval)
        print("INTEGRATION INTERVAL:",startf/1e6,"to",stopf/1e6,"MHz")
        if 'ch' not in s.dimlabels:
            # {{{ a hack to create a fake ch axis
            t_label = s.getaxis('t')
            t_units = s.get_units('t')
            s.setaxis('t',None)
            s.chunk('t',['t','ch'],[-1,1])
            s.setaxis('t',t_label)
            s.set_units('t',t_units)
            # }}}
#        try:
#            s_slice = s['t':interval]['ch',0] #CH1=DUT
#        #{{{ for scope noise test
#        except:
#            raise ValueError(strm("problem trying to pull the slice, shape of s is",ndshape(s),"numchan is",numchan))
#        if gain_factor == 1.0:
#            print "Noise coming from the scope is",s['t':interval]['ch',0].mean('t', return_error=False).data
#
#            #}}}
#        else:
        fl.next('FULL Power Spectral Density (Input-referred) (convolution = %0.1e Hz)'%width)
        s.name('$S_{xx}(\\nu)$').set_units('W/Hz')
#        s_slice.name('$S_{xx}(\\nu)$').set_units('W/Hz')
        fl.plot(s['ch',0], alpha=0.35, label="%s"%label, plottype='semilogy')
        axhline(y=k_B*T/1e-12, alpha=0.9, color='purple') # 1e-12 b/c the axis is given in pW
#        fl.next('Power Spectral Density (Input-referred) (convolution = %0.1e Hz)'%width)
#        fl.plot(s['t':(0,250e6)]['ch',0], alpha=0.35, label="%s"%label, plottype='semilogy')
        #   fl.plot(s_slice, alpha=0.8, color='black', label="integration slice",
        #      plottype='semilogy')
        axhline(y=k_B*T/1e-12, alpha=0.9, color='purple') # 1e-12 b/c the axis is given in pW
        #    # {{{ calculates power at input of component over specified frequency interval
        #    if numchan == 2:
        #        #CH1=DUT, CH2=REF(signal) or NULL(noise)
        #        print "CH1 POWER IS:",s['t':interval]['ch',0].integrate('t')
        #        print "CH2 POWER IS:",s['t':interval]['ch',1].integrate('t')*atten_factor*gain_factor
        #        power_dens_CH2_dict[id_string] = (s['t':interval]['ch',1].integrate('t').data)
        #        # }}}
        #    power_dens_CH1_dict[id_string] = s['t':interval]['ch',0].integrate('t').data
        #    expand_x()
        #    print "THERMAL NOISE POWER IS:",k_B*T*float(interval[-1]-interval[0])
        #    NF = (s['t':interval]['ch',0].integrate('t').data)/(k_B*T*float(interval[-1]-interval[0]))
        #    print "NOISE FIGURE IS:",NF
        #    print "EFFECTIVE TEMPERATURE IS:",(293.0*(NF-1))
        #    print "*** EXITING:",id_string,"***"
        #print "error is %0.12f"%(((power_dens_CH1_dict['sine_pomona_dpx_cascade12_2CH'] - power_dens_CH1_dict['noise_pomona_dpx_cascade12_2CH'] - power_dens_CH2_dict['sine_pomona_dpx_cascade12_2CH'])/power_dens_CH2_dict['sine_pomona_dpx_cascade12_2CH'])*100)
        #}}}
fl.show()

