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
        (1, 0.2, 0.603),
        (2.6333, 0.854, 1.4624),
        (4.2667, 1.2881, 2.413),
        (5.9, 1.5898, 4.2176),
        (7.5333, 2.069, 6.7284),
        (9.1667, 2.7225, 9.8321),
        (10.8, 3.569, 13.3085),
        (12.433, 4.715, 17.0918),
        (14.0667, 5.9358, 20.9478),
        (15.7, 7.2835, 24.7825),
        (17.333, 8.9098, 28.6645),
        (18.9667, 10.5522, 32.6229),
        (20.6, 12.2771, 36.2588),
        (22.233, 14.0948, 39.959),
        (23.8667, 15.9531, 43.5116),
        (25.5, 17.8739, 47.0756),
        (27.1333, 19.8158, 50.682),
        (28.7667, 21.8677, 54.3098),
        (30.4, 23.8168, 57.986),
        (32.0333, 25.7351, 61.709),
        (33.667, 27.6883, 65.276),
        (35.3, 29.5504, 68.8988),
        (36.9333, 31.5029, 72.7002),
        (38.5667, 33.3261, 76.2829),
        (40.2, 35.199, 80.0737),
        (41.8333, 36.991, 83.7567),
        (43.4667, 38.8625, 87.4775),
        (45.1, 40.5405, 91.0234),
        (46.7333, 42.4791, 94.9011),
        (48.3667, 43.8854, 98.3805),
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
def prog_plen_lo(desired_actual):
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
