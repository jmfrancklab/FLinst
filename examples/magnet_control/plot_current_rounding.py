from pathlib import Path
import copy
import os
import re
import matplotlib.pyplot as plt
import pyspecdata as psd
import numpy as np
import sympy as sp


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


class MonteCarloLmfitData(psd.lmfitdata):
    # {{{ Use a custom Monte Carlo walk here because we want to keep the
    #     local optimizer as plain LM, but still hop between different local
    #     minima by taking covariance-scaled random steps between LM solves.
    # }}}
    # {{{ These settings control the Monte Carlo walk:
    #     `mc_steps` is the number of local-minimum evaluations to attempt;
    #     `mc_temperature` is the Metropolis temperature used for uphill
    #     accepts; and `seed` makes the random directions reproducible.
    # }}}
    mc_kws = dict(
        mc_steps=100,
        mc_temperature=1.0,
        seed=0,
    )

    def fit(
        self,
        use_jacobian=False,
        basinhopping=False,
        basinhopping_updates=True,
        mc_steps=None,
    ):
        if not basinhopping:
            return super().fit(use_jacobian=use_jacobian)
        original_guess_parameters = copy.deepcopy(self.guess_parameters)
        original_guess_dict = copy.deepcopy(getattr(self, "guess_dict", None))
        parameter_names = [
            name for name, par in original_guess_parameters.items() if par.vary
        ]
        if mc_steps is None:
            mc_steps = self.mc_kws["mc_steps"]

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
                        "custom Monte Carlo stepping requires finite bounds for"
                        f" {this_name}"
                    )
                bounds[j] = [lower, upper]
            return bounds

        def load_parameter_vector(params, values):
            for this_name, this_value in zip(parameter_names, values):
                lower, upper = sorted((params[this_name].min, params[this_name].max))
                params[this_name].value = float(np.clip(this_value, lower, upper))
            params.update_constraints()

        def run_local_fit(start_vector):
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
            return trial_fit, trial_output, fit_exception

        def covariance_step(center_vector, covariance):
            covariance = np.asarray(covariance, dtype=float)
            eigenvalues, eigenvectors = np.linalg.eigh(covariance)
            eigenvalues = np.clip(eigenvalues, 0.0, None)
            if not np.any(eigenvalues > 0):
                return None
            random_direction = rng.normal(size=len(parameter_names))
            random_direction /= np.linalg.norm(random_direction)
            return np.clip(
                center_vector
                + eigenvectors @ (np.sqrt(eigenvalues) * random_direction),
                bounds[:, 0],
                bounds[:, 1],
            )

        def covariance_from_chisqr(fit_object):
            base_vector = pack_parameter_vector(
                fit_object.fit_output.params,
                parameter_names,
            )
            margin = np.minimum(base_vector - bounds[:, 0], bounds[:, 1] - base_vector)
            if np.any(margin <= 0):
                return None
            step_sizes = np.minimum(1e-3 * (bounds[:, 1] - bounds[:, 0]), 0.25 * margin)
            step_sizes = np.maximum(
                step_sizes,
                1e-8 * np.maximum(1.0, np.abs(base_vector)),
            )

            def chisqr_at(this_vector):
                trial_params = copy.deepcopy(fit_object.fit_output.params)
                load_parameter_vector(trial_params, this_vector)
                residual = fit_object.residual(trial_params, fit_object.get_error())
                return float((residual**2).sum())

            base_chisqr = chisqr_at(base_vector)
            hessian = np.zeros((len(parameter_names), len(parameter_names)), dtype=float)
            for j, step_j in enumerate(step_sizes):
                delta_j = np.zeros(len(parameter_names))
                delta_j[j] = step_j
                hessian[j, j] = (
                    chisqr_at(base_vector + delta_j)
                    - 2 * base_chisqr
                    + chisqr_at(base_vector - delta_j)
                ) / step_j**2
                for k in range(j + 1, len(parameter_names)):
                    step_k = step_sizes[k]
                    delta_k = np.zeros(len(parameter_names))
                    delta_k[k] = step_k
                    cross_term = (
                        chisqr_at(base_vector + delta_j + delta_k)
                        - chisqr_at(base_vector + delta_j - delta_k)
                        - chisqr_at(base_vector - delta_j + delta_k)
                        + chisqr_at(base_vector - delta_j - delta_k)
                    ) / (4 * step_j * step_k)
                    hessian[j, k] = cross_term
                    hessian[k, j] = cross_term
            if not np.all(np.isfinite(hessian)):
                return None
            return 2.0 * np.linalg.pinv(hessian)

        def report_step(step_number, chisqr, best_chisqr, status):
            if basinhopping_updates:
                print(
                    "mc_step",
                    step_number,
                    f"chi-square={chisqr:.6g}",
                    f"best={best_chisqr:.6g}",
                    status,
                    flush=True,
                )

        bounds = parameter_bounds()
        rng = np.random.default_rng(self.mc_kws["seed"])
        total_nfev = 0
        first_failure = None
        best_fit = None
        best_step = 1
        current_fit = None
        mc_history = []

        current_vector = pack_parameter_vector(
            original_guess_parameters,
            parameter_names,
        )
        current_fit, current_output, first_failure = run_local_fit(current_vector)
        if current_output is not None:
            total_nfev += int(getattr(current_output, "nfev", 0))
        if not (
            current_output is not None and getattr(current_output, "success", False)
        ):
            self.guess_parameters = original_guess_parameters
            if original_guess_dict is not None:
                self.guess_dict = original_guess_dict
            raise RuntimeError(
                "custom Monte Carlo search could not find the initial local minimum"
            ) from first_failure
        best_fit = current_fit
        current_chisqr = float(current_fit.fit_output.chisqr)
        mc_history.append(dict(step=1, chisqr=current_chisqr, accepted=True))
        report_step(1, current_chisqr, current_chisqr, "accepted")

        for step_number in range(2, mc_steps + 1):
            covariance = getattr(current_fit.fit_output, "covar", None)
            if covariance is None:
                covariance = covariance_from_chisqr(current_fit)
            if covariance is None:
                report_step(
                    step_number,
                    current_chisqr,
                    float(best_fit.fit_output.chisqr),
                    "stopped(no_covar)",
                )
                break
            proposal_start = covariance_step(
                pack_parameter_vector(current_fit.fit_output.params, parameter_names),
                covariance,
            )
            if proposal_start is None:
                report_step(
                    step_number,
                    current_chisqr,
                    float(best_fit.fit_output.chisqr),
                    "stopped(singular_covar)",
                )
                break
            proposal_fit, proposal_output, proposal_exception = run_local_fit(
                proposal_start
            )
            if proposal_output is not None:
                total_nfev += int(getattr(proposal_output, "nfev", 0))
            if not (
                proposal_output is not None
                and getattr(proposal_output, "success", False)
            ):
                failure_name = (
                    type(proposal_exception).__name__
                    if proposal_exception is not None
                    else "fit_failed"
                )
                mc_history.append(
                    dict(step=step_number, chisqr=np.inf, accepted=False)
                )
                report_step(
                    step_number,
                    np.inf,
                    float(best_fit.fit_output.chisqr),
                    f"rejected({failure_name})",
                )
                continue
            proposal_chisqr = float(proposal_fit.fit_output.chisqr)
            delta_chisqr = proposal_chisqr - current_chisqr
            accept_probability = np.exp(
                -0.5 * max(delta_chisqr, 0.0) / self.mc_kws["mc_temperature"]
            )
            accepted = delta_chisqr <= 0 or rng.random() < accept_probability
            if accepted:
                current_fit = proposal_fit
                current_chisqr = proposal_chisqr
            if proposal_chisqr < float(best_fit.fit_output.chisqr):
                best_fit = proposal_fit
                best_step = step_number
            mc_history.append(
                dict(
                    step=step_number,
                    chisqr=proposal_chisqr,
                    accepted=accepted,
                )
            )
            report_step(
                step_number,
                proposal_chisqr,
                float(best_fit.fit_output.chisqr),
                "accepted" if accepted else "rejected",
            )

        self.guess_parameters = original_guess_parameters
        if original_guess_dict is not None:
            self.guess_dict = original_guess_dict
        self.fit_output = best_fit.fit_output
        self.fit_output.method = "custom Monte Carlo (leastsq)"
        self.fit_output.nfev = total_nfev
        self.fit_parameters = best_fit.fit_parameters
        self.fit_coeff = list(best_fit.fit_coeff)
        self.mc_history = mc_history
        self.mc_best_step = best_step
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
staircase_fit = MonteCarloLmfitData(hall_probe_data)


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
    # Set `mc_steps=1` to recover a plain local LM fit from the current guess.
    # Larger values turn on the Monte Carlo walk between local minima.
    staircase_fit.fit(
        use_jacobian=False,
        basinhopping=True,
        basinhopping_updates=True,
        mc_steps=100,
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
