"""
test of dip locking and logging
===============================

This is roughly derived from the combined_ODNP.py example in SpinCore. Similar in fashion, the script generates a power list, and loops through each power generating fake data using the run_scans function defined below. At each power the "data" records the start and stop times that will correspond to the times and powers inside the log allowing one to average over each power step. 
"""
from numpy import *
from numpy.random import rand
from pyspecdata import *
from pyspecdata.file_saving.hdf_save_dict_to_group import hdf_save_dict_to_group
import SpinCore_pp
from SpinCore_pp.power_helper import Ep_spacing_from_phalf
from Instruments import *
import os,sys,time
import random
import h5py
from datetime import datetime

# {{{create filename and save to config file
config_dict = SpinCore_pp.configuration("active.ini")
date = datetime.now().strftime("%y%m%d")
config_dict["type"] = "test_B12_log"
config_dict["date"] = date
filename = f"{config_dict['date']}_{config_dict['chemical']}_{config_dict['type']}.h5"
target_directory = getDATADIR(exp_type="ODNP_NMR_comp/test_equipment")
# }}}
# {{{set phase cycling
ph1_cyc = r_[0, 1, 2, 3]
ph2_cyc = r_[0]
nPhaseSteps = len(ph1_cyc)*len(ph2_cyc)
#}}}
#{{{ params for Bridge 12/power
dB_settings = Ep_spacing_from_phalf(
        est_phalf = 0.2,
        max_power = config_dict['max_power'],
        p_steps = config_dict['power_steps']+1,
        min_dBm_step = config_dict['min_dBm_step'],
        three_down = True)
powers =1e-3*10**(dB_settings/10.)
nPoints = 2048
short_delay = 0.5
long_delay = 5
#}}}
#{{{ function that generates fake data with two indirect dimensions
def run_scans(nScans, indirect_idx, indirect_len, nEchoes, indirect_fields = None, ret_data=None):
    nPhaseSteps = len(ph1_cyc)*len(ph2_cyc)
    data_length = 2*nPoints*nEchoes*nPhaseSteps
    for nScans_idx in range(nScans):
        raw_data = np.random.random(data_length) + np.random.random(data_length) * 1j
        data_array = []
        data_array[::] = complex128(raw_data[0::2]+1j*raw_data[1::2])
        dataPoints = float(shape(data_array)[0])
        if ret_data is None:
            times_dtype = dtype(
                    [(indirect_fields[0],double),(indirect_fields[1],double)]
            )
            mytimes = zeros(indirect_len,dtype = times_dtype)
            time_axis =  r_[0:dataPoints] / (3.9 * 1e3)
            ret_data = ndshape(
                    [indirect_len,nScans,len(time_axis)],["indirect","nScans","t"]).alloc(dtype=complex128)
            ret_data.setaxis('indirect',mytimes)
            ret_data.setaxis('t',time_axis).set_units('t','s')
            ret_data.setaxis('nScans',r_[0:nScans])
        ret_data['indirect',indirect_idx]['nScans',nScans_idx] = data_array
    return ret_data
#}}}
power_settings_dBm = zeros_like(dB_settings)
with power_control() as p:
    for j,this_dB in enumerate(dB_settings):
        print("I'm going to pretend to run",this_dB,"dBm")
        if j == 0:
            time.sleep(short_delay)
            p.start_log()
        p.set_power(this_dB)
        for k in range(10):
            time.sleep(short_delay)
            if p.get_power_setting() >= this_dB: 
                break
        time.sleep(long_delay)
        power_settings_dBm[j] = p.get_power_setting()
        DNP_ini_time = time.time()
        if j == 0: 
            retval = p.dip_lock(
                config_dict['uw_dip_center_GHz'] - config_dict['uw_dip_width_GHz'] / 2,
                config_dict['uw_dip_center_GHz'] + config_dict['uw_dip_width_GHz'] / 2,
            ) #needed to set powers above 10 dBm - in future we plan on debugging so this is not needed
            DNP_data = run_scans(
                    nScans = config_dict['nScans'],
                    indirect_idx=j,
                    indirect_len=len(powers),
                    nEchoes=config_dict["nEchoes"],
                    indirect_fields=("start_times", "stop_times"),
                    ret_data=None,
                    )
        else:
            run_scans(
                    nScans = config_dict['nScans'],
                    indirect_idx=j,
                    indirect_len=len(powers),
                    nEchoes=config_dict["nEchoes"],
                    indirect_fields=("start_times", "stop_times"),
                    ret_data=DNP_data,
                    )
        DNP_done = time.time()
        if j == 0:
            time_axis_coords = DNP_data.getaxis("indirect")
        time_axis_coords[j]['start_times'] = DNP_ini_time
        time_axis_coords[j]['stop_times'] = DNP_done
    DNP_data.name("nodename_test")
    nodename = DNP_data.name()
    try:
        DNP_data.hdf5_write(filename,directory=target_directory)
    except:
        if os.path.exists("temp.h5"):
            os.remove("temp.h5")
            DNP_data.hdf5_write("temp.h5")
    this_log = p.stop_log()        
with h5py.File(os.path.normpath(os.path.join(target_directory, filename)),"a") as f:
    log_grp = f.create_group("log")
    hdf_save_dict_to_group(log_grp,this_log.__getstate__())

