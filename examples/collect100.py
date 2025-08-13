# {{{ Program doc
r"""
Collect 100 noise captures
==========================
Use this program to collect 100 snapshots of noise in
about 1 min. This is to generate the Power Spectral
Density of the device/system. Set up for testing the
noise of the spectrometer is as follows (also
see AAB-LAB-2, 9/26/2018):
*Attach 50 Ohm terminator to a Tee, then connect this
to the DUT.
DUT (Tee-port) --> DPX --> LNA1 --> LNA2 --> LP --> CH1 (GDS)
Important settings on GDS are:
(1) Set to vertical scale to 50 mV/div (note for BNC cable length tests, we
have started using 10 mV/div)
(2) Set horizontal scale to 20 us/div (100 MSPS)
These parameters were determined to be ideal for capturing
noise on earliest version of spectrometer (using Probe v1.0)
Note: Set Trigger (Menu) --> Mode --> Auto

TO RUN: Type 'py collec100.py file_name' where file_name will be the string
identifier which is associated with the output file. The file will be saved
as YYMMDD_file_name.h5 following today's date.

*** want to have CH2 on as well as CH1 - both set to 50 mV

"""
# }}}
from datetime import datetime
import time
from timeit import default_timer as timer
import pyspecdata as psd
import Instruments as inst
import numpy as np
import sys

import json

acquire = False
fl = psd.figlist_var()


# print "These are the instruments available:"
# SerialInstrument(None)
# print "done printing available instruments"
#
# with SerialInstrument('GDS-3254') as s:
#    print s.respond('*idn?')
def collect(date, id_string, captures):
    capture_length = len(captures)
    start = timer()
    datalist = []
    print("about to load GDS")
    with inst.GDS_scope() as g:
        print("loaded GDS")
        for x in range(1, capture_length + 1):
            print("entering capture", x)
            ch2_waveform = g.waveform(ch=2)
            print("GOT WAVEFORM")
            data = psd.concat([ch2_waveform], "ch").reorder("t")
            if x == 1:
                channels = ((data.shape) + ("capture", capture_length)).alloc(
                    dtype=np.float64
                )
                channels.setaxis("t", data.getaxis("t")).set_units("t", "s")
                channels.setaxis("ch", data.getaxis("ch"))
            channels["capture", x - 1] = data
            time.sleep(1)
            # {{{ in case pulled from inactive channel
            if not np.isfinite(data.getaxis("t")[0]):
                j = 0
                while not np.isfinite(data.getaxis("t")[0]):
                    data.setaxis("t", datalist[j].getaxis("t"))
                    j += 1
                    if j == len(datalist):
                        raise ValueError(
                            "None of the time axes returned by the scope are"
                            " finite, which probably means no traces are"
                            " active??"
                        )
            # }}}
    s = channels
    s.labels("capture", captures)
    # {{{ convert to analytic
    s.ft("t", shift=True)
    s = s["t":(0, None)]
    s *= 2
    s["t", 0] *= 0.5
    s.ift("t")
    # }}}
    s.name("accumulated_" + date)
    
    s.hdf5_write(py
        date + "_" + id_string + ".h5",
        directory=psd.getDATADIR(exp_type="B27/noise"),
    )
    print("name of data", s.name())
    print("units should be", s.get_units("t"))
    print("shape of data", s.shape)
    return start


date = datetime.now().strftime("%y%m%d")
if len(sys.argv) < 2:
    raise ValueError("give an experiment name on the command line!")
id_string = sys.argv[1]
captures = np.linspace(1, 100, 100)

print("Starting collection...")
start = collect(date, id_string, captures)
end = timer()

print("Collection time:", (end - start), "s")