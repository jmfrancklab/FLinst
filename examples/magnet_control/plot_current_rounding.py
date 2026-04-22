from pathlib import Path
import os
import re

import matplotlib.pyplot as plt
import pyspecdata as psd
import numpy as np

# {{{ changeable parameters
# □ TODO: explain why this is needed
POINTS_TO_SKIP_FIRST_FIGURE = 3
pull_old_file = True
# }}}
# {{{ changeable parameters to describe the staircase function
Del_I = 0.003115
step = 0.00005
offset = 0.0016
c_1 = 178.66095
c_0 = -358.56219
# }}}

# am I pulling previously stored data, or something I just ran
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
raw_columns = np.genfromtxt(datafile, names=True)
# following gives ('I_desiredA', 'I_act_reqA', 'I_measA', 'B0G', 'I_act_setB0')
# print(raw_columns.dtype.names);quit()
hall_probe_data = psd.nddata(raw_columns["B0G"], ["I_desired"]).setaxis(
    "I_desired", raw_columns["I_desiredA"]
)
hall_probe_data = hall_probe_data["I_desired", POINTS_TO_SKIP_FIRST_FIGURE:]
# }}}
coeff = hall_probe_data.polyfit("I_desired", order=1)
intercept, slope = coeff
y_fit = hall_probe_data.eval_poly(coeff, "I_desired", npts=500)
staircase_function = lambda x: (
    c_1 * Del_I * ((x - offset) / Del_I).runcopy(np.round) + c_0
)

fig, (ax_fit, ax_resid) = plt.subplots(
    2,
    1,
    sharex=True,
    figsize=(7.5, 8.0),
    gridspec_kw={"height_ratios": [2.4, 1.2]},
)

# TODO ☐: this shows up as being in G -- is that really true??
#         Think about setting the units and/or using the pyspec
#         div_units function to get into the units you want.
psd.plot(
    hall_probe_data,
    "o",
    ms=4,
    label="Hall Probe Reading",
    alpha=0.5,
    ax=ax_fit,
)
psd.plot(
    y_fit,
    label=(
        "Linear fit: " rf"$B_0 = ({slope:.10g})\,I_{{req}} {intercept:+.10g}$"
    ),
    alpha=0.5,
    ax=ax_fit,
)
psd.plot(
    staircase_function(y_fit.fromaxis("I_desired")),
    label=(
        rf"$({c_1:.8g})\cdot({Del_I:.8g})\cdot"
        rf"\mathrm{{round}}\!\left((I_{{req}}-{offset:.8g})/"
        rf"({Del_I:.8g})\right){c_0:+.8g}$"
    ),
    alpha=0.5,
    ax=ax_fit,
)
ax_fit.set_ylabel("Hall Probe Reading G)")
ax_fit.set_title("Hall Probe Reading vs Requested Current")
ax_fit.legend()
ax_fit.grid(alpha=0.25)

psd.plot(
    hall_probe_data
    - staircase_function(hall_probe_data.fromaxis("I_desired")),
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
ax_resid.set_title("Fit Residuals")
ax_resid.grid(alpha=0.25)

fig.tight_layout()
plt.show()
