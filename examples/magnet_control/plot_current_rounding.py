from pathlib import Path
import os
import re
import matplotlib.pyplot as plt
import pyspecdata as psd
import numpy as np
import sympy as sp
from lmfit import fit_report

# {{{ changeable parameters
# We skip the first 3 points since the magnet has not warmed up
POINTS_TO_SKIP_FIRST_FIGURE = 3
pull_old_file = True
# }}}
# {{{ changeable parameters to describe the staircase function
# TODO ☐: these values don't give a good guess for the staircase fit --
#         probably better to base off of the data
Del_I = 0.003115
step = 0.00005
offset = 0.0016
c_1 = 178.66095
c_0 = 3393 - c_1 * 21
do_fit = True
# }}}

# am I pulling previously stored data, or something I just ran
if pull_old_file:
    datafile = Path(
        psd.search_filename(
            re.escape("260428_Irounding.txt"),
            exp_type="b27/Irounding",
            unique=True,
            print_result=False,
        )
    )
else:
    datafile = Path("Irounding.txt")
if not os.path.exists(datafile):
    raise IOError(
        f"{datafile} not found. Check that you've set the "
        "pull_old_file flag as you intend"
    )
# {{{ loading directly into an nddata is a much better choice
raw_columns = np.genfromtxt(datafile, names=True)
# following gives ('I_desiredA', 'I_act_reqA', 'I_measA', 'B0G', 'I_act_setB0')
# print(raw_columns.dtype.names);quit()
hall_probe_data = (
    psd.nddata(raw_columns["B0G"], ["I_desired"])
    .setaxis("I_desired", raw_columns["I_desiredA"])
    .set_units("G")
    .set_units("I_desired", "A")
)
hall_probe_data = hall_probe_data["I_desired", POINTS_TO_SKIP_FIRST_FIGURE:]
# }}}
coeff = hall_probe_data.polyfit("I_desired", order=1)
intercept, slope = coeff
# {{{ use a convolution transform to smooth the staircase model just enough
#     that the optimizer sees a response as the step locations move between
#     sampled x points
staircase_smoothing_width = (
    0.5 * np.abs(np.diff(hall_probe_data["I_desired"])).mean()
)
# TODO ☐: this gives several different values -- why?? Something is
#         wrong with the data. → see todos in the acquisition script.
print(np.unique(np.abs(np.diff(hall_probe_data["I_desired"]))))
# }}}
# {{{ fit the staircase response using lmfitdata, seeding from the current
#     hand-tuned parameters and smoothing the discontinuities with a
#     transform
I_desired, Del_I_symbol, offset_symbol, c_1_symbol, c_0_symbol = sp.symbols(
    "I_desired Del_I offset c_1 c_0", real=True
)
staircase_fit = psd.lmfitdata(hall_probe_data)


@staircase_fit.define_residual_transform
def smooth_staircase_response(d):
    original_axis = d.getaxis("I_desired").copy()
    # TODO ☐: it should not need to do this because the axis of
    #         requested currents should be evenly spaced!!!  This leads
    #         to the other problems!
    d.setaxis(
        "I_desired",
        np.linspace(original_axis[0], original_axis[-1], len(original_axis)),
    )
    # TODO ☐: (for JF) I have fold-back from the conv, and need to fill
    #         to both sides with values equal to endpoints before conv.
    #         The following is required for convolve, but should not be.
    d.ft("I_desired", shift=True).ift("I_desired")
    d.convolve("I_desired", staircase_smoothing_width, enforce_causality=False)
    d.setaxis("I_desired", original_axis)
    return d.real


staircase_fit.functional_form = (
    c_1_symbol
    * Del_I_symbol
    * sp.floor((I_desired - offset_symbol) / Del_I_symbol + sp.Rational(1, 2))
    + c_0_symbol
)
staircase_fit.set_guess(
    Del_I=dict(value=Del_I, min=step, max=2 * Del_I),
    offset={"value": offset, "min": -2 * offset, "max": 2 * offset},
    c_1={"value": c_1, "min": 0.5 * c_1, "max": 2 * c_1},
    c_0={"value": c_0, "min": -2 * c_0, "max": 2 * c_0},
)
staircase_fit.set_to_guess()
# TODO ☐: (for JF) eval here seems to give a complex number, unless I add real
#         to the transform.  Why?  With all real variables, the lambda function
#         should eval to real.  I checked that both the data and the axis
#         coords are float64, NOT complex!
staircase_guess, staircase_guess_label = (
    staircase_fit.eval(500).name("Hall Probe Reading"),
    "Initial staircase guess: "
    rf"$\Delta I={Del_I:.8g},\ x_0={offset:.8g},\ w={staircase_smoothing_width:.8g}$",
)
# The model is still floor-based, so let lmfit estimate derivatives
# numerically rather than relying on a symbolic Jacobian.
if do_fit:
    staircase_fit.fit(use_jacobian=False)
    print(fit_report(staircase_fit.fit_output))
# }}}

fig, (ax_fit, ax_resid) = plt.subplots(
    2,
    1,
    sharex=True,
    figsize=(7.5, 8.0),
    gridspec_kw={"height_ratios": [2.4, 1.2]},
)

psd.plot(
    hall_probe_data,
    "o",
    ms=4,
    label="Hall Probe Reading",
    alpha=0.5,
    ax=ax_fit,
)
psd.plot(
    hall_probe_data.eval_poly(coeff, "I_desired", npts=500),
    label=(
        "Linear fit: " rf"$B_0 = ({slope:.10g})\,I_{{req}} {intercept:+.10g}$"
    ),
    alpha=0.5,
    ax=ax_fit,
)
psd.plot(
    staircase_guess,
    "--",
    label=staircase_guess_label,
    alpha=0.5,
    ax=ax_fit,
)
if do_fit:
    psd.plot(
        staircase_fit.eval(500).name("Hall Probe Reading"),
        label=(
            "Staircase lmfit: "
            + staircase_fit.latex()
            + rf", $w={staircase_smoothing_width:.8g}$"
        ),
        alpha=0.5,
        ax=ax_fit,
    )
ax_fit.set_title("Hall Probe Reading vs Requested Current")
ax_fit.legend()
ax_fit.grid(alpha=0.25)

psd.plot(
    staircase_fit.residual_transform(hall_probe_data.C).name(
        "Hall Probe Reading"
    )
    - staircase_fit.eval().name("Hall Probe Reading"),
    ".",
    ms=8,
    color="C0",
    alpha=0.5,
    ax=ax_resid,
)
ax_resid.axhline(0.1, color="C3", alpha=0.2, lw=3)
ax_resid.axhline(-0.1, color="C3", alpha=0.2, lw=3)
ax_resid.set_xlabel("Requested Current (A)")
ax_resid.set_ylabel("Residuals (G)")
ax_resid.set_title("Smoothed Fit Residuals")
ax_resid.grid(alpha=0.25)

fig.tight_layout()
plt.show()
