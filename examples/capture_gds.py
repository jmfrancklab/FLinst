"""
Capture the signal acquired on the GDS. and converts to analytic 
================================================================
A single capture of the signal on the GDS is converted to analytic signal,
frequency filtered and the absolute is taken to calculate the $V_{amp}$. The
final plot that is generated plots the raw data, analytic data, filtered
analytic data, and the absolute value and the caluclated $V_{amp}$ (in mV). 
This script serves two purposes in calibrating test signal generated by the
AFG: 

1. Calculating the raw output of the AFG (no attenuator assemblies). For this
step, simply set the calibrating_atten to False. Note that for the next step
you need to set the input_Vamp to the value calculated in this step.

2. Calculating the voltage ratio of the attenuator assemblies (placed between
the AFG output and the GDS). Prior to running the script the user needs to
have a rough estimate of the expected_Vamp when the attenuator assemblies are
in place. The calculated voltage ratio and dB are printed on the final
generated plot.
"""
from Instruments import GDS_scope
from pyspecdata import figlist_var
from pylab import text, gca
import numpy as np

calibrating_atten = True
expected_Vamp = float(input("What is the expected peak voltage (in units of V)?"))
if calibrating_atten:
    print("Make sure the input_Vamp here is accurate so I can calculate the right voltage ratio!")
    input_Vamp = 500e-3  # this should be calculated prior to calibrating
    #                      the attenuator assemblies
else:
    input_Vamp = expected_Vamp
filter_width = 10e6  # 10 MHz filter about the average frequency
with GDS_scope() as g:
    g.reset()
    # {{{ display settings - use channel 2
    g.CH2.disp = True
    # g.write(":CHAN1:DISP OFF")
    # g.write(":CHAN2:DISP ON")
    # g.write(":CHAN3:DISP OFF")
    # g.write(":CHAN4:DISP OFF")
    # }}}
    # {{{ voltage scale and acquisition settings
    print(expected_Vamp)
    print(type(expected_Vamp))
    g.CH2.voltscal = (
        expected_Vamp * 1.1 / 4
    )  # set to a little more than $\frac{V_{amp}}{4}$
    g.timscal(10e-9, pos=0)
    g.write(":TIM:MOD WIND")
    g.write(":CHAN2:IMP 5.0E+1")  # set impedance to 50 ohms
    g.write(":TRIG:SOUR CH2")  # set the source of the trigger to channel 2
    g.write(":TRIG:MOD AUTO")  # set trigger to auto
    g.write(":ACQ:MOD HIR")  # high vertical res.
    # }}}
    # {{{ set horizontal cursors on oscilloscope display
    g.write(":CURS:MOD HV")  # set horizontal cursors
    g.write(":CURS:SOUR CH2")  # cursors pertain to channel 2
    # }}}
    # {{{ use expected amplitude to set initial
    #     position of cursors
    g.write(":CURS:V1P " + ("%0.2e" % expected_Vamp).replace("e", "E"))
    g.write(":CURS:V2P " + ("%0.2e" % -expected_Vamp).replace("e", "E"))
    # }}}
    # {{{ grab waveform from oscilloscope
    g.write(":SING")  # capture single acquisition
    data = g.waveform(ch=2)
    data.set_units("t", "s")
    # }}}
with figlist_var() as fl:
    fl.next("Signal captured on GDS oscilloscope")
    fl.plot(data, label="raw signal")
    # {{{ convert to analytic signal
    data.ft("t", shift=True)
    data = data["t":(0, None)]
    data *= 2
    data["t", 0] *= 0.5
    data.ift("t")
    # }}}
    fl.plot(abs(data), label="analytic signal")
    # calculate average frequency of signal
    frq = data.C.phdiff("t", return_error=False).mean("t").item()
    # {{{ now, filter the signal
    data.ft("t")
    data["t" : (0, frq - filter_width / 2)] = 0
    data["t" : (frq + filter_width / 2, None)] = 0
    data.ift("t")
    # }}}
    fl.plot(data, label="filtered analytic signal")
    fl.plot(abs(data), label="abs(filtered analytic signal)")
    Vamp = abs(data["t":(1e-6, 4e-6)]).mean("t").real.item()
    if calibrating_atten:
        text(
            0.5,
            0.02,
            s=r"$V_{amp}$ = %0.6f mV, voltage ratio $\frac{V_{input}}{V_{atten}}$ = %0.8g"
            % (Vamp / 1e-3, input_Vamp / Vamp),
            transform=gca().transAxes,
        )
    else:
        text(
            0.5,
            0.02,
            s=r"$V_{amp} = %0.6f$ mV" % (Vamp / 1e-3),
            transform=gca().transAxes,
        )
