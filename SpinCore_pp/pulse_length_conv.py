import numpy as np


def prog_plen(desired_beta, amplitude):
    """
    Takes the desired β (μs√(W)) and tells the user
    what pulse length should be programmed in order to
    get the desired β
    ** Note: the following coefficients are specifically for when the
    deblanking is 1 us and therefore the pulse shapes are wonky **

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
    if np.isscalar(desired_beta):
        assert desired_beta < 1000e-6, "You asked for a desired beta of over 1,000 μs√W.  This is not the beta value you are looking for!!!"
    else:
        assert desired_beta[-1] < 1000e-6, "You asked for a desired beta of over 1,000 μs√W.  This is not the beta value you are looking for!!!"
    linear_threshold = 100e-6
    if amplitude == 1.0:
        c_curve =  [
                -8.84841307e-02,
                6.55556440e+05,
                -4.69857455e+10,
                2.93923872e+15,
                -1.29939177e+20,
                3.87062707e+24,
                -7.62589253e+28,
                9.75456190e+32,
                -7.77020412e+36,
                3.49583577e+40,
                -6.77665633e+43
             ]
        c_linear = [3.48764362e+00, 1.01357692e+05]
    elif amplitude == 0.1:
        c_curve = [-1.62998207e-01,
                1.21649137e+06,
                -9.52394324e+09,
                4.27424338e+13,
                2.74572110e+19,
                -1.52994986e+24,
                4.03585362e+28,
                -6.08790488e+32,
                5.37176819e+36,
                -2.58581092e+40,
                5.25471331e+43
                ]
        c_linear = [1.87827645e+00, 1.06425500e+06] 
    elif amplitude == 0.2:
        c_curve = [-1.34853331e+00,
                7.97484995e+05,
                -1.53053658e+10,
                3.36352634e+14,
                -3.46369790e+18,
                1.30572241e+22,
                5.08941012e+25,
                -6.26236299e+29,
                1.72966943e+33,
                1.86321080e+35,
                -5.22477826e+39]
        c_linear = [3.54846532e+00, 4.97504125e+05] 
    elif amplitude == 0.05:
        c_curve = [
                -5.44563661e+00,
                2.96227215e+06,
                -5.72743016e+10,
                3.04582938e+15,
                -9.04768615e+19,
                1.57713073e+24,
                -1.68492579e+28,
                1.11808412e+32,
                -4.49625171e+35,
                1.00367069e+39,
                -9.54606566e+41
                ]
        c_linear = [3.66783425e+00, 2.30130747e+06] 
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
