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

from Instruments import GDS_scope, SerialInstrument
from pyspecdata import ndshape, concat, figlist_var
import SpinCore_pp
import numpy as np
from numpy import r_

parser_dict = SpinCore_pp.configuration("active.ini")
carrierFreq_MHz = parser_dict["carrierFreq_MHz"]
print(
    "I'm using the carrier frequency of %f entered into your active.ini"
    % carrierFreq_MHz
)

print("")
# CH1 of the scope is busted so we are now using CH2 and CH3 instead
input(
    "Please note I'm going to assume the control is hooked up to CH2 of the"
    " GDS and the reflection is hooked up to CH3 of the GDS... (press enter to"
    " continue)"
)

print("These are the instruments available:")
SerialInstrument(None)
print("done printing available instruments")


def grab_waveforms(g):
    # {{{ capture a "successful" waveform
    # CH1 of the scope is busted so we are now using CH2 and CH3 instead
    # to maintain the master/original copy I don't change the variable names
    ch1 = g.waveform(ch=2)
    ch2 = g.waveform(ch=3)
    success = False
    for j in range(10):
        if ch1.data.max() < 50e-3:
            ch1 = g.waveform(ch=2)
            ch2 = g.waveform(ch=3)
        else:
            success = True
    if not success:
        raise ValueError("can't seem to get a waveform that's large enough!")
    # }}}
    d = concat([ch1, ch2], "ch")
    d.reorder("ch")
    return d


d_all = None
jump_series = r_[
    -(parser_dict["tuning_offset_jumps"] // 2) : parser_dict[
        "tuning_offset_jumps"
    ]
    // 2
    + 1
]
print("jump_series", jump_series)
jump_series = jump_series / parser_dict["tuning_offset_jumps"]
print("jump_series", jump_series)
with GDS_scope() as g:
    g.reset()
    g.CH2.disp = True
    g.CH3.disp = True
    g.write(":CHAN1:DISP OFF")
    g.write(":CHAN2:DISP ON")
    g.write(":CHAN3:DISP ON")
    g.write(":CHAN4:DISP OFF")
    g.CH2.voltscal = 100e-3
    g.CH3.voltscal = 50e-3
    g.timscal(500e-9, pos=2.325e-6)
    g.write(":CHAN2:IMP 5.0E+1")
    g.write(":CHAN3:IMP 5.0E+1")
    g.write(":TRIG:SOUR CH2")
    g.write(":TRIG:MOD NORMAL")
    g.write(":TRIG:HLEV 7.5E-2")
    freq_series = (
        carrierFreq_MHz + parser_dict["tuning_offset_jump_MHz"] * jump_series
    )
    center_idx = np.where(jump_series == 0)[0].item()
    freq_series = freq_series[
        r_[center_idx, 0:center_idx, center_idx + 1 : len(freq_series)]
    ]
    for j, thiscarrier in enumerate(freq_series):
        print("about to change frequency to", thiscarrier)
        if j == 0:
            print(
                "***this is the center frequency -- adjust while this "
                "waveform is up.  Do not touch the tuning during "
                "collection of the other waveforms!***"
            )
        SpinCore_pp.tune(thiscarrier)
        print("changed frequency")
        print("about to grab the waveform")
        d = grab_waveforms(g)
        print("grabbed the waveform")
        SpinCore_pp.stopBoard()
        print("I just stopped the SpinCore")
        d_orig = d.C
        if d_all is None:
            d_all = (d.shape + ("offset", len(jump_series))).alloc(
                dtype="float"
            )
            d_all["offset", j] = d
            d_all["t"] = d["t"]
            d_all["ch"] = d["ch"]
            d_all.setaxis("offset", (freq_series - carrierFreq_MHz) / 0.001)
        else:
            d_all["offset", j] = d

d_all.sort("offset")
# {{{ analytic signal conversion
d_all.ft("t", shift=True)
d_all["t" : (carrierFreq_MHz * 2.3e6, None)] = 0
d_all["t" : (None, 0)] = 0
d_all *= 2
d_all.ift("t")
flat_slice = d_all["offset":0][
    "t" : (4.5e-6, 6.5e-6)
]  # will always be the same since the scope settings are the same
# }}}

with figlist_var() as fl:
    d_all["ch", 1] *= (
        2  # just empirically, I need to scale up the reflection by a
    )
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
            label=(
                (f"carrier: {carrierFreq_MHz:0.3f} MHz\n" if j == 0 else "")
                + f"offset {d_all['offset'][j]:#0.2g} kHz"
            ),
        )
flat_slice.run(abs).mean("t")
print(
    "reflection ratio calculated from ratio of %f to %f mV"
    % (
        abs(flat_slice["ch", 1]).item() / 1e-3,
        abs(flat_slice["ch", 0]).item() / 1e-3,
    )
)
ratio = (abs(flat_slice["ch", 1] / flat_slice["ch", 0])).item()
tuning_dB = np.log10(ratio) * 20
if tuning_dB < -25:
    print(
        "congratulations! you have achieved a reflection ratio of %0.1f dB"
        % tuning_dB
    )
else:
    print(
        "Sorry! Your reflection ratio is %0.1f dB.  TRY HARDER!!!!" % tuning_dB
    )
# this is put here in case it used the default
parser_dict["carrierFreq_MHz"] = carrierFreq_MHz
parser_dict.write()
