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
        (10, 1.6816, 4.3987),
        (11.7996, 2.0908, 5.6696),
        (13.60006, 2.5583, 7.0707),
        (15.3997, 3.0091, 8.6477),
        (17.2001, 3.5688, 10.3898),
        (18.9997, 4.0651, 12.4032),
        (20.8002, 4.5997, 14.5975),
        (22.5998, 5.2121, 17.1804),
        (24.40027, 5.8534, 20.1967),
        (26.19987, 6.5583, 23.2631),
        (28.0003, 7.2702, 26.7712),
        (29.7999, 8.0251, 30.3686),
        (31.6004, 8.9074, 34.5012),
        (33.4, 9.7384, 38.7034),
        (35.1996, 10.7763, 42.6708),
        (37.0001, 11.6433, 46.9659),
        (38.79967, 12.6973, 51.2199),
        (40.6001, 13.8144, 55.3932),
        (42.3997, 14.9417, 59.7294),
        (44.2002, 16.2722, 64.1023),
        (46.0, 17.5555, 68.244),
        (47.8003, 19.0664, 72.5224),
        (49.5999, 20.5732, 76.7574),
        (51.5003, 22.0963, 81.1876),
        (53.1999, 23.941, 85.1532),
        (55.0, 25.6027, 89.3484),
        (56.80, 27.5236, 93.6942),
        (58.5996, 29.3019, 97.8921),
        (60.4001, 31.3594, 102.1701),
        (62.1997, 33.1336, 106.2936),
        (63.9993, 35.0956, 110.7996),
        (65.7997, 37.4469, 114.4828),
        (67.6000, 39.4635, 119.1428),
        (69.3998, 41.5064, 123.2025),
        (71.2003, 43.6143, 126.6790),
        (73.0, 45.9168, 131.4047),
        (74.8004, 48.0163, 135.4793),
        (76.6, 50.1507, 139.2970),
        (78.4004, 52.4808, 144.0103),
        (80.2000, 54.5556, 147.6949),
        (81.9996, 56.7011, 152.1547),
        (83.8001, 58.7643, 155.8218),
        (85.5997, 60.8571, 159.8310),
        (87.4002, 62.9501, 164.1420),
        (89.1998, 64.9480, 168.1456),
        (91.0002, 67.2708, 172.1686),
        (92.7998, 69.4676, 176.1556),
        (94.6003, 71.6768, 180.6902),
        (96.3999, 73.8858, 184.8543),
        (98.2004, 75.7488, 188.7464),
    ]
    # neat JF trick for organizing these data points
    prog_beta90, beta90, beta180 = map(array, zip(*datapoints))
    # }}}
    # {{{ prepare data into arrays for interpolation
    # gather programmed pulse lengths in array
    plen_prog = r_[0, prog_beta90, 2 * prog_beta90]
    # assume the longest pulse is about the correct length
    # and again gather into an array
    plen_actual = r_[0, beta90, beta180] * 2 * prog_beta90[-1] / beta180[-1]

    # }}}
    def zonefit(desired_actual):
        if desired_actual < 100:
            mask = np.ones_like(plen_prog, dtype=bool)
        else:
            mask = plen_prog > 40
        calibration_data = nddata(plen_prog[mask], [-1], ["plen"]).setaxis(
            "plen", plen_actual[mask]
        )
        calibration_data.sort("plen")
        # fit the programmed vs actual lengths to a polynomial
        if desired_actual < 100:
            c = calibration_data.polyfit("plen", order=10)
        else:
            c = calibration_data.polyfit("plen", order=1)
        return np.polyval(c[::-1], desired_actual)
    ret_val = np.vectorize(zonefit)(desired_actual)
    if ret_val.size > 1:
        return ret_val
    else:
        return ret_val.item()
