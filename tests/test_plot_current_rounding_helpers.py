from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import numpy as np
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
