from pathlib import Path
import re
import os
import pyspecdata as psd
import matplotlib.pyplot as plt
import numpy as np


POINTS_TO_SKIP_FIRST_FIGURE = 3

# am I pulling previously stored data, or something I just ran
pull_old_file = False
if pull_old_file:
    DEFAULT_DATA = "260420_Irounding.txt"
    DEFAULT_EXP_TYPE = "b27/Irounding"
    datafile = Path(
        psd.search_filename(
            re.escape(DEFAULT_DATA),
            exp_type=DEFAULT_EXP_TYPE,
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
table = np.genfromtxt(datafile, names=True)

x_all = table["I_desiredA"]
y_all = table["B0G"]

x_data = x_all[POINTS_TO_SKIP_FIRST_FIGURE:]
y_data = y_all[POINTS_TO_SKIP_FIRST_FIGURE:]

c = np.polyfit(x_data, y_data, 1)
slope, intercept = c
y_fit = slope * x_data + intercept
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
)
ax_fit.plot(
    x_data,
    y_fit,
    "-",
    lw=2.5,
    label=(
        "Linear fit: "
        rf"$B_0 = ({slope:.10g})\,I_{{req}} {intercept:+.10g}$"
    ),
)
ax_fit.plot(
    x_quantized,
    y_quantized_fit,
    "--",
    lw=2.0,
    label=(
        rf"$({c_0:.8g})\cdot({Del_I:.8g})\cdot"
        rf"\mathrm{{round}}\!\left((I_{{req}}-{offset:.8g})/"
        rf"({Del_I:.8g})\right){c_1:+.8g}$"
    ),
)
ax_fit.set_ylabel("Hall Probe Reading G)")
ax_fit.set_title("Hall Probe Reading vs Requested Current")
ax_fit.legend()
ax_fit.grid(alpha=0.25)

ax_resid.plot(x_data, residuals, ".", ms=8, color="C0")
ax_resid.axhline(0.1, color="C3", alpha=0.2, lw=3)
ax_resid.axhline(-0.1, color="C3", alpha=0.2, lw=3)
ax_resid.set_xlabel("Requested Current (A)")
ax_resid.set_ylabel("Residuals (G)")
ax_resid.set_title("Fit Residuals")
ax_resid.grid(alpha=0.25)

fig.tight_layout()
plt.show()
