"""
Capture signal as a function of frequency on the SpinCore
=========================================================
Signal is outpupt at an array of frequencies (defined by the user) from a
source. The SpinCore then captures a user defined number of scans of the
resulting signal. The nodename that contains the data corresponds to the output
frequency in kHz.
"""
from Instruments import AFG
from pyspecdata import r_, ndshape
import time
from numpy import linspace, complex128
import SpinCore_pp as sc
from datetime import datetime

# {{{ Set filename, SW and ν_{RX,LO}
date = datetime.now().strftime("%y%m%d")
description = "3p9kHz_filter"
SW_kHz = 3.9
output_name = date + "_" + description
carrierFreq_MHz = 14.9  # ν_{RX,LO}
# }}}
# {{{ Source settings
freq_array = linspace(14.8766e6, 14.9234e6, 300)
Vpp = 0.01  # Desired Vₚₚ
# }}}
# {{{ Spincore settings
adcOffset = 42
tx_phases = r_[0.0, 90.0, 180.0, 270.0]
nScans = 25
nPoints = 1024 * 2
# }}}
with AFG() as a:  # Context block that automatically handles routines to
    #               initiate communication with source, perform checks, and to
    #               close the (USB serial) connection at the end of the block
    a.reset()
    for j, frq in enumerate(freq_array):
        a[0].output = True
        a.sin(ch=1, V=Vpp, f=frq)  # Set a sine wave output with the desired
        #                            Vₚₚ and frequency
        time.sleep(2)
        # {{{ Acquire data
        for k in range(nScans):
            # {{{ Configure SpinCore receiver
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
            # {{{ Pulse program to generate the SpinCore Data
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
            # Grab data for the single capture as a complex value
            raw_data = (
                sc.getData((2 * nPoints * 1 * 1), nPoints, 1, 1)
                .astype(float)
                .view(complex)
            )  # Assume nEchoes and nPhaseSteps = 1
            # {{{ Allocate an array that's shaped like a single capture, but
            #     with an additional "nScans" dimension to drop data into and
            #     assign the axis coordinates, etc.
            if k == 0:
                time_axis = linspace(0.0, acq_time_ms * 1e-3, raw_data.size)
                # note that earlier versions of this code stored the data in
                # separate nodes, but that's a silly strategy -- especially
                # since OneDrive will see each new node write as a new
                # "version" of the file.  So, we use a new dimension instead.
                data = (
                    ndshape(
                        [raw_data.size, nScans, len(freq_array)],
                        ["t", "nScans", "afg_frq"],
                    )
                    .alloc(dtype=complex128)
                    .setaxis("t", time_axis)
                    .setaxis("afg_frq", freq_array)
                    .set_units("t", "s")
                    .set_units("afg_frq", "Hz")
                    .setaxis("nScans", r_[0:nScans])
                    .name("afg_data")
                )
            # }}}
            # Store data for capture in appropriate index
            data["nScans", k, "afg_frq", j] = raw_data
            sc.stopBoard()
        data.set_prop("afg_frq_kHz", frq / 1e3)  # Store the output frequency
        #                                          in units of kHz
        nodename = data.name()
        data.hdf5_write(
            output_name + ".h5",
            directory="ODNP_NMR_comp/noise_tests",
        )
