"""
test save_data with fake power stepping
======================================

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
from Instruments import instrument_control
import os
import time
import h5py
import SpinCore_pp
from SpinCore_pp import save_data


my_exp_type = "ODNP_NMR_comp/test_equipment"
config_dict = SpinCore_pp.configuration("active.ini")
config_dict["type"] = "save_data_test"
# {{{ data properties
nPoints = 2048
nScans = 1
# }}}
# {{{ params for Bridge 12/power
dB_settings = np.unique(np.round(np.linspace(0, 10, 5) / 0.5) * 0.5)
powers = 1e-3 * 10 ** (dB_settings / 10.0)
uw_dip_center_GHz = 9.707295
uw_dip_width_GHz = 0.008
result = input(
    "to keep this example minimal, it doesn't read from the config file!!"
    "\nThe dip frequency is currently set to %0.6f GHz\nIs that correct???"
    % uw_dip_center_GHz
)
if not result.lower().startswith("y"):
    raise ValueError("Incorrect dip frequency")
# }}}
# {{{ delays used in test
short_delay = 0.5
long_delay = 10

ph1_cyc = r_[0, 1, 2, 3]


# }}}
# {{{ function that generates fake data with two indirect dimensions
def run_scans(
    indirect_idx, indirect_len, nScans, indirect_fields=None, ret_data=None
):
    "this is a dummy replacement to run_scans that generates random data"
    data_length = 2 * nPoints * len(ph1_cyc)
    for nScans_idx in range(nScans):
        data_array = np.random.random(2 * data_length).view(
            np.complex128
        )  # enough random numbers for both real and imaginary, then
        #    use view to alternate real,imag
        if ret_data is None:
            times_dtype = np.dtype(
                [
                    (indirect_fields[0], np.double),
                    (indirect_fields[1], np.double),
                ]  # typically, the two columns/fields give start and
                # stop times
            )
            mytimes = np.zeros(indirect_len, dtype=times_dtype)
            direct_time_axis = r_[0:data_length] / 3.9e3
            ret_data = ndshape(
                [indirect_len, nScans, len(ph1_cyc), data_length],
                ["indirect", "nScans", "ph1", "t2"],
            ).alloc(dtype=np.complex128)
            ret_data.setaxis("indirect", mytimes)
            ret_data.setaxis("t2", direct_time_axis).set_units("t2", "s")
            ret_data.setaxis("ph1", ph1_cyc / 4)
            ret_data.setaxis("nScans", r_[0:nScans])
            for ph1_idx in range(len(ph1_cyc)):
                ret_data["indirect", indirect_idx]["nScans", nScans_idx][
                    "ph1", ph1_idx
                ] = data_array
    return ret_data


# }}}
power_settings_dBm = np.zeros_like(dB_settings)
with instrument_control() as ic:
    DNP_data = None
    for j, this_dB in enumerate(dB_settings):
        print("I'm going to pretend to run", this_dB, "dBm")
        if j == 0:
            time.sleep(short_delay)
            ic.start_log()
            time.sleep(short_delay)
        ic.set_power(this_dB)
        for k in range(10):
            time.sleep(short_delay)
            if ic.get_power_setting() >= this_dB:
                break
        time.sleep(long_delay)
        power_settings_dBm[j] = ic.get_power_setting()
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
    DNP_data.name("nodename_test")
    DNP_data.set_prop("power_settings", power_settings_dBm)
    # note that the validity of saving the log data in this way (rather
    # than manually creating the HDF5 node) is already tested as part of
    # the test suite (test_logobj.py)
    DNP_data.set_prop("log", ic.stop_log().__getstate__())
    # TODO ☐: before merging this PR, make sure to run
    #  find . -iname '*.py' -exec grep {} -le 'with h5py'  \;
    #         and fix the code in all the files that it finds to follow the
    #         convention that we use in the previous line.  Also, be sure that
    #         we bump the postproc_type of all affected data.
    # TODO ☐: I think it should be easy (esp. w/ codex help) to make a short
    #         processing PR to add postproc functions for these new postproc
    #         types.  These new postproc types should use the logs to create a
    #         structured array axis coord for the indirect dimension that
    #         includes fields for time (the original axis coord) as well as all
    #         the average of all logged quantities.  The stdev can be attached
    #         as the axis coord error.
    nodename = DNP_data.name()
    this_log = ic.stop_log()

DNP_data.set_prop("power_settings", power_settings_dBm)
DNP_data.set_prop("postproc_type", "spincore_SE_v1")
DNP_data.set_prop("coherence_pathway", {"ph1": 1})
DNP_data.set_prop("acq_params", config_dict.asdict())
config_dict = save_data(
    DNP_data, my_exp_type, config_dict, counter_type="odnp", proc=True
)
# all of the following will be auto-adjusted by save_data
filename = (
    f"{config_dict['date']}_{config_dict['chemical']}_{config_dict['type']}.h5"
)
target_directory = getDATADIR(exp_type=my_exp_type)
with h5py.File(
    os.path.normpath(os.path.join(target_directory, filename)), "a"
) as f:
    hdf_save_dict_to_group(f, {"log": this_log.__getstate__()})
