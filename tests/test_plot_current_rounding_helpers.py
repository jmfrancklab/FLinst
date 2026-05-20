import copy
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import numpy as np
import pytest
import sympy as sp


# {{{ changeable parameters
AXIS = np.linspace(21.10186155, 21.16143108, 97)
EXAMPLE_GUESS = dict(
    Del_I=0.001241031948229221,
    step=0.0006205159741128341,
    offset=0.0,
    vertoff=0.5,
    c_2=0.0,
    c_1=177.15357843342412,
    c_0=-327.3859380927358,
)
VERIFICATION_POINTS = [
    ("example_guess", {}),
    (
        "shifted_step_location",
        dict(
            Del_I=EXAMPLE_GUESS["Del_I"] * 1.03,
            offset=EXAMPLE_GUESS["offset"] + 0.15 * EXAMPLE_GUESS["Del_I"],
            vertoff=0.35,
        ),
    ),
    (
        "mixed_later_point",
        dict(
            Del_I=EXAMPLE_GUESS["Del_I"] * 0.98,
            offset=EXAMPLE_GUESS["offset"] + 0.22 * EXAMPLE_GUESS["Del_I"],
            vertoff=0.65,
            c_2=0.2,
            c_1=EXAMPLE_GUESS["c_1"] * 0.97,
            c_0=EXAMPLE_GUESS["c_0"] + 12.0,
        ),
    ),
]
# }}}


def build_lmfit_object(axis, dim_name, expression, guesses, residual_transform=None):
    import pyspecdata as psd

    fit_object = psd.lmfitdata(
        psd.nddata(np.zeros_like(axis), [dim_name]).setaxis(dim_name, axis)
    )
    if residual_transform is not None:
        residual_transform(fit_object)
    fit_object.functional_form = expression
    fit_object.set_guess(**guesses)
    fit_object.set_to_guess()
    return fit_object


def attach_smoothed_residual_transform(fit_object, dim_name, smoothing_width):
    @fit_object.define_residual_transform
    def smooth_response(d):
        original_axis = d.getaxis(dim_name).copy()
        uniform_axis = np.linspace(original_axis[0], original_axis[-1], len(original_axis))
        d.setaxis(dim_name, uniform_axis)
        axis_step = np.abs(np.diff(uniform_axis)).mean()
        gaussian_sigma = smoothing_width / (2 * np.sqrt(2 * np.log(2)))
        padding_width = max(axis_step, 6 * gaussian_sigma)
        d.extend(dim_name, uniform_axis[0] - padding_width, fill_with=d.data[0])
        d.extend(dim_name, uniform_axis[-1] + padding_width, fill_with=d.data[-1])
        padded_axis = d.getaxis(dim_name)
        original_start = np.searchsorted(padded_axis, uniform_axis[0])
        original_stop = original_start + len(original_axis)
        d.ft(dim_name, shift=True).ift(dim_name)
        d.convolve(dim_name, smoothing_width, enforce_causality=False)
        d = d[dim_name, original_start:original_stop]
        d.setaxis(dim_name, original_axis)
        return d.real

def assert_symbolic_matches_numerical_jacobian(
    fit_object,
    params,
    *,
    rtol,
    atol,
    label,
):
    def adaptive_directional_derivative(
        baseline_vector,
        baseline_scale,
        base_value,
        shifted_vector,
    ):
        step = max(1e-8, 1e-4 * max(abs(base_value), 1.0))
        for _ in range(20):
            deltas = []
            slopes = []
            for multiple in (1.0, 2.0, 3.0):
                delta = shifted_vector(base_value + multiple * step) - baseline_vector
                deltas.append(delta)
                slopes.append(delta / (multiple * step))
            if (
                max(np.linalg.norm(delta) for delta in deltas)
                < 1e3 * np.finfo(float).eps * baseline_scale
            ):
                step *= 8.0
                continue
            slope_mean = np.mean(slopes, axis=0)
            mismatch = max(
                np.linalg.norm(slope - slope_mean) for slope in slopes
            ) / max(np.linalg.norm(slope_mean), 1e-12)
            if mismatch < 1e-2:
                return slope_mean
            step *= 0.25
        raise AssertionError("could not find a linear finite-difference step")

    sigma = fit_object.get_error()
    baseline = fit_object.residual(params, sigma)
    baseline_scale = max(np.linalg.norm(baseline), 1.0)
    symbolic_jacobian = fit_object.jacobian(params)
    numerical_columns = []
    for name in fit_object.parameter_names:
        base_value = params[name].value

        def shifted_vector(shifted_value, *, name=name):
            shifted = copy.deepcopy(params)
            shifted[name].value = shifted_value
            shifted.update_constraints()
            return fit_object.residual(shifted, sigma)

        try:
            numerical_columns.append(
                adaptive_directional_derivative(
                    baseline,
                    baseline_scale,
                    base_value,
                    shifted_vector,
                )
            )
        except AssertionError as exc:
            raise AssertionError(
                f"{label}: could not find a linear finite-difference step for {name}"
            ) from exc
    np.testing.assert_allclose(
        symbolic_jacobian,
        np.array(numerical_columns),
        rtol=rtol,
        atol=atol,
        err_msg=f"Jacobian mismatch at {label}",
    )


