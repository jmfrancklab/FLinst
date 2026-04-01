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
        shims["Z0"].I_limit = 1.5
        shims["Z0"].V_limit = 1.0
        shims["Y"].I_limit = 1.5
        shims["Y"].V_limit = 1.0
        # shims["Z1"].I_limit = 0.0
        # shims["Z1"].V_limit = 0.0
        # shims["Z2"].I_limit = 0.0
        # shims["Z2"].V_limit = 0.0
        # shims["X"].I_limit = 0.0
        # shims["X"].V_limit = 0.0
        # }}}
        input("Press enter to exit")
        shims[:].V_limit = 0.0
        shims[:].I_limit = 0.0
