"""
One Pulse Experiment
====================

Not an echo detection but rather just capturing
the FID with a 4-step phase cycle. 
"""

from pyspecdata import *
from numpy import *
import SpinCore_pp
from SpinCore_pp import prog_plen, get_integer_sampling_intervals, save_data
from SpinCore_pp.ppg import generic
from datetime import datetime
from Instruments.XEPR_eth import xepr

my_exp_type = "ODNP_NMR_comp/FID"
assert os.path.exists(psd.getDATADIR(exp_type=my_exp_type))
# {{{importing acquisition parameters
config_dict = SpinCore_pp.configuration("active.ini")
(
    nPoints,
    config_dict["SW_kHz"],
    config_dict["acq_time_ms"],
) = get_integer_sampling_intervals(
    SW_kHz=config_dict["SW_kHz"],
    time_per_segment_ms=config_dict["acq_time_ms"],
)
# }}}
# {{{add file saving parameters to config dict
config_dict["type"] = "FID"
config_dict["date"] = datetime.now().strftime("%y%m%d")
config_dict["echo_counter"] += 1
# }}}
# {{{ command-line option to leave the field untouched (if you set it once, why set it again)
adjust_field = True
if len(sys.argv) == 2 and sys.argv[1] == "stayput":
    adjust_field = False
# }}}
input(
    "I'm assuming that you've tuned your probe to %f since that's what's in your .ini file. Hit enter if this is true"
    % config_dict["carrierFreq_MHz"]
)
# {{{ let computer set field
if adjust_field:
    field_G = config_dict["carrierFreq_MHz"] / config_dict["gamma_eff_MHz_G"]
    print(
        "Based on that, and the gamma_eff_MHz_G you have in your .ini file, I'm setting the field to %f"
        % field_G
    )
    with xepr() as x:
        assert field_G < 3700, "are you crazy??? field is too high!"
        assert field_G > 3300, "are you crazy?? field is too low!"
        field_G = x.set_field(field_G)
        print("field set to ", field_G)
# }}}
# {{{set phase cycling
ph1_cyc = r_[0,1,2,3]
nPhaseSteps = 4
#}}}
prog_p90_us = prog_plen(config_dict['p90_us'])
# {{{check total points
total_pts = nPoints * nPhaseSteps
assert total_pts < 2**14, (
    "You are trying to acquire %d points (too many points) -- either change SW or acq time so nPoints x nPhaseSteps is less than 16384"
    % total_pts
)
# }}}
# {{{ acquire FID
data = generic(
    ppg_list=[
        ('phase_reset',1),
        ('delay_TTL',config_dict['deblank_us']),
        ('pulse_TTL',prog_p90_us,'ph1',ph1_cyc),
        ('delay',config_dict['deadtime_us']),
        ('acquire',config_dict['acq_time_ms']),
        ('delay',config_dict['repetition_us']),
        ],
    nScans = config_dict['nScans'],
    indirect_idx = 0,
    indirect_len = 1,
    adcOffset = config_dict["adc_offset"],
    carrierFreq_MHz=config_dict["carrierFreq_MHz"],
    nPoints=nPoints,
    time_per_segment_ms=config_dict["acq_time_ms"],
    SW_kHz=config_dict["SW_kHz"],
    amplitude=config_dict["amplitude"],
    ret_data=None,
)
# }}}
# {{{ chunk and save data
data.chunk(
    "t",
    ["ph1", "t2"], 
    [len(ph1_cyc),-1]
)
data.setaxis("ph1", ph1_cyc/4)
data.set_prop("postproc_type","spincore_FID_v1")
data.set_prop("coherence_pathway", {"ph1"})
data.set_prop("acq_params", config_dict.asdict())
config_dict = save_data(data, my_exp_type, config_dict, "FID")
config_dict.write()
# }}}
