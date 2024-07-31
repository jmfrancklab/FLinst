import numpy as np


def prog_plen(desired_beta, amplitude):
    """
    Takes the desired beta (μs sqrt(W)) and tells the
    user what pulse length should be programmed in order to get the actual desired
    beta
    Parameters
    ==========
    desired_actual: float
                    the desired beta you wish the spincore to output,
                    in μs*sqrt(W)
    amplitude:  float
                amplitude setting of measurement
    Returns
    =======
    retval: float
            The pulse length you tell spincore in order to get the desired beta.
    """
    if amplitude > 0.5:
        c = [
            1.60730341e02 + 0.0j,
            -3.00153883e02 + 0.0j,
            2.43406692e02 + 0.0j,
            -1.08779978e02 + 0.0j,
            3.10482870e01 + 0.0j,
            -5.93976000e00 + 0.0j,
            7.72557235e-01 + 0.0j,
            -6.74756111e-02 + 0.0j,
            3.78673112e-03 + 0.0j,
            -1.23280806e-04 + 0.0j,
            1.76812546e-06 + 0.0j,
        ]
    else:
        c = [
            2.27868899e03 + 0.0j,
            -3.17948111e03 + 0.0j,
            1.95216192e03 + 0.0j,
            -6.93869836e02 + 0.0j,
            1.58378940e02 + 0.0j,
            -2.42789260e01 + 0.0j,
            2.53532435e00 + 0.0j,
            -1.78351870e-01 + 0.0j,
            8.09953581e-03 + 0.0j,
            -2.14653411e-04 + 0.0j,
            2.52318231e-06 + 0.0j,
        ]

    # }}}
    def zonefit(desired_beta):
        return np.polyval(c[::-1], desired_beta)

    ret_val = np.vectorize(zonefit)(desired_beta)
    if ret_val.size > 1:
        return ret_val
    else:
        return ret_val.item()
