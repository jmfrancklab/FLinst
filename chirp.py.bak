#f{ Program doc
r'''Use this program to capture a single S11 (reflection) measurement
    Must use the appropriate set up of the power splitter (PS) and
    reference channel (CH1). Set up as follows (also see AAB-2, 7/12/2018
    yellow tab):
    CH1 (AFG) -*ref*-> CH1 (GDS) *Use coax labeled 'REF'
    CH2 (AFG) --> PS (PORT 1) --> PS (S) --> DUT --> PS (2) --> CH2 (GDS)
    Sends out programmed waveform on both channels of the AFG, with
    the option to correct for amplitude variation (due to use of
    the power splitter), so that the reflection is calculated
    correctly (using *proc_chirp.py*)
    There are two options for a programmed waveform:
        (1) A proper chirp from 5 to 25 MHz,
    and (2) A pulse of a specified frequency
    These options are chosen by the :pulse_90: boolean,
    where True is (2) and False is (1).
'''
#}}}
from Instruments import *
from pyspecdata import *
import time
from serial.tools.list_ports import comports
import serial
from scipy import signal

fl = figlist_var()

print "These are the instruments available:"
SerialInstrument(None)
print "done printing available instruments"

with SerialInstrument('GDS-3254') as s:
    print s.respond('*idn?')
    
with SerialInstrument('AFG-2225') as s:
    print s.respond('*idn?')


pulse_90 = True

#{{{ no sys var = default (3 Vpp), 0 = define amplitudes, 1 = choose from amplitudes
default = True
try:
    sys.argv[1]
    default = False 
except:
    sys.argv[0]
if default:
    ref_amp = 3.0
    volt_scale = 200e-3
if not default:
    setup = int(sys.argv[1])
    if setup == 0:
    #{{{ Allows for user defined amplitude/voltage parameters
        print "User defined amplitude"
        print "250 mVpp displays best on 20 mV/div"
        print "750 mVpp displays best on 50 mV/div"
        print "1.5 Vpp displays best on 100 mV/div"
        print "3 Vpp displays best on 200 mV/div"
        print "7.5 Vpp displays best on 500 mV/div"
        print "e.g., input 750 mVpp as 750e-3"
        print "e.g., input 500 mV/div as 500e-3"
        amp_choice = raw_input("Enter amplitude: ")
        amp_choice = float(amp_choice)
        ref_amp = amp_choice
        volt_scale = raw_input("Enter volt/div: ")
        volt_scale = float(volt_scale)
#}}}
    if setup == 1:
#{{{ The following amplitudes maximize display on scope, may facilitate processing
        print "Choose amplitude by entering corresponding number..."
        print "1 = 250 mVpp \n2 = 750 mVpp \n3 = 1.5 Vpp \n4 = 3.0 Vpp \n5 = 7.6 Vpp"
        amp_choice = raw_input("Enter number: ")
        if amp_choice == '1':
            ref_amp = 0.25
            volt_scale = 20e-3
        elif amp_choice == '2':
            ref_amp = 0.75
            volt_scale = 50e-3
        elif amp_choice == '3':
            ref_amp = 1.5 
            volt_scale = 100e-3
        elif amp_choice == '4':
            ref_amp = 3.0 
            volt_scale = 200e-3
        elif amp_choice == '5':
            ref_amp = 7.6 
            volt_scale = 500e-3
        else:
            ref_amp = 3.0
            volt_scale = 200e-3
            print "Did not recognize amplitude choice."
            #}}}
print "Will set amplitude to:",ref_amp,"V"
    #}}}
#{{{ Generating arbitrary waveform
if pulse_90:
    freq = 14.89e6 #[Hz]
    t_90 = 6.15e-6 #[micro sec]
    freq_carrier = freq     #[Hz] rf pulse frequency
    points_total = 4096     #[pts] total points, property of AFG
    rate = freq_carrier*4   #[pts/sec] AFG requires for arb waveform
    time_spacing = 1/rate   #[sec] time between points  
    time_total = time_spacing * points_total #[sec] total time of sequence, allowed by AFG
    points_90 = t_90/time_spacing
    print "LENGTH OF 90 PULSE:",t_90
    points_seq = points_90
    print "LENGTH OF PULSE SEQUENCE:",t_90
    print "POINTS IN 90 PULSE:",points_90
    print "POINTS IN PULSE SEQUENCE:",points_90
    t = r_[0 : int(points_seq)]
    freq_sampling = 0.25
    y = exp(1j*2*pi*t[1 : -1]*freq_sampling)
    y[0] = 0
    y[-1] = 0
#if not pulse_90: # standard chirp
    #t = r_[0:4096]
    #y = imag(exp(1j*2*pi*0.25*(1-0.5/4096.*t)*t))
    #}}}
with AFG() as a:
    a.reset()
    DUT_amp = sqrt(((((ref_amp/2/sqrt(2))**2)/50)/4)*50)*2*sqrt(2)
    for this_ch in range(2):
    #for this_ch in [0]:
        if pulse_90:
            a[this_ch].digital_ndarray(y,rate)
        if not pulse_90:
            a[this_ch].digital_ndarray(y,rate=100e6)
        a[this_ch].output = True
    for this_ch in range(2):
        a[this_ch].burst = True
        #{{{ this uses ref_amp to correct voltage after power splitter 
        if this_ch == 0: 
            a[this_ch].ampl=DUT_amp
        elif this_ch == 1: 
            a[this_ch].ampl=ref_amp
        else:
            print "Channel not recognized"
            #}}}

datalist = []
print "about to load GDS"
#raw_input("Turn on RF amp") 

with GDS_scope() as g:
    #g.timscal(5e-6)  #set to 5 microsec/div
    #for this_ch in range(2):
    #    g[this_ch].voltscal = volt_scale
    print "loaded GDS"
    g.acquire_mode('average',32)
    input("Wait for averaging to relax...")

    for j in range(1,3):
        print "trying to grab data from channel",j
        datalist.append(g.waveform(ch=j))
data = concat(datalist,'ch').reorder('t')
j = 1
try_again = True
while try_again:
    data_name = 'capture%d'%j
    data.name(data_name)
    try:
        data.hdf5_write('200312_chirp_coile_2.h5')
        try_again = False
    except Exception as e:
        print e
        print "name taken, trying again..."
        j += 1
        try_again = True
print "name of data",data.name()
print "units should be",data.get_units('t')
print "shape of data",ndshape(data)
fl.next('Dual-channel data')
fl.plot(data)
fl.show()
#
