from pyspecdata import *
fl = figlist_var()
import os
import sys
matplotlib.rcParams['legend.fontsize'] ='xx-small'
matplotlib.rcParams['legend.labelspacing'] = 0.2 
rcParams['savefig.transparent'] = True
#4096 points
# {{{ constants measured elsewhere
gain_factor_new = 73503.77279 
gain_factor_amp1 = 525.94786172         #LNA 2
gain_factor_amp2 = 531.84920761         #LNA 1
gain_factor_casc12 = 171428.95568926    #cascade (1 then 2)
gain_factor_damp1 = 318.5103874         #duplexer,LNA 1 
gain_factor_damp2 = 325.65682308        #duplexer,LNA 2 
gain_factor_dcasc12 = 114008.55204672   #duplexer,cascade(1,2)
gain_factor_pdcasc12 = 45514.53212012    #probe,duplexer,cascade

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
# }}}
captures = linspace(0,100,100)
power_dens_CH1_dict = {}
power_dens_CH2_dict = {}

# {{{ call files
for date,id_string,numchan,gain_factor in [
        #('180601','noise_pomona_dpx_cascade12_2CH',2,gain_factor_casc12),
        #('180530','noise_dpx_cascade12_2CH',2,gain_factor_casc12),
        #('180710','spectrometer_noise_50ohm',2,gain_factor_new),
        #('180710','spectrometer_noise_AFG_smagnet',2,gain_factor_new),
        #('180926','noise_probe',2,gain_factor_new),
        #('180927','noise_probe_Magnet',2,gain_factor_new),
        #('180927','noise_probe_TXD_ENI_Magnet',2,gain_factor_new),
        #('180927','noise_spectrometer',2,gain_factor_new),
        #('181001','noise_probe_magnet',2,gain_factor_new),
        #('181001','noise_probe_magnet_ENI',2,gain_factor_new), # 20 us/div
        #('181001','noise_probe_magnet_ENI_2',2,gain_factor_new), # 50 us/div
        #('181001','noise_probe_magnet_ENI_3',2,gain_factor_new), # 10 us/div
        #('181001','noise_spec_1',2,gain_factor_new), # 10 us/div
        #('181001','noise_spec_2',2,gain_factor_new), # 20 us/div
        #('181103','noise_spec',2,gain_factor_new), # 20 us/div
        #('181103','noise_spec_TL',2,gain_factor_new), # 20 us/div
        #('180926','noise_probe_TXD',2,gain_factor_new),
        #('180926','noise_probe_TXD_ENI_off',2,gain_factor_new),
        #('180926','noise_probe_TXD_ENI_on',2,gain_factor_new),
        #('180926','noise_probe_TXD_ENI_Magnet',2,gain_factor_new),
        #('180710','spectrometer_noise_AFG',2,gain_factor_new),
        #('180710','spectrometer_noise_AFG_magnet',2,gain_factor_new),
        #('180710','spectrometer_noise_AFG_smagnet',2,gain_factor_new),
        #('190220','probev2',1,gain_factor_new),
        #('190220','probev2_noTL',1,gain_factor_new),
        #('190220','probev2_noTL_2',1,gain_factor_new),
        #('190220','probev2_ENI',1,gain_factor_new),
        #('190220','probev2_ENI_2',1,gain_factor_new),
        #('190220','probev2_ENI_3',1,gain_factor_new),
        #('190220','probev2_SC',1,gain_factor_new),
        #('190220','probev2_magoff',1,gain_factor_new),
        #('190220','probev2_magon',1,gain_factor_new),
        #('190220','probev2_magon_2',1,gain_factor_new),
        #('190220','probev2A_magoff',1,gain_factor_new),
        #('190220','probev2A_magon',1,gain_factor_new),
        #('190220','probev2A_magon_2',1,gain_factor_new),
        #('190220','probev2A_magon_3',1,gain_factor_new),
        #('190220','probev2C_magoff',1,gain_factor_new),
        #('190220','probev2C_magon',1,gain_factor_new),
        #('190220','probev2C_magon_2',1,gain_factor_new),
        #('190220','probev2D_magoff',1,gain_factor_new),
        #('190220','probev2D_magon',1,gain_factor_new),
        #('190220','probev2D_magon_2',1,gain_factor_new),
        #('190220','probev2B_ENI_1',1,gain_factor_new),
        #('190220','probev2B_ENI_2',1,gain_factor_new),
        #('190220','probev2B_ENI_3',1,gain_factor_new),
        #('190220','probev2B_SC',1,gain_factor_new),
        #('190220','probev2B_magoff',1,gain_factor_new),
        #('190220','probev2B_magon',1,gain_factor_new),
        #('190220','probev2B_magon_2',1,gain_factor_new),
        #('190221','probev2',2,gain_factor_new), #50 mV/div, CH2 200 mV
        #('190221','probev2_1',2,gain_factor_new), #50 mV/div, CH2 200 mV
        #('190221','probev2_2',2,gain_factor_new), #10 mV/div, CH2 200 mV
        #('190221','probev2_3',2,gain_factor_new), #20 mV/div, CH2 200 mV
        #('190221','probev2_6',2,gain_factor_new), #20 mV/div, CH2 200 mV
        #('190221','probev2_7',2,gain_factor_new), #20 mV/div, CH2 200 mV
        #('190408','noise_1',2,gain_factor_new),
        #('190408','noise_2',2,gain_factor_new),
        #('190408','noise_3',2,gain_factor_new),
        #('190408','noise_4',2,gain_factor_new),
        #('190408','noise_5',2,gain_factor_new),
        #('190408','noise_6',2,gain_factor_new),
        #('190408','noise_7',2,gain_factor_new),
        #('190409','noise_1',2,gain_factor_new),
        #('190409','noise_2',2,gain_factor_new),
        #('190409','noise_3',2,gain_factor_new),
        #('190409','noise_4',2,gain_factor_new),
        #('190409','noise_4_1',2,gain_factor_new),
        #('190410','noise_50Ohm_RX',2,gain_factor_new), #50 mVdiv
        #('190410','noise_50Ohm_RX_2',2,gain_factor_new), #5 mVdiv
        #('190410','noise_50Ohm_RX_3',2,gain_factor_new), #10 mVdiv
        #('190410','noise_50Ohm_RX_4',2,gain_factor_new), #20 mVdiv
        #('190410','noise_50Ohm_AMP_RX',2,gain_factor_new),
        #('190410','noise_50Ohm_AMP_RX_2',2,gain_factor_new),
        #('190410','noise_50Ohm_AMP_TXD_RX',2,gain_factor_new),
        #('190410','noise_50Ohm_AMP_TXD_RX_2',2,gain_factor_new),
        #('190410','noise_TX_RX',2,gain_factor_new),
        #('190410','noise_TX_RX_console',2,gain_factor_new),
        #('190410','noise_TX_RX_magnet',2,gain_factor_new), #20 mVdiv
        #('190410','noise_TX_RX_magnet_2',2,gain_factor_new), #50 mVdiv
        #('190410','noise_TX_RX_magnet_3',2,gain_factor_new), #100 mVdiv
        #('190410','noise_TX_RX_magnet_3_2',2,gain_factor_new),
        #('190410','noise_TX_RX_magnet_2_2',2,gain_factor_new),
        #('190410','noise_TX_RX_magnet_1_2',2,gain_factor_new),
        #('190410','noise_TX_RX_magnet_2_3',2,gain_factor_new),
        #('190410','noise_TX_RX_magnet_2_3_1',2,gain_factor_new),
        #('190410','noise_TX_RX_magnet_2_4',2,gain_factor_new),
        #('190411','50RX_1',2,gain_factor_new),
        #('190411','50RX_2',2,gain_factor_new),
        #('190411','50AMP_RX_1',2,gain_factor_new),
        #('190411','50AMP_RX_2',2,gain_factor_new),
        #('190411','TX_RX_1',2,gain_factor_new),
        #('190411','TX_RX_2',2,gain_factor_new),
        #('190411','console_TX_RX_1',2,gain_factor_new),
        #('190411','console_TX_RX_2',2,gain_factor_new),
        #('190411','magnet_TX_RX_1',2,gain_factor_new),
        #('190411','magnet_TX_RX_2',2,gain_factor_new),
        #('190411','Cu_1',2,gain_factor_new),
        #('190411','Cu_2',2,gain_factor_new),
        #('190415','probe',2,gain_factor_new),
        #('190415','probe_2',2,gain_factor_new),
        #('190415','TX_RX',2,gain_factor_new),
        #('190415','TX_RX_2',2,gain_factor_new),
        #('190415','console',2,gain_factor_new),
        #('190415','console_2',2,gain_factor_new),
        #('190415','magnet',2,gain_factor_new),
        #('190423','probe',2,gain_factor_new),
        #('190423','AMP',2,gain_factor_new),
        #('190423','TX',2,gain_factor_new),
        #('190423','TX_2',2,gain_factor_new),
        #('190423','system',2,gain_factor_new),
        #('190423','magnet',2,gain_factor_new),
        #('190423','magnet_2',2,gain_factor_new),
        #('190423','disconnected',2,gain_factor_new),
        #('190423','magnet_3',2,gain_factor_new),
        #('190423','magnet_4',2,gain_factor_new),
        #('190423','probe_B',2,gain_factor_new),
        #('190423','probe_foil',2,gain_factor_new),
        #('190423','probe_foil_magnet',2,gain_factor_new),
        #('190423','probe_B_magnet',2,gain_factor_new),
        #('190424','probev1p5_solenoid_1',2,gain_factor_new),
        #('190424','probev1p5_solenoid_2',2,gain_factor_new),
        #('190424','probev1p5_solenoid_3',2,gain_factor_new),
        #('190424','probev1p5_solenoid_4',2,gain_factor_new),
        #('190424','probev1p5_solenoid_5',2,gain_factor_new),
        #('190424','probev1p5_solenoid_6',2,gain_factor_new),
        #('190424','probev1p5_solenoid_7',2,gain_factor_new),
        #('190424','probev1p5_solenoid_8',2,gain_factor_new),
        #('190424','probev1p5_solenoid_10',2,gain_factor_new),
        #('190424','probev1p5_solenoid_11',2,gain_factor_new),
        #('190425','probev1p5_solenoid_1',2,gain_factor_new),
        #('190425','term_1',2,gain_factor_new),
        #('190425','term_2',2,gain_factor_new),
        #('190425','term_3',2,gain_factor_new),
        #('190425','term_4',2,gain_factor_new),
        #('190425','term_4_1',2,gain_factor_new),
        #('190425','term_5',2,gain_factor_new),
        #('190425','term_5_1',2,gain_factor_new),
        #('190425','term_5_2',2,gain_factor_new),
        #('190425','term_5_3',2,gain_factor_new),
        #('190425','term_5_4',2,gain_factor_new),
        #('190425','term_5_5',2,gain_factor_new),
        #('190425','term_6',2,gain_factor_new),
        #('190425','term_7',2,gain_factor_new),
        #('190425','term_7_1',2,gain_factor_new),
        #('190425','term_7_1_1',2,gain_factor_new),
        #('190425','term_8',2,gain_factor_new),
        #('190425','term_9',2,gain_factor_new),
        #('190425','term_11',2,gain_factor_new),
        #('190425','term_12',2,gain_factor_new),
        #('190425','term_13',2,gain_factor_new),
        #('190425','term_14',2,gain_factor_new),
        #('190425','term_15',2,gain_factor_new),
        #('190425','term_16',2,gain_factor_new),
        #('190425','term_17',2,gain_factor_new),
        #('190425','term_17_1',2,gain_factor_new),
        #('190425','term_17_1_1',2,gain_factor_new),
        #('190425','term_18',2,gain_factor_new),
        #('190425','term_19',2,gain_factor_new),
        #('190425','term_20',2,gain_factor_new),
        #('190425','term_21',2,gain_factor_new),
        #('190425','term_22',2,gain_factor_new),
        #('190425','term_23',2,gain_factor_new),
        #('190425','term_24',2,gain_factor_new),
        #('190425','term_24_9inch',2,gain_factor_new),
        #('190425','term_24_58inch',2,gain_factor_new),
        #('190425','term_25_0_0',2,gain_factor_new),
        #('190425','term_25_0_1',2,gain_factor_new),
        #('190425','term_25_0_2',2,gain_factor_new),
        #('190425','term_25_0_0_1',2,gain_factor_new),
        #('190425','term_test_0_0',2,gain_factor_new),
        #('190425','term_test_0_1',2,gain_factor_new),
        #('190425','term_test_0_2',2,gain_factor_new),
        #('190425','term_test_1_0',2,gain_factor_new),
        #('190425','term_test_1_1',2,gain_factor_new),
        #('190425','term_test_1_2',2,gain_factor_new),
        #('190425','term_test_2_0',2,gain_factor_new),
        #('190425','term_test_2_1',2,gain_factor_new),
        #('190425','term_test_2_2',2,gain_factor_new),
        #('190425','term_test_2_3',2,gain_factor_new),
        #('190425','term_test_1_0_0',2,gain_factor_new),
        #('190425','term_test_1_0_0_0_0_0',2,gain_factor_new),
        #('190425','term_test_1_0_1',2,gain_factor_new),
        #('190425','term_test_1_0_2',2,gain_factor_new),
        #('190425','term_test_1_0_0_0',2,gain_factor_new),
        #('190425','term_test_1_0_0_1',2,gain_factor_new),
        #('190425','term_test_1_0_0_2',2,gain_factor_new),
        #('190425','term_test_1_0_0_0_0',2,gain_factor_new),
        #('190425','term_test_1_0_0_0_1',2,gain_factor_new),
        #('190425','term_test_1_0_0_0_0_1',2,gain_factor_new),
        #('190425','term_test_1_0_0_0_0_0_0',2,gain_factor_new),
        #('190425','term_test_1_0_0_0_0_0_1',2,gain_factor_new),
        #('190425','term_test_3_0',2,gain_factor_new),
        #('190425','term_test_3_1',2,gain_factor_new),
        #('190531','term_test_0',2,gain_factor_new),
        #('190531','term_test_0_12in',2,gain_factor_new),
        #('190531','term_test_0_24in',2,gain_factor_new),
        #('190531','term_test_0_36in',2,gain_factor_new),
        #('190531','term_test_0_48in',2,gain_factor_new),
        #('190531','term_test_0_60in',2,gain_factor_new),
        #('190531','term_test_0_72in',2,gain_factor_new),
        #('190531','term_test_0_72in',2,gain_factor_new),
        #('190712','test_4',2,gain_factor_new),
        #('190712','test_5',2,gain_factor_new),
        ('190716','test_2',2,gain_factor_new),
        #('190716','test_3',2,gain_factor_new),
        #('200212','test_50_off_0',2,gain_factor_new),
        #('200212','test_50_off_1',2,gain_factor_new),
        ('200212','test_50_off_2',2,gain_factor_new),
        ('200212','test_50_on_0',2,gain_factor_new),
        #('200212','test_short50_on_0',2,gain_factor_new),
        #('200212','test_long50_on_0',2,gain_factor_new),

    ]:
    # }}}
    # {{{ plot labels
    plot_params = False # toggle this to use plot params preset below
    label = date+'_'+id_string 
    probe2 = True
    if probe2:
        if 'probev2D_magon' in id_string:
            #label = 'spectrometer (EPR system on, DC on) probe v2.0'
            label = 'spectrometer noise, probe v2.0'
        if 'ENI' in id_string:
            label = r'50$\Omega$ input to ENI, probe v2.0'
        if 'SC' in id_string:
            label = 'spectrometer, no EPR system, probe v2.0'
        if 'magoff' in id_string:
            label = 'spectrometer, EPR system on, DC off, probe v2.0'
        if 'probev2B_magon' in id_string:
            label = 'full spectrometer, probe v2.0 detached from cavity'
    plot_labels = True
    if plot_labels:
        if 'test_0_0' in id_string:
            label = 'No box, magnet off'
        elif 'test_1_0' in id_string:
            label = 'No box, magnet on'
        elif 'test_50_off' in id_string:
            label = 'Box, magnet off'
        elif 'test_50_on' in id_string:
            label = 'Box, magnet on'
        elif 'test_short50_on' in id_string:
            label = 'Box, magnet on, 1 ft BNC'
        elif 'test_long50_on' in id_string:
            label = 'Box, magnet on, 5.5 ft BNC'
        #}}}
    #label += ' (g=%0.2f)'%gain_factor
   # }}}
    print("\n*** LOADING:",id_string,"***")
    s = load_noise(date,id_string,captures)
    #{{{ slicing
    if 'spectrometer_noise' in id_string:
        u = s.C['t':(124e-6,None)]
        #{{{ old slicing
    elif '250MSPS' in id_string:
        u = s.C['t':(40e-6,None)]       #250 MSPS
    elif '500MSPS' in id_string:
        u = s.C['t':(0,35e-6)]          #500 MSPS
    elif id_string == 'control_SE':
        u = s.C['t':(159.0e-6,None)]   #100 MSPS
    elif id_string == 'control_SE_nofilter':
        u = s.C['t':(159.0e-6,None)]   #100 MSPS
    elif id_string == 'network_SE':
        u = s.C['t':(159.0e-6,None)]   #100 MSPS
    elif id_string == 'network_SE_full':
        u = s.C['t':(100.0e-6,None)]   #100 MSPS
        #}}}
    else:
        u = s.C
        #}}}
    acq_time = diff(s.getaxis('t')[r_[0,-1]])[0]
    u_acq_time = diff(u.getaxis('t')[r_[0,-1]])[0]
    print(acq_time)
    print("\t")
    print(u_acq_time)
    print("\t")
    print("ACQUISITION TIME IS:\t",acq_time)
    #{{{ calculate PSD for s
    s.ft('t',shift=True)
    s = abs(s)['t':(0,None)]**2   #mod square and throw out negative frequencies
    s.mean('capture')
    width = 0.04e6
    #s.convolve('t',width) # we do this before chopping things up, since it uses
    #                      fft and assumes that the signal is periodic (at this
    #                      point, the signal at both ends is very close to
    #                      zero, so that's good
    s /= 50.              # divide by resistance, gives units: W*s, or W/Hz
    s /= acq_time         # divide by acquisition time
    s *= 2               # because the power is split over negative and positive frequencies
