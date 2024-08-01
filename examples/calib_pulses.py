r"""
Calibrate pulses output from RF amplifier
=========================================
If calibrating the pulse lengths, a series of pulse lengths are sent to the 
spincore directly and the output pulse is captured on the GDS oscilloscope.
If testing the calibration or capturing using a series of desired betas,
the calibrating conditional should be set to false and the script will calibrate
the pulse lengths so that the output of the amplifier produces the desired beta.
It is very important to note that there MUST BE at least a 40 dBm
attenuator between the RF amplifier output and the GDS oscilloscope input to
avoid damaging the instrumentation! It is advised that the attenuator be
calibrated using the GDS and AFG beforehand
"""
import pyspecdata as psd
import os
import SpinCore_pp as spc
from datetime import datetime
from Instruments import GDS_scope
import numpy as np

calibrating = True
my_exp_type = "test_equipment"
nominal_power = 75
nominal_atten = 1e4
assert os.path.exists(psd.getDATADIR(exp_type=my_exp_type))
# {{{ importing acquisition parameters
config_dict = spc.configuration("active.ini")
(
    nPoints,
    config_dict["SW_kHz"],
    config_dict["acq_time_ms"],
) = spc.get_integer_sampling_intervals(
    config_dict["SW_kHz"], config_dict["acq_time_ms"]
)
# }}}
if calibrating:
    t_pulse = np.linspace(
        0.5,
        150
        / np.sqrt(nominal_power)
        / config_dict[
            "amplitude"
        ],  # if the amplitude is small we want to go out to much longer pulse lengths
        30,
    )
else:
    desired_beta = np.linspace(0.5, 150, 50)
    t_pulse = spc.prog_plen(desired_beta, config_dict["amplitude"])
# {{{ add file saving parameters to config dict
config_dict["type"] = "pulse_calib"
config_dict["date"] = datetime.now().strftime("%y%m%d")
config_dict["misc_counter"] += 1
# }}}
# {{{ ppg
tx_phases = np.r_[0.0, 90.0, 180.0, 270.0]
datalist = []
with GDS_scope() as gds:
    # {{{ set up settings for GDS
    gds.reset()
    gds.autoset
    gds.CH1.disp = True
    gds.CH2.disp = True
    gds.write(":CHAN1:DISP OFF")
    gds.write(":CHAN2:DISP ON")
    gds.write(":CHAN3:DISP OFF")
    gds.write(":CHAN4:DISP OFF")
    gds.write(":CHAN2:IMP 5.0E+1")  # set impedance to 50 ohm
    gds.write(":TRIG:SOUR CH2")
    gds.write(":TRIG:MOD NORMAL")  # set trigger mode to normal
    # PR COMMENT: I tried to make the following so that it could be used flexibly with a range of powers
    gds.CH2.voltscal = config_dict["amplitude"] * np.sqrt(
        2 * nominal_power / nominal_atten * 50
    )  # 2 inside is for rms-amp
    gds.timscal(np.max(t_pulse * 1e-6), pos=20e-6)
    # }}}
    for index, this_t_pulse in enumerate(t_pulse):
        spc.configureTX(
            config_dict["adc_offset"],
            config_dict["carrierFreq_MHz"],
            tx_phases,
            config_dict["amplitude"],
            nPoints,
        )
        acq_time = spc.configureRX(
            # Rx scans, echos, and nPhaseSteps set to 1
            config_dict["SW_kHz"],
            nPoints,
            1,
            1,
            1,
        )
        config_dict["acq_time_ms"] = acq_time
        spc.init_ppg()
        spc.load(
            [
                ("phase_reset", 1),
                ("delay_TTL", 1.0),
                ("pulse_TTL", this_t_pulse, 0),
                ("delay", config_dict["deadtime_us"]),
            ]
        )
        spc.stop_ppg()
        spc.runBoard()
        datalist.append(gds.waveform(ch=2))
        spc.stopBoard()
if calibrating:
    data = psd.concat(datalist, "t_pulse").reorder("t", first=False)
    data.setaxis("t_pulse", t_pulse)
else:
    data = psd.concat(datalist, "beta").reorder("t", first=False)
    data.setaxis("beta", desired_beta)
    data.set_prop("programmed_t_pulse", t_pulse)
data.set_units("t", "s")
data.set_prop("acq_params", config_dict.asdict())
config_dict = spc.save_data(data, my_exp_type, config_dict, "misc")
config_dict.write()
