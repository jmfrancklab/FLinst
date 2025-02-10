# {{{ Program doc
r"""
Collect noise captures on oscilloscope
======================================
Use this program to collect snapshots of noise in minutes. This is to generate
the Power Spectral Density of the device/system as acquired on the
oscilloscope.  Set up for testing the noise of the spectrometer is as follows
(also see
AAB-LAB-2, 9/26/2018):
DUT (Tee-port) --> receiver chain --> CH1 (GDS)
Important settings on GDS are:
(1) Minimize the vertical scale to without clipping any signal (we have started
using 10 mV/div for a typical low noise set up)
(2) Set horizontal scale to 20 us/div (100 MSPS)
These parameters were determined to be ideal for capturing
noise on earliest version of spectrometer (using Probe v1.0)
Note: Set Trigger (Menu) --> Mode --> Auto

TO RUN: Type 'py collect_GDS.py file_name N_capture' where file_name will be
the string identifier which is associated with the output file and N_capture is
the desired number of captures. The file will be saved as YYMMDD_file_name.h5
following today's date.
"""
# }}}
from datetime import datetime
import time
from timeit import default_timer as timer
import pyspecdata as psd
from Instruments import GDS_scope
import numpy as np
import sys

acquire = False
fl = psd.figlist_var()


def collect(file_string, N_capture):
    """Function that acquires a number of captures of signal and converts to
    analytic signal prior to saving as an HDF5 file.

    Parameters
    ==========
    file_string: str
        Name of file to save data to.
    N_capture: int
        Number of captures to acquire.
    """

    start = timer()
    with GDS_scope() as g:
        for x in range(N_capture):
            data = g.waveform(ch=2)
            # {{{ Allocate an array that's shaped like a single capture, but
            #     with an additional "capture" dimension
            if x == 0:
                s = (
                    data.shape + ("capture", N_capture)
                ).alloc(dtype=np.float64)
                s["t"] = data.getaxis("t").set_units("t", data.get_units("t"))
            # }}}
            # Store data in appropriate index
            s["capture", x] = data
            time.sleep(1)
    s.setaxis("capture", "#")  # Just set to a series of integers
    date = datetime.now().strftime("%y%m%d")
    s.name("accumulated_" + date)
    # {{{ convert to analytic
    s.ft("t", shift=True)
    s = s["t":(0, 40e6)]  # Frequency filter to save disk space
    s *= 2
    s["t", 0] *= 0.5
    s.ift("t")
    # }}}
    s.hdf5_write(
        date + "_" + file_string + ".h5",
        directory=psd.getDATADIR(exp_type="ODNP_NMR_comp/noise_tests"),
    )
    return start

write
def raise_arg_error():
    raise ValueError(
        """Call like this: 
    python collect100.py file_string N_capture (where file_string is added to
    the filename along with the date, and N_capture is the number of captures
    you want to acquire)"""
    )


if __name__ == "__main__":
    if len(sys.argv) < 3:
        raise_arg_error()
    # The filename will be the date followed by the first argument in the
    # terminal
    file_string, N_capture = sys.argv[1:3]
    try:
        N_capture = int(N_capture)
    except Exception:
        raise_arg_error()

print("Starting collection...")
start = collect(file_string, N_capture)  # Acquire data
end = timer()

print("Collection time:", (end - start), "s")
