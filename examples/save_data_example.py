"""
test of dip locking and logging
===============================

This is roughly derived from the combined_ODNP.py example in SpinCore.
Similar in fashion, the script generates a power list, and loops through
each power generating fake data using the run_scans function defined
below. At each power the "data" records the start and stop times that
will correspond to the times and powers inside the log allowing one to
average over each power step in a later post processing step. 
"""
from numpy import r_
import numpy as np
from pyspecdata import ndshape, getDATADIR
from pyspecdata.file_saving.hdf_save_dict_to_group import (
    hdf_save_dict_to_group,
)
from Instruments import power_control
import os, time, h5py
from datetime import datetime

filename = datetime.now().strftime("%y%m%d") + "_" + "test_B12_log.h5"
target_directory = getDATADIR(exp_type="ODNP_NMR_comp/test_equipment")
# {{{ data properties
nPoints = 2048
nScans = 1
# }}}
# {{{ params for Bridge 12/power
dB_settings = np.unique(np.round(np.linspace(0, 35, 5) / 0.5) * 0.5)
powers = 1e-3 * 10 ** (dB_settings / 10.0)
uw_dip_center_GHz = 9.818061
uw_dip_width_GHz = 0.008
result = input(
    "to keep this example minimal, it doesn't read from the config file!!\nThe dip frequency is currently set to %0.6f GHz\nIs that correct???"
    % uw_dip_center_GHz
)
if not result.lower().startswith("y"):
    raise ValueError("Incorrect dip frequency")
# }}}
# {{{ delays used in test
short_delay = 0.5
long_delay = 10  # this is the delay where it holds the same power


# }}}
# {{{ function that generates fake data with two indirect dimensions
def run_scans(indirect_idx, indirect_len, nScans, indirect_fields=None, ret_data=None):
    "this is a dummy replacement to run_scans that generates random data"
    data_length = 2 * nPoints
    for nScans_idx in range(nScans):
        data_array = np.random.random(2 * data_length).view(
            np.complex128
        )  # enough random numbers for both real and imaginary, then use view to alternate real,imag
        if ret_data is None:
            times_dtype = np.dtype(
                [
                    (indirect_fields[0], np.double),
                    (indirect_fields[1], np.double),
                ]  # typically, the two columns/fields give start and stop times
            )
            mytimes = np.zeros(indirect_len, dtype=times_dtype)
            direct_time_axis = r_[0 : np.shape(data_array)[0]] / (
                3.9e3
            )  # fake it like this is 3.9 kHz SW data
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
with power_control() as p:
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
        if j == 0:
            retval = p.dip_lock(
                uw_dip_center_GHz - uw_dip_width_GHz / 2,
                uw_dip_center_GHz + uw_dip_width_GHz / 2,
            )  # test the dip lock!
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
    DNP_data.name("nodename_test")
    DNP_data.set_prop("power_settings", power_settings_dBm)
    nodename = DNP_data.name()
    try:
        DNP_data.hdf5_write(filename, directory=target_directory)
    except:
        print(
            "***Warning*** Writing to",
            filename,
            " failed, so saving to temp.h5",
        )
        if os.path.exists("temp.h5"):
            os.remove("temp.h5")
            DNP_data.hdf5_write("temp.h5")
    this_log = p.stop_log()
with h5py.File(os.path.normpath(os.path.join(target_directory, filename)), "a") as f:
    log_grp = f.create_group("log")
    hdf_save_dict_to_group(log_grp, this_log.__getstate__())
