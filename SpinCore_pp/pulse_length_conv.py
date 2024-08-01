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
    assert desired_beta[-1] < 1000e-6, "You asked for a desired beta of over 1,000 μs√W.  This is not the beta value you are looking for!!!"
    linear_threshold = 100e-6
    if amplitude == 1.0:
        c_curve = [
            1.43847887e-01,
            6.53636766e05,
            -4.56741958e10,
            2.78823021e15,
            -1.20097177e20,
            3.48337724e24,
            -6.68632180e28,
            8.34587735e32,
            -6.50244107e36,
            2.86944940e40,
            -5.47275992e43,
        ]
        c_linear = [3.56177606e00, 1.02937057e05]
    elif amplitude == 0.1:
        c_curve = [
            -1.53710953e-01,
            4.78586837e06,
            -6.10725991e11,
            5.22043434e16,
            -2.66724479e21,
            8.55685579e25,
            -1.76080232e30,
            2.31759121e34,
            -1.88465235e38,
            8.61892078e41,
            -1.69461930e45,
        ]
        c_linear = [1.19373725e01, 9.50492101e05]
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
