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
            1.52779970e00,
            6.46342316e-01,
            -4.20790841e-02,
            1.54615214e-03,
            -3.22038534e-05,
            4.11797855e-07,
            -3.34941665e-09,
            1.73822364e-11,
            -5.57199254e-14,
            1.00500791e-16,
            -7.79871620e-20,
        ]
        c_linear = [3.69252691, 0.09851093]
    elif amplitude == 0.1:
        linear_threshold = 25
        c_curve = [
            5.88195827e03,
            -7.33265938e01,
            1.52741371e-01,
            1.05325651e-03,
            -1.36835426e-06,
            -1.74874468e-08,
            -1.15607351e-11,
            2.37656268e-13,
            4.99773612e-16,
            -3.98586789e-18,
            5.02175704e-21,
        ]
        c_linear = [6.49990799, 0.07069775]
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
