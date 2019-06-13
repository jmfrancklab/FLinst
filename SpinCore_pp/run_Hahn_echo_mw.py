from pyspecdata import *
from numpy import *
import os
import sys
import SpinCore_pp

from Instruments import Bridge12
from serial import Serial
import time

fl = figlist_var()
#{{{ Verify arguments compatible with board
def verifyParams():
    if (nPoints > 16*1024 or nPoints < 1):
        print "ERROR: MAXIMUM NUMBER OF POINTS IS 16384."
        print "EXITING."
        quit()
    else:
        print "VERIFIED NUMBER OF POINTS."
    if (nScans < 1):
        print "ERROR: THERE MUST BE AT LEAST 1 SCAN."
        print "EXITING."
        quit()
    else:
        print "VERIFIED NUMBER OF SCANS."
    if (p90 < 0.065):
        print "ERROR: PULSE TIME TOO SMALL."
        print "EXITING."
        quit()
    else:
        print "VERIFIED PULSE TIME."
    if (tau < 0.065):
        print "ERROR: DELAY TIME TOO SMALL."
        print "EXITING."
        quit()
    else:
        print "VERIFIED DELAY TIME."
    return
#}}}

# Parameters for Bridge12
powers = r_[1e-3:4.:20j]
dB_settings = round_(2*log10(powers/1e-3)*10.)/2
dB_settings = unique(dB_settings)
def check_for_3dB_step(x):
    assert len(x.shape) == 1
    if any(diff(x) > 3.0):
        idx = nonzero(diff(x) > 3)[0][0]
        x = insert(x,idx+1,r_[x[idx]:x[idx+1]:3.0][1:])
        x = check_for_3dB_step(x)
        return x
    else:
        return x
ini_len = len(dB_settings)
dB_settings = check_for_3dB_step(dB_settings)
print "adjusted my power list by",len(dB_settings)-len(powers),"to satisfy the 3dB step requirement and the 0.5 dB resolution"
powers = 1e-3*10**(dB_settings/10.)

date = '190609'
output_name = 'echo_DNP'
adcOffset = 42
carrierFreq_MHz = 14.894439
tx_phases = r_[0.0,90.0,180.0,270.0]
amplitude = 1.0
nScans = 4
nEchoes = 1
phase_cycling = True
if phase_cycling:
    nPhaseSteps = 8
if not phase_cycling:
    nPhaseSteps = 1
#{{{ note on timing
# putting all times in microseconds
# as this is generally what the SpinCore takes
# note that acq_time is always milliseconds
#}}}
p90 = 4.1
deadtime = 100.0
repetition = 4e6

SW_kHz = 9.0
nPoints = 128


acq_time = nPoints/SW_kHz # ms
tau_adjust = 0.0
deblank = 1.0
tau = deadtime + acq_time*1e3*0.5 + tau_adjust
pad = 2.0*tau - deadtime - acq_time*1e3 - deblank
print "ACQUISITION TIME:",acq_time,"ms"
print "TAU DELAY:",tau,"us"
print "PAD DELAY:",pad,"us"
data_length = 2*nPoints*nEchoes*nPhaseSteps
print "\n*** *** ***\n"
print "CONFIGURING TRANSMITTER..."
SpinCore_pp.configureTX(adcOffset, carrierFreq_MHz, tx_phases, amplitude, nPoints)
print "\nTRANSMITTER CONFIGURED."
print "***"
print "CONFIGURING RECEIVER..."
acq_time = SpinCore_pp.configureRX(SW_kHz, nPoints, nScans, nEchoes, nPhaseSteps)
# acq_time is in msec!
print "ACQUISITION TIME IS",acq_time,"ms"
verifyParams()
print "\nRECEIVER CONFIGURED."
print "***"
print "\nINITIALIZING PROG BOARD...\n"
SpinCore_pp.init_ppg();
print "PROGRAMMING BOARD..."
print "\nLOADING PULSE PROG...\n"
if phase_cycling:
    SpinCore_pp.load([
        ('marker','start',1),
        ('phase_reset',1),
        ('delay_TTL',deblank),
        ('pulse_TTL',p90,'ph1',r_[0,1,2,3]),
        ('delay',tau),
        ('delay_TTL',deblank),
        ('pulse_TTL',2.0*p90,'ph2',r_[0,2]),
        ('delay',deadtime),
        ('acquire',acq_time),
        ('delay',pad),
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
        ('delay',pad),
        ('delay',repetition),
        ('jumpto','start')
        ])
print "\nSTOPPING PROG BOARD...\n"
SpinCore_pp.stop_ppg();
print "\nRUNNING BOARD...\n"
if phase_cycling:
    for x in xrange(nScans):
        print "SCAN NO. %d"%(x+1)
        SpinCore_pp.runBoard();
if not phase_cycling:
    SpinCore_pp.runBoard();
