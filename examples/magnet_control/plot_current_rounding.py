from pathlib import Path
import copy
import os
import re
import matplotlib.pyplot as plt
import pyspecdata as psd
import numpy as np
import sympy as sp
from scipy.optimize import linprog


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
c_2 = 0
do_fit = True
# }}}

def pack_parameter_vector(params, parameter_names):
    return np.array([params[this_name].value for this_name in parameter_names])


class CustomBasinSearchLmfitData(psd.lmfitdata):
    # {{{ Use a custom LM basin search here because lmfit's built-in
    #     basinhopping path delegates the local minimizer through
    #     scipy.optimize.minimize, which does not accept LM/leastsq as a
    #     standard local method.
    # }}}
    # {{{ These settings control the custom search:
    #     `n_locals` is how many distinct wells we want to discover;
    #     `basin_sigma` is the covariance-scaled threshold for calling two
    #     minima connected; `max_trials` caps the number of LM solves;
    #     `max_start_draws` limits how long we spend drawing a restart that
    #     lies outside the convex hulls of already-connected spaces; and
    #     `seed` makes the random starts reproducible.
    # }}}
    basinhopping_kws = dict(
        n_locals=200,
        basin_sigma=3.0,
        max_trials=500,
        max_start_draws=500,
        seed=0,
    )

    def fit(
        self,
        use_jacobian=False,
        basinhopping=False,
        basinhopping_updates=True,
    ):
        if not basinhopping:
            return super().fit(use_jacobian=use_jacobian)
        original_guess_parameters = copy.deepcopy(self.guess_parameters)
        original_guess_dict = copy.deepcopy(getattr(self, "guess_dict", None))
        parameter_names = [
            name for name, par in original_guess_parameters.items() if par.vary
        ]

        def parameter_bounds():
            bounds = np.zeros((len(parameter_names), 2), dtype=float)
            for j, this_name in enumerate(parameter_names):
                lower, upper = sorted(
                    (
                        original_guess_parameters[this_name].min,
                        original_guess_parameters[this_name].max,
                    )
                )
                if not np.isfinite(lower) or not np.isfinite(upper):
                    raise ValueError(
                        "custom LM basin search requires finite bounds for"
                        f" {this_name}"
                    )
                bounds[j] = [lower, upper]
            return bounds

        def load_parameter_vector(params, values):
            for this_name, this_value in zip(parameter_names, values):
                lower, upper = sorted((params[this_name].min, params[this_name].max))
                params[this_name].value = float(np.clip(this_value, lower, upper))
            params.update_constraints()

        def same_well_by_covariance(
            left_vector,
            left_covar,
            right_vector,
            right_covar,
        ):
            if left_covar is None or right_covar is None:
                return False
            average_covar = 0.5 * (
                np.asarray(left_covar, dtype=float)
                + np.asarray(right_covar, dtype=float)
            )
            delta = np.asarray(left_vector, dtype=float) - np.asarray(
                right_vector,
                dtype=float,
            )
            metric = float(delta @ np.linalg.pinv(average_covar) @ delta)
            if not np.isfinite(metric):
                return False
            return np.sqrt(max(metric, 0.0)) <= self.basinhopping_kws["basin_sigma"]

        def point_in_convex_hull(candidate, hull_points):
            hull_points = np.asarray(hull_points, dtype=float)
            if hull_points.ndim != 2 or len(hull_points) == 0:
                return False
            scaled_points = hull_points / scales
            scaled_candidate = np.asarray(candidate, dtype=float) / scales
            n_points = scaled_points.shape[0]
            # Hull membership for a general connected cloud is a convex-
            # combination feasibility test; determinant tests only apply
            # directly to simplices.
            result = linprog(
                c=np.zeros(n_points),
                A_eq=np.vstack([np.ones(n_points), scaled_points.T]),
                b_eq=np.concatenate([[1.0], scaled_candidate]),
                bounds=[(0, None)] * n_points,
                method="highs",
            )
            return bool(result.success)

        def choose_random_start(connected_spaces):
            best_candidate = None
            fewest_hits = np.inf
            for _ in range(self.basinhopping_kws["max_start_draws"]):
                candidate = rng.uniform(bounds[:, 0], bounds[:, 1])
                hull_hits = sum(
                    point_in_convex_hull(candidate, this_set)
                    for this_set in connected_spaces
                )
                if hull_hits == 0:
                    return candidate, 0, False
                if hull_hits < fewest_hits:
                    best_candidate = candidate.copy()
                    fewest_hits = hull_hits
            return best_candidate, int(fewest_hits), True

        def build_connection_matrix(points):
            n_points = len(points)
            connection_matrix = -np.ones((n_points, n_points), dtype=int)
            for j in range(n_points):
                connection_matrix[j, j] = 1
            for j in range(1, n_points):
                for k in range(j):
                    if points[j]["trial_index"] == points[k]["trial_index"]:
                        this_relation = 1
                    elif (
                        points[j]["well_id"] is not None
                        and points[j]["well_id"] == points[k]["well_id"]
                    ):
                        this_relation = 1
                    elif (
                        points[j]["well_id"] is not None
                        and points[k]["well_id"] is not None
                    ):
                        this_relation = 0
                    else:
                        this_relation = -1
                    connection_matrix[j, k] = this_relation
                    connection_matrix[k, j] = this_relation
            return connection_matrix

        bounds = parameter_bounds()
        scales = np.maximum(bounds[:, 1] - bounds[:, 0], np.finfo(float).eps)
        rng = np.random.default_rng(self.basinhopping_kws["seed"])
        tested_points = []
        total_nfev = 0
        next_well_id = 0
        best_fit = None
        best_trial_index = None
        first_failure = None
        for trial_index in range(self.basinhopping_kws["max_trials"]):
            if trial_index == 0:
                start_vector = pack_parameter_vector(
                    original_guess_parameters,
                    parameter_names,
                )
                used_fallback = False
                hull_hits = 0
            else:
                connected_spaces = [
                    [j["vector"] for j in tested_points if j["well_id"] == this_well]
                    for this_well in sorted(
                        {
                            j["well_id"]
                            for j in tested_points
                            if j["well_id"] is not None
                        }
                    )
                ]
                (
                    start_vector,
                    hull_hits,
                    used_fallback,
                ) = choose_random_start(connected_spaces)
            trial_fit = self.copy()
            trial_fit.guess_parameters = copy.deepcopy(original_guess_parameters)
            if original_guess_dict is not None:
                trial_fit.guess_dict = copy.deepcopy(original_guess_dict)
            load_parameter_vector(trial_fit.guess_parameters, start_vector)
            trial_output = None
            fit_exception = None
            try:
                # Use lmfitdata's inherited fit path for each local solve so
                # transforms, complex residual handling, and fit-report state
                # stay consistent with the single-fit behavior.
                psd.lmfitdata.fit(trial_fit, use_jacobian=use_jacobian)
                trial_output = trial_fit.fit_output
            except Exception as exc:
                fit_exception = exc
                trial_output = getattr(trial_fit, "fit_output", None)
                if first_failure is None:
                    first_failure = exc
            trial_success = bool(
                trial_output is not None and getattr(trial_output, "success", False)
            )
            trial_chisqr = float(
                getattr(trial_output, "chisqr", np.inf)
                if trial_output is not None
                else np.inf
            )
            total_nfev += int(
                getattr(trial_output, "nfev", 0) if trial_output is not None else 0
            )
            well_id = None
            well_state = "failed"
            if trial_success:
                minimum_vector = pack_parameter_vector(
                    trial_output.params,
                    parameter_names,
                )
                covariance = getattr(trial_output, "covar", None)
                if covariance is not None:
                    covariance = np.asarray(covariance, dtype=float)
                matching_wells = sorted(
                    {
                        this_point["well_id"]
                        for this_point in tested_points
                        if this_point["kind"] == "minimum"
                        and this_point["well_id"] is not None
                        and this_point["covariance"] is not None
                        and covariance is not None
                        and same_well_by_covariance(
                            minimum_vector,
                            covariance,
                            this_point["vector"],
                            this_point["covariance"],
                        )
                    }
                )
                if matching_wells:
                    well_id = matching_wells[0]
                    for this_point in tested_points:
                        if this_point["well_id"] in matching_wells[1:]:
                            this_point["well_id"] = well_id
                    well_state = "connected"
                else:
                    well_id = next_well_id
                    next_well_id += 1
                    # If LM does not provide a covariance, we cannot merge
                    # this result into an older connected space, so treat this
                    # successful start/minimum pair as a new one.
                    well_state = "new" if covariance is not None else "new_no_covar"
                # {{{ Each successful trial contributes a start point and a
                #     converged minimum. They are connected by definition, so
                #     both carry the same `well_id`. A failed trial contributes
                #     only the failed start and remains outside any connected
                #     space.
                # }}}
                tested_points.extend(
                    [
                        dict(
                            vector=start_vector.copy(),
                            trial_index=trial_index,
                            kind="start",
                            well_id=well_id,
                        ),
                        dict(
                            vector=minimum_vector.copy(),
                            trial_index=trial_index,
                            kind="minimum",
                            covariance=covariance,
                            well_id=well_id,
                        ),
                    ]
                )
            else:
                tested_points.append(
                    dict(
                        vector=start_vector.copy(),
                        trial_index=trial_index,
                        kind="start",
                        well_id=None,
                    )
                )
            successful_wells = sorted(
                {
                    j["well_id"]
                    for j in tested_points
                    if j["kind"] == "minimum" and j["well_id"] is not None
                }
            )
            if trial_success and (
                best_fit is None or trial_chisqr < float(best_fit.fit_output.chisqr)
            ):
                best_fit = trial_fit
                best_trial_index = trial_index
            if basinhopping_updates:
                if trial_success:
                    update_text = [
                        "basin_search",
                        str(trial_index + 1),
                        f"success chi-square={trial_chisqr:.6g}",
                        f"well={well_state}",
                        f"n_wells={len(successful_wells)}",
                        f"best={float(best_fit.fit_output.chisqr):.6g}",
                    ]
                else:
                    failure_name = (
                        type(fit_exception).__name__
                        if fit_exception is not None
                        else "fit_failed"
                    )
                    update_text = [
                        "basin_search",
                        str(trial_index + 1),
                        f"failed error={failure_name}",
                        f"n_wells={len(successful_wells)}",
                    ]
                if trial_index > 0:
                    update_text.append(f"hull_hits={hull_hits}")
                    if used_fallback:
                        update_text.append("draw=best_of_sample")
                print(*update_text, flush=True)
            if len(successful_wells) >= self.basinhopping_kws["n_locals"]:
                break
        if best_fit is None:
            self.guess_parameters = original_guess_parameters
            if original_guess_dict is not None:
                self.guess_dict = original_guess_dict
            raise RuntimeError(
                "custom LM basin search did not find a successful fit"
            ) from first_failure
        self.guess_parameters = original_guess_parameters
        if original_guess_dict is not None:
            self.guess_dict = original_guess_dict
        self.fit_output = best_fit.fit_output
        self.fit_output.method = "custom basin search (leastsq)"
        self.fit_output.nfev = total_nfev
        self.fit_parameters = best_fit.fit_parameters
        self.fit_coeff = list(best_fit.fit_coeff)
        self.basin_tested_points = tested_points
        self.basin_connection_matrix = build_connection_matrix(tested_points)
        self.basin_connection_labels = [
            f"trial {j['trial_index'] + 1} {j['kind']}" for j in tested_points
        ]
        self.basin_best_trial = best_trial_index
        return self

