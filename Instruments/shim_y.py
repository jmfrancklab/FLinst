"""
Y shim sweep
============

Acquire a series of spin echoes while stepping the Y shim current.
The saved dataset can then be processed to determine the best Y shim.
"""

from pyspecdata import getDATADIR
from numpy import r_
import os
import time
import matplotlib.pyplot as plt
import numpy as np
import SpinCore_pp
from SpinCore_pp import get_integer_sampling_intervals, save_data
from SpinCore_pp.ppg import run_spin_echo
from Instruments import HP6623A, prologix_connection, power_control
from datetime import datetime

my_exp_type = "ODNP_NMR_comp/Echoes"
assert os.path.exists(getDATADIR(exp_type=my_exp_type))

# {{{ user settings
Y_channel = 1
y_current_max = 1.5
y_voltage_limit = 15.0
settle_s = 2.0
set_B_field = False
auto_adc_offset = False
filter_timeconst = 10e-3
# }}}


def fwhm(trace):
    x = trace.getaxis("t2")
    y = abs(trace.data)
    peak_idx = y.argmax()
    peak_height = y[peak_idx]
    half_height = peak_height / 2.0
    left_idx = peak_idx
    while left_idx > 0 and y[left_idx] >= half_height:
        left_idx -= 1
    right_idx = peak_idx
    while right_idx < len(y) - 1 and y[right_idx] >= half_height:
        right_idx += 1
    if left_idx == peak_idx:
        left_cross = x[peak_idx]
    else:
        left_cross = np.interp(
            half_height,
            [y[left_idx], y[left_idx + 1]],
            [x[left_idx], x[left_idx + 1]],
        )
    if right_idx == peak_idx:
        right_cross = x[peak_idx]
    else:
        right_cross = np.interp(
            half_height,
            [y[right_idx], y[right_idx - 1]],
            [x[right_idx], x[right_idx - 1]],
        )
    return x[peak_idx], left_cross, right_cross, right_cross - left_cross


def integrate_energy(trace, left_lim, right_lim):
    x = trace.getaxis("t2")
    y = abs(trace.data) ** 2
    mask = np.logical_and(x >= left_lim, x <= right_lim)
    if not mask.any():
        return 0.0
    return np.trapz(y[mask], x[mask])


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
    for idx, this_current in enumerate(y_current_list):
        HP1.I_limit[Y_channel] = this_current
        HP1.output[Y_channel] = 1
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
data.set_prop("postproc_type", "spincore_SE_v2")
data.set_prop("coherence_pathway", {"ph1": +1})
data.set_prop("acq_params", config_dict.asdict())
config_dict = save_data(data, my_exp_type, config_dict, "shim_y")
config_dict.write()
# }}}

# {{{ process and plot
for_plot = data.C
if config_dict["nScans"] > 1:
    for_plot.mean("nScans")
for_plot.ft("ph1", unitary=True)
signal = for_plot["ph1", 1].C
signal.ift("t2")
signal *= np.exp(
    -abs(signal.fromaxis("t2") - config_dict["tau_us"] * 1e-6)
    / filter_timeconst
)
# {{{ Zero phasing and FID slicing
for j in range(len(y_current_list)):
    center_idx = abs(signal["y_current", j]).argmax("t2", raw_index=True).data
    this_fid = np.array(signal["y_current", j].data, copy=True)
    this_fid[:center_idx] = 0
    this_fid[center_idx] *= 0.5
    phase_ref = this_fid[center_idx]
    if abs(phase_ref) > 0:
        this_fid /= phase_ref / abs(phase_ref)
    signal["y_current", j].data[:] = this_fid
signal.ft("t2", shift=True)
# }}}
# {{{ Calculate FWHM  each Y current, using the same
# frequency range for energy integration
linewidth = np.zeros(len(y_current_list))
peak_position = np.zeros(len(y_current_list))
left_edge = np.zeros(len(y_current_list))
right_edge = np.zeros(len(y_current_list))
for j in range(len(y_current_list)):
    (
        peak_position[j],
        left_edge[j],
        right_edge[j],
        linewidth[j],
    ) = fwhm(signal["y_current", j])
# }}}
# {{{ Determine the Y current with the largest FWHM
# to set the frequency range in energy integration
widest_idx = linewidth.argmax()
left_offset = left_edge[widest_idx] - peak_position[widest_idx]
right_offset = right_edge[widest_idx] - peak_position[widest_idx]
energy = np.zeros(len(y_current_list))
for j in range(len(y_current_list)):
    energy[j] = integrate_energy(
        signal["y_current", j],
        peak_position[j] + left_offset,
        peak_position[j] + right_offset,
    )
# }}}
best_idx = energy.argmax()
print("best Y current based on energy is", y_current_list[best_idx], "A")

fig, ax = plt.subplots(2, 1, figsize=(8, 10), constrained_layout=True)
mesh = ax[0].pcolormesh(
    signal.getaxis("t2") / 1e3,
    y_current_list,
    abs(signal.data),
    shading="auto",
)
for j in range(len(y_current_list)):
    ax[0].plot(
        np.array([left_edge[j], right_edge[j]]) / 1e3,
        np.array([y_current_list[j], y_current_list[j]]),
        color="w",
        alpha=0.3,
    )
ax[0].set_xlabel("frequency shift / kHz")
ax[0].set_ylabel("Y current / A")
ax[0].set_title("Echo-phase spectrum vs Y current")
fig.colorbar(mesh, ax=ax[0], label="abs(signal)")

ax[1].plot(y_current_list, energy, "o-", color="k", label="energy")
ax[1].axvline(y_current_list[best_idx], color="k", ls=":", alpha=0.5)
ax[1].set_xlabel("Y current / A")
ax[1].set_ylabel("Energy / a.u.", color="k")
ax[1].tick_params(axis="y", labelcolor="k")
ax2 = ax[1].twinx()
ax2.plot(y_current_list, linewidth / 1e3, "s-", color="r", label="FWHM")
ax2.set_ylabel("FWHM / kHz", color="r")
ax2.tick_params(axis="y", labelcolor="r")
ax[1].set_title("Energy and FWHM linewidth vs Y current")
plt.show()
# }}}
