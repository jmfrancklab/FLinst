from pyspecdata import find_file, DCCT
import matplotlib.pyplot as plt
from numpy import r_
import matplotlib as mpl
import numpy as np
import pyspecProcScripts as prscr
import pyspecdata as psd

apply_apod = False
center_echo = False
slicing = True
lims = (-10.7e3, -6.61e3)


def my_preproc(x):
    if center_echo:
        x["t2"] -= x.get_prop("acq_params")["tau_us"] * 1e-6
    x.setaxis(
        "ph1", r_[0:4] / 4
    )  # this appears to be set, but not correctly, which is bad
    x.ft("ph1")
    x.run(np.conj)  # so that offset goes up when field goes up
    x.ft("t2", shift=True)
    x.set_units("indirect", "G")  # this should have been done when saving!
    x.rename("indirect", "field")
    return x


my_lookup = dict(prscr.lookup_table)

this_expno = "shim_y_0"
d = find_file(
    f"260324_hydroxytempo_{this_expno}.*h5",
    exp_type="ODNP_NMR_comp/Echoes",
    expno=this_expno,  # when I leave out expno, it gives me an error that
    # lists all the nodes
    lookup=my_lookup,
)
nscans = d.get_prop("acq_params")["nScans"]
if nscans > 1:
    d = d.mean("nScans")
d.ift("t2")
fig = plt.figure(figsize=(6, 4))
gs = mpl.gridspec.GridSpec(1, 2, left=0.05, right=0.95)
d = d[
    "t2" : (None, 6.5e-3 - center_echo * 3.5e-3)
]  # just slice all the data since we're not filtering
DCCT(
    d,
    fig=fig,
    title=("Y current vs. Signal"),
    bbox=gs[0, 0],
)
d = d["t2", 1:]  # remove first point, which has ringdown
if apply_apod:
    d *= np.exp(
        -abs(d.fromaxis("t2")) / 0.5e-3
    )  # apply a filter to clean up signal
d.ft("t2")
DCCT(
    d,
    fig=fig,
    title=("Y current vs. Signal"),
    interpolation="nearest",
    bbox=gs[0, 1],
)
fig2 = plt.figure()
if slicing:
    d = d["t2":lims]
DCCT(
    d,
    fig=fig2,
    title=("Y current vs. Signal, sliced"),
    interpolation="nearest",
    bbox=gs[0, 0],
)
fig3 = plt.figure()
d = prscr.select_pathway(d, d.get_prop("coherence_pathway"))
d.ift("t2")
psd.image(d, ax=fig3.add_subplot(gs[0, 0]))
psd.plot(
    d.C.run(lambda x: abs(x) ** 2).integrate("t2"),
    "o-",
    ax=fig3.add_subplot(gs[0, 1]),
)
d.ft("t2")
d = abs(d)
d.pcolor(ax=fig2.add_subplot(gs[0, 1]))
d.run(lambda x: x**2).integrate("t2")
fig4 = plt.figure()
psd.plot(d, "o")
fig4.suptitle("Energy vs. Y current")
fig4.axes[0].set_ylabel("Energy / a.u.")
plt.show()
