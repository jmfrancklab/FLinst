import numpy as np
from numpy import r_


def prog_plen(desired_beta, settings):
    """
    Takes the desired β (s√(W)) and configuration file
    to calculate what pulse length should be programmed in order to
    get the desired β based on the amplitude and deblank setting.

    Parameters
    ==========
    desired_beta : float
        The desired β you wish the spincore to output,
        in s*sqrt(W).
    settings :  dict-like
        Contains the following keys.  It's crucial that these get used in
        the pulse sequence.

        :amplitude: float
        :deblank_us: float

    Returns
    =======
    retval : float
        The pulse length you tell spincore in order to get the desired β.
    """
    if np.isscalar(desired_beta):
        assert (
            desired_beta < 1000e-6
        ), "You asked for a desired beta of over 1,000 μs√W.  This is not the beta value you are looking for!!!"
    else:
        assert (
            desired_beta[-1] < 1000e-6
        ), "You asked for a desired beta of over 1,000 μs√W.  This is not the beta value you are looking for!!!"
    assert (
        settings["deblank_us"] == 50
    ), "currently only calibrated for deblank_us = 50, so you almost definitely want to set that value in your active.ini"
    if settings["amplitude"] == 1.0:
        linear_threshold = 270e-6
        c_nonlinear = r_[
            -8.84841307e-02,
            6.55556440e05,
            -4.69857455e10,
            2.93923872e15,
            -1.29939177e20,
            3.87062707e24,
            -7.62589253e28,
            9.75456190e32,
            -7.77020412e36,
            3.49583577e40,
            -6.77665633e43,
        ]
        c_linear = r_[3.48764362e00, 1.01357692e05]
    elif settings["amplitude"] == 0.2:
        linear_threshold = (
            310e-6  # we found different thresholds for different amplitudes
        )
        c_nonlinear = r_[
            1.62924179e02,
            4.91729568e05,
            -1.99215893e09,
            -6.38076923e13,
            -1.05046642e18,
            -1.04830747e22,
            -6.88084080e25,
            -3.02459440e29,
            -8.58707023e32,
            -1.41598700e36,
            -1.02210088e39,
        ]
        c_linear = r_[-7.43656432e00, 5.48421364e05]
    elif settings["amplitude"] == 0.1:
        linear_threshold = (
            270e-6  # we found different thresholds for different amplitudes
        )
        c_nonlinear = r_[
            2.93528215e02,
            9.59757416e05,
            -1.32947207e10,
            -5.17620066e14,
            -1.05255134e19,
            -1.27041564e23,
            -9.58050939e26,
            -4.56587780e30,
            -1.33800953e34,
            -2.20250690e37,
            -1.55941251e40,
        ]
        c_linear = r_[4.38010537e00, 1.06971597e06]
    elif settings["amplitude"] == 0.05:
        linear_threshold = (
            150e-6  # we found different thresholds for different amplitudes
        )
        c_nonlinear = r_[
            3.75442878e02,
            2.00599762e06,
            -8.17658362e10,
            -6.14612522e15,
            -2.47655751e20,
            -5.88569415e24,
            -8.65005568e28,
            -7.95171001e32,
            -4.45091091e36,
            -1.38696656e40,
            -1.84433605e43,
        ]
        c_linear = r_[2.31318373e00, 2.49223410e06]
    else:
        raise ValueError("not currently calibrated for this amplitude!!!")

    # }}}
    def zonefit(desired_beta):
        """Calculates the pulse length that should be fed to the SpinCore
        to obtain the desired beta based off of the coefficients for the
        linear and nonlinear regimes of the calibrated pulse lengths for
        a given amplitude.

        Parameters
        ==========
        desired_beta: float
            Beta that the user wants to obtain from the output pulse.
        
        Returns
        =======
        retval: ndarray
            Array containing the pulse length that will enable the
            SpinCore to output the desired beta(s).
        """    
        if desired_beta > linear_threshold:
            return np.polyval(c_linear[::-1], desired_beta)
        else:
            return np.polyval(
                c_nonlinear[::-1], desired_beta - linear_threshold
            )

    ret_val = np.vectorize(zonefit)(desired_beta)
    if ret_val.size > 1:
        return ret_val
    else:
        return ret_val.item()
