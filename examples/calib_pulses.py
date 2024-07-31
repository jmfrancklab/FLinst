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
# {{{ add file saving parameters to config dict
config_dict["type"] = "pulse_calib"
config_dict["date"] = datetime.now().strftime("%y%m%d")
config_dict["misc_counter"] += 1
# }}}
# {{{ ppg
sqrt_P = config_dict["amplitude"] * np.sqrt(75)  # we have a 75 W amplifier
desired_beta = np.linspace(0.5*sqrt_P, 100, 50)
tx_phases = np.r_[0.0, 90.0, 180.0, 270.0]
Rx_scans = 1
datalist = []
prog_t = []
# {{{ set up settings for GDS
with GDS_scope() as gds:
    gds.reset()
    gds.CH2.disp = True
    gds.write(":CHAN1:DISP OFF")
    gds.write(":CHAN2:DISP ON")
    gds.write(":CHAN3:DISP OFF")
    gds.write(":CHAN4:DISP OFF")
    gds.CH2.voltscal = 100e-3  # set voltscale to 100 mV
    gds.timescal(50e-6, pos=0)  # set timescale to 50 us
    gds.write(":CHAN2:IMP 5.0E+1")  # set impedance to 50 ohm
    gds.write(":TRIG:SOUR CH2")
    gds.write(":TRIG:MOD NORMAL")  # set trigger mode to normal
    gds.write(":TRIG:HLEV 7.5E-2")  # used in gds_for_tune which seems reasonable
    # }}}
    if calibrating:
        t_p_range = linspace(0.5,25,25)
    else:
        t_p_range = spc.prog_plen(desired_beta,config_dict["amplitude"])
    for index, val in enumerate(t_p_range):
        t_p = val
        prog_t.append(t_p)
        spc.configureTX(
            config_dict["adc_offset"],
            config_dict["carrierFreq_MHz"],
            tx_phases,
            config_dict["amplitude"],
            nPoints,
        )
        acq_time = spc.configureRX(
            config_dict["SW_kHz"], nPoints, Rx_scans, config_dict["nEchoes"], 1
        )  # Not phase cycling so setting nPhaseSteps to 1
        config_dict["acq_time_ms"] = acq_time
        spc.init_ppg()
        spc.load(
            [
                ("phase_reset", 1),
                ("delay_TTL", 1.0),
                ("pulse_TTL", t_p, 0),
                ("delay", config_dict["deadtime_us"]),
            ]
        )
        spc.stop_ppg()
        spc.runBoard()
        datalist.append(gds.waveform(ch=2))
        spc.stopBoard()
data = psd.concat(datalist, "t_p").reorder("t")
data.set_units("t", "s")
data.set_prop("set_t", prog_t)
data.set_prop("desired_betas", desired_beta) 
data.set_prop("acq_params", config_dict.asdict())
config_dict = spc.save_data(data, my_exp_type, config_dict, "misc")
config_dict.write()
