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
    if (type(desired_beta) ==float):
        assert desired_beta < 1000e-6, "You asked for a desired beta of over 1,000 μs√W.  This is not the beta value you are looking for!!!"
    else:
        assert desired_beta[-1] < 1000e-6, "You asked for a desired beta of over 1,000 μs√W.  This is not the beta value you are looking for!!!"
    linear_threshold = 100e-6
    if amplitude == 1.0:
        c_curve = [
            1.29614940e-01,
            6.05419346e+05,
            -3.74685011e+10,
            1.87746896e+15,
            -6.42496915e+19,
            1.45001963e+24,
            -2.08137249e+28,
            1.79383408e+32,
            -8.10627165e+35,
            1.13199343e+39,
            2.24515671e+42,
            ]
        c_linear = [3.28599542e+00, 1.01070497e+05]
    elif amplitude == 0.1:
        c_curve = [
           -2.73737244e-01,
           4.60824209e+06,
           -5.73979960e+11,
           4.79104378e+16,
           -2.39814728e+21,
           7.54873308e+25,
           -1.52565827e+30,
           1.97405428e+34,
           -1.57942808e+38,
           7.11242889e+41,
           -1.37801556e+45
        ]
        c_linear = [1.19657012e+01, 8.89588619e+05] 
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