raw_data = SpinCore_pp.getData(data_length, nPoints, nEchoes, nPhaseSteps, output_name)
raw_data.astype(float)
data = []
# according to JF, this commented out line
# should work same as line below and be more effic
#data = raw_data.view(complex128)
data[::] = complex128(raw_data[0::2]+1j*raw_data[1::2])
print "COMPLEX DATA ARRAY LENGTH:",shape(data)[0]
print "RAW DATA ARRAY LENGTH:",shape(raw_data)[0]
dataPoints = float(shape(data)[0])
time_axis = linspace(0.0,nEchoes*nPhaseSteps*acq_time*1e-3,dataPoints)
data = nddata(array(data),'t')
data.setaxis('t',time_axis).set_units('t','s')
data.name('signal')
# Define nddata to store along the new power dimension
DNP_data = ndshape([len(powers)+1,len(time_axis)],['power','t']).alloc(dtype=complex128)
DNP_data.setaxis('power',r_[0,powers]).set_units('W')
DNP_data.setaxis('t',time_axis).set_units('t','s')
DNP_data['power',0] = data
raw_input("CONNECT AND TURN ON BRIDGE12...")

with Bridge12() as b:
    # Begin actual Bridge12 amplifier set up
    b.lock_on_dip(ini_range=(9.81e9,9.83e9))
    for j in xrange(3):
        b.zoom(dBm_increment=3)
    zoom_return = b.zoom(dBm_increment=2) #Ends at 24 dBm
    dip_f = zoom_return[2] # frequency of MW radiation needed
    b.set_freq(dip_f)
    rx_array = empty_like(dB_settings)
    tx_array = empty_like(dB_settings) #inserted tx here
    for j,this_power in enumerate(dB_settings):
        print "\n*** *** *** *** ***\n"
        print "SETTING THIS POWER",this_power,"(",powers[j],"W)"
        b.set_power(this_power)
        if this_power >= 32.0:
            raw_input("ADJUST IRIS TO MINIMIZE RX...")
            print "ADJUSTMENT ACCEPTED."
        rx_array[j] = b.rxpowermv_float()
        tx_array[j] = b.txpowermv_float() #inserted tx here
        print "\n*** *** *** *** ***\n"
        print "\n*** *** ***\n"
        print "CONFIGURING TRANSMITTER..."
        SpinCore_pp.configureTX(adcOffset, carrierFreq_MHz, tx_phases, amplitude, nPoints)
        print "\nTRANSMITTER CONFIGURED."
        print "***"
        print "CONFIGURING RECEIVER..."
        acq_time = SpinCore_pp.configureRX(SW_kHz, nPoints, nScans, nEchoes, nPhaseSteps) #ms
        # acq_time is in msec!
        print "\nRECEIVER CONFIGURED."
        print "***"
        # MORE CODE GOES HERE
        print "\nINITIALIZING PROG BOARD...\n"
        SpinCore_pp.init_ppg();
        print "\nLOADING PULSE PROG...\n"
        if phase_cycling:
            SpinCore_pp.load([
                ('marker','start',1),
                ('phase_reset',1),
                ('delay_TTL',deblank),
                ('pulse_TTL',p90,'ph1',r_[0,1,2,3]),
                ('delay',tau),
                ('delay_TTL',deblank),
                ('pulse_TTL',2.0*p90,'ph2',r_[0,2]),
                ('delay',deadtime),
                ('acquire',acq_time),
                ('delay',pad),
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
                ('delay',pad),
                ('delay',repetition),
                ('jumpto','start')
                ])
        print "\nSTOPPING PROG BOARD...\n"
        SpinCore_pp.stop_ppg();
        print "\nRUNNING BOARD...\n"
        if phase_cycling:
            for x in xrange(nScans):
                print "SCAN NO. %d"%(x+1)
                SpinCore_pp.runBoard();
        if not phase_cycling:
            SpinCore_pp.runBoard(); 
        raw_data = SpinCore_pp.getData(data_length, nPoints, nEchoes, nPhaseSteps, output_name)
        raw_data.astype(float)
        data = []
        data[::] = complex128(raw_data[0::2]+1j*raw_data[1::2])
        print "COMPLEX DATA ARRAY LENGTH:",shape(data)[0]
        print "RAW DATA ARRAY LENGTH:",shape(raw_data)[0]
        dataPoints = float(shape(data)[0])
        time_axis = linspace(0.0,nEchoes*nPhaseSteps*acq_time*1e-3,dataPoints)
        data = nddata(array(data),'t')
        data.setaxis('t',time_axis).set_units('t','s')
        data.name('signal')
        DNP_data['power',j+1] = data
DNP_data.set_prop('rx_array',rx_array)
DNP_data.set_prop('tx_array',tx_array) #added ", 'tx_array', tx_array" here
SpinCore_pp.stopBoard();
print "EXITING..."
print "\n*** *** ***\n"
save_file = True
while save_file:
    try:
        print "SAVING FILE..."
        DNP_data.hdf5_write(date+'_'+output_name+'.h5')
        print "Name of saved data",DNP_data.name()
        print "Units of saved data",DNP_data.get_units('t')
        print "Shape of saved data",ndshape(DNP_data)
        save_file = False
    except Exception as e:
        print e
        print "FILE ALREADY EXISTS."
        save_file = False
fl.next('abs raw data')
fl.image(abs(DNP_data),':',alpha=0.8)
data.ft('t',shift=True)
fl.next('abs FT raw data')
fl.image(abs(DNP_data),':',alpha=0.8)
fl.show()

