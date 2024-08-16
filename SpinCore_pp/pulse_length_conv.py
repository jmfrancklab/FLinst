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
        c_curve = [-2.18604440e-02,
                1.12609436e+05,
                -7.02313385e+08,
                2.81572086e+13,
                -5.75070630e+17,
                6.50493142e+21,
                -4.13166742e+25,
                1.31890898e+29,
                -8.88908652e+31,
                -5.61555178e+35,
                1.07957439e+39
        ]
        c_linear = [1.27141619e-01, 1.02116203e+05] 
    elif amplitude == 0.2:
        c_curve = [-4.30951070e-02,
                1.45897573e+05,
                -2.18475287e+09,
                3.77237323e+13,
                -1.25445609e+17,
                -3.92335103e+21,
                5.56015209e+25,
                -3.07389834e+29,
                7.03641877e+32,
                -8.02184129e+34,
                -1.47488423e+39
         ]
        c_linear = [8.07420843e-01, 9.86507116e+04] 
    elif amplitude == 0.05:
        c_curve = [-8.56537987e-03,
                1.19786732e+05,
                1.37880448e+08,
                -1.75451873e+13,
                7.21581204e+17,
                -1.60069793e+22,
                2.07317160e+26,
                -1.60910164e+30,
                7.37276574e+33,
                -1.83970614e+37,
                1.92860602e+40 
         ]
        c_linear = [2.00670966e-01, 1.14235895e+05] 
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
