import pyspecdata as ps
import numpy as np
from numpy import r_
import SpinCore_pp as sc
from datetime import datetime

# {{{ Set filename, SW and $\nu_{RX,LO}$
date = datetime.now().strftime("%y%m%d")
description = "SpinCore_noise"
SW_kHz = 75000
output_name = (
    date + "_" + description + "_" + str(SW_kHz) + "kHz"
)
carrierFreq_MHz = 20  # $\nu_{RX,LO}$
# }}}
# {{{ SpinCore settings
adcOffset = 38
tx_phases = r_[0.0, 90.0, 180.0, 270.0]
nScans = 100
nPoints = 1024 * 2
# }}}
# {{{ Acquire data
for x in range(nScans):
    # {{{ Configure SpinCore
    sc.configureTX(
        adcOffset,
        carrierFreq_MHz,
        tx_phases,
        1.0,
        nPoints,
    )
    acq_time_ms = sc.configureRX(
        SW_kHz,
        nPoints,
        1,
        1,  # Assume nEchoes = 1
        1,  # Assume nPhaseSteps = 1
    )
    sc.init_ppg()
    # }}}
    # {{{ Pulse program to generate the SpinCore data
    sc.load(
        [
            ("marker", "start", 1),
            ("phase_reset", 1),
            ("delay", 0.5e3),  # Short delay (ms)
            ("acquire", acq_time_ms),
            ("delay", 1e4),  # Short delay (μs)
            ("jumpto", "start"),
        ]
    )
    # }}}
    sc.stop_ppg()
    sc.runBoard()
    # Grab data for the single capture as complex values
    raw_data = (
        sc.getData((2 * nPoints * 1 * 1), nPoints, 1, 1)
        .astype(float)
        .view(complex)
    )  # Assume nEchoes and nPhaseSteps = 1
    # {{{ Allocate an array that's shaped like a single
    #     capture, but with an additional "nScans" dimension
    #     to drop data into and assign the axis coordinates,
    #     etc.
    if x == 0:
        time_axis = np.linspace(
            0.0, acq_time_ms * 1e-3, raw_data.size
        )
        data = (
            ps.ndshape(
                [raw_data.size, nScans], ["t", "nScans"]
            )
            .alloc(dtype=np.complex128)
            .setaxis("t", time_axis)
            .set_units("t", "s")
            .setaxis("nScans", r_[0:nScans])
            .name("noise_capture")
        )
    # }}}
    # Store data for the capture in the appropriate index
    data["nScans", x] = raw_data
    sc.stopBoard()
# }}}
data.hdf5_write(
    output_name + ".h5",
    directory=ps.getDATADIR(
        exp_type="ODNP_NMR_comp/noise_tests"
    ),
)
