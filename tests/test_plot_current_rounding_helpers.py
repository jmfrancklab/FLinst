from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import numpy as np
import pytest
import sympy as sp


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


def test_staircase_floor_symbolic_derivative_uses_floorprime():
    current_rounding_helpers = load_current_rounding_helpers()
    x = sp.Symbol("x", real=True)
    expr = current_rounding_helpers.StaircaseFloor(x)
    assert sp.diff(expr, x) == current_rounding_helpers.FloorPrime(x)


def test_finite_difference_floor_derivative_adds_each_integer_jump():
    current_rounding_helpers = load_current_rounding_helpers()
    x = np.linspace(-1.5, 2.5, 9)
    def finite_difference_heaviside_derivative(x):
        x = np.asarray(x, dtype=float)
        if not np.allclose(np.diff(x), np.diff(x)[0]):
            raise ValueError("x should be uniformly spaced")
        crossing_idx = np.searchsorted(x, 0)
        idx = crossing_idx
        if abs(x[crossing_idx]) > abs(x[crossing_idx - 1]):
            idx = crossing_idx - 1
        weights = np.zeros_like(x)
        weights[idx] = 1.0
        return weights
    weights = current_rounding_helpers.finite_difference_floor_derivative(
        x,
        finite_difference_heaviside_derivative,
    )
    expected = np.zeros_like(x)
    for jump_location in (-1, 0, 1, 2):
        expected += finite_difference_heaviside_derivative(x - jump_location)
    np.testing.assert_allclose(weights, expected)


def test_axis_spacing_diagnostics_reports_uniform_regrid():
    current_rounding_helpers = load_current_rounding_helpers()
    axis = np.array([0.0, 1.0, 2.1, 3.0])
    report = current_rounding_helpers.axis_spacing_diagnostics(axis)
    np.testing.assert_allclose(
        report["uniform_axis"],
        np.linspace(axis[0], axis[-1], len(axis)),
    )
    assert report["max_spacing_error"] > 0


def test_lambdified_staircase_parameter_derivatives_are_vector_valued():
    current_rounding_helpers = load_current_rounding_helpers()

    def finite_difference_heaviside_derivative(x):
        x = np.asarray(x, dtype=float)
        if not np.allclose(np.diff(x), np.diff(x)[0]):
            raise ValueError("x should be uniformly spaced")
        crossing_idx = np.searchsorted(x, 0)
        idx = crossing_idx
        if abs(x[crossing_idx]) > abs(x[crossing_idx - 1]):
            idx = crossing_idx - 1
        weights = np.zeros_like(x)
        weights[idx] = 1.0
        return weights

    symbol_map = {
        "StaircaseFloor": np.floor,
        "FloorPrime": lambda x: (
            current_rounding_helpers.finite_difference_floor_derivative(
                x,
                finite_difference_heaviside_derivative,
            )
        ),
    }
    I_desired, Del_I, offset, vertoff, c_2, c_1, c_0 = sp.symbols(
        "I_desired Del_I offset vertoff c_2 c_1 c_0",
        real=True,
    )
    axis_ones_expr = sp.Add(
        sp.Mul(sp.Integer(0), I_desired, evaluate=False),
        sp.Integer(1),
        evaluate=False,
    )
    expr = (
        c_2
        * (
            Del_I
            * current_rounding_helpers.StaircaseFloor(
                (I_desired - offset) / Del_I + vertoff
            )
        )**2
        + c_1
        * Del_I
        * current_rounding_helpers.StaircaseFloor(
            (I_desired - offset) / Del_I + vertoff
        )
        + c_0 * axis_ones_expr
    )
    axis = np.linspace(21.1, 21.16, 97)
    for sym in [Del_I, offset, vertoff, c_2, c_1, c_0]:
        derivative_fn = sp.lambdify(
            (I_desired, Del_I, offset, vertoff, c_2, c_1, c_0),
            sp.diff(expr, sym, 1),
            modules=[symbol_map, "numpy"],
        )
        values = np.asarray(
            derivative_fn(axis, 0.00124, 0.0002, 0.5, 0.0, 177.0, -327.0)
        )
        assert values.shape == axis.shape
    np.testing.assert_allclose(
        np.asarray(
            sp.lambdify(
                (I_desired, Del_I, offset, vertoff, c_2, c_1, c_0),
                sp.diff(expr, c_0, 1),
                modules=[symbol_map, "numpy"],
            )(axis, 0.00124, 0.0002, 0.5, 0.0, 177.0, -327.0)
        ),
        np.ones_like(axis),
    )


