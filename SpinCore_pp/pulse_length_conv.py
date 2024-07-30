from pylab import array
import numpy as np
from pyspecdata import r_, nddata


def prog_plen(desired_actual, amplitude = 1.0):
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
            The pulse length you tell spincore in order to get the desired actual.
    """
    if amplitude > 0.5:
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
    else:
        datapoints = [
            (11.547, 4.1412, 15.2434),
            (13.6255, 5.7172, 20.3020),
            (15.7039, 7.5095, 25.2638),
            (17.7824, 9.5193, 30.327),
            (19.8608, 11.7134, 35.1643),
            (21.9393, 14.0303, 39.9120),
            (24.0178, 16.4052, 44.5099),
            (26.0962, 18.8642, 49.0761),
            (28.1747, 21.4557, 53.7334),
            (30.2532, 23.9185, 58.4419),
            (32.3316, 26.5755, 63.2849),
            (34.4101, 28.9640, 67.9343),
            (36.4885, 31.5071, 72.7484),
            (38.5670, 33.9187, 77.4533),
            (40.6455, 36.2690, 82.2564),
            (42.7239, 38.5646, 86.9304),
            (44.8024, 40.9847, 91.8215),
            (46.8808, 43.2152, 96.5977),
            (48.9593, 45.4133, 101.2667),
            (51.0378, 47.7366, 106.0197),
            (53.1162, 50.0399, 110.9629),
            (55.1947, 52.2936, 115.7806),
            (57.2731, 54.5585, 120.5675),
            (59.3516, 56.9132, 125.5209),
            (61.4301, 59.1557, 129.9507),
            (63.5085, 61.3713, 134.8636),
            (65.5870, 63.7982, 139.9420),
            (67.6655, 65.9272, 144.4730),
            (69.7439, 68.4241, 149.3814),
            (71.8224, 70.5704, 154.0034),
            (73.9008, 73.0067, 158.8563),
            (75.9793, 75.3862, 163.7938),
            (78.0578, 77.6440, 168.4955),
            (80.1362, 79.7656, 173.0118),
            (82.2147, 82.2667, 178.15414),
            (84.2931, 84.5948, 183.0573),
            (86.3716, 87.00512, 188.0497),
            (88.4501, 89.2426, 192.6221),
            (90.5285, 91.4740, 197.0563),
            (92.607, 93.7013, 201.7675),
            (94.6854, 96.1666, 206.5946),
            (96.7639, 98.2554, 211.3164),
            (98.8424, 100.79537, 216.2765),
            (100.9208, 103.0646, 220.8820),
            (102.9993, 105.4331, 225.9226),
            (105.0777, 107.9422, 230.7902),
        ]
    # neat JF trick for organizing these data points
    prog_beta90, beta90, beta180 = map(array, zip(*datapoints))
    # }}}
    sqrt_P = amplitude * np.sqrt(75)
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
    ret_val /= sqrt_P #convert from beta to pulse length
    if ret_val.size > 1:
        return ret_val
    else:
        return ret_val.item()
