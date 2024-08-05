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
    if np.isscalar(desired_beta):
        assert desired_beta < 1000e-6, "You asked for a desired beta of over 1,000 μs√W.  This is not the beta value you are looking for!!!"
    else:
        assert desired_beta[-1] < 1000e-6, "You asked for a desired beta of over 1,000 μs√W.  This is not the beta value you are looking for!!!"
    linear_threshold = 100e-6
    if amplitude == 1.0:
        c_curve =  [
                8.84841307e-02,
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
        c_curve = [
                -3.54792496e-01,
                4.74405761e+06,
                -5.95918855e+11,
                4.98779166e+16,
                -2.49466965e+21,
                7.82865427e+25,
                -1.57455098e+30,
                2.02408858e+34,
                -1.60648454e+38,
                7.16623753e+41,
                -1.37365186e+45
        ]
        c_linear = [1.20357312e+01, 9.17498983e+05] 
    elif amplitude == 0.2:
        c_curve = [
                -1.78861374e-01,
                2.40897544e+06,
                -1.77277085e+11,
                9.26388401e+15,
                -2.95989268e+20,
                5.86098212e+24,
                -7.05992210e+28,
                4.75188891e+32,
                -1.24691247e+36,
                -3.00072381e+39,
                1.86363314e+43
         ]
        c_linear = [8.86472856e+00, 4.79777211e+05] 
    elif amplitude == 0.05:
        c_curve = [ 
                3.41398842e-01,
                6.86888916e+06,
                -9.45154990e+11,
                8.60865342e+16,
                -4.45800994e+21,
                1.41772441e+26,
                -2.86513894e+30,
                3.68984074e+34,
                -2.93180125e+38,
                1.30949420e+42,
                -2.51448623e+45
        ]
        c_linear = [1.16313219e+01, 1.81093419e+06] 
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
