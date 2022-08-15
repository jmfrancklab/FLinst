# {{{ note on phase cycling
"""
FOR PHASE CYCLING: Provide both a phase cycle label (e.g.,
'ph1', 'ph2') as str and an array containing the indices
(i.e., registers) of the phases you which to use that are
specified in the numpy array 'tx_phases'.  Note that
specifying the same phase cycle label will loop the
corresponding phase steps together, regardless of whether
the indices are the same or not.
    e.g.,
    The following:
        ('pulse',2.0,'ph1',r_[0,1]),
        ('delay',1.5),
        ('pulse',2.0,'ph1',r_[2,3]),
    will provide two transients with phases of the two pulses (p1,p2):
        (0,2)
        (1,3)
    whereas the following:
        ('pulse',2.0,'ph1',r_[0,1]),
        ('delay',1.5),
        ('pulse',2.0,'ph2',r_[2,3]),
    will provide four transients with phases of the two pulses (p1,p2):
        (0,2)
        (0,3)
        (1,2)
        (1,3)
FURTHER: The total number of transients that will be
collected are determined by both nScans (determined when
calling the appropriate marker) and the number of steps
calculated in the phase cycle as shown above.  Thus for
nScans = 1, the SpinCore will trigger 2 times in the first
case and 4 times in the second case.  for nScans = 2, the
SpinCore will trigger 4 times in the first case and 8 times
in the second case.
"""
# }}}
from pyspecdata import *
from pylab import *
import os
import SpinCore_pp
from SpinCore_pp.ppg import run_spin_echo
from datetime import datetime
from Instruments.XEPR_eth import xepr
import numpy as np
import h5py

fl = figlist_var()
# {{{importing acquisition parameters
config_dict = SpinCore_pp.configuration("active.ini")
# }}}
#{{{ make field axis
left = (((config_dict['guessed_mhz_to_ghz']*config_dict['mw_freqs'])/config_dict['gamma_eff_MHz_G']))/1e9
left = left - (config_dict['field_width']/2)
right = (((config_dict['guessed_mhz_to_ghz']*config_dict['mw_freqs'])/config_dict['gamma_eff_MHz_G']))/1e9
right = right + (config_dict['field_width']/2)
field_axis = r_[left:right:1.0]
input("Does this look okay? Hit enter if so")
#}}}
# {{{create filename and save to config file
date = datetime.now().strftime("%y%m%d")
config_dict["type"] = "field"
config_dict["date"] = date
config_dict["field_counter"] += 1
filename = f"{config_dict['date']}_{config_dict['chemical']}_{config_dict['type']}"
# }}}
print("Here is my field axis:",field_axis)
#{{{ phase cycling
phase_cycling = True
if phase_cycling:
    nPhaseSteps = 4
if not phase_cycling:
    nPhaseSteps = 1
nPoints = int(config_dict["acq_time_ms"] * config_dict["SW_kHz"] + 0.5)
#}}}
total_pts = nPoints * nPhaseSteps
assert total_pts < 2 ** 14, (
    "You are trying to acquire %d points (too many points) -- either change SW or acq time so nPoints x nPhaseSteps is less than 16384"
    % total_pts
)
with xepr() as x_server:
        first_B0 = x_server.set_field(field_axis[0])
        time.sleep(3.0)
        carrierFreq_MHz = config_dict["gamma_eff_MHz_G"] * first_B0
        sweep_data = run_spin_echo(
            nScans=config_dict["nScans"],
            indirect_idx=0,
            indirect_len=len(field_axis),
            adcOffset=config_dict["adc_offset"],
            carrierFreq_MHz=carrierFreq_MHz,
            nPoints=nPoints,
            nEchoes=config_dict["nEchoes"],
            p90_us=config_dict["p90_us"],
            repetition=config_dict["repetition_us"],
            tau_us=config_dict["tau_us"],
            SW_kHz=config_dict["SW_kHz"],
            output_name=filename,
            indirect_fields=("Field", "carrierFreq"),
            ret_data=None,
        )
        myfreqs_fields = sweep_data.getaxis("indirect")
        myfreqs_fields[0]["Field"] = first_B0
        myfreqs_fields[0]["carrierFreq"] = config_dict["carrierFreq_MHz"]
        for B0_index, desired_B0 in enumerate(field_axis[1:]):
            true_B0 = x_server.set_field(desired_B0)
            logging.info("My field in G is %f" % true_B0)
            time.sleep(3.0)
            new_carrierFreq_MHz = config_dict["gamma_eff_MHz_G"] * true_B0
            myfreqs_fields[B0_index + 1]["Field"] = true_B0
            myfreqs_fields[B0_index + 1]["carrierFreq"] = new_carrierFreq_MHz
            logging.info("My frequency in MHz is", new_carrierFreq_MHz)
            run_spin_echo(
                nScans=config_dict["nScans"],
                indirect_idx=B0_index + 1,
                indirect_len=len(field_axis),
                adcOffset=config_dict["adc_offset"],
                carrierFreq_MHz=new_carrierFreq_MHz,
                nPoints=nPoints,
                nEchoes=config_dict["nEchoes"],
                p90_us=config_dict["p90_us"],
                repetition=config_dict["repetition_us"],
                tau_us=config_dict["tau_us"],
                SW_kHz=config_dict["SW_kHz"],
                output_name=filename,
                ret_data=sweep_data,
            )
        SpinCore_pp.stopBoard();
