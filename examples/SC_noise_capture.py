import pyspecdata as ps
import numpy as np
from numpy import r_
import SpinCore_pp as sc
from datetime import datetime

# {{{ experimental parameters that should be checked
description = "terminated_RX"
SW_kHz = 75000
carrierFreq_MHz = 20
adcOffset = 38
nScans = 100
# }}}
# {{{ set filename
date = datetime.now().strftime("%y%m%d")
output_name = date + "_" + description + "_" + str(SW_kHz) + "kHz"
# }}}
# {{{ SpinCore settings - these don't change
tx_phases = r_[0.0, 90.0, 180.0, 270.0]
nPoints = 1024 * 2
acq_time = nPoints / SW_kHz + 1.0
tau = 10 + acq_time * 1e3 * (1.0 / 8.0)
data_length = 2 * nPoints * 1 * 1
# }}}
# {{{ Acquire data
for x in range(nScans):
    # {{{ configure SpinCore
    sc.configureTX(
        adcOffset,
        carrierFreq_MHz,
        tx_phases,
        1.0,
        nPoints,
    )
    acq_time = sc.configureRX(SW_kHz, nPoints, 1, 1, 1)
    sc.init_ppg()
    # }}}
    # {{{ ppg to generate the SpinCore data
    sc.load(
        [
            ("marker", "start", 1),
            ("phase_reset", 1),
            ("delay", tau),
            ("acquire", acq_time),
            ("delay", 1e4),
            ("jumpto", "start"),
        ]
    )
    # }}}
    sc.stop_ppg()
    sc.runBoard()
    # {{{grab data for the single capture as a complex value
    raw_data = (
        sc.getData(data_length, nPoints, 1, 1).astype(float).view(complex)
    )
    # }}}
    # {{{ if this is the first scan, then allocate an array
    #     to drop the data into, and assign the axis
    #     coordinates, etc.
    if x == 0:
        time_axis = np.linspace(0.0, acq_time * 1e-3, raw_data.size)
        data = (
            ps.ndshape(
                [raw_data.size, nScans],
                ["t", "nScans"],
            )
            .alloc(dtype=np.complex128)
            .setaxis("t", time_axis)
            .set_units("t", "s")
            .setaxis("nScans", r_[0:nScans])
            .name("signal")
        )
    # }}}
    data["nScans", x] = raw_data  # drop the data into appropriate index
    sc.stopBoard()
# }}}
data.set_prop("postproc_type", "spincore_general")
data.hdf5_write(
    output_name + ".h5",
    directory=ps.getDATADIR(exp_type="ODNP_NMR_comp/noise_tests"),
)  # save data as h5 file
