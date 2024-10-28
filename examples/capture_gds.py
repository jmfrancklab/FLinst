"This script is used in calibrating test signal generated by the AFG. After
calibrating the raw output of the AFG (with no attenuators) the user should set
the input_amp variable to the actual measured value of the raw output. The
voltage ratio of each individual attenuator assembly is then calculated by
taking the ratio of the measured voltage with the attenuator assembly in place
to the raw AFG output.
The final plot shows the acquired analytic signal, frequency filtered and 
the abs of the data is plotted for the final calculation of the $V_{amp}$.
The $V_{amp}$ in mV, the voltage ratio of the input_amp to the measured 
$V_{amp}$, and the calculated dB of the total assembly is also printed on
the final plot."
from Instruments import GDS_scope
from pyspecdata import figlist_var
from pylab import text, gca
import numpy as np

expected_Vamp = 25e-3
input_Vamp = 500.877318e-3 # needed for calculating the voltage ratio
filter_width = 10e6  # 10 MHz filter about the average
#                      frequency
with figlist_var() as fl:
    with GDS_scope() as g:
        g.reset()
        # {{{ display settings - use channel 2
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
        g.write(":CURS:V1P " + ("%0.2e" % expected_amp).replace("e", "E"))
        g.write(":CURS:V2P " + ("%0.2e" % -expected_amp).replace("e", "E"))
        # }}}
        # {{{ grab waveform from oscilloscope
        g.write(":SING")  # capture single acquisition
        data = g.waveform(ch=2)
        data.set_units("t", "s")
        # }}}
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
    text(
        0.5,
        0.05,
        s=(
            "$V_{amp} = %0.6f$ mV, voltage ratio %0.8g, dB %0.6f"
            % (Vamp / 1e-3, input_amp / Vamp, 20 * np.log10(input_amp / Vamp)),
        ),
        transform=gca().transAxes,
    )
