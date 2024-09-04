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
        linear_threshold = 200e-6
        c_nonlinear = r_[
                2.68496032e+01,
                1.54958845e+05,
                8.28561689e+08,
                -3.20835099e+13,
                -2.69415213e+18,
                -7.30200109e+22,
                -1.04245486e+27,
                -8.66033141e+30,
                -4.20815065e+34,
                -1.11019573e+38,
                -1.22948186e+41
         ]
        c_linear = r_[1.95945884e-01, 1.33178711e+05]
    elif settings["amplitude"] == 0.2:
        linear_threshold = (
            310e-6  # we found different thresholds for different amplitudes
        )
        c_nonlinear = r_[
                1.53530304e+02,
                4.69799799e+05,
                3.26390522e+08,
                3.97291280e+13,
                1.00417750e+18,
                1.21574434e+22,
                8.14008030e+25,
                3.10362647e+29,
                6.41280707e+32,
                5.96434320e+35,
                1.09405855e+38 
        ]
        c_linear = r_[4.56119399e+00, 4.81125564e+05]
    elif settings["amplitude"] == 0.1:
        linear_threshold = (
            270e-6  # we found different thresholds for different amplitudes
        )
        c_nonlinear = r_[
               2.71110558e+02,
               1.26092360e+06,
               2.10477748e+10,
               7.32201360e+14,
               1.37697994e+19,
               1.54149832e+23,
               1.07532575e+27, 
               4.71428707e+30,
               1.26063506e+34,
               1.87492898e+37,
               1.18598034e+40 
                 ]
        c_linear = r_[1.99000734e+00, 9.94243760e+05]
    elif settings["amplitude"] == 0.05:
        linear_threshold = (
            230e-6  # we found different thresholds for different amplitudes
        )
        c_nonlinear = r_[
                5.13484572e+02,
                2.44244879e+06,
                1.83230003e+10,
                6.72020583e+14,
                1.42875534e+19,
                1.90209584e+23,
                1.61298290e+27,
                8.64097771e+30,
                2.82075013e+34,
                5.11349633e+37,
                3.94317419e+40
         ]
        c_linear = r_[6.15670614e-02, 2.23001110e+06]
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
