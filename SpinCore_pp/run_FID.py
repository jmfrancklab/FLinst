# Just capturing FID, not echo detection
# 4-step phase cycle
from pylab import *
from pyspecdata import *
import os
import sys
import SpinCore_pp
from datetime import datetime
import numpy as np
raise RuntimeError("This pulse program has not been updated.  Before running again, it should be possible to replace a lot of the code below with a call to the function provided by the 'generic' pulse program inside the ppg directory!")
fl = figlist_var()
# {{{importing acquisition parameters
config_dict = SpinCore_pp.configuration("active.ini")
nPoints = int(config_dict["acq_time_ms"] * config_dict["SW_kHz"] + 0.5)
# }}}
# NOTE: Number of segments is nEchoes * nPhaseSteps
# {{{create filename and save to config file
date = datetime.now().strftime("%y%m%d")
config_dict["type"] = "FID"
config_dict["date"] = date
filename = f"{config_dict['date']}_{config_dict['chemical']}_{config_dict['type']}"
# }}}
#{{{ phase cycling
tx_phases = r_[0.0,90.0,180.0,270.0]
phase_cycling = True
if phase_cycling:
    nPhaseSteps = 4
if not phase_cycling:
    nPhaseSteps = 1
#}}}    
#{{{ note on timing
# putting all times in microseconds
# as this is generally what the SpinCore takes
# note that acq_time is always milliseconds
#}}}
#{{{ppg
nPoints = int(config_dict['acq_time_ms']*config_dict['SW_kHz']+0.5)
data_length = 2*nPoints*config_dict['nEchoes']*nPhaseSteps
for x in range(config_dict['nScans']):
    SpinCore_pp.configureTX(config_dict['adcOffset_ms'], config_dict['carrierFreq_MHz'], 
            tx_phases, config_dict['amplitude'], nPoints)
    acq_time = SpinCore_pp.configureRX(config_dict['SW_kHz'], nPoints, 1, config_dict['nEchoes'], 
            nPhaseSteps)
    SpinCore_pp.init_ppg();
    if phase_cycling:
        SpinCore_pp.load([
            ('marker','start',1),
            ('phase_reset',1),
            ('delay_TTL',config_dict['deblank_us']),
            ('pulse_TTL',config_dict['p90_us'],'ph1',r_[0,1,2,3]),
            ('delay',config_dict['deadtime_us']),
            ('acquire',config_dict['acq_time_ms']),
            ('delay',config_dict['repetition_us']),
            ('jumpto','start')
            ])
    if not phase_cycling:
        SpinCore_pp.load([
            ('marker','start',1),
            ('phase_reset',1),
            ('delay_TTL',config_dict['deblank_us']),
            ('pulse_TTL',config_dict['p90_us'],0),
            ('delay',config_dict['deadtime_us']),
            ('acquire',config_dict['acq_time_ms']),
            ('delay',config_dict['repetition_us']),
            ('jumpto','start')
            ])
    SpinCore_pp.stop_ppg();
    SpinCore_pp.runBoard();
    raw_data = SpinCore_pp.getData(data_length, nPoints, config_dict['nEchoes'], nPhaseSteps)
    raw_data.astype(float)
    data_array = []
    data_array[::] = np.complex128(raw_data[0::2]+1j*raw_data[1::2])
    dataPoints = float(np.shape(data_array)[0])
    if x == 0:
        time_axis = np.linspace(0.0,config_dict['nEchoes']*nPhaseSteps*config_dict['acq_time_ms']*1e-3,dataPoints)
        data = ndshape([len(data_array),config_dict['nScans']],['t','nScans']).alloc(dtype=np.complex128)
        data.setaxis('t',time_axis).set_units('t','s')
        data.setaxis('nScans',r_[0:config_dict['nScans']])
        data.name(config_dict['type'])
        data.set_prop('acq_params',config_dict())
    data['nScans',x] = data_array
    SpinCore_pp.stopBoard();
#}}}
#{{{ saving data
save_file = True
while save_file:
    try:
        data.hdf5_write(filename+'.h5',
                directory=getDATADIR(exp_type='ODNP_NMR_comp/FID'))
        print(("Name of saved data",data.name()))
        print(("Units of saved data",data.get_units('t')))
        print(("Shape of saved data",ndshape(data)))
        save_file = False
    except Exception as e:
        print(e)
        print("\nEXCEPTION ERROR.")
        print("FILE MAY ALREADY EXIST IN TARGET DIRECTORY.")
        print("WILL TRY CURRENT DIRECTORY LOCATION...")
        filename = input("ENTER NEW NAME FOR FILE (AT LEAST TWO CHARACTERS):")
        if len(filename) is not 0:
            data.hdf5_write(filename+'.h5')
            print("\n*** FILE SAVED WITH NEW NAME IN CURRENT DIRECTORY ***\n")
            break
        else:
            print("\n*** *** ***")
            print("UNACCEPTABLE NAME. EXITING WITHOUT SAVING DATA.")
            print("*** *** ***\n")
            break
config_dict.write()
#}}}
