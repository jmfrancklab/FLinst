from pylab import array
import numpy as np
from pyspecdata import r_, nddata


def prog_beta(desired_actual):
    """
    Takes the desired beta (us *sqrt(W)) and tells the
    user what beta should be programmed in order to get the actual desired
    beta
    Parameters
    ==========
    desired_actual: float
                    the actual beta you wish the spincore to output,
                    in us sqrt(W)
    Returns
    =======
    retval: float
            The beta you tell spincore in order to get the desired actual.
    """
    # {{{ list of programmed beta, and actual beta - used in
    # generating the calibrated fit
    datapoints = [
        (1, 2.25869),
        (2, 5.78065),
        (3, 10.4132),
        (3.5, 13.2053),
        (4, 16.9808),
        (4.5, 20.4275),
        (5, 24.8538),
        (5.5, 30.0159),
        (6, 35.6903),
        (6.5, 42.2129),
        (7, 48.9577),
        (7.5, 55.977),
        (8, 63.0445),
        (8.5, 69.881),
        (9, 76.9727),
        (9.5, 84.51),
        (10, 91.700),
        (10.5, 98.63),
        (11, 105.327),
        (11.5, 112.9),
        (12, 120.264),
        (12.5, 126.2),
    ]
    # neat JF trick for organizing these data points
    progB, actB = map(array, zip(*datapoints))
    # }}}
    # {{{ prepare data into arrays for interpolation
    # gather programmed pulse lengths in array
    B_prog = r_[0, progB]
    # assume the longest pulse is about the correct length
    # and again gather into an array
    B_actual = r_[0, actB] * progB[-1] / actB[-1]

    # }}}
    def zonefit(desired_actual):
        if desired_actual < 60:
            mask = np.ones_like(B_prog, dtype=bool)
        else:
            mask = B_prog > 20
        calibration_data = nddata(B_prog[mask], [-1], ["beta"]).setaxis(
            "beta", B_actual[mask]
        )
        calibration_data.sort("beta")
        # fit the programmed vs actual lengths to a polynomial
        if desired_actual < 60:
            c = calibration_data.polyfit("beta", order=10)
        else:
            c = calibration_data.polyfit("beta", order=1)
        return np.polyval(c[::-1], desired_actual)

    ret_val = np.vectorize(zonefit)(desired_actual)
    if ret_val.size > 1:
        return ret_val
    else:
        return ret_val.item()
