"""
Processing the Captured Tuning Curve
====================================

Takes the npy file of the captured tuning curve at different
zoom levels and plots them on the same plot, allowing us to 
look at any drift or discrepancies of the tuning curve.
"""
from pyspecdata import *
import matplotlib.pyplot as plt

filename = search_filename(
    "211116_120mM_TEMPOL.npz", exp_type="francklab_esr/alex", unique=True
)
data = np.load(filename)
zooms = ["zoom1", "zoom2", "zoom4", "zoom8"]
nd_data = {}
with figlist_var() as fl:
    fl.next("tuning curve", legend=True)
    for thisname in zooms:
        zoom_data = data["%s" % thisname].squeeze()
        zoom_data_nd = nddata(zoom_data[0], "frequency")
        zoom_data_nd.setaxis("frequency", zoom_data[1])
        zoom_data_nd.name(thisname)
        nd_data["%s" % thisname] = zoom_data_nd
        fl.plot(zoom_data_nd, alpha=0.5)
