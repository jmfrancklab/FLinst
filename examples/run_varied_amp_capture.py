"""
Amp variation
=============
A Hahn echo is output directly to the GDS oscilloscope from the SpinCore.
The amplitude is varied through a list that the user defines.
It is very important to not that there MUST BE at least a 40 dBm 
attenuator between the RF amplifier output and the GDS oscilloscope input
to avoid damaging the instrumentation! It is advised that the attenuator be
calibrated using the GDS and AFG beforehand
"""
import pyspecdata as psd
import os
import SpinCore_pp as spc
from datetime import datetime
import numpy as np
from Instruments.gds import GDS_scope
from SpinCore_pp.ppg import run_spin_echo

amp_range = np.linspace(0, 0.5, 200)[1:]
nominal_power = 75
nominal_atten = 1e4
num_div_per_screen = 16
t_pulse_us = 4
my_exp_type = "ODNP_NMR_comp/Echoes"
assert os.path.exists(psd.getDATADIR(exp_type=my_exp_type))
# {{{importing acquisition parameters
config_dict = spc.configuration("active.ini")
(
    nPoints,
    config_dict["SW_kHz"],
    config_dict["acq_time_ms"],
) = spc.get_integer_sampling_intervals(
    config_dict["SW_kHz"], config_dict["acq_time_ms"]
)
# }}}
# {{{add file saving parameters to config dict
config_dict["type"] = "echo"
config_dict["date"] = datetime.now().strftime("%y%m%d")
config_dict["echo_counter"] += 1
# }}}
tx_phases = np.r_[0.0, 90.0, 180.0, 270.0]
with GDS_scope() as g:
    g.reset()
    g.autoset
    g.CH1.disp = True
    g.CH2.disp = True
    g.write(":CHAN1:DISP OFF")
    g.write(":CHAN2:DISP ON")
    g.write(":CHAN3:DISP OFF")
    g.write(":CHAN4:DISP OFF")
    g.write(":CHAN2:IM 5.0E+1")  # set impedance to 50 ohms
    g.write(":TRIG:SOUR CH2")
    g.write(":TRIG:MOD NORMAL")
    g.write(":TRIG:LEV 1.5E-2")
    g.acquire_mode("HIR")

    def round_for_scope(val, multiples=1):
        val_oom = np.floor(np.log10(val))
        val = (
            np.ceil(val / 10**val_oom / multiples)
            * 10**val_oom
            * multiples
        )
        return val

    g.CH2.voltscal = round_for_scope(
        amp_range[-1]
        * np.sqrt(2 * nominal_power / nominal_atten * 50)
        * 2
        / num_div_per_screen
    )  # 2 inside is for rms-amp 2 outside is for positive and negative
    scope_timescale = round_for_scope(
        t_pulse_us * 1e-6 * 0.5 / num_div_per_screen, multiples=5
    )
    g.timscal(
        scope_timescale,
        pos=round_for_scope(0.5 * t_pulse_us * 1e-6 - 3e-6),
    )
    data = None
    for idx, amplitude in enumerate(amp_range):
        echo_data = run_spin_echo(
            nScans=config_dict["nScans"],
            indirect_idx=0,
            indirect_len=1,
            adcOffset=config_dict["adc_offset"],
            carrierFreq_MHz=config_dict["carrierFreq_MHz"],
            nPoints=nPoints,
            nEchoes=config_dict["nEchoes"],
            p90_us=config_dict["p90_us"],
            repetition=config_dict["repetition_us"],
            tau_us=config_dict["tau_us"],
            SW_kHz=config_dict["SW_kHz"],
            plen_as_beta=False,
            ret_data=None,
        )
        thiscapture = g.waveform(ch=2)
        if data is None:
            data = thiscapture.shape
            data += ("amps", len(amp_range))
            data = data.alloc()
            data.copy_axes(thiscapture)
            data.copy_props(thiscapture)
        data["amps", idx] = thiscapture
data.setaxis("amps", amp_range)
data.set_units("t", "s")
data.set_prop("postproc_type", "GDS_capture_v1")
data.set_prop("acq_params", config_dict.asdict())
config_dict = spc.save_data(data, my_exp_type, config_dict, "misc", proc=False)
# }}}
config_dict.write()
# }}}
