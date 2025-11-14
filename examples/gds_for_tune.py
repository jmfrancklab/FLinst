"""
GDS for tune
============

A command line utility for tuning using the SpinCore as a pulse generator and
the GDS scope to observe the reflection.
(GDS scope must be hooked up to an appropriate splitter configuration).

Takes one or two command line arguments:

1.      *Either* a field in G or a frequency in *MHz* --> note that these will
        be very different types of numbers (thousands vs. tens respectively),
        so the program can use that to determine.
2.      If supplied, this overrides the default effective γ value.
"""

from pyspecdata import ndshape, figlist_var
import numpy as np
from Instruments.gds_tune import (
    load_active_config,
    list_serial_instruments,
    run_frequency_sweep,
    reflection_metrics,
    jump_series_default,
)

parser_dict = load_active_config()
print(
    "I'm using the carrier frequency of %f entered into your active.ini"
    % parser_dict["carrierFreq_MHz"]
)

print("")
# CH1 of the scope is busted so we are now using CH2 and CH3 instead
input(
    "Please note I'm going to assume the control is hooked up to CH2 of the"
    " GDS and the reflection is hooked up to CH3 of the GDS... (press enter to"
    " continue)"
)

print("These are the instruments available:")
list_serial_instruments()
print("done printing available instruments")

d_all, flat_slice = run_frequency_sweep(parser_dict, jump_series_default)

with figlist_var() as fl:
    d_all[
        "ch", 1
    ] *= 2  # just empirically, I need to scale up the reflection by a
    #         factor of 2 in order to get it to be the right size
    try_again = False
    while try_again:
        data_name = "capture1"
        d_all["offset":0].name(data_name)
        try:
            d_all["offset":0].hdf5_write("201020_sol_probe_1.h5")
            try_again = False
        except Exception as e:
            print(e)
            print("name taken, trying again...")
            try_again = True
    print(("name of data", d_all["offset":0].name()))
    print(("units should be", d_all["offset":0].get_units("t")))
    print(("shape of data", ndshape(d_all["offset":0])))
    fl.next("waveforms")
    fl.plot(d_all["offset":0], alpha=0.1)
    fl.plot(abs(d_all["offset":0]), alpha=0.5, linewidth=3)
    fl.plot(abs(flat_slice), alpha=0.5, linewidth=3)
    fl.next("frequency sweep", label=True)
    for j in range(d_all.shape["offset"]):
        fl.plot(
            abs(d_all["ch", 1]["offset", j]),
            label=f"{parser_dict['carrierFreq_MHz']} {d_all['offset'][j]:+0.3f} MHz",
        )
flat_slice.run(abs).mean("t")
ratio, tuning_dB = reflection_metrics(flat_slice)
print(
    "reflection ratio calculated from ratio of %f to %f mV"
    % (abs(flat_slice["ch", 1]).item() / 1e-3, abs(flat_slice["ch", 0]).item() / 1e-3)
)
if tuning_dB < -25:
    print(
        "congratulations! you have achieved a reflection ratio of %0.1f dB"
        % tuning_dB
    )
else:
    print(
        "Sorry! Your reflection ratio is %0.1f dB.  TRY HARDER!!!!" % tuning_dB
    )
