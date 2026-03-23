from pyspecdata import figlist_var, nddata, find_file
from numpy import r_
import numpy as np
import matplotlib.pyplot as plt
import pyspecProcScripts as prscr
from pyspecProcScripts.load_data import proc_spincore_generalproc_v1


def integrate_energy(trace, left_lim, right_lim):
    x = trace.getaxis("t2")
    y = abs(trace.data) ** 2
    mask = np.logical_and(x >= left_lim, x <= right_lim)
    if not mask.any():
        return 0.0
    return np.trapezoid(y[mask], x[mask])


filter_timeconst = 4e-3
slicing = True
my_lookup = dict(prscr.lookup_table)
my_lookup["spincore_SE_v2"] = proc_spincore_generalproc_v1

# {{{ choose file manually
thisfile, exptype, nodename = (
    "260319_hydroxytempo_shim_y.h5",
    "ODNP_NMR_comp/Echoes",
    "shim_y_1",
)
# }}}

with figlist_var() as fl:
    data = find_file(
        thisfile,
        exp_type=exptype,
        expno=nodename,
        lookup=my_lookup,
    )
    assert data.get_units("t2") is not None, (
        "bad data file! units of s for t2 should be stored in nddata!"
    )
    for_plot = data.C
    if "nScans" in for_plot.dimlabels:
        for_plot.mean("nScans")
    if not for_plot.get_ft_prop("ph1"):
        for_plot.ft("ph1", unitary=True)
    signal = for_plot["ph1", 1].C
    signal.ift("t2")
    acq_params = signal.get_prop("acq_params")
    signal *= np.exp(
        -abs(signal.fromaxis("t2") - acq_params["tau_us"] * 1e-6)
        / filter_timeconst
    )
    for j in range(len(signal.getaxis("y_current"))):
        center_idx = (
            abs(signal["y_current", j]).argmax("t2", raw_index=True).data
        )
        this_fid = np.array(signal["y_current", j].data, copy=True)
        this_fid[:center_idx] = 0
        this_fid[center_idx] *= 0.5
        phase_ref = this_fid[center_idx]
        if abs(phase_ref) > 0:
            this_fid /= phase_ref / abs(phase_ref)
        signal["y_current", j].data[:] = this_fid
    signal.ft("t2", shift=False)
    if slicing:
        signal = signal["t2" : (-8e3, 8e3)]
    energy = np.zeros(len(signal.getaxis("y_current")))
    left_lim, right_lim = signal.getaxis("t2")[r_[0, -1]]
    for j in range(len(signal.getaxis("y_current"))):
        energy[j] = integrate_energy(
            signal["y_current", j],
            left_lim,
            right_lim,
        )

    best_idx = energy.argmax()
    print(
        "best Y current based on energy is",
        signal.getaxis("y_current")[best_idx],
        "A",
    )

    signal_for_plot = abs(signal).C
    signal_for_plot.setaxis("t2", lambda x: x / 1e3).set_units("t2", "kHz")
    signal_for_plot.setaxis(
        "y_current", signal.getaxis("y_current")
    ).set_units("y_current", "A")
    energy_nd = nddata(energy, "y_current")
    energy_nd.setaxis("y_current", signal.getaxis("y_current")).set_units(
        "y_current", "A"
    )

    fl.next("Raw DCCT")
    ax_dcct = plt.gca()
    fl.image(signal_for_plot, ax=ax_dcct, human_units=False)
    y_current_vals = signal.getaxis("y_current")
    y_tick_idx = np.linspace(
        0, len(y_current_vals) - 1, min(6, len(y_current_vals)), dtype=int
    )
    ax_dcct.set_yticks(y_tick_idx)
    ax_dcct.set_yticklabels([f"{y_current_vals[j]:0.2f}" for j in y_tick_idx])
    ax_dcct.set_ylabel("Y current / A")

    fl.next("Energy vs Y current")
    ax_energy = plt.gca()
    fl.plot(energy_nd, "o-", ax=ax_energy, label="energy")
    ax_energy.set_ylabel("energy")
    ax_energy.legend(loc="upper left")
