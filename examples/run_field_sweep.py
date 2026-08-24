"""
Field Sweep
===========

Acquire repeated spin echoes while sweeping the magnet field through the
instrument control server. The requested sweep width is configured in MHz and
converted to a field axis with gamma_eff_MHz_G. At each field point, the
measured field readback is used to update the NMR carrier frequency before
running the echo, and both requested and measured fields are stored with the
data.

The microwave source is held at uw_dip_center_GHz and set to
field_sweep_microwave_power_dBm. Set field_sweep_microwave_power_dBm to -100
for a no-microwave-power experiment.
"""

import logging
import os
import time

import numpy as np
import pyspecdata as psd
import SpinCore_pp
from numpy import r_
from pyspecdata import strm
from SpinCore_pp import get_integer_sampling_intervals, save_data
from SpinCore_pp.ppg import run_spin_echo

from Instruments import instrument_control


my_exp_type = "b27/field_dependent"
assert os.path.exists(psd.getDATADIR(exp_type=my_exp_type))

config_dict = SpinCore_pp.configuration("active.ini")

# {{{ importing acquisition parameters
(
    nPoints,
    config_dict["SW_kHz"],
    config_dict["acq_time_ms"],
) = get_integer_sampling_intervals(
    config_dict["SW_kHz"], config_dict["acq_time_ms"]
)
gamma_eff_MHz_G = config_dict["gamma_eff_MHz_G"]
config_dict["type"] = "field_sweep"
settle_s = config_dict["magnet_settle_medium"]
if config_dict["nEchoes"] != 1:
    raise ValueError("run_spin_echo requires nEchoes = 1")
mw_power_dBm = config_dict["field_sweep_microwave_power_dBm"]
# }}}
# {{{ build field axis
requested_field_sweep_width_MHz = config_dict["field_sweep_width_MHz"]
center_field_G = config_dict["carrierFreq_MHz"] / gamma_eff_MHz_G
requested_field_sweep_width_G = (
    requested_field_sweep_width_MHz / gamma_eff_MHz_G
)
requested_resolution_G = config_dict["field_sweep_resolution_G"]
n_intervals = int(
    np.ceil(requested_field_sweep_width_G / requested_resolution_G)
)
field_sweep_width_G = n_intervals * requested_resolution_G
field_sweep_width_MHz = field_sweep_width_G * gamma_eff_MHz_G
left_field_G = center_field_G - field_sweep_width_G / 2
right_field_G = center_field_G + field_sweep_width_G / 2
assert right_field_G < 3700, "Are you crazy??? Field is too high!!!"
assert left_field_G > 3300, "Are you crazy??? Field is too low!!!"
field_axis = (
    center_field_G
    + (np.arange(n_intervals + 1) - n_intervals / 2) * requested_resolution_G
)
myinput = input(
    strm(
        "Your field axis is:",
        field_axis,
        "\ncenter field:",
        center_field_G,
        "G",
        "\nrequested sweep width:",
        requested_field_sweep_width_G,
        "G /",
        requested_field_sweep_width_MHz,
        "MHz",
        "\nrounded sweep width:",
        field_sweep_width_G,
        "G /",
        field_sweep_width_MHz,
        "MHz",
        "\nrequested resolution:",
        requested_resolution_G,
        "G",
        "\nsweep points:",
        len(field_axis),
        "\nmicrowave power:",
        mw_power_dBm,
        "dBm",
        "\nMicrowave power should be in the linear regime of the E(p) curve.",
        "\nDoes this look okay? [y/N]",
    )
)
if not myinput.lower().startswith("y"):
    raise ValueError("You should modify your parameters in active.ini")
# }}}
# {{{ set phase cycling
ph1_cyc = r_[0, 1, 2, 3]
nPhaseSteps = len(ph1_cyc)
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
# {{{ run field sweep
data = None
field_axis_coords = None
field_requested_G = []
field_readback_G = []
with instrument_control() as ic:
    ic.start_log()
    if mw_power_dBm == -100:
        ic.mw_off()
    else:
        ic.set_power(10)
        ic.set_freq(config_dict["uw_dip_center_GHz"] * 1e9)
        ic.set_power(mw_power_dBm)
        for _ in range(10):
            time.sleep(0.5)
            if abs(ic.get_power_setting() - mw_power_dBm) <= 0.1:
                break
        if abs(ic.get_power_setting() - mw_power_dBm) > 0.1:
            raise ValueError(
                "After 10 tries, this power has still not settled"
            )
    for field_idx, desired_B0_G in enumerate(field_axis):
        try:
            true_B0_G = ic.set_field(desired_B0_G)
        except RuntimeError as e:
            logging.warning(
                "Skipping field point %d of %d at %f G because field setting"
                " failed: %s",
                field_idx + 1,
                len(field_axis),
                desired_B0_G,
                e,
            )
            continue
        print("field set to", true_B0_G, "G")
        print("waiting", settle_s, "s for the magnet to settle")
        time.sleep(settle_s)
        carrierFreq_MHz = gamma_eff_MHz_G * true_B0_G
        acquired_idx = len(field_requested_G)
        logging.info(f"{field_idx + 1} of {len(field_axis)}")
        logging.info(
            "The ratio of the field I want to the one I get is"
            f" {desired_B0_G / true_B0_G}\n"
            "In other words, the discrepancy is"
            f" {true_B0_G - desired_B0_G} G"
        )
        DNP_ini_time = time.time()
        data = run_spin_echo(
            nScans=config_dict["nScans"],
            indirect_idx=acquired_idx,
            indirect_len=len(field_axis),
            ph1_cyc=ph1_cyc,
            adcOffset=config_dict["adc_offset"],
            carrierFreq_MHz=carrierFreq_MHz,
            nPoints=nPoints,
            deadtime_us=config_dict["deadtime_us"],
            deblank_us=config_dict["deblank_us"],
            plen=config_dict["beta_90_s_sqrtW"],
            nEchoes=config_dict["nEchoes"],
            repetition_us=config_dict["repetition_us"],
            tau_us=config_dict["tau_us"],
            SW_kHz=config_dict["SW_kHz"],
            amplitude=config_dict["amplitude"],
            ret_data=data,
            indirect_fields=("start_times", "stop_times"),
        )
        DNP_done = time.time()
        if acquired_idx == 0:
            field_axis_coords = data.getaxis("indirect")
        field_axis_coords[acquired_idx]["start_times"] = DNP_ini_time
        field_axis_coords[acquired_idx]["stop_times"] = DNP_done
        field_requested_G.append(desired_B0_G)
        field_readback_G.append(true_B0_G)
    this_log = ic.stop_log()
if data is None:
    raise RuntimeError(
        "Field setting failed for every requested field point"
    )
data = data["indirect", : len(field_requested_G)]
field_requested_G = np.asarray(field_requested_G)
field_readback_G = np.asarray(field_readback_G)
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
data.set_prop("postproc_type", "field_sweep_v5")
data.set_prop("coherence_pathway", {"ph1": +1})
data.set_prop("acq_params", config_dict.asdict())
data.set_prop("field_axis_G", field_requested_G)
data.set_prop("field_readback_G", field_readback_G)
data.set_prop("log", this_log.__getstate__())
config_dict = save_data(data, my_exp_type, config_dict, "field_sweep")
config_dict.write()
# }}}
