"""
Capture signal as a function of frequency on the GDS
====================================================
Signal is output at an array of frequencies (defined by the user) from a
source. The resulting signal is then captured on the GDS, frequency filtered
and stored as analytic signal. The nodename that contains the data corresponds
to the output frequency in kHz.
"""

from Instruments import AFG, GDS_scope
import numpy as np
import pyspecdata as psd
import time
import datetime
import os
import h5py

# {{{ Set filename and saving location
date = datetime.now().strftime("%y%m%d")
description = "AFG_GDS_5mVpp_fin"
filename = date + "_" + description + ".h5"
target_directory = psd.getDATADIR(exp_type="ODNP_NMR_comp/Echoes")
# }}}
# {{{ Source settings
freq_list_Hz = np.linspace(0.1e3, 50e6, 50)
Vpp = 0.005  # Desired Vₚₚ
# }}}
# {{{ GDS settings
N_capture = 3
# }}}
with AFG() as a:  # Context block that automatically handles routines to
    #               initiate communication with source, perform checks, and to
    #               close the (USB serial) connection at the end of the block
    a.reset()
    with GDS_scope() as g:
        for j, frq in enumerate(freq_list_Hz):
            a[0].output = True
            a.sin(ch=1, V=Vpp, f=frq)  # Set a sine wave output with the
            #                            desired Vₚₚ and frequency
            time.sleep(2)
            for x in range(N_capture):
                data = g.waveform(ch=2)  # Capture waveform
                # {{{ Allocate an array that's shaped like a single capture,
                #     but with an additional "capture" dimension
                if x == 0:
                    s = (
                        data.shape + ("capture", N_capture)
                    ).alloc(dtype=np.float64)
                    s["t"] = data.getaxis("t")
                    s.set_units("t", data.getunits("t"))
                # }}}
                # Store data in appropriate index
                s["capture", x] = data
                time.sleep(1)
            s.setaxis("capture", "#")  # Just set to a series of integers
            s.name("afg_%d" % frq / 1e3)  # Nodename for HDF5 file with output
            #                               frequency in kHz
            s.set_units("t", "s")
            s = s["ch", 0]
            # {{{ Convert to analytic signal (Eq. 20)
            s.ft("t", shift=True)
            s = s["t":(0, 40e6)]  # Frequency filter to save disk
            #                       space
            s *= 2
            s["t":0] *= 0.5
            s.ift("t")
            # }}}
            nodename = s.name()
            if os.path.exists(target_directory):
                with h5py.File(
                    os.path.normpath(
                        os.path.join(
                            target_directory, filename
                        )
                    )
                ) as fp:
                    if nodename in fp.keys():
                        s.name("temp_%d" % j)
                        nodename = "temp_%d" % j
                s.hdf5_write(filename, directory=target_directory)
            else:
                s.hdf5_write(filename, directory=target_directory)
