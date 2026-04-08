"""
test save_data with fake power stepping
======================================

This keeps the original fake-data profile: step through a list of powers,
generate dummy data with indirect start/stop timestamps, and retain the
instrument-control logging block. The final dataset is saved using
``SpinCore_pp.save_data`` so the script can be used to test updates to
``save_data.py``.
"""

from numpy import r_
import numpy as np
from pyspecdata import ndshape, getDATADIR
from pyspecdata.file_saving.hdf_save_dict_to_group import (
    hdf_save_dict_to_group,
)
from Instruments import instrument_control
import os
import time
import h5py
from datetime import datetime
import SpinCore_pp
from SpinCore_pp import save_data

my_exp_type = "ODNP_NMR_comp/test_equipment"
config_dict = SpinCore_pp.configuration("active.ini")
config_dict["date"] = datetime.now().strftime("%y%m%d")
config_dict["type"] = "save_data_test"

# {{{ data properties
nPoints = 2048
nScans = 1
# }}}
# {{{ params for Bridge 12/power
dB_settings = np.unique(np.round(np.linspace(0, 10, 5) / 0.5) * 0.5)
powers = 1e-3 * 10 ** (dB_settings / 10.0)
# }}}
# {{{ delays used in test
short_delay = 0.5
long_delay = 10


# }}}
# {{{ function that generates fake data with two indirect dimensions
def run_scans(
    indirect_idx, indirect_len, nScans, indirect_fields=None, ret_data=None
):
    "this is a dummy replacement to run_scans that generates random data"
    data_length = 2 * nPoints
    for nScans_idx in range(nScans):
        data_array = np.random.random(2 * data_length).view(np.complex128)
        if ret_data is None:
            times_dtype = np.dtype(
                [
                    (indirect_fields[0], np.double),
                    (indirect_fields[1], np.double),
                ]
            )
            mytimes = np.zeros(indirect_len, dtype=times_dtype)
            direct_time_axis = r_[0 : np.shape(data_array)[0]] / 3.9e3
            ret_data = ndshape(
                [indirect_len, nScans, len(direct_time_axis)],
                ["indirect", "nScans", "t"],
            ).alloc(dtype=np.complex128)
            ret_data.setaxis("indirect", mytimes)
            ret_data.setaxis("t", direct_time_axis).set_units("t", "s")
            ret_data.setaxis("nScans", r_[0:nScans])
        ret_data["indirect", indirect_idx]["nScans", nScans_idx] = data_array
    return ret_data


# }}}
power_settings_dBm = np.zeros_like(dB_settings)
with instrument_control() as p:
    DNP_data = None
    for j, this_dB in enumerate(dB_settings):
        print("I'm going to pretend to run", this_dB, "dBm")
        if j == 0:
            time.sleep(short_delay)
            p.start_log()
            time.sleep(short_delay)
        p.set_power(this_dB)
        for k in range(10):
            time.sleep(short_delay)
            if p.get_power_setting() >= this_dB:
                break
        time.sleep(long_delay)
        power_settings_dBm[j] = p.get_power_setting()
        DNP_ini_time = time.time()
        DNP_data = run_scans(
            indirect_idx=j,
            indirect_len=len(powers),
            nScans=nScans,
            indirect_fields=("start_times", "stop_times"),
            ret_data=DNP_data,
        )
        DNP_done = time.time()
        if j == 0:
            time_axis_coords = DNP_data.getaxis("indirect")
        time_axis_coords[j]["start_times"] = DNP_ini_time
        time_axis_coords[j]["stop_times"] = DNP_done
    this_log = p.stop_log()

DNP_data.set_prop("power_settings", power_settings_dBm)
DNP_data.set_prop("postproc_type", "synthetic_test")
DNP_data.set_prop("acq_params", config_dict.asdict())
config_dict = save_data(
    DNP_data, my_exp_type, config_dict, counter_type="odnp", proc=False
)

filename = (
    f"{config_dict['date']}_{config_dict['chemical']}_{config_dict['type']}.h5"
)
target_directory = getDATADIR(exp_type=my_exp_type)
with h5py.File(
    os.path.normpath(os.path.join(target_directory, filename)), "a"
) as f:
    log_grp = f.require_group("log")
    hdf_save_dict_to_group(log_grp, this_log.__getstate__())
