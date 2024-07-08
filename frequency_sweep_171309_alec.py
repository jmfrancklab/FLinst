#!/c/ProgramData/Anaconda2/python
from Instruments import *
from pyspecdata import *
import time



with AFG() as a:
    a.reset()
    print(a.CH1.sweep)
    a.CH1.sweep = True
    print(a.CH1.sweep)
    a.set_sweep(start=10e6,stop=20e6)
    a.CH1.output = True

