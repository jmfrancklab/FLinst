"""
One Pulse Experiment
====================

Not an echo detection but rather just capturing
the FID with a 4-step phase cycle. 
"""

from pyspecdata import getDATADIR
from numpy import r_, linspace
import sys
import os
import SpinCore_pp
import SpinCore_pp as spc
from SpinCore_pp.ppg import generic
from datetime import datetime

my_exp_type = "ODNP_NMR_comp/nutation"
assert os.path.exists(getDATADIR(exp_type=my_exp_type))
beta_range_s_sqrtW = linspace(0.1e-6, 150e-6, 20)
# {{{importing acquisition parameters
config_dict = SpinCore_pp.configuration("active.ini")
(
    nPoints,
    config_dict["SW_kHz"],
    config_dict["acq_time_ms"],
) = spc.get_integer_sampling_intervals(
    SW_kHz=config_dict["SW_kHz"],
    time_per_segment_ms=config_dict["acq_time_ms"],
)
# }}}
# {{{add file saving parameters to config dict
config_dict["type"] = "FID_nutation"
config_dict["date"] = datetime.now().strftime("%y%m%d")
config_dict["FID_nutation_counter"] += 1
# }}}
# {{{ command-line option to leave the field untouched (if you set it once, why set it again)
if len(sys.argv) == 2 and sys.argv[1] == "stayput":
    pass
else:
    spc.set_field(config_dict)
# }}}
# {{{set phase cycling
ph1_cyc = r_[0, 1, 2, 3]
nPhaseSteps = 4
# }}}
prog_p90_us = spc.prog_plen(beta_range_s_sqrtW, config_dict["amplitude"])
# {{{check total points
total_pts = nPoints * nPhaseSteps
assert total_pts < 2**14, (
    "You are trying to acquire %d points (too many points) -- either change SW or acq time so nPoints x nPhaseSteps is less than 16384"
    % total_pts
)
# }}}
# {{{ acquire FID nutation
data = None
for idx, p90_us in enumerate(prog_p90_us):
    data = generic(
        ppg_list=[
            ("phase_reset", 1),
            ("delay_TTL", config_dict["deblank_us"]),
            ("pulse_TTL", p90_us, "ph1", ph1_cyc),
            ("delay", config_dict["deadtime_us"]),
            ("acquire", config_dict["acq_time_ms"]),
            ("delay", config_dict["repetition_us"]),
        ],
        nScans=config_dict["nScans"],
        indirect_idx=idx,
        indirect_len=len(beta_range_s_sqrtW),
        adcOffset=config_dict["adc_offset"],
        carrierFreq_MHz=config_dict["carrierFreq_MHz"],
        nPoints=nPoints,
        time_per_segment_ms=config_dict["acq_time_ms"],
        SW_kHz=config_dict["SW_kHz"],
        amplitude=config_dict["amplitude"],
        ret_data=data,
    )
# }}}
data.rename("indirect", "beta")
data.setaxis("beta", desired_beta_range).set_units("beta", "s√W")
data.set_prop("prog_p90s", prog_p90_us)
# {{{ chunk and save data
data.chunk("t", ["ph1", "t2"], [len(ph1_cyc), -1])
data.setaxis("ph1", ph1_cyc / 4)
if config_dict["nScans"] > 1:
    data.setaxis("nScans", r_[0 : config_dict["nScans"]])
data.reorder(["nScans", "ph1", "beta", "t2"])
data.set_units("t2", "s")
data.set_prop("postproc_type", "spincore_FID_nutation_v1")
data.set_prop("coherence_pathway", {"ph1": -1})
data.set_prop("acq_params", config_dict.asdict())
config_dict = spc.save_data(data, my_exp_type, config_dict, "FID_nutation")
config_dict.write()
# }}}
