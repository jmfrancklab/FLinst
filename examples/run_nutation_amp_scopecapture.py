"""
Amp varied Nutation
===================
A Hahn echo is output directly to the GDS oscilloscope from the SpinCore.
The amplitude is varied through a series that the user defines.
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
import h5py
from Instruments.XEPR_eth import xepr
from Instruments.gds import GDS_scope
from SpinCore_pp.ppg import run_spin_echo

amp_range = np.linspace(0, 0.5, 200)[1:]
nominal_power = 75
nominal_atten = 1e4
num_div_per_screen = 16
my_exp_type = "ODNP_NMR_comp/nutation"
assert os.path.exists(psd.getDATADIR(exp_type=my_exp_type))
# {{{importing acquisition parameters
config_dict = SpinCore_pp.configuration("active.ini")
(
    nPoints,
    config_dict["SW_kHz"],
    config_dict["acq_time_ms"],
) = get_integer_sampling_intervals(config_dict["SW_kHz"], config_dict["acq_time_ms"])
# }}}
# {{{add file saving parameters to config dict
config_dict["type"] = "nutation"
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
    g.write(":CHAN2:IM 5.0E+1") # set impedance to 50 ohms
    g.write(":TRIG:SOUR CH2")
    g.write(":TRIG:MOD NORMAL")
    g.write(":TRIG:LEV 1.5E-2")
    g.acquire_mode("HIR")
    if config
    for index, amplitude in enumerate(amp_range):
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
            ph1_cyc=ph1,
            ph2_cyc=ph2,
            ret_data=None,
        )
        datalist.append(g.waveform(ch=1))
nutation_data = np.concat(datalist, "repeats").reorder("t")
nutation_data.chunk("t", ["ph2", "ph1", "t2"], [2, 4, -1])
nutation_data.setaxis("ph2", np.r_[0:2] / 4).setaxis("ph1", np.r_[0:4] / 4)
nutation_data.set_units("t2", "s")
nutation_data.set_prop("postproc_type", "nutation_scopecapture_v1")
nutation_data.name(config_dict["type"] + config_dict["echo_counter"])
nutation_data.set_prop("acq_params", config_dict.asdict())
# }}}
# {{{save data
nodename = nutation_data.name()
filename_out = filename + ".h5"
with h5py.File(
    os.path.normpath(os.path.join(target_directory, f"{filename_out}"))
) as fp:
    if nodename in fp.keys():
        print(
            "this nodename already exists, so I will call it temp_nutation_amp_%d"
            % config_dict["echo_counter"]
        )
        nutation_data.name("temp__nutation_amp_%d" % config_dict["echo_counter"])
        nodename = "temp_nutation_amp_%d" % config_dict["echo_counter"]
        nutation_data.hdf5_write(f"{filename_out}", directory=target_directory)
    else:
        nutation_data.hdf5_write(f"{filename_out}", directory=target_directory)
print("\n*** FILE SAVED IN TARGET DIRECTORY ***\n")
print(("Name of saved data", nutation_data.name()))
print(("Shape of saved data", ndshape(nutation_data)))
config_dict.write()
# }}}
# {{{image data
with figlist_var() as fl:
    fl.next("raw data")
    fl.image(nutation_data)
    nutation_data.ft("t2", shift=True)
    fl.next("FT raw data")
    fl.image(nutation_data)
    fl.show()
# }}}
