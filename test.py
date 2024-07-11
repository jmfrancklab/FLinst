from Instruments import *
from pyspecdata import *
import time

# set the sine wave

with AFG() as a:
    a.reset()
    x = r_[-6:6:200j]
    a.CH1.digital_ndarray(exp(-x**2))
    print("CH1 burst set to",a.CH1.burst)
    print("now, I try to turn burst on")
    a.CH1.burst = True
    print("CH1 burst set to",a.CH1.burst)
    print("now, I turn on the output")
    a.CH1.output = True
    print("now, capture the data")
    # grab it on the scope
    with GDS_scope() as g:
        g.autoset()
        data = g.waveform(ch=2)
    print("turn off the output again")
    a.CH1.output = False

# plot the result

plot(data.human_units())

show()
