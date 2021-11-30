from pyspecdata import *
from numpy import *
import os
import sys
import SpinCore_pp
from Instruments import Bridge12,prologix_connection,gigatronics
from serial import Serial
import time
from datetime import datetime
from SpinCore_pp.verifyParams import verifyParams
from SpinCore_pp.power_helper import gen_powerlist

fl = figlist_var()

# {{{ experimental parameters
# Parameters for Bridge12
max_power = 4 #W
power_steps = 18
dB_settings = gen_powerlist(max_power,power_steps)
append_dB = [dB_settings[abs(10**(dB_settings/10.-3)-max_power*frac).argmin()]
        for frac in [0.75,0.5,0.25]]
dB_settings = append(dB_settings,append_dB)
print("dB_settings",dB_settings)
print("correspond to powers in Watts",10**(dB_settings/10.-3))
input("Look ok?")
powers = 1e-3*10**(dB_settings/10.)

date = datetime.now().strftime('%y%m%d')
output_name = 'TEMPOL_289uM_heat_exch_0C'
node_name = 'enhancement'
adcOffset = 28
carrierFreq_MHz = 14.549013
tx_phases = r_[0.0,90.0,180.0,270.0]
amplitude = 1.0
nScans = 1
nEchoes = 1
phase_cycling = True
if phase_cycling:
    nPhaseSteps = 4
if not phase_cycling:
    nPhaseSteps = 1

#{{{ note on timing
# putting all times in microseconds
# as this is generally what the SpinCore takes
# note that acq_time is always milliseconds
#}}}
p90 = 1.781
deadtime = 10.0
repetition = 10e6

SW_kHz = 10
acq_ms = 200.
nPoints = int(acq_ms*SW_kHz+0.5)
tau_adjust = 0
deblank = 1.0
#tau = deadtime + acq_time*1e3*(1./8.) + tau_adjust
tau = 3500
pad = 0
total_pts = nPoints*nPhaseSteps
assert total_pts < 2**14, "You are trying to acquire %d points (too many points) -- either change SW or acq time so nPoints x nPhaseSteps is less than 16384"%total_pts
#{{{ setting acq_params dictionary
acq_params = {}
acq_params['adcOffset'] = adcOffset
acq_params['carrierFreq_MHz'] = carrierFreq_MHz
acq_params['amplitude'] = amplitude
acq_params['nScans'] = nScans
acq_params['nEchoes'] = nEchoes
acq_params['p90_us'] = p90
acq_params['deadtime_us'] = deadtime
acq_params['repetition_us'] = repetition
acq_params['SW_kHz'] = SW_kHz
acq_params['nPoints'] = nPoints
acq_params['tau_adjust_us'] = tau_adjust
acq_params['deblank_us'] = deblank
acq_params['tau_us'] = tau
#acq_params['pad_us'] = pad 
if phase_cycling:
    acq_params['nPhaseSteps'] = nPhaseSteps
