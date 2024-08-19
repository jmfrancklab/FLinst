import numpy as np
import SpinCore_pp as spc

def prog_plen(desired_beta, settings):
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
    settings:  configuration
        contains the following keys.  It's crucial that these get used in the pulse sequence.

        :amplitude: float
        :deblank_us: float

    Returns
    =======
    retval: float
        The pulse length you tell spincore in order to
        get the desired β.
    """
    assert isinstance(
        settings,spc.config_parser_fn.configuration), "You need to pass your configuration dict so I know what the amplitude and deblank time are"
      
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
        c_nonlinear = [
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
        c_linear = [3.48764362e00, 1.01357692e05]
    elif settings["amplitude"] == 0.1:
        linear_threshold = 270e-6
        c_nonlinear = [
            -1.62998207e-01,
            1.21649137e06,
            -9.52394324e09,
            4.27424338e13,
            2.74572110e19,
            -1.52994986e24,
            4.03585362e28,
            -6.08790488e32,
            5.37176819e36,
            -2.58581092e40,
            5.25471331e43,
        ]
        c_linear = [1.87827645e00, 1.06425500e06]
    elif settings["amplitude"] == 0.2:
        linear_threshold = 270e-6
        c_nonlinear = [
            -1.34853331e00,
            7.97484995e05,
            -1.53053658e10,
            3.36352634e14,
            -3.46369790e18,
            1.30572241e22,
            5.08941012e25,
            -6.26236299e29,
            1.72966943e33,
            1.86321080e35,
            -5.22477826e39,
        ]
        c_linear = [3.54846532e00, 4.97504125e05]
    elif settings["amplitude"] == 0.05:
        linear_threshold = 150e-6
        c_nonlinear = [
                3.75442878e+02,
                2.00599762e+06,
                -8.17658362e+10,
                -6.14612522e+15,
                -2.47655751e+20,
                -5.88569415e+24,
                -8.65005568e+28,
                -7.95171001e+32,
                -4.45091091e+36,
                -1.38696656e+40,
                -1.84433605e+43
            ]
        c_linear = [2.31318373e+00, 2.49223410e+06]
    else:
        raise ValueError("not currently calibrated for this amplitude!!!")

    # }}}
    def zonefit(desired_beta):
        if desired_beta > linear_threshold:
            return np.polyval(c_linear[::-1], desired_beta)
        else:
            return np.polyval(c_nonlinear[::-1], desired_beta - linear_threshold)

    ret_val = np.vectorize(zonefit)(desired_beta)
    if ret_val.size > 1:
        return ret_val
    else:
        return ret_val.item()
