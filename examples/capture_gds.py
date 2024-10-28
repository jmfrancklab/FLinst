"""
Capture the signal acquired on the GDS. and converts to analytic 
================================================================
A single capture of the signal on the GDS is converted to analytic signal,
frequency filtered and the absolute is taken to calculate the $V_{amp}$, 
the voltage ratio and the dB of the setup based on the voltage ratio.
"""
from Instruments import GDS_scope
from pyspecdata import figlist_var
from pylab import text, gca
import numpy as np

expected_Vamp = 500e-3 # what is expected on the GDS
input_Vamp = 500e-3 # Vamp at the input of the chain
assert input_Vamp < 505e-3, (
    "That's way too high of a peak voltage! You either need an attenuator or"
    " you didn't put the input in units of V"
)
with figlist_var() as fl:
    with GDS_scope() as g:
        g.reset()
        # {{{ display settings
        g.CH1.disp = True
        g.CH2.disp = True
        g.write(":CHAN1:DISP OFF")
        g.write(":CHAN2:DISP ON")
        g.write(":CHAN3:DISP OFF")
        g.write(":CHAN4:DISP OFF")
        # }}}
        # {{{ voltage scale and acquisition settings
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
        mycursors = (expected_amp, -expected_amp)
        g.write(":CURS:V1P " + ("%0.2e" % mycursors[0]).replace("e", "E"))
        g.write(":CURS:V2P " + ("%0.2e" % mycursors[1]).replace("e", "E"))
        # }}}
        # {{{ grab waveform from oscilloscope
        datalist = []
        for j in range(1,2): # this is dumb but leave to keep flexible
            print("trying to grab data from channel",j)
            g.write(":SING")  # capture single acquisition
            datalist.append(g.waveform(ch=2))
        data = concat(datalist, "ch").reorder("t")    
        data.set_units("t", "s")
        # }}}
    fl.next("data from all channels, raw")
    fl.plot(data, label="orignal signal")
    # {{{ convert to analytic signal
    data.ft("t", shift=True)
    data = data["t":(0, None)]
    data *= 2
    data["t", 0] *= 0.5
    data.ift("t")
    # }}}
    # {{{ show the manual cursor positions
    for y in mycursors:
        axhline(y=y, color - "k", alpha = 0.5)
    # }}}
    fl.plot(abs(data), label="analytic signal")
    # calculate average frequency of signal
    ph = (data["t",1:] / data["t",:-1]).angle.sum("t").item()
    Dt = np.diff(data.getaxis("t")[r_[0, -1]]).item()
    frq = ph / Dt / 2 / np.pi
    # {{{ now, filter the signal
    data.ft("t")
    data["t" : (0, frq - 5e6)] = 0
    data["t" : (frq + 5e6, None)] = 0
    data.ift("t")
    # }}}
    fl.plot(data, label="filtered analytic signal")
    fl.plot(abs(data), label="abs(filtered analytic signal)")
    Vamp = abs(data["t":(1e-6, 4e-6)]).mean("t").real.item()
    text(
        0.5,
        0.75,
        s=(
            r"$V_{amp}$ = %0.6f mV, voltage ratio"
            r" = %0.8g, dB = %0.6f"
        )
        % (Vamp / 1e-3, input_Vamp / Vamp, 20 * np.log10(input_amp / Vamp)),
        transform=gca().transAxes,
    )
