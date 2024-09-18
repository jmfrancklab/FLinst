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
        linear_threshold = 222e-6
        c_nonlinear = r_[
                2.83254968e+01,
                1.03867025e+05,
                -2.73366110e+09,
                -1.56481154e+14,
                -4.80881950e+18,
                -8.65256318e+22,
                -9.52607928e+26,
                -6.49641533e+30,
                -2.67546621e+34,
                -6.09361358e+37,
                -5.89263001e+40
         ]
        c_linear = r_[1.66630601e-01, 1.26926858e+05]
    elif settings["amplitude"] == 0.2:
        linear_threshold = (
            230e-6  # we found different thresholds for different amplitudes
        )
        c_nonlinear = r_[
                1.23888584e+02,
                5.97001269e+05,
                1.04375266e+10,
                5.88735236e+14,
                1.62405348e+19,
                2.52493339e+23,
                2.36657464e+27,
                1.36586450e+31,
                4.74816650e+34,
                9.11010743e+37,
                7.40065857e+40 
        ]
        c_linear = r_[3.99316443e+00, 5.21058492e+05]
    elif settings["amplitude"] == 0.1:
        linear_threshold = (
            230e-6  # we found different thresholds for different amplitudes
        )
        c_nonlinear = r_[
                2.51955026e+02,
                7.25813809e+05,
                -3.11011134e+10,
                -1.08128822e+15,
                -2.06213928e+19,
                -2.43901939e+23,
                -1.87672640e+27,
                -9.43897849e+30,
                -2.99801032e+34,
                -5.46040994e+37,
                -4.34595668e+40
                ]
        c_linear = r_[2.83491811e+00, 1.08705017e+06]
    elif settings["amplitude"] == 0.05:
        linear_threshold = (
            260e-6  # we found different thresholds for different amplitudes
        )
        c_nonlinear = r_[
                6.39332096e+02,
                2.55480324e+06,
                1.70083937e+10,
                7.28033155e+14,
                1.52955864e+19,
                1.86373755e+23,
                1.40680247e+27,
                6.69775289e+30,
                1.96375618e+34,
                3.24559827e+37,
                2.31731361e+40
         ]
        c_linear = r_[-2.05940437e+00,  2.46360552e+06]
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