#}}}
# }}}
print("ACQUISITION TIME:",acq_time,"ms")
print("TAU DELAY:",tau,"us")
#print "PAD DELAY:",pad,"us"
data_length = 2*nPoints*nEchoes*nPhaseSteps
for x in range(nScans):
    print(("*** *** *** SCAN NO. %d *** *** ***"%(x+1)))
    print("\n*** *** ***\n")
    print("CONFIGURING TRANSMITTER...")
    SpinCore_pp.configureTX(adcOffset, carrierFreq_MHz, tx_phases, amplitude, nPoints)
    print("\nTRANSMITTER CONFIGURED.")
    print("***")
    print("CONFIGURING RECEIVER...")
    acq_time = SpinCore_pp.configureRX(SW_kHz, nPoints, nScans, nEchoes, nPhaseSteps)
    acq_params['acq_time_ms'] = acq_time
    print("ACQUISITION TIME IS",acq_time,"ms")
    verifyParams(nPoints=nPoints, nScans=nScans, p90_us=p90, tau_us=tau)
    print("\nRECEIVER CONFIGURED.")
    print("***")
    print("\nINITIALIZING PROG BOARD...\n")
    SpinCore_pp.init_ppg()
    print("PROGRAMMING BOARD...")
    print("\nLOADING PULSE PROG...\n")
    if phase_cycling:
        SpinCore_pp.load([
            ('marker','start',1),
            ('phase_reset',1),
            ('delay_TTL',deblank),
            ('pulse_TTL',p90,'ph1',r_[0,1,2,3]),
            ('delay',tau),
            ('delay_TTL',deblank),
            ('pulse_TTL',2.0*p90,0),
            ('delay',deadtime),
            ('acquire',acq_time),
            #('delay',pad),
            ('delay',repetition),
            ('jumpto','start')
            ])
    if not phase_cycling:
        SpinCore_pp.load([
            ('marker','start',nScans),
            ('phase_reset',1),
            ('delay_TTL',deblank),
            ('pulse_TTL',p90,0.0),
            ('delay',tau),
            ('delay_TTL',deblank),
            ('pulse_TTL',2.0*p90,0.0),
            ('delay',deadtime),
            ('acquire',acq_time),
            #('delay',pad),
            ('delay',repetition),
            ('jumpto','start')
            ])
    print("\nSTOPPING PROG BOARD...\n")
    SpinCore_pp.stop_ppg();
    print("\nRUNNING BOARD...\n")
    SpinCore_pp.runBoard();
    raw_data = SpinCore_pp.getData(data_length, nPoints, nEchoes, nPhaseSteps, output_name)
    raw_data.astype(float)
    data_array = []
    data_array[::] = complex128(raw_data[0::2]+1j*raw_data[1::2])
    print("COMPLEX DATA ARRAY LENGTH:",shape(data_array)[0])
    print("RAW DATA ARRAY LENGTH:",shape(raw_data)[0])
    dataPoints = float(shape(data_array)[0])
    if x == 0:
        time_axis = linspace(0.0,nEchoes*nPhaseSteps*acq_time*1e-3,dataPoints)
        DNP_data = ndshape([len(powers)+1,nScans,len(time_axis)],['power','nScans','t']).alloc(dtype=complex128)
        DNP_data.setaxis('power',r_[0,powers]).set_units('W')
        DNP_data.setaxis('t',time_axis).set_units('t','s')
        DNP_data.setaxis('nScans',r_[0:nScans])
    data_array = nddata(array(data_array),'t')
    data_array.setaxis('t',time_axis)
    # Define nddata to store along the new power dimension
    DNP_data['power',0]['nScans',x] = data_array

with Bridge12() as b:
    b.set_wg(True)
    b.set_rf(True)
    b.set_amp(True)
    this_return = b.lock_on_dip(ini_range=(9.579e9,9.595e9))
    dip_f = this_return[2]
    print("Frequency",dip_f)
    b.set_freq(dip_f)
    meter_powers = zeros_like(dB_settings)
    for j,this_power in enumerate(dB_settings):
        print("\n*** *** *** *** ***\n")
        print("SETTING THIS POWER",this_power,"(",dB_settings[j-1],powers[j],"W)")
        if j>0 and this_power > last_power + 3:
            last_power += 3
            print("SETTING TO...",last_power)
            b.set_power(last_power)
            time.sleep(3.0)
            while this_power > last_power+3:
                last_power += 3
                print("SETTING TO...",last_power)
                b.set_power(last_power)
                time.sleep(3.0)
            print("FINALLY - SETTING TO DESIRED POWER")
            b.set_power(this_power)
        elif j == 0:
            threshold_power = 10
            if this_power > threshold_power:
                next_power = threshold_power + 3
                while next_power < this_power:
                    print("SETTING To...",next_power)
                    b.set_power(next_power)
                    time.sleep(3.0)
                    next_power += 3
            b.set_power(this_power)
        else:
            b.set_power(this_power)
        time.sleep(15)
        with prologix_connection() as p:
            with gigatronics(prologix_instance=p, address=7) as g:
                meter_powers[j] = g.read_power()
                print("POWER READING",meter_powers[j])
                print("\n*** *** *** *** ***\n")
                print("\n*** *** ***\n")
        for x in range(nScans):
            print(("*** *** *** SCAN NO. %d *** *** ***"%(x+1)))
            print("\n*** *** ***\n")
            print("CONFIGURING TRANSMITTER...")
            SpinCore_pp.configureTX(adcOffset, carrierFreq_MHz, tx_phases, amplitude, nPoints)
            print("\nTRANSMITTER CONFIGURED.")
            print("***")
            print("CONFIGURING RECEIVER...")
            acq_time = SpinCore_pp.configureRX(SW_kHz, nPoints, nScans, nEchoes, nPhaseSteps) #ms
            print("\nRECEIVER CONFIGURED.")
            print("***")
            print("\nINITIALIZING PROG BOARD...\n")
            SpinCore_pp.init_ppg();
            print("\nLOADING PULSE PROG...\n")
            if phase_cycling:
                SpinCore_pp.load([
                    ('marker','start',1),
                    ('phase_reset',1),
                    ('delay_TTL',deblank),
                    ('pulse_TTL',p90,'ph1',r_[0,1,2,3]),
                    ('delay',tau),
                    ('delay_TTL',deblank),
                    ('pulse_TTL',2.0*p90,0),
                    ('delay',deadtime),
                    ('acquire',acq_time),
                    #('delay',pad),
                    ('delay',repetition),
                    ('jumpto','start')
                    ])
                #{{{
            if not phase_cycling:
                SpinCore_pp.load([
                    ('marker','start',nScans),
                    ('phase_reset',1),
                    ('delay_TTL',deblank),
                    ('pulse_TTL',p90,0.0),
                    ('delay',tau),
                    ('delay_TTL',deblank),
                    ('pulse_TTL',2.0*p90,0.0),
                    ('delay',deadtime),
                    ('acquire',acq_time),
                    #('delay',pad),
                    ('delay',repetition),
                    ('jumpto','start')
                    ])
                #}}}
            print("\nSTOPPING PROG BOARD...\n")
            SpinCore_pp.stop_ppg();
            print("\nRUNNING BOARD...\n")
            SpinCore_pp.runBoard();
            raw_data = SpinCore_pp.getData(data_length, nPoints, nEchoes, nPhaseSteps, output_name)
            raw_data.astype(float)
            data_array = []
            data_array[::] = complex128(raw_data[0::2]+1j*raw_data[1::2])
            print("COMPLEX DATA ARRAY LENGTH:",shape(data_array)[0])
            print("RAW DATA ARRAY LENGTH:",shape(raw_data)[0])
            dataPoints = float(shape(data_array)[0])
            time_axis = linspace(0.0,nEchoes*nPhaseSteps*acq_time*1e-3,dataPoints)
            data_array = nddata(array(data_array),'t')
            data_array.setaxis('t',time_axis).set_units('t','s')
            data_array.name('signal')
            DNP_data['power',j+1]['nScans',x] = data_array
        last_power = this_power