#}}}
# {{{chunk and save data
sweep_data.set_prop("acq_params", config_dict.asdict())
if phase_cycling:
    sweep_data.chunk("t", ["ph1", "t2"], [4, -1])
    sweep_data.setaxis("ph1", r_[0.0, 1.0, 2.0, 3.0] / 4)
    if config_dict["nScans"] > 1:
        sweep_data.setaxis("nScans", r_[0 : config_dict["nScans"]])
    sweep_data.reorder(["ph1", "nScans", "t2"])
    fl.next("Raw - time")
    fl.image(
        sweep_data.C.mean("nScans")
        .setaxis("indirect", "#")
        .set_units("indirect", "scan #")
    )
    sweep_data.reorder("t2", first=False)
    sweep_data.ft("t2", shift=True)
    sweep_data.ft("ph1", unitary=True)
    fl.next("Raw - frequency")
    fl.image(
        sweep_data.C.mean("nScans")
        .setaxis("indirect", "#")
        .set_units("indirect", "scan #")
    )
else:
    if config_dict["nScans"] > 1:
        sweep_data.setaxis("nScans", r_[0 : config_dict["nScans"]])
    fl.next("Raw - time")
    fl.image(
        sweep_data.C.mean("nScans")
        .setaxis("indirect", "#")
        .set_units("indirect", "scan #")
    )
    sweep_data.reorder("t", first=False)
    sweep_data.ft("t", shift=True)
    fl.next("Raw - frequency")
    fl.image(
        sweep_data.C.mean("nScans")
        .setaxis("indirect", "#")
        .set_units("indirect", "scan #")
    )
sweep_data.name(config_dict["type"] + "_" + str(config_dict["field_counter"]))
sweep_data.set_prop("postproc_type", "field_sweep_v1")
target_directory = getDATADIR(exp_type="ODNP_NMR_comp/field_dependent")
filename_out = filename + ".h5"
nodename = sweep_data.name()
if os.path.exists(filename + ".h5"):
    print("this file already exists so we will add a node to it!")
    with h5py.File(
        os.path.normpath(os.path.join(target_directory, f"{filename_out}"))
    ) as fp:
        if nodename in fp.keys():
            print("this nodename already exists, so I will call it temp")
            sweep_data.name("temp")
            nodename = "temp"
        sweep_data.hdf5_write(f"{filename_out}", directory=target_directory)
else:
    try:
        sweep_data.hdf5_write(f"{filename_out}", directory=target_directory)
    except:
        print(
            f"I had problems writing to the correct file {filename}.h5, so I'm going to try to save your file to temp.h5 in the current directory"
        )
        if os.path.exists("temp.h5"):
            print("there is a temp.h5 -- I'm removing it")
            os.remove("temp.h5")
        sweep_data.hdf5_write("temp.h5")
        print(
            "if I got this far, that probably worked -- be sure to move/rename temp.h5 to the correct name!!"
        )
print("\n*** FILE SAVED IN TARGET DIRECTORY ***\n")
print(("Name of saved data", sweep_data.name()))
print(("Shape of saved data", ndshape(sweep_data)))
config_dict.write()
fl.show()
