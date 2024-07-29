from pylab import array
import numpy as np
from pyspecdata import r_, nddata


def prog_plen(desired_actual):
    """
    Takes the desired beta (us sqrt(W)) and tells the
    user what beta should be programmed in order to get the actual desired
    beta
    Parameters
    ==========
    desired_actual: float
                    the actual beta you wish the spincore to output,
                    in us*sqrt(W)
    Returns
    =======
    retval: float
            The beta you tell spincore in order to get the desired actual.
    """
    # {{{ list of programmed p90, actual p90*sqrt(W) and actual p180*sqrt(W) - used in
    # generating the calibrated fit
    # list of the programmed pulse length, the actual p90*sqrt(P)
    # and the actual p180*sqrt(P) based on the programmed p90
    datapoints = [
        (1.1547, 1.6816, 4.3987),
        (1.3625, 2.0908, 5.6696),
        (1.5704, 2.5583, 7.0707),
        (1.7782, 3.0091, 8.6477),
        (1.9861, 3.5688, 10.3898),
        (2.1939, 4.0651, 12.4032),
        (2.4018, 4.5997, 14.5975),
        (2.6096, 5.2121, 17.1804),
        (2.8175, 5.8534, 20.1967),
        (3.0253, 6.5583, 23.2631),
        (3.2332, 7.2702, 26.7712),
        (3.4410, 8.0251, 30.3686),
        (3.6489, 8.9074, 34.5012),
        (3.8567, 9.7384, 38.7034),
        (4.0645, 10.7763, 42.6708),
        (4.2724, 11.6433, 46.9659),
        (4.4802, 12.6973, 51.2199),
        (4.6881, 13.8144, 55.3932),
        (4.8959, 14.9417, 59.7294),
        (5.1038, 16.2722, 64.1023),
        (5.3116, 17.5555, 68.244),
        (5.5195, 19.0664, 72.5224),
        (5.7273, 20.5732, 76.7574),
        (5.9352, 22.0963, 81.1876),
        (6.1430, 23.941, 85.1532),
        (6.3509, 25.6027, 89.3484),
        (6.5587, 27.5236, 93.6942),
        (6.7665, 29.3019, 97.8921),
        (6.9744, 31.3594, 102.1701),
        (7.1822, 33.1336, 106.2936),
        (7.3900, 35.0956, 110.7996),
        (7.5979, 37.4469, 114.4828),
        (7.8058, 39.4635, 119.1428),
        (8.0136, 41.5064, 123.2025),
        (8.2215, 43.6143, 126.6790),
        (8.4293, 45.9168, 131.4047),
        (8.6372, 48.0163, 135.4793),
        (8.8450, 50.1507, 139.2970),
        (9.0529, 52.4808, 144.0103),
        (9.2607, 54.5556, 147.6949),
        (9.4685, 56.7011, 152.1547),
        (9.6764, 58.7643, 155.8218),
        (9.8842, 60.8571, 159.8310),
        (10.0921, 62.9501, 164.1420),
        (10.2999, 64.9480, 168.1456),
        (10.5078, 67.2708, 172.1686),
        (10.7156, 69.4676, 176.1556),
        (10.9235, 71.6768, 180.6902),
        (11.1313, 73.8858, 184.8543),
        (11.3392, 75.7488, 188.7464),
    ]
    # neat JF trick for organizing these data points
    prog90, beta90, beta180 = map(array, zip(*datapoints))
    # }}}
    # {{{ prepare data into arrays for interpolation
    # gather programmed pulse lengths in array
    plen_prog = r_[0, prog90, 2 * prog90]
    # assume the longest pulse is about the correct length
    # and again gather into an array
    plen_actual = r_[0, beta90, beta180] * 2 * prog90[-1] / beta180[-1]

    # }}}
    def zonefit(desired_actual):
        if desired_actual < 25:
            mask = np.ones_like(plen_prog, dtype=bool)
        else:
            mask = plen_prog > 10
        calibration_data = nddata(plen_prog[mask], [-1], ["plen"]).setaxis(
            "plen", plen_actual[mask]
        )
        calibration_data.sort("plen")
        # fit the programmed vs actual lengths to a polynomial
        if desired_actual < 25:
            c = calibration_data.polyfit("plen", order=10)
        else:
            c = calibration_data.polyfit("plen", order=1)
        return np.polyval(c[::-1], desired_actual)
    ret_val = np.vectorize(zonefit)(desired_actual)
    if ret_val.size > 1:
        return ret_val
    else:
        return ret_val.item()
