"""
Z0 shim sweep
=============

Acquire a series of spin echoes while stepping the Z0 shim voltage.
The saved dataset can then be processed to determine the best Z0 shim.
"""

import os
import time

import numpy as np
import pyspecdata as psd
import SpinCore_pp
from numpy import r_
from SpinCore_pp import get_integer_sampling_intervals, save_data
from SpinCore_pp.ppg import run_spin_echo

from Instruments import power_control

# {{{ before wasting time running the experiment, make sure the output
#     directory exists
my_exp_type = "ODNP_NMR_comp/Echoes"
assert os.path.exists(psd.getDATADIR(exp_type=my_exp_type))
# }}}

config_dict = SpinCore_pp.configuration("active.ini")

# {{{ user settings
settle_s = config_dict["magnet_settle_medium"]
stepsize = 0.005
max_V = 1 / 3.69
# }}}

# {{{ pull acq settings, and check for consistency
(
    nPoints,
    config_dict["SW_kHz"],
    config_dict["acq_time_ms"],
) = get_integer_sampling_intervals(
    config_dict["SW_kHz"], config_dict["acq_time_ms"]
)
ph1_cyc = r_[0, 1, 2, 3]
nPhaseSteps = len(ph1_cyc)
total_pts = nPoints * nPhaseSteps
assert total_pts < 2**14, (
    "You are trying to acquire %d points (too many points) -- either"
    " change SW or acq time so nPoints x nPhaseSteps is less than 16384"
    "\nyou could try reducing the acq_time_ms to %f"
    % (total_pts, config_dict["acq_time_ms"] * 16384 / total_pts)
)
# }}}

# {{{ add file saving parameters to config dict
config_dict["type"] = "shim_z0"  # save_data.py expects type in config_dict
# }}}

data = None
with power_control() as p:
    orig_voltage_V = p.get_shim()["Z0"][0]
    requested_z0_voltage_list = orig_voltage_V + np.arange(0, max_V, stepsize)
    z0_voltage_list = p.round_shim_voltage("Z0", requested_z0_voltage_list)
    print("current Z0 voltage:", orig_voltage_V)
    print("requested Z0 voltages:", requested_z0_voltage_list)
    print("allowed Z0 voltages:", z0_voltage_list)
    for idx, requested_voltage in enumerate(z0_voltage_list):
        p.shim["Z0"] = requested_voltage
        applied_voltage = p.shim["Z0"]
        print(
            "set Z0 shim to",
            applied_voltage,
            "V and waiting",
            settle_s,
            "s",
        )
        time.sleep(settle_s)
        data = run_spin_echo(
            deadtime_us=config_dict["deadtime_us"],
            deblank_us=config_dict["deblank_us"],
            nScans=config_dict["nScans"],
            indirect_idx=idx,
            indirect_len=len(z0_voltage_list),
            ph1_cyc=ph1_cyc,
            amplitude=config_dict["amplitude"],
            adcOffset=config_dict["adc_offset"],
            carrierFreq_MHz=config_dict["carrierFreq_MHz"],
            nPoints=nPoints,
            nEchoes=config_dict["nEchoes"],
            plen=config_dict["beta_90_s_sqrtW"],
            repetition_us=config_dict["repetition_us"],
            tau_us=config_dict["tau_us"],
            SW_kHz=config_dict["SW_kHz"],
            ret_data=data,
        )
    # set back to the original voltage at the end
    p.shim["Z0"] = orig_voltage_V
    print("restored Z0 shim to", orig_voltage_V, "V")

data.rename("indirect", "z0_voltage")
data.set_axis("z0_voltage", z0_voltage_list).set_units("z0_voltage", "V")

# {{{ chunk and save data
data.chunk("t", ["ph1", "t2"], [len(ph1_cyc), -1])
data.setaxis("ph1", ph1_cyc / 4)
if config_dict["nScans"] > 1:
    data.setaxis("nScans", r_[0 : config_dict["nScans"]])
data.reorder(["nScans", "ph1", "z0_voltage", "t2"])
data.set_units("t2", "s")
data.set_prop("postproc_type", "spincore_generalproc_v1")
data.set_prop("coherence_pathway", {"ph1": +1})
data.set_prop("acq_params", config_dict.asdict())
config_dict = save_data(data, my_exp_type, config_dict, "shim_z0")
config_dict.write()
# }}}
