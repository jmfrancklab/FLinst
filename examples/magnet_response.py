from Instruments import genesys
from numpy import r_
from pyspecdata import ndshape
r_[r_[0:21.7:50j],
    r_[21.7:0:50j]]
current_log = ndshape([('t',100)])
with genesys() as g:
    g.V_limit = 25.0
    g.I_limit = 0.01
    g.output = True
    g.I_meas