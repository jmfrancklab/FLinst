"""
Repeated Echo Experiment at Constant Magnetic Field
===================================================

Repeated echo signal according to `indirect_pts` in `active.ini`.
"""

import logging
import os
import time
import pyspecdata as psd
import SpinCore_pp
import h5py
from numpy import r_
from pyspecdata import strm
from pyspecdata.file_saving.hdf_save_dict_to_group import (
    hdf_save_dict_to_group,
)
from SpinCore_pp import get_integer_sampling_intervals, save_data
from SpinCore_pp.ppg import run_spin_echo

from Instruments import instrument_control

my_exp_type = "ODNP_NMR_comp/n_scans"
assert os.path.exists(psd.getDATADIR(exp_type=my_exp_type))

config_dict = SpinCore_pp.configuration("active.ini")

# {{{ importing acquisition parameters
gamma_eff_mhz_g = (
    "gamma_eff_MHz_G"
    if "gamma_eff_MHz_G" in config_dict.keys()
    else "gamma_eff_mhz_g"
)
(
    nPoints,
    config_dict["SW_kHz"],
    config_dict["acq_time_ms"],
) = get_integer_sampling_intervals(
    config_dict["SW_kHz"], config_dict["acq_time_ms"]
)
ph1_cyc = r_[0, 1, 2, 3]
nPhaseSteps = len(ph1_cyc)
config_dict["type"] = "n_scan"
settle_s = config_dict["magnet_settle_long"]
# }}}
# {{{ set magnetic field
B0_G = config_dict["carrierFreq_MHz"] / config_dict["gamma_eff_mhz_g"]
print(
    "I see",
    config_dict["indirect_pts"],
    "indirect points setting.",
)
_ = input("enter to confirm...")
myinput = input(strm("Your field is:", B0_G, "\nDoes this look okay?"))
if myinput.lower().startswith("n"):
    raise ValueError("You said no!!!")
# }}}
# {{{ check total points and duty cycle
total_pts = nPoints * nPhaseSteps
assert total_pts < 2**14, (
    "You are trying to acquire %d points (too many points) -- either"
    " change SW or acq time so nPoints x nPhaseSteps is less than 16384"
    "\nyou could try reducing the acq_time_ms to %f"
    % (total_pts, config_dict["acq_time_ms"] * 16384 / total_pts)
)
if (
    config_dict["acq_time_ms"] * 1e-3 + config_dict["repetition_us"] * 1e-6
    < 0.1
):
    raise RuntimeError("Warning! Your duty cycle is too high!!")
# }}}
# {{{ run n-scan
data = None
with instrument_control() as ic:
    ic.start_log()
    true_B0_G = ic.set_field(B0_G)
    print("field set to", true_B0_G, "G")
    print("waiting", settle_s, "s for the magnet to settle")
    time.sleep(settle_s)
    for idx in range(config_dict["indirect_pts"]):
        true_B0_G = ic.get_field()
        logging.info(f"{idx + 1} of {config_dict['indirect_pts']}")
        logging.info(
            "The ratio of the field I want to the one I get is"
            f" {B0_G / true_B0_G}\n"
            "In other words, the discrepancy is"
            f" {true_B0_G - B0_G} G"
        )
        data = run_spin_echo(
            nScans=config_dict["nScans"],
            indirect_idx=idx,
            indirect_len=config_dict["indirect_pts"],
            ph1_cyc=ph1_cyc,
            adcOffset=config_dict["adc_offset"],
            carrierFreq_MHz=config_dict["carrierFreq_MHz"],
            nPoints=nPoints,
            deblank_us=config_dict["deblank_us"],
            plen=config_dict["beta_90_s_sqrtW"],
            nEchoes=1,
            repetition_us=config_dict["repetition_us"],
            tau_us=config_dict["tau_us"],
            SW_kHz=config_dict["SW_kHz"],
            amplitude=config_dict["amplitude"],
            ret_data=data,
            indirect_fields=("time", "field"),
        )
        if idx == 0:
            x_axis = data.getaxis("indirect")
        x_axis[idx]["field"] = true_B0_G
        x_axis[idx]["time"] = time.time()
    this_log = ic.stop_log()
data.set_prop("acq_params", config_dict.asdict())
# }}}
# {{{ chunk and save data
data.chunk("t", ["ph1", "t2"], [len(ph1_cyc), -1])
data.setaxis("ph1", ph1_cyc / 4)
if config_dict["nScans"] > 1:
    data.setaxis("nScans", r_[0 : config_dict["nScans"]])
data.reorder(["nScans", "ph1", "indirect", "t2"])
data.squeeze()
data.set_units("t2", "s")
data.set_prop("postproc_type", "spincore_generalproc_v1")
data.set_prop("coherence_pathway", {"ph1": +1})
data.set_prop("acq_params", config_dict.asdict())
config_dict = save_data(data, my_exp_type, config_dict, counter_type="n_scan")
filename_out = (
    f"{config_dict['date']}_{config_dict['chemical']}_{config_dict['type']}.h5"
)
target_directory = psd.getDATADIR(exp_type=my_exp_type)
with h5py.File(
    os.path.normpath(os.path.join(target_directory, filename_out)), "a"
) as fp:
    hdf_save_dict_to_group(fp, {"log": this_log.__getstate__()})
config_dict.write()
# }}}
