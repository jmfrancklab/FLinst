import numpy as np
import sympy as sp


def finite_difference_floor_derivative(
    x, finite_difference_heaviside_derivative=None
):
    x = np.asarray(x, dtype=float)
    if x.ndim != 1:
        raise ValueError("x must be one-dimensional")
    if len(x) < 2:
        raise ValueError("x must have at least two points")
    lower = int(np.ceil(np.min(x)))
    upper = int(np.floor(np.max(x)))
    weights = np.zeros_like(x)
    for jump_location in range(lower, upper + 1):
        offset = x - jump_location
        nearest_idx = np.argmin(np.abs(offset))
        if np.isclose(offset[nearest_idx], 0.0):
            weights[nearest_idx] += 1.0
            continue
        crossing_idx = np.nonzero(
            ((offset[:-1] < 0.0) & (offset[1:] > 0.0))
            | ((offset[:-1] > 0.0) & (offset[1:] < 0.0))
        )[0]
        if len(crossing_idx) == 0:
            continue
        left_idx = crossing_idx[0]
        right_idx = left_idx + 1
        interval = x[right_idx] - x[left_idx]
        if np.isclose(interval, 0.0):
            weights[nearest_idx] += 1.0
            continue
        right_weight = (jump_location - x[left_idx]) / interval
        left_weight = 1.0 - right_weight
        weights[left_idx] += left_weight
        weights[right_idx] += right_weight
    return weights


class FloorPrime(sp.Function):
    nargs = 1


class StaircaseFloor(sp.Function):
    nargs = 1

    @classmethod
    def eval(cls, arg):
        if arg.is_number:
            return sp.floor(arg)
        return None

    def fdiff(self, argindex=1):
        if argindex != 1:
            raise ValueError("StaircaseFloor takes one argument")
        return FloorPrime(self.args[0])




def axis_spacing_diagnostics(axis):
    axis = np.asarray(axis, dtype=float)
    if axis.ndim != 1:
        raise ValueError("axis must be one-dimensional")
    if len(axis) < 2:
        raise ValueError("axis must have at least two points")
    uniform_axis = np.linspace(axis[0], axis[-1], len(axis))
    spacing_error = axis - uniform_axis
    return dict(
        uniform_axis=uniform_axis,
        median_step=np.median(np.diff(uniform_axis)),
        max_spacing_error=np.max(np.abs(spacing_error)),
    )


def estimate_staircase_guesses(axis, field_values, slope, intercept):
    axis = np.asarray(axis, dtype=float)
    field_values = np.asarray(field_values, dtype=float)
    uniform_axis = np.linspace(axis[0], axis[-1], len(axis))
    spacing = dict(
        uniform_axis=uniform_axis,
        median_step=np.median(np.diff(uniform_axis)),
        max_spacing_error=np.max(np.abs(axis - uniform_axis)),
    )
    inferred_current = (field_values - intercept) / slope
    inferred_step = np.diff(inferred_current)
    inferred_step = np.abs(inferred_step[np.abs(inferred_step) > 0])
    if len(inferred_step):
        current_quantum = np.median(inferred_step)
    else:
        current_quantum = spacing["median_step"]
    quantized = np.round(inferred_current / current_quantum) * current_quantum
    transition_idx = np.flatnonzero(np.diff(quantized) != 0)
    if len(transition_idx) >= 2:
        del_i = np.median(np.diff(axis[transition_idx + 1]))
    else:
        del_i = 64 * spacing["median_step"]
    del_i = max(float(del_i), float(spacing["median_step"]))
    offset_candidates = np.linspace(0.0, del_i, 128, endpoint=False)
    best_offset = 0.0
    best_error = np.inf
    for offset in offset_candidates:
        staircase_axis = del_i * np.floor((axis - offset) / del_i + 0.5)
        this_error = ((staircase_axis - inferred_current) ** 2).mean()
        if this_error < best_error:
            best_error = this_error
            best_offset = offset
    return dict(
        Del_I=del_i,
        step=spacing["median_step"],
        offset=float(best_offset),
        c_1=float(slope),
        c_0=float(intercept),
        c_2=0.0,
        vertoff=0.5,
        uniform_axis=spacing["uniform_axis"],
        max_spacing_error=float(spacing["max_spacing_error"]),
    )
