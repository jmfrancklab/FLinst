from pyspecdata import figlist_var, nddata
from numpy import r_
import numpy as np
import SpinCore_pp
import pyspecProcScripts as prscr


def fwhm(trace):
    x = trace.getaxis("t2")
    y = abs(trace.data)
    peak_idx = y.argmax()
    peak_height = y[peak_idx]
    half_height = peak_height / 2.0
    left_idx = peak_idx
    while left_idx > 0 and y[left_idx] >= half_height:
        left_idx -= 1
    right_idx = peak_idx
    while right_idx < len(y) - 1 and y[right_idx] >= half_height:
        right_idx += 1
    if left_idx == peak_idx:
        left_cross = x[peak_idx]
    else:
        left_cross = np.interp(
            half_height,
            [y[left_idx], y[left_idx + 1]],
            [x[left_idx], x[left_idx + 1]],
        )
    if right_idx == peak_idx:
        right_cross = x[peak_idx]
    else:
        right_cross = np.interp(
            half_height,
            [y[right_idx], y[right_idx - 1]],
            [x[right_idx], x[right_idx - 1]],
        )
    return x[peak_idx], left_cross, right_cross, right_cross - left_cross


def integrate_energy(trace, left_lim, right_lim):
    x = trace.getaxis("t2")
    y = abs(trace.data) ** 2
    mask = np.logical_and(x >= left_lim, x <= right_lim)
    if not mask.any():
        return 0.0
    return np.trapz(y[mask], x[mask])


filter_timeconst = 10e-3

# {{{ choose file manually
thisfile, exptype, nodename = (
    "260107_hydroxytempo_ODNP_1.h5",
    "ODNP_NMR_comp/Echoes",
    "shim_y",
)
# }}}

with figlist_var() as fl:
    config_dict = SpinCore_pp.configuration("active.ini")
    data = find_file(
        thisfile,
        exp_type=exptype,
        expno=nodename,
        lookup=prscr.lookup_table,
    )
    assert data.get_units("t2") is not None, (
        "bad data file! units of s for t2 should be stored in nddata!"
    )
    for_plot = data.C
    if "nScans" in for_plot.dimlabels:
        for_plot.mean("nScans")
    for_plot.ft("ph1", unitary=True)
    signal = for_plot["ph1", 1].C
    signal.ift("t2")
    signal *= np.exp(
        -abs(signal.fromaxis("t2") - config_dict["tau_us"] * 1e-6)
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
    signal.ft("t2", shift=True)

    linewidth = np.zeros(len(signal.getaxis("y_current")))
    peak_position = np.zeros(len(signal.getaxis("y_current")))
    left_edge = np.zeros(len(signal.getaxis("y_current")))
    right_edge = np.zeros(len(signal.getaxis("y_current")))
    for j in range(len(signal.getaxis("y_current"))):
        (
            peak_position[j],
            left_edge[j],
            right_edge[j],
            linewidth[j],
        ) = fwhm(signal["y_current", j])

    widest_idx = linewidth.argmax()
    left_offset = left_edge[widest_idx] - peak_position[widest_idx]
    right_offset = right_edge[widest_idx] - peak_position[widest_idx]
    energy = np.zeros(len(signal.getaxis("y_current")))
    for j in range(len(signal.getaxis("y_current"))):
        energy[j] = integrate_energy(
            signal["y_current", j],
            peak_position[j] + left_offset,
            peak_position[j] + right_offset,
        )

    best_idx = energy.argmax()
    print(
        "best Y current based on energy is",
        signal.getaxis("y_current")[best_idx],
        "A",
    )

    signal_for_plot = abs(signal).C
    signal_for_plot.setaxis("t2", lambda x: x / 1e3).set_units("t2", "kHz")
    energy_nd = nddata(energy, "y_current")
    energy_nd.setaxis("y_current", signal.getaxis("y_current")).set_units(
        "y_current", "A"
    )
    linewidth_nd = nddata(linewidth / 1e3, "y_current")
    linewidth_nd.setaxis("y_current", signal.getaxis("y_current")).set_units(
        "y_current", "A"
    )

    fl.next("Raw DCCT")
    fl.image(signal_for_plot)
    fl.next("Energy and FWHM linewidth vs Y current", legend=True)
    fl.plot(energy_nd, "o-", label="energy")
    fl.plot(linewidth_nd, "s-", label="FWHM / kHz")
