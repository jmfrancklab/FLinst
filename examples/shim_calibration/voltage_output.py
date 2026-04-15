# TODO ☐: not reviewed: think just moved -- check
"""
Voltage Output Characterization
===============================

Characterize the discrete output voltages supported by selected HP6623A
channels by stepping each channel through a voltage range and reporting the
observed setpoints.

This is provided as an example rather than an automated live test because it
is meant to be run intentionally against attached hardware to characterize the
allowed output voltages for a specific setup. The reported values can then be
used to update the corresponding limits or lookup values in the main code.
"""

from Instruments import HP6623A, prologix_connection
import numpy as np

# give a series of channel and voltage pairs.
ch_max_V = [(0, 1), (6, 10.5)]
with (
    prologix_connection() as p,
    HP6623A(prologix_instance=p, address=3) as HP1,
):
    HP1.safe_current = 1.8
    for ch, test_max_V in ch_max_V:
        HP1.I_limit[ch] = 1.5
        HP1.V_limit[ch] = 0.0
        step = 0.006
        n_steps = int(test_max_V / step) + 1
        for thisV in np.arange(0, test_max_V + step / 2, step / 2):
            HP1.V_limit[ch] = thisV
            print(
                f"channel {ch} is set to {thisV} V and it is actually"
                f" set to {HP1.V_limit[ch]}."
            )
        HP1.V_limit[ch] = 0.0
        result = np.array(sorted(list(HP1.observed_V[ch])))
        print(
            "for channel",
            ch,
            "allowed values are",
            result,
            "(",
            len(result),
            "/",
            n_steps,
            ")",
        )
