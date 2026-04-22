from pathlib import Path
import os
import re

import matplotlib.pyplot as plt
import pyspecdata as psd
import numpy as np

# □ TODO: explain why this is needed
POINTS_TO_SKIP_FIRST_FIGURE = 3

# am I pulling previously stored data, or something I just ran
pull_old_file = True
if pull_old_file:
    datafile = Path(
        psd.search_filename(
            re.escape("260420_Irounding.txt"),
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
raw_columns = np.atleast_2d(np.loadtxt(datafile, skiprows=1))
hall_probe_data = psd.nddata(raw_columns[:, 1], ["I_desired"]).setaxis(
    "I_desired", raw_columns[:, 0]
)
hall_probe_data = hall_probe_data["I_desired"][POINTS_TO_SKIP_FIRST_FIGURE:]
# }}}
coeff = hall_probe_data.polyfit("I_desired", order=1)
intercept, slope = coeff
y_data = fit_data.data
y_fit = fit_data.eval_poly(coeff, "I_desired").data
Del_I = 0.003115
step = 0.00005
offset = 0.0016
c_0 = 178.66095
c_1 = -358.56219
x_quantized = np.arange(x_data[0], x_data[-1] + step, step)
y_quantized_fit = c_0 * Del_I * np.round((x_quantized - offset) / Del_I) + c_1
y_quantized_fit_for_res = (
    c_0 * Del_I * np.round((x_data - offset) / Del_I) + c_1
)
residuals = y_data - y_quantized_fit_for_res

fig, (ax_fit, ax_resid) = plt.subplots(
    2,
    1,
    sharex=True,
    figsize=(7.5, 8.0),
    gridspec_kw={"height_ratios": [2.4, 1.2]},
)

ax_fit.plot(
    x_data,
    y_data,
    "o",
    ms=4,
    label="Hall Probe Reading",
    alpha=0.5,
)
ax_fit.plot(
    x_data,
    y_fit,
    label=(
        "Linear fit: " rf"$B_0 = ({slope:.10g})\,I_{{req}} {intercept:+.10g}$"
    ),
    alpha=0.5,
)
ax_fit.plot(
    x_quantized,
    y_quantized_fit,
    label=(
        rf"$({c_0:.8g})\cdot({Del_I:.8g})\cdot"
        rf"\mathrm{{round}}\!\left((I_{{req}}-{offset:.8g})/"
        rf"({Del_I:.8g})\right){c_1:+.8g}$"
    ),
    alpha=0.5,
)
ax_fit.set_ylabel("Hall Probe Reading G)")
ax_fit.set_title("Hall Probe Reading vs Requested Current")
ax_fit.legend()
ax_fit.grid(alpha=0.25)

ax_resid.plot(x_data, residuals, ".", ms=8, color="C0", alpha=0.5)
ax_resid.axhline(0.1, color="C3", alpha=0.2, lw=3)
ax_resid.axhline(-0.1, color="C3", alpha=0.2, lw=3)
ax_resid.set_xlabel("Requested Current (A)")
ax_resid.set_ylabel("Residuals (G)")
ax_resid.set_title("Fit Residuals")
ax_resid.grid(alpha=0.25)

fig.tight_layout()
plt.show()
