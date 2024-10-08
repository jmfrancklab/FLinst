"""
Field Sweep
===========

A ppg that performs a series of echoes at a range of designated field 
values that are determined from the guessed_MHz_to_GHz value in your 
active.ini and the field width parameter. 
"""
from pylab import *
from pyspecdata import *
import os
import SpinCore_pp
from SpinCore_pp.ppg import run_spin_echo
from datetime import datetime
from Instruments.XEPR_eth import xepr
import h5py

logger = init_logging(level="debug")
fl = figlist_var()
# {{{importing acquisition parameters
config_dict = SpinCore_pp.configuration("active.ini")
nPoints = int(config_dict["acq_time_ms"] * config_dict["SW_kHz"] + 0.5)
# }}}
# {{{ make field axis
left = (
    config_dict["guessed_mhz_to_ghz"] * config_dict["uw_dip_center_GHz"]
) / config_dict["gamma_eff_MHz_G"]
left = left - (config_dict["field_width"] / 2)
right = (
    config_dict["guessed_mhz_to_ghz"] * config_dict["uw_dip_center_GHz"]
) / config_dict["gamma_eff_MHz_G"]
right = right + (config_dict["field_width"] / 2)
assert right < 3700, "Are you crazy??? Field is too high!!!"
assert left > 3300, "Are you crazy??? Field is too low!!!"
field_axis = r_[left:right:1.0]
logger.info("Your field axis is:", field_axis)
myinput = input("Does this look okay?")
if myinput.lower().startswith("n"):
    raise ValueError("you said no!!")
# }}}
# {{{create filename and save to config file
date = datetime.now().strftime("%y%m%d")
config_dict["type"] = "field"
config_dict["date"] = date
config_dict["field_counter"] += 1
filename = (
    f"{config_dict['date']}_{config_dict['chemical']}_{config_dict['type']}"
)
# }}}
# {{{set phase cycling
phase_cycling = True
if phase_cycling:
    ph1_cyc = r_[0, 1, 2, 3]
    nPhaseSteps = 4
if not phase_cycling:
    ph1_cyc = 0.0
    nPhaseSteps = 1
# }}}
# {{{check total points
total_pts = nPoints * nPhaseSteps
assert total_pts < 2**14, (
    "You are trying to acquire %d points (too many points) -- either change SW or acq time so nPoints x nPhaseSteps is less than 16384\nyou could try reducing the acq_time_ms to %f"
    % (total_pts, config_dict["acq_time_ms"] * 16384 / total_pts)
)
# }}}
# {{{Run field sweep
with xepr() as x_server:
    first_B0 = x_server.set_field(field_axis[0])
    time.sleep(3.0)
    carrierFreq_MHz = config_dict["gamma_eff_MHz_G"] * first_B0
    sweep_data = run_spin_echo(
        nScans=config_dict["nScans"],
        indirect_idx=0,
        indirect_len=len(field_axis),
        ph1_cyc=ph1_cyc,
        adcOffset=config_dict["adc_offset"],
        carrierFreq_MHz=carrierFreq_MHz,
        nPoints=nPoints,
        nEchoes=config_dict["nEchoes"],
        p90_us=config_dict["p90_us"],
        repetition_us=config_dict["repetition_us"],
        tau_us=config_dict["tau_us"],
        SW_kHz=config_dict["SW_kHz"],
        indirect_fields=("Field", "carrierFreq"),
        ret_data=None,
    )
    myfreqs_fields = sweep_data.getaxis("indirect")
    myfreqs_fields[0]["Field"] = first_B0
    myfreqs_fields[0]["carrierFreq"] = carrierFreq_MHz
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
            repetition_us=config_dict["repetition_us"],
            tau_us=config_dict["tau_us"],
            SW_kHz=config_dict["SW_kHz"],
            ret_data=sweep_data,
        )
# }}}
# {{{chunk and save data
if phase_cycling:
    sweep_data.chunk("t", ["ph1", "t2"], [4, -1])
    sweep_data.setaxis("ph1", r_[0.0, 1.0, 2.0, 3.0] / 4)
    if config_dict["nScans"] > 1:
        sweep_data.setaxis("nScans", r_[0 : config_dict["nScans"]])
    sweep_data.reorder(["ph1", "indirect", "t2"])
    sweep_data.squeeze()
    sweep_data.set_units("t2", "s")
    fl.next("Raw - time")
    fl.image(
        sweep_data.C.mean("nScans")
        .setaxis("indirect", "#")
        .set_units("indirect", "scan #")
    )
    sweep_data.reorder("t2", first=False)
    for_plot = sweep_data.C
    for_plot.ft("t2", shift=True)
    for_plot.ft(["ph1"], unitary=True)
    fl.next("FTed data")
    fl.image(
        for_plot.C.mean("nScans")
        .setaxis("indirect", "#")
        .set_units("indirect", "scan #")
    )
else:
    if config_dict["nScans"] > 1:
        sweep_data.setaxis("nScans", r_[0 : config_dict["nScans"]])
    sweep_data.rename("t", "t2")
    fl.next("Raw - time")
    fl.image(
        sweep_data.C.mean("nScans")
        .setaxis("indirect", "#")
        .set_units("indirect", "scan #")
    )
    for_plot = sweep_data.C
    for_plot.ft("t2", shift=True)
    fl.next("FTed data")
    fl.image(
        for_plot.C.mean("nScans")
        .setaxis("indirect", "#")
        .set_units("indirect", "scan #")
    )
sweep_data.name(config_dict["type"] + "_" + str(config_dict["field_counter"]))
sweep_data.set_prop("postproc_type", "field_sweep_v1")
sweep_data.set_prop("acq_params", config_dict.asdict())
target_directory = getDATADIR(exp_type="ODNP_NMR_comp/field_dependent")
filename_out = filename + ".h5"
nodename = sweep_data.name()
if os.path.exists(f"{filename_out}"):
    print("this file already exists so we will add a node to it!")
    with h5py.File(
        os.path.normpath(os.path.join(target_directory, f"{filename_out}"))
    ) as fp:
        if nodename in fp.keys():
            print(
                "this nodename already exists, so I will call it temp_field_sweep"
            )
            sweep_data.name("temp_field_sweep")
            nodename = "temp_field_sweep"
    sweep_data.hdf5_write(f"{filename_out}", directory=target_directory)
else:
    try:
        sweep_data.hdf5_write(f"{filename_out}", directory=target_directory)
    except:
        print(
            f"I had problems writing to the correct file {filename}.h5, so I'm going to try to save your file to temp_field_sweep.h5 in the current directory"
        )
        if os.path.exists("temp_field_sweep.h5"):
            print("there is a temp_field_sweep.h5 already! -- I'm removing it")
            os.remove("temp_field_sweep.h5")
            sweep_data.hdf5_write("temp_field_sweep.h5")
            print(
                "if I got this far, that probably worked -- be sure to move/rename temp_field_sweep.h5 to the correct name!!"
            )
print("\n*** FILE SAVED IN TARGET DIRECTORY ***\n")
print(("Name of saved data", sweep_data.name()))
config_dict.write()
fl.show()