def test_symbolic_staircase_amplitude_derivatives_match_finite_difference():
    current_rounding_helpers = load_current_rounding_helpers()
    symbol_map = {
        "StaircaseFloor": np.floor,
        "FloorPrime": lambda x: (
            current_rounding_helpers.finite_difference_floor_derivative(x)
        ),
    }
    I_desired, Del_I, offset, vertoff, c_2, c_1, c_0 = sp.symbols(
        "I_desired Del_I offset vertoff c_2 c_1 c_0",
        real=True,
    )
    expr = (
        c_2
        * (
            Del_I
            * current_rounding_helpers.StaircaseFloor(
                (I_desired - offset) / Del_I + vertoff
            )
        )**2
        + c_1
        * Del_I
        * current_rounding_helpers.StaircaseFloor(
            (I_desired - offset) / Del_I + vertoff
        )
        + c_0
    )
    model = sp.lambdify(
        (I_desired, Del_I, offset, vertoff, c_2, c_1, c_0),
        expr,
        modules=[symbol_map, "numpy"],
    )
    axis = np.linspace(21.1, 21.16, 97)
    params = dict(Del_I=0.00124, offset=0.0002, vertoff=0.5, c_2=0.3, c_1=177.0, c_0=-327.0)
    for sym, eps in [(c_2, 1e-6), (c_1, 1e-6), (c_0, 1e-6)]:
        derivative_fn = sp.lambdify(
            (I_desired, Del_I, offset, vertoff, c_2, c_1, c_0),
            sp.diff(expr, sym, 1),
            modules=[symbol_map, "numpy"],
        )
        analytical = np.asarray(
            derivative_fn(axis, **params),
            dtype=float,
        )
        if analytical.ndim == 0:
            analytical = np.full_like(axis, analytical, dtype=float)
        plus = params.copy()
        minus = params.copy()
        plus[str(sym)] += eps
        minus[str(sym)] -= eps
        numeric = (
            np.asarray(model(axis, **plus), dtype=float)
            - np.asarray(model(axis, **minus), dtype=float)
        ) / (2 * eps)
        np.testing.assert_allclose(analytical, numeric, rtol=1e-6, atol=1e-6)


@pytest.mark.xfail(
    strict=True,
    reason=(
        "The current StaircaseFloor/FloorPrime pair does not yet make the"
        " Del_I/offset/vertoff symbolic derivatives match finite differences"
        " of the implemented staircase model."
    ),
)
def test_symbolic_staircase_location_derivatives_match_finite_difference():
    current_rounding_helpers = load_current_rounding_helpers()
    symbol_map = {
        "StaircaseFloor": np.floor,
        "FloorPrime": lambda x: (
            current_rounding_helpers.finite_difference_floor_derivative(x)
        ),
    }
    I_desired, Del_I, offset, vertoff, c_2, c_1, c_0 = sp.symbols(
        "I_desired Del_I offset vertoff c_2 c_1 c_0",
        real=True,
    )
    expr = (
        c_2
        * (
            Del_I
            * current_rounding_helpers.StaircaseFloor(
                (I_desired - offset) / Del_I + vertoff
            )
        )**2
        + c_1
        * Del_I
        * current_rounding_helpers.StaircaseFloor(
            (I_desired - offset) / Del_I + vertoff
        )
        + c_0
    )
    model = sp.lambdify(
        (I_desired, Del_I, offset, vertoff, c_2, c_1, c_0),
        expr,
        modules=[symbol_map, "numpy"],
    )
    axis = np.linspace(21.1, 21.16, 97)
    params = dict(Del_I=0.00124, offset=0.0002, vertoff=0.5, c_2=0.3, c_1=177.0, c_0=-327.0)
    for sym, eps in [(Del_I, 1e-6), (offset, 1e-6), (vertoff, 1e-6)]:
        derivative_fn = sp.lambdify(
            (I_desired, Del_I, offset, vertoff, c_2, c_1, c_0),
            sp.diff(expr, sym, 1),
            modules=[symbol_map, "numpy"],
        )
        analytical = np.asarray(
            derivative_fn(axis, **params),
            dtype=float,
        )
        plus = params.copy()
        minus = params.copy()
        plus[str(sym)] += eps
        minus[str(sym)] -= eps
        numeric = (
            np.asarray(model(axis, **plus), dtype=float)
            - np.asarray(model(axis, **minus), dtype=float)
        ) / (2 * eps)
        np.testing.assert_allclose(analytical, numeric, rtol=1e-4, atol=1e-4)
