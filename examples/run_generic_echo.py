"""
Spin Echo
=========

A Hahn echo is generated by feeding the generic ppg the specific ppg_list
required. Note that the overall phase and the 90-180 phase difference are
phase cycled in a nested way similar to run_CPMG.py. If you wish to keep
the field as is without adjustment follow the 'py run_generic_echo.py'
command with 'stayput' (e.g. 'py run_generic_echo.py stayput')
"""
from pylab import *
from pyspecdata import *
import os, sys
from numpy import *
import SpinCore_pp
from SpinCore_pp import prog_plen, get_integer_sampling_intervals
from SpinCore_pp.ppg import generic
from datetime import datetime
from Instruments.XEPR_eth import xepr
import h5py

# {{{importing acquisition parameters
config_dict = SpinCore_pp.configuration("active.ini")
(
    nPoints,
    config_dict["SW_kHz"],
    config_dict["acq_time_ms"],
) = get_integer_sampling_intervals(
    SW_kHz=config_dict["SW_kHz"], acq_time_ms=config_dict["acq_time_ms"]
)
my_exp_type = "ODNP_NMR_comp/Echoes"
target_directory = getDATADIR(exp_type=my_exp_type)
assert os.path.exists(target_directory)
# }}}
# {{{ command-line option to leave the field untouched (if you set it once, why set it again)
adjust_field = True
if len(sys.argv) == 2 and sys.argv[1] == "stayput":
    adjust_field = False
# }}}
# {{{ let computer set field
if adjust_field:
    print(
        "I'm assuming that you've tuned your probe to",
        config_dict["carrierFreq_MHz"],
        "since that's what's in your .ini file",
    )
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
# {{{create filename and save to config file
date = datetime.now().strftime("%y%m%d")
config_dict["type"] = "echo"
config_dict["date"] = date
config_dict["echo_counter"] += 1
filename = (
    f"{config_dict['date']}_{config_dict['chemical']}_generic_{config_dict['type']}"
)
# }}}
# {{{set phase cycling
# NOTE: The overall phase and the 90-180 phase difference are phase cycled
# in a nested way
ph2 = r_[0, 1, 2, 3]
ph_diff = r_[0, 2]
# the following puts ph_diff on the inside, which I would not have expected
ph1_cyc = array([(j + k) % 4 for k in ph2 for j in ph_diff])
ph2_cyc = array([(k + 1) % 4 for k in ph2 for j in ph_diff])
nPhaseSteps = len(ph2) * len(ph_diff)
# }}}
# {{{ calibrate pulse lengths
# NOTE: This is done inside the run_spin_echo rather than in the example
# but to keep the generic function more robust we do it outside of the ppg
prog_p90_us = prog_plen(config_dict["p90_us"])
prog_p180_us = prog_plen(2 * config_dict["p90_us"])
# }}}
# NOTE: Unlike CPMG, here, tau is the estimated time it takes for FID to
# decay to zero
assert config_dict["tau_us"] > 2 * prog_p90_us / pi + config_dict["deblank_us"]
# Because we are only doing one 180 pulse we do not bother with a
# symmetric echo as we can make timing corrections in post processing
# {{{check total points
total_pts = nPoints * nPhaseSteps * config_dict["nEchoes"]
assert total_pts < 2**14, (
    "You are trying to acquire %d points (too many points) -- either change SW or acq time so nPoints x nPhaseSteps is less than 16384"
    % total_pts
)
# }}}
# {{{ acquire echo
data = generic(
    ppg_list=[
        ("phase_reset", 1),
        ("delay_TTL", config_dict["deblank_us"]),
        ("pulse_TTL", prog_p90_us, "ph_cyc", ph1_cyc),
        ("delay", config_dict["tau_us"]),
        # NOTE: Unlike CPMG, here, tau is the estimated time it takes for FID to
        # decay to zero
        ("delay_TTL", config_dict["deblank_us"]),
        ("pulse_TTL", prog_p180_us, "ph_cyc", ph2_cyc),
        ("delay", config_dict["deadtime_us"]),
        ("acquire", config_dict["acq_time_ms"]),
        ("delay", config_dict["repetition_us"]),
    ],
    nScans=config_dict["nScans"],
    indirect_idx=0,
    indirect_len=1,
    adcOffset=config_dict["adc_offset"],
    carrierFreq_MHz=config_dict["carrierFreq_MHz"],
    nPoints=nPoints,
    acq_time_ms=config_dict["acq_time_ms"],
    SW_kHz=config_dict["SW_kHz"],
    ret_data=None,
)
# }}}
# {{{ chunk and save data
data.chunk(
    "t",
    ["ph2", "ph_diff", "t2"],
    [len(ph2), len(ph_diff), -1],
)
data.setaxis("ph2", ph2 / 4).setaxis("ph_diff", ph_diff / 4)
data.set_prop("postproc_type", "spincore_diffph_SE_v1")
data.set_prop("coherence_pathway", {"ph_overall": -1, "ph1": +1})
data.set_prop("acq_params", config_dict.asdict())
nodename = config_dict["type"] + "_" + str(config_dict["cpmg_counter"])
data.name(nodename)
filename_out = filename + ".h5"
if os.path.exists(f"{filename_out}"):
    print("this file already exists so we will add a node to it!")
    with h5py.File(
        os.path.normpath(os.path.join(target_directory, f"{filename_out}"))
    ) as fp:
        tempcounter = 1
        orig_nodename = nodename
        while nodename in fp.keys():
            nodename = "%s_temp_%d" % (orig_nodename, tempcounter)
            data.name(nodename)
            tempcounter += 1
data.hdf5_write(f"{filename_out}", directory=target_directory)
print("\n*** FILE SAVED IN TARGET DIRECTORY ***\n")
print(
    "saved data to (node, file, exp_type):",
    data.name(),
    filename_out,
    my_exp_type,
)
config_dict.write()
# }}}