# am I pulling previously stored data, or something I just ran
if pull_old_file:
    datafile = Path(
        psd.search_filename(
            re.escape("260420_Irounding_old_script.txt"),
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
I_desired, Del_I_symbol, offset_symbol, vertoff_symbol, c_2_symbol, c_1_symbol, c_0_symbol = sp.symbols(
    "I_desired Del_I offset vertoff c_2 c_1 c_0", real=True
)
staircase_fit = CustomBasinSearchLmfitData(hall_probe_data)


@staircase_fit.define_residual_transform
def smooth_staircase_response(d):
    original_axis = d.getaxis("I_desired").copy()
    # TODO ☐: it should not need to do this because the axis of
    #         requested currents should be evenly spaced!!!  This leads
    #         to the other problems!
    uniform_axis = np.linspace(
        original_axis[0], original_axis[-1], len(original_axis)
    )
    d.setaxis("I_desired", uniform_axis)
    # Pad by ~6 sigma on both sides so the Gaussian convolution sees
    # endpoint plateaus instead of wrapping around the finite axis.
    axis_step = np.abs(np.diff(uniform_axis)).mean()
    gaussian_sigma = staircase_smoothing_width / (
        2 * np.sqrt(2 * np.log(2))
    )
    padding_width = max(axis_step, 6 * gaussian_sigma)
    d.extend(
        "I_desired",
        uniform_axis[0] - padding_width,
        fill_with=d.data[0],
    )
    d.extend(
        "I_desired",
        uniform_axis[-1] + padding_width,
        fill_with=d.data[-1],
    )
    padded_axis = d.getaxis("I_desired")
    original_start = np.searchsorted(padded_axis, uniform_axis[0])
    original_stop = original_start + len(original_axis)
    # The following is required for convolve, but should not be.
    d.ft("I_desired", shift=True).ift("I_desired")
    d.convolve("I_desired", staircase_smoothing_width, enforce_causality=False)
    d = d["I_desired", original_start: original_stop]
    d.setaxis("I_desired", original_axis)
    return d.real


staircase_fit.functional_form = (
    c_2_symbol
    * (Del_I_symbol
    * sp.floor((I_desired - offset_symbol) / Del_I_symbol + vertoff_symbol))**2
    +
    c_1_symbol
    * Del_I_symbol
    * sp.floor((I_desired - offset_symbol) / Del_I_symbol + vertoff_symbol)
    + c_0_symbol
)
staircase_fit.set_guess(
    Del_I=dict(value=Del_I, min=step, max=2 * Del_I),
    offset={"value": offset, "min": -2 * offset, "max": 2 * offset},
    c_1={"value": c_1, "min": 0.5 * c_1, "max": 2 * c_1},
    c_2={"value": 0, "min": -c_1, "max": c_1},
    c_0={"value": c_0, "min": -2 * c_0, "max": 2 * c_0},
    vertoff={"value": 0.5, "min": 0, "max":1},
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
    # Set basinhopping=False here to fall back to the inherited single LM fit.
    # Set basinhopping_updates=False to silence the live basin-by-basin prints.
    staircase_fit.fit(
        use_jacobian=False,
        basinhopping=True,
        basinhopping_updates=True,
    )
    print(staircase_fit.fit_report())
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
            "Staircase lmfit"
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