def load_current_rounding_helpers():
    helper_path = (
        Path(__file__).resolve().parents[1]
        / "examples"
        / "magnet_control"
        / "current_rounding_helpers.py"
    )
    spec = spec_from_file_location("current_rounding_helpers", helper_path)
    current_rounding_helpers = module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(current_rounding_helpers)
    return current_rounding_helpers


def test_lmfitdata_numerical_jacobian_check_works_for_sine_and_cosine():
    x = np.linspace(-0.7, 0.9, 17)
    x_symbol, amplitude, phase, offset = sp.symbols(
        "x amplitude phase offset",
        real=True,
    )
    trig_fit = build_lmfit_object(
        x,
        "x",
        amplitude * sp.sin(x_symbol + phase) + offset * sp.cos(2 * x_symbol),
        dict(
            amplitude=dict(value=1.7, min=-5, max=5),
            phase=dict(value=-0.4, min=-2, max=2),
            offset=dict(value=0.2, min=-2, max=2),
        ),
    )
    assert_symbolic_matches_numerical_jacobian(
        trig_fit,
        copy.deepcopy(trig_fit.guess_parameters),
        rtol=3e-4,
        atol=3e-4,
        label="smooth trig model",
    )


def test_lmfitdata_numerical_jacobian_check_works_for_smoothed_sine_and_cosine():
    x = np.linspace(-0.7, 0.9, 17)
    x_symbol, amplitude, phase, offset = sp.symbols(
        "x amplitude phase offset",
        real=True,
    )
    smoothing_width = 0.35 * np.abs(np.diff(x)).mean()

    def add_trig_transform(fit_object):
        attach_smoothed_residual_transform(fit_object, "x", smoothing_width)

    trig_fit = build_lmfit_object(
        x,
        "x",
        amplitude * sp.sin(x_symbol + phase) + offset * sp.cos(2 * x_symbol),
        dict(
            amplitude=dict(value=1.7, min=-5, max=5),
            phase=dict(value=-0.4, min=-2, max=2),
            offset=dict(value=0.2, min=-2, max=2),
        ),
        residual_transform=add_trig_transform,
    )
    assert_symbolic_matches_numerical_jacobian(
        trig_fit,
        copy.deepcopy(trig_fit.guess_parameters),
        rtol=3e-4,
        atol=3e-4,
        label="smoothed trig model",
    )


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason=(
        "The smooth lmfitdata checks pass, but the current floor derivative "
        "helper still fails on an isolated smoothed step."
    ),
)
def test_lmfitdata_symbolic_jacobian_matches_numerical_jacobian_for_single_step_floor():
    from pyspecdata.lmfitdata import sympy_module_arg

    current_rounding_helpers = load_current_rounding_helpers()
    sympy_module_arg[0].update(
        {
            "StaircaseFloor": np.floor,
            "FloorPrime": lambda x: (
                current_rounding_helpers.finite_difference_floor_derivative(x)
            ),
        }
    )
    x = np.linspace(-0.15, 0.15, 33)
    x_symbol, amplitude_symbol, center_symbol, offset_symbol = sp.symbols(
        "x amplitude center offset",
        real=True,
    )
    smoothing_width = 0.5 * np.abs(np.diff(x)).mean()

    def attach_single_step_transform(fit_object):
        attach_smoothed_residual_transform(fit_object, "x", smoothing_width)

    fit_object = build_lmfit_object(
        x,
        "x",
        amplitude_symbol
        * current_rounding_helpers.StaircaseFloor(
            (x_symbol - center_symbol) / 0.3 + 0.5
        )
        + offset_symbol,
        dict(
            amplitude=dict(value=1.7, min=-5, max=5),
            center=dict(value=0.02, min=-0.1, max=0.1),
            offset=dict(value=-0.3, min=-2, max=2),
        ),
        residual_transform=attach_single_step_transform,
    )
    assert_symbolic_matches_numerical_jacobian(
        fit_object,
        copy.deepcopy(fit_object.guess_parameters),
        rtol=5e-3,
        atol=5e-3,
        label="single-step floor model",
    )


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason=(
        "The smooth lmfitdata checks pass, but the current staircase floor "
        "helper still fails on the full smoothed staircase model."
    ),
)
def test_lmfitdata_symbolic_jacobian_matches_numerical_jacobian():
    from pyspecdata.lmfitdata import sympy_module_arg

    current_rounding_helpers = load_current_rounding_helpers()
    sympy_module_arg[0].update(
        {
            "StaircaseFloor": np.floor,
            "FloorPrime": lambda x: (
                current_rounding_helpers.finite_difference_floor_derivative(x)
            ),
        }
    )
    staircase_smoothing_width = 0.5 * np.abs(np.diff(AXIS)).mean()
    (
        I_desired,
        Del_I_symbol,
        offset_symbol,
        vertoff_symbol,
        c_2_symbol,
        c_1_symbol,
        c_0_symbol,
    ) = sp.symbols(
        "I_desired Del_I offset vertoff c_2 c_1 c_0",
        real=True,
    )

    def attach_staircase_residual_transform(fit_object):
        attach_smoothed_residual_transform(
            fit_object,
            "I_desired",
            staircase_smoothing_width,
        )

    fit_object = build_lmfit_object(
        AXIS,
        "I_desired",
        c_2_symbol
        * (
            Del_I_symbol
            * current_rounding_helpers.StaircaseFloor(
                (I_desired - offset_symbol) / Del_I_symbol + vertoff_symbol
            )
        )**2
        + c_1_symbol
        * Del_I_symbol
        * current_rounding_helpers.StaircaseFloor(
            (I_desired - offset_symbol) / Del_I_symbol + vertoff_symbol
        )
        + c_0_symbol,
        dict(
            Del_I=dict(
                value=EXAMPLE_GUESS["Del_I"],
                min=EXAMPLE_GUESS["step"],
                max=2 * EXAMPLE_GUESS["Del_I"],
            ),
            offset=dict(
                value=EXAMPLE_GUESS["offset"],
                min=-max(
                    0.5 * EXAMPLE_GUESS["step"],
                    0.25 * EXAMPLE_GUESS["Del_I"],
                    abs(EXAMPLE_GUESS["offset"]),
                ),
                max=max(
                    0.5 * EXAMPLE_GUESS["step"],
                    0.25 * EXAMPLE_GUESS["Del_I"],
                    abs(EXAMPLE_GUESS["offset"]),
                ),
            ),
            c_1=dict(
                value=EXAMPLE_GUESS["c_1"],
                min=-2 * max(abs(EXAMPLE_GUESS["c_1"]), 1.0),
                max=2 * max(abs(EXAMPLE_GUESS["c_1"]), 1.0),
            ),
            c_2=dict(
                value=EXAMPLE_GUESS["c_2"],
                min=-max(abs(EXAMPLE_GUESS["c_1"]), 1.0),
                max=max(abs(EXAMPLE_GUESS["c_1"]), 1.0),
            ),
            c_0=dict(
                value=EXAMPLE_GUESS["c_0"],
                min=-2
                * max(
                    abs(EXAMPLE_GUESS["c_0"]),
                    abs(EXAMPLE_GUESS["c_1"] * EXAMPLE_GUESS["Del_I"]),
                    1.0,
                ),
                max=2
                * max(
                    abs(EXAMPLE_GUESS["c_0"]),
                    abs(EXAMPLE_GUESS["c_1"] * EXAMPLE_GUESS["Del_I"]),
                    1.0,
                ),
            ),
            vertoff=dict(value=EXAMPLE_GUESS["vertoff"], min=0, max=1),
        ),
        residual_transform=attach_staircase_residual_transform,
    )
    for label, overrides in VERIFICATION_POINTS:
        params = copy.deepcopy(fit_object.guess_parameters)
        for name, value in overrides.items():
            params[name].value = value
        params.update_constraints()
        assert_symbolic_matches_numerical_jacobian(
            fit_object,
            params,
            rtol=5e-3,
            atol=5e-3,
            label=label,
        )
