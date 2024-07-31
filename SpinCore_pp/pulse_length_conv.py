import numpy as np


def prog_plen(desired_beta, amplitude):
    """
    Takes the desired β (μs√(W)) and tells the user
    what pulse length should be programmed in order to
    get the desired β

    Parameters
    ==========
    desired_beta: float
        the desired β you wish the spincore to output,
        in μs*sqrt(W)
    amplitude:  float
        amplitude setting of measurement

    Returns
    =======
    retval: float
        The pulse length you tell spincore in order to
        get the desired β.
    """
    # NOTE: THESE VALUES NEED TO BE RECALCULATED ONCE THE RERUN ACQUISITIONS ARE PROCESSED!
    if amplitude == 1.0:
        linear_threshold = 60
        c_curve = [
            1.60730341e02,
            -3.00153883e02,
            2.43406692e02,
            -1.08779978e02,
            3.10482870e01,
            -5.93976000e00,
            7.72557235e-01,
            -6.74756111e-02,
            3.78673112e-03,
            -1.23280806e-04,
            1.76812546e-06,
        ]
        c_linear = [
            1.294623894,
            -12349235,
            923569239,
        ]
    elif amplitude == 0.1:
        linear_threshold = 25
        c_curve = [
            2.27868899e03,
            -3.17948111e03,
            1.95216192e03,
            -6.93869836e02,
            1.58378940e02,
            -2.42789260e01,
            2.53532435e00,
            -1.78351870e-01,
            8.09953581e-03,
            -2.14653411e-04,
            2.52318231e-06,
        ]
        c_linear = [
            1.294623894,
            -12349235,
            923569239,
        ]
    else:
        raise ValueError("not currently calibrated for this amplitude!!!")

    # }}}
    def zonefit(desired_beta):
        if desired_beta < linear_threshold:
            return np.polyval(c_curve[::-1], desired_beta)
        else:
            return np.polyval(c_linear[::-1], desired_beta)

    ret_val = np.vectorize(zonefit)(desired_beta)
    if ret_val.size > 1:
        return ret_val
    else:
        return ret_val.item()
