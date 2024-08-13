import time
import os
import pyspecdata as psd
import SpinCore_pp as spc
from datetime import datetime
from Instruments import GDS_scope
import numpy as np

my_exp_type = "test_equipment"
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
t90_pulse_us = 20
# {{{ add file saving parameters to config dict
config_dict["type"] = "pulse_capture"
config_dict["date"] = datetime.now().strftime("%y%m%d")
config_dict["misc_counter"] += 1
# }}}
# {{{ ppg
tx_phases = np.r_[0.0, 90.0, 180.0, 270.0]
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
    gds.write(":TRIG:LEV 6.4E-2")  # set trigger level
    gds.CH2.voltscal = config_dict["amplitude"] * 0.5
    if config_dict["amplitude"] < 0.1:
        gds.timscal(5e-6, pos=-9.5e-6)
    else:
        gds.timscal(5e-6, pos=9.5e-6)
    # )
    # }}}
    data = None
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
            ("delay_TTL", config_dict["deblank_us"]),
            ("pulse_TTL", t90_pulse_us, 0),
            ("delay", config_dict["deadtime_us"]),
        ]
    )
    spc.stop_ppg()
    spc.runBoard()
    spc.stopBoard()
    time.sleep(1.0)
    thiscapture = gds.waveform(ch=2)
    # {{{ just convert to analytic here, and also downsample
    thiscapture.ft("t", shift=True)
    # this is a rare case where we care more about not keeping
    # ridiculous quantities of garbage on disk, so we are going to
    # throw some stuff out beforehand
    thiscapture = thiscapture["t":(0, None)]["t":(None, 24e6)]
    thiscapture *= 2
    thiscapture["t", 0] *= 0.5
    thiscapture.ift("t")
    # }}}
    data = thiscapture
data.set_prop("programmed_t_pulse_us", t90_pulse_us)
data.set_units("t", "s")
data.set_prop("acq_params", config_dict.asdict())
config_dict = spc.save_data(data, my_exp_type, config_dict, "misc", proc=False)
config_dict.write()
