"""
SpinCore Noise Acquisition
==========================

This script acquires a set number of captures of the noise
as seen by the SpinCore. Remember to add a terminated attenuator 
to the output of the SpinCore prior to measurement!
"""
import pyspecdata as ps
import numpy as np
import os
from numpy import r_
from timeit import default_timer as timer
import SpinCore_pp as sc
from datetime import datetime


# {{{ Function for data acquisition
def collect(config_dict):
    """
    Collects `nScans` identical captures (specified by the config file) of the
    noise as acquired on the SpinCore.
    The resulting data has a direct dimension called `t` and the
    acquisitions are repeated along the `nScans` dimension.
    :Note: Some delays (e.g. the repetition
    and time between phase reset and acquisition
    are hard set to short values and are not pulled or stored in the
    config file).

    Parameters
    ==========
    config_dict: dict-like
        Contains the following keys:

        :SW_kHz: float
        :nScans: int
        :adc_offset: float
        :amplitude: float
        :carrier frequency: float
        :acq_time_ms: float
        :chemical: str
        :type: str
        :noise_counter: int

    Returns
    =======
    start: float
        Start time of acquisition for calculation of total acquisition time.
    data: nddata
        nddata containing captures of noise as acquired on the SpinCore.
    """
    # {{{ SpinCore settings - these don't change
    tx_phases = r_[0.0, 90.0, 180.0, 270.0]
    (
        nPoints,
        config_dict["SW_kHz"],
        config_dict["acq_time_ms"],
    ) = sc.get_integer_sampling_intervals(
        SW_kHz=config_dict["SW_kHz"],
        time_per_segment_ms=config_dict["acq_time_ms"],
    )
    data_length = 2 * nPoints * 1 * 1  # assume nEchoes and nPhaseSteps = 1
    RX_nScans = 1
    # }}}
    nScans_length = len(config_dict["nScans"])
    # {{{ Acquire data
    for j in range(1, nScans_length + 1):
        # {{{ configure SpinCore
        sc.configureTX(
            config_dict["adc_offset"],
            config_dict["carrierFreq_MHz"],
            tx_phases,
            config_dict["amplitude"],
            nPoints,
        )
        acq_time = sc.configureRX(
            config_dict["SW_kHz"],
            nPoints,
            RX_nScans,
            1,  # assume nEchoes = 1
            1,  # assume nPhaseSteps = 1
        )
        sc.init_ppg()
        # }}}
        # {{{ ppg to generate the SpinCore data
        sc.load(
            [
                ("marker", "start", 1),
                ("phase_reset", 1),
                ("delay", 0.5e3),  # pick short delay for tau_us (0.5 ms)
                ("acquire", acq_time),
                ("delay", 1e4),  # short rep_delay_us (10 ms)
                ("jumpto", "start"),
            ]
        )
        # }}}
        sc.stop_ppg()
        sc.runBoard()
        # {{{grab data for the single capture as a complex value
        raw_data = (
            sc.getData(data_length, nPoints, 1, 1).astype(float).view(complex)
        )  # assume nEchoes and nPhaseSteps = 1
        # }}}
        # {{{ if this is the first scan, then allocate an array
        #     to drop the data into, and assign the axis
        #     coordinates, etc.
        if j == 1:
            time_axis = np.linspace(0.0, acq_time * 1e-3, raw_data.size)
            data = (
                ps.ndshape(
                    [raw_data.size, nScans_length],
                    ["t", "nScans"],
                )
                .alloc(dtype=np.complex128)
                .setaxis("t", time_axis)
                .set_units("t", "s")
                .setaxis("nScans", r_[1 : nScans_length + 1])
                .name("signal")
            )
        # }}}
        data["nScans", j] = raw_data  # drop the data into appropriate index
        sc.stopBoard()
    # }}}
    data.set_prop("postproc_type", "spincore_general")
    data.set_prop("coherence_pathway", None)
    data.set_prop("acq_params", config_dict.as_dict())
    return data


# }}}
# {{{ set up config file and define exp_type
my_exp_type = "ODNP_NMR_comp/noise_tests"
assert os.path.exists(ps.getDATADIR(exp_type=my_exp_type))
config_dict = sc.configuration("active.ini")
# {{{ add file saving parameters to config dict
config_dict["chemical"] = (
    config_dict["chemical"] + "_" + str(config_dict["SW_kHz"]) + "kHz"
)
config_dict["type"] = "noise"
config_dict["date"] = datetime.now().strftime("%y%m%d")
config_dict["noise_counter"] += 1
# }}}
# }}}
print("Starting collection...")
start = timer()
data = collect(config_dict, my_exp_type)
end = timer()
data.set_prop("exp_times", (start, end))
print("Collection time:", (end - start), "s")
config_dict = sc.save_data(data, my_exp_type, config_dict, "noise")
config_dict.write()
