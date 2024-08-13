""" Pulse length conversion
===========================
The programmed SpinCore pulse length does not
match the actual output pulse length. This example
finds what pulse length should be fed to SpinCore
in order to get the desired β.
"""
import matplotlib.pyplot as plt
from numpy import r_
import pyspecdata as psd
from SpinCore_pp.pulse_length_conv import prog_plen

with psd.figlist_var() as fl:
    fl.next(r"Pulse Length vs. Desired $\beta$", legend=True)
    for amplitude in [1.0, 0.1]:
        plt.plot(
            r_[0:450e-6:100j],
            prog_plen(r_[0:450e-6:100j], amplitude),
            "o",
            label=f"amp={amplitude}",
            alpha=0.5,
        )
    plt.xlabel(r"desired $\beta$ / $\mathrm{s \sqrt{W}}$")
    plt.ylabel(r"required pulse lengths / $\mathrm{\mu s}$")