#    if gain_factor != 1: # if we're not talking about the scope noise
#        s -= scope_noise
    s /= gain_factor      # input referred power
    #                       
    # }}}
    #{{{ calculate PSD for u 
    u_filt = u.C
    ##fl.next('plot')
    ##fl.plot(u['capture',1])
    u.ft('t',shift=True)
    u = abs(u)['t':(0,None)]**2
    u.mean('capture')
    #u.convolve('t',width)
    u /= 50.
    u /= u_acq_time
    u *= 2
    u /= gain_factor
    #}}}
    filtering = True
    #{{{ calculate PSD for filtered u
    if filtering:
        u_filt.ft('t',shift=True)
        ##fl.plot(u_filt['capture',1])
        ##fl.show()
        ##quit()
        u_filt = abs(u_filt)['t':(0,None)]**2
        u_filt.mean('capture')
        u_filt.convolve('t',width)
        u_filt /= 50.
        u_filt /= u_acq_time
        u_filt *= 2
        u_filt /= gain_factor
    #}}}
    if not integration:
            if not plot_params:
                s /= k_B*T
                u /= k_B*T
                u_filt /= k_B*T
                fl.next('Network Noise Power Spectral Density (Input-referred) (convolution = %0.1e Hz)'%width)
                s.name('${S(\\nu)}/{k_{B}T}$')
                fl.plot(s['ch',0],alpha=0.35,label='%s'%label,plottype='semilogy')
                #axhline(y=k_B*T/1e-12, alpha=0.9, color='purple') # 1e-12 b/c the axis is given in pW
                fl.next('Network Noise Power Spectral Density, Input-referred')
                u.name('${S(\\nu)}/{k_{B}T}$')
                fl.plot(u['ch',0],alpha=0.35,plottype='semilogy')
                #axhline(y=k_B*T/1e-12, alpha=0.9, color='purple') # 1e-12 b/c the axis is given in pW
                u_filt = u_filt['t':(None,45e6)]
                if filtering:
                    fl.next('Digitally-Filtered Network Noise Power Spectral Density,\n Input-referred ($\sigma$=%0.3f kHz)'%(width*1e-3))
                    u_filt.name('${S(\\nu)}/{k_{B}T}$')
                    fl.plot(u_filt['ch',0],alpha=0.8,label='%s'%label,plottype='semilogy')
                    #ylim(None,10**1.75)
                    #axhline(y=k_B*T/1e-12, linestyle=':', alpha=0.5, color='purple') # 1e-12 b/c the axis is given in pW
                    #axvline(14.46, linestyle=':', alpha=0.5, c='k')
            if plot_params:
                fl.next('Network Noise Power Spectral Density (Input-referred) (convolution = %0.1e Hz)'%width)
                s.name('${S(\\nu)}/{k_{B}T}$')
                fl.plot(s['ch',0],**plot_params)
                #axhline(y=k_B*T/1e-12, alpha=0.9, color='purple') # 1e-12 b/c the axis is given in pW
                fl.next('Network Noise Power Spectral Density, Input-referred')
                u.name('${S(\\nu)}/{k_{B}T}$')
                fl.plot(u['ch',0],**plot_params)
                #axhline(y=k_B*T/1e-12, alpha=0.9, color='purple') # 1e-12 b/c the axis is given in pW
                if filtering:
                    fl.next('Digitally-Filtered Network Noise Power Spectral Density, Input-referred')
                    u_filt.name('${S(\\nu)}/{k_{B}T}$')
                    fl.plot(u_filt['ch',0]**plot_params)
                    #axhline(y=k_B*T/1e-12, alpha=0.9, color='purple') # 1e-12 b/c the axis is given in pW
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
        s.name('$S(\\nu)$').set_units('W/Hz')
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

