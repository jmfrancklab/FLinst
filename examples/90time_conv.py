""" Pulse length conversion
===========================
The programmed SpinCore pulse length does not
match the actual output pulse length. This example
finds what pulse length should be fed to SpinCore
in order to get the desired beta.
"""
import matplotlib.pyplot as plt
from numpy import r_
import pyspecdata as psd
from SpinCore_pp.pulse_length_conv import prog_plen

# the following choice fails dramatically with the old code
desired_beta = r_[10:150:50j]
prog_plen = prog_plen(desired_beta)
with psd.figlist_var() as fl:
    fl.next(r"desired $\beta$ vs pulse length")
    plt.plot(desired_beta, prog_plen, "o")
    plt.xlabel(r"desired $\beta$ / $\mathrm{\mu s \sqrt{W}}$")
    plt.ylabel(r"required pulse lengths / $\mathrm{\mu s}$")
    plt.title(r"Pulse Length vs. Desired $\beta$")