DNP_data.name(node_name)
DNP_data.set_prop('meter_powers',meter_powers)
SpinCore_pp.stopBoard();
print("EXITING...")
print("\n*** *** ***\n")
save_file = True
while save_file:
    try:
        print("SAVING FILE...")
        DNP_data.set_prop('acq_params',acq_params)
        DNP_data.name(node_name)
        DNP_data.hdf5_write(date+'_'+output_name+'.h5',
                directory=getDATADIR(exp_type='ODNP_NMR_comp/ODNP'))
        print("*** *** *** *** *** *** *** *** *** *** ***")
        print("\n*** FILE SAVED IN TARGET DIRECTORY ***\n")
        print("*** *** *** *** *** *** *** *** *** *** ***")
        print("Name of saved data_array",DNP_data.name())
        print("Units of saved data_array",DNP_data.get_units('t'))
        print("Shape of saved data_array",ndshape(DNP_data))
        save_file = False
    except Exception as e:
        print("\nEXCEPTION ERROR.")
        print("FILE MAY ALREADY EXIST IN TARGET DIRECTORY.")
        print("WILL TRY CURRENT DIRECTORY LOCATION...")
        output_name = input("ENTER NEW NAME FOR FILE (AT LEAST TWO CHARACTERS):")
        if len(output_name) is not 0:
            DNP_data.hdf5_write(date+'_'+output_name+'.h5')
            print("\n*** FILE SAVED WITH NEW NAME IN CURRENT DIRECTORY ***\n")
            break
        else:
            print("\n*** *** ***")
            print("UNACCEPTABLE NAME. EXITING WITHOUT SAVING DATA.")
            print("*** *** ***\n")
            break
        save_file = False
fl.next('raw data_array')
fl.image(DNP_data.C.setaxis('power',
    '#').set_units('power','scan #'))
fl.next('abs raw data_array')
fl.image(abs(DNP_data).C.setaxis('power',
    '#').set_units('power','scan #'))
data_array.ft('t',shift=True)
fl.next('raw data_array - ft')
fl.image(DNP_data.C.setaxis('power','#'))
fl.next('abs raw data_array - ft')
fl.image(abs(DNP_data.C.setaxis('power','#')))
fl.show();quit()
