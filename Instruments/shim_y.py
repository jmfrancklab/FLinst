"""
Y shim sweep
============

Acquire a series of spin echoes while stepping the Y shim current.
The saved dataset can then be processed to determine the best Y shim.
"""

# TODO ☐: this belongs in examples, not here

from pyspecdata import getDATADIR, figlist_var, nddata
from numpy import r_
import os
import time
import numpy as np
import matplotlib.pyplot as plt
import SpinCore_pp
from SpinCore_pp import get_integer_sampling_intervals
from SpinCore_pp.ppg import run_spin_echo
from Instruments import HP6623A, prologix_connection, power_control
from datetime import datetime
import h5py

my_exp_type = "ODNP_NMR_comp/Echoes"
assert os.path.exists(getDATADIR(exp_type=my_exp_type))

# {{{ user settings
Y_channel = 1
y_current_max = 1.5
y_voltage_limit = 15.0
settle_s = 2.0
set_B_field = False
auto_adc_offset = False
# }}}

# {{{ importing acquisition parameters
config_dict = SpinCore_pp.configuration("active.ini")
(
    nPoints,
    config_dict["SW_kHz"],
    config_dict["acq_time_ms"],
) = get_integer_sampling_intervals(
    config_dict["SW_kHz"], config_dict["acq_time_ms"]
)
ph1_cyc = r_[0, 1, 2, 3]
nPhaseSteps = len(ph1_cyc)
# }}}

# {{{ add file saving parameters to config dict
config_dict["type"] = "shim_y"
config_dict["date"] = datetime.now().strftime("%y%m%d")
config_dict["shim_y_counter"] += 1
filename = (
    f"{config_dict['date']}_"
    f"{config_dict['chemical']}_"
    f"{config_dict['type']}_"
    f"{config_dict['shim_y_counter']}"
)
# }}}

# {{{ check total points
total_pts = nPoints * nPhaseSteps
assert total_pts < 2**14, (
    "You are trying to acquire %d points (too many points) -- either"
    " change SW or acq time so nPoints x nPhaseSteps is less than 16384"
    "\nyou could try reducing the acq_time_ms to %f"
    % (total_pts, config_dict["acq_time_ms"] * 16384 / total_pts)
)
# }}}

# {{{ optionally remeasure adc offset
if auto_adc_offset:
    print("adc was ", config_dict["adc_offset"], end=" and ")
    counter = 0
    first = True
    result1 = result2 = result3 = None
    while first or not (result1 == result2 == result3):
        first = False
        result1 = SpinCore_pp.adc_offset()
        time.sleep(0.1)
        result2 = SpinCore_pp.adc_offset()
        time.sleep(0.1)
        result3 = SpinCore_pp.adc_offset()
        if counter > 20:
            raise RuntimeError("after 20 tries, I can't stabilize ADC")
        counter += 1
    config_dict["adc_offset"] = result3
    print("adc determined to be:", config_dict["adc_offset"])
# }}}

# {{{ set field
if set_B_field:
    input(
        "I'm assuming that you've tuned your probe to %f since that's"
        " what's in your .ini file. Hit enter if this is true"
        % config_dict["carrierFreq_MHz"]
    )
    field_G = config_dict["carrierFreq_MHz"] / config_dict["gamma_eff_MHz_G"]
    print(
        "Based on that, and the gamma_eff_MHz_G you have in your .ini"
        " file, I'm setting the field to %f" % field_G
    )
    with power_control() as p:
        assert field_G < 3700, "are you crazy??? field is too high!"
        assert field_G > 3300, "are you crazy?? field is too low!"
        field_G = p.set_field(field_G)
        print("field set to ", field_G)
# }}}

data = None
with (
    prologix_connection(
        ip=config_dict["prologix_ip"],
        port=config_dict["prologix_port"],
    ) as p,
    HP6623A(
        prologix_instance=p,
        address=config_dict["HP1_address"],
    ) as HP1,
):
    HP1.safe_current = 1.6
    initial_current = HP1.I_limit[Y_channel]
    y_current_list = HP1.allowed_I[Y_channel]
    y_current_list = y_current_list[y_current_list <= y_current_max]
    assert len(y_current_list) > 0, (
        "No allowed Y currents are less than or equal to y_current_max"
    )
    print("acquiring at Y currents:", y_current_list)
    HP1.V_limit[Y_channel] = y_voltage_limit
    HP1.I_limit[Y_channel] = 0
    HP1.output[Y_channel] = 1
    for idx, this_current in enumerate(y_current_list):
        HP1.I_limit[Y_channel] = this_current
        print(
            "set Y shim to",
            HP1.I_limit[Y_channel],
            "A and waiting",
            settle_s,
            "s",
        )
        time.sleep(settle_s)
        data = run_spin_echo(
            deadtime_us=config_dict["deadtime_us"],
            deblank_us=config_dict["deblank_us"],
            nScans=config_dict["nScans"],
            indirect_idx=idx,
            indirect_len=len(y_current_list),
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
    HP1.V_limit[Y_channel] = 0
    HP1.I_limit[Y_channel] = 0
    HP1.output[Y_channel] = 0
    print("Y shim is turned off")

data.rename("indirect", "y_current")
data.setaxis("y_current", y_current_list).set_units("y_current", "A")

# {{{ chunk and save data
data.chunk("t", ["ph1", "t2"], [len(ph1_cyc), -1])
data.setaxis("ph1", ph1_cyc / 4)
if config_dict["nScans"] > 1:
    data.setaxis("nScans", r_[0 : config_dict["nScans"]])
data.reorder(["nScans", "ph1", "y_current", "t2"])
data.set_units("t2", "s")
data.set_prop("postproc_type", "proc_spincore_generalproc_v1")
data.set_prop("coherence_pathway", {"ph1": +1})
data.set_prop("acq_params", config_dict.asdict())
data.name(config_dict["type"] + "_" + str(config_dict["shim_y_counter"]))
target_directory = getDATADIR(exp_type=my_exp_type)
filename_out = filename + ".h5"
nodename = config_dict["type"]
if os.path.exists(f"{target_directory}{filename_out}"):
    print("this file already exists so we will add a node to it!")
    with h5py.File(
        os.path.normpath(os.path.join(target_directory, f"{filename_out}"))
    ) as fp:
        while nodename in fp.keys():
            config_dict["shim_y_counter"] += 1
            nodename = (
                config_dict["type"] + "_" + str(config_dict["shim_y_counter"])
            )
        data.name(nodename)
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
