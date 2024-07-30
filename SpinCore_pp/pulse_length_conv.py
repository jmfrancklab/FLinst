from pylab import array
import numpy as np
from pyspecdata import r_, nddata


def prog_plen(desired_actual, amplitude=1.0):
    """
    Takes the desired beta (us sqrt(W)) and tells the
    user what pulse length should be programmed in order to get the actual desired
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
        # {{{ list of programmed p90, actual p90*sqrt(W) - used in
        # generating the calibrated fit
        datapoints = [
            (1.1547, 1.6816),
            (1.3625, 2.0908),
            (1.5704, 2.5583),
            (1.7782, 3.0091),
            (1.9861, 3.56888),
            (2.1939, 4.06512),
            (2.4018, 4.59975),
            (2.6096, 5.21214),
            (2.8175, 5.8534),
            (3.0253, 6.5583),
            (3.2332, 7.2702),
            (3.441, 8.0251),
            (3.6489, 8.9074),
            (3.8567, 9.7384),
            (4.0645, 10.7763),
            (4.2724, 11.6433),
            (4.4802, 12.6973),
            (4.6881, 13.8144),
            (4.8959, 14.9417),
            (5.1038, 16.2722),
            (5.31162, 17.5555),
            (5.5195, 19.0664),
            (5.7273, 20.5732),
            (5.9352, 22.0963),
            (6.143, 23.941),
            (6.35085, 25.6027),
            (6.5587, 27.5236),
            (6.7665, 29.3019),
            (6.9744, 31.3594),
            (7.1822, 33.1336),
            (7.39, 35.0956),
            (7.5979, 37.4469),
            (7.80578, 39.4635),
            (8.0136, 41.5064),
            (8.2215, 43.6143),
            (8.4293, 45.9168),
            (8.6372, 48.0163),
            (8.845, 50.1507),
            (9.0529, 52.4808),
            (9.2607, 54.5556),
            (9.4685, 56.7011),
            (9.6764, 58.7643),
            (9.8842, 60.8571),
            (10.0921, 62.9501),
            (10.2999, 64.9480),
            (10.5078, 67.2708),
            (10.7156, 69.4676),
            (10.9235, 71.6768),
            (11.1313, 73.8858),
            (11.3392, 75.7488),
        ]
    else:
        datapoints = [
            (11.547, 4.1412),
            (13.6255, 5.7172),
            (15.7039, 7.5095),
            (17.7824, 9.5193),
            (19.8608, 11.7134),
            (21.9393, 14.0303),
            (24.0178, 16.4052),
            (26.0962, 18.8642),
            (28.1747, 21.4557),
            (30.2532, 23.9185),
            (32.3316, 26.5755),
            (34.4101, 28.9640),
            (36.4885, 31.5071),
            (38.5670, 33.9187),
            (40.6455, 36.2690),
            (42.7239, 38.5646),
            (44.8024, 40.9847),
            (46.8808, 43.2152),
            (48.9593, 45.4133),
            (51.0378, 47.7366),
            (53.1162, 50.0399),
            (55.1947, 52.2936),
            (57.2731, 54.5585),
            (59.3516, 56.9132),
            (61.4301, 59.1557),
            (63.5085, 61.3713),
            (65.5870, 63.7982),
            (67.6655, 65.9272),
            (69.7439, 68.4241),
            (71.8224, 70.5704),
            (73.9008, 73.0067),
            (75.9793, 75.3862),
            (78.0578, 77.6440),
            (80.1362, 79.7656),
            (82.2147, 82.26674),
            (84.2931, 84.5948),
            (86.3716, 87.00512),
            (88.4501, 89.2426),
            (90.5285, 91.4740),
            (92.607, 93.7013),
            (94.6854, 96.1666),
            (96.7639, 98.2554),
            (98.8424, 100.79537),
            (100.9208, 103.0646),
            (102.9993, 105.4331),
            (105.0777, 107.9422),
        ]
    # neat JF trick for organizing these data points
    t_p, beta = map(array, zip(*datapoints))
    # }}}
    # {{{ prepare data into arrays for interpolation
    # gather programmed pulse lengths in array
    plen_prog = r_[0, t_p]
    sqrt_P = amplitude * np.sqrt(75)
    # assume the longest pulse is about the correct length
    # and again gather into an array
    plen_actual = r_[0, beta] * ((2 * t_p[-1] * sqrt_P) / (2 * beta[-1]))

    # }}}
    def zonefit(desired_actual):
        if desired_actual < 100:
            mask = np.ones_like(plen_prog, dtype=bool)
        else:
            mask = plen_prog > 60  # where line is curved
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
