"""
HP Shim Power Supply
====================

This script provides a small shim-mapping layer for HP6623A supplies.
Named shim channels (e.g., Z0, Z1, Z2, X, Y) are mapped to a specific
instrument address and output channel.
"""

from collections import OrderedDict

from Instruments import ShimDictMapping, prologix_connection


with prologix_connection() as p:
    with ShimDictMapping(
        OrderedDict(
            {
                "Z0": (3, 0),
                "Y": (3, 1),
                # "Z1": (5, 0),
                # "Z2": (5, 1),
                # "X": (5, 2),
            }
        ),
        prologix_instance=p,
        safe_current=1.8,
        overvoltage=16.0,
    ) as shims:
        # {{{ Commented HP2 attributes since we are not using
        # them currently. We will use them when we implement
        # Z1 and Z2 correction.
        shims.I_limit["Z0"] = 1.5
        shims.V_limit["Z0"] = 1.0
        shims.I_limit["Y"] = 1.5
        shims.V_limit["Y"] = 1.0
        # shims.I_limit["Z1"] = 0.0
        # shims.V_limit["Z1"] = 0.0
        # shims.I_limit["Z2"] = 0.0
        # shims.V_limit["Z2"] = 0.0
        # shims.I_limit["X"] = 0.0
        # shims.V_limit["X"] = 0.0
        # }}}
        input("Press enter to exit")
        shims.V_limit[:] = 0.0
        shims.I_limit[:] = 0.0
