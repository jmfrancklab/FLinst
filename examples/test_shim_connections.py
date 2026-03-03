"""
HP Shim Power Supply
====================

This script provides a small shim-mapping layer for two HP6623A supplies.
Named shim channels (e.g., Z0, Z1, Z2, X, Y) are mapped to a specific
instrument and output channel, and item assignment applies a current limit,
voltage limit, and output on/off state in one call.
"""

from collections import OrderedDict
from collections.abc import Iterable
from Instruments import HP6623A, prologix_connection
import logging


class ShimCurrentMapping:
    """Dictionary-like shim controller with ordered, vector-style access."""

    def __init__(self, shim_dict, default_v_limit=15.0, overvoltage=15.0):
        assert isinstance(shim_dict, OrderedDict), (
            "shim_dict must be an OrderedDict"
        )
        self._shim_dict = shim_dict
        self._default_v_limit = default_v_limit
        for _, (inst, ch) in self.connections():
            inst.set_overvoltage(ch, overvoltage)

    def __len__(self):
        return len(self._shim_dict)

    def __iter__(self):
        return iter(self._shim_dict)

    def __contains__(self, which_shim):
        return which_shim in self._shim_dict

    def __getitem__(self, which_shim):
        if isinstance(which_shim, slice):
            ordered_names = list(self._shim_dict)
            return [self[name] for name in ordered_names[which_shim]]
        if isinstance(which_shim, int):
            ordered_names = list(self._shim_dict)
            return self[ordered_names[which_shim]]
        if isinstance(which_shim, Iterable) and not isinstance(
            which_shim, (str, bytes)
        ):
            return [self[item] for item in which_shim]
        hp_inst, ch = self._shim_dict[which_shim]
        return hp_inst.I_limit[ch]

    def __setitem__(self, which_shim, value_oneormore):
        # translate slice or int to list of shim names
        if isinstance(which_shim, slice):
            which_shim = list(self._shim_dict)[which_shim]
        elif isinstance(which_shim, int):
            which_shim = list(self._shim_dict)[which_shim]

        if isinstance(which_shim, Iterable) and not isinstance(
            which_shim, (str, bytes)
        ):
            # which shim given as a vector-like quantity
            if isinstance(value_oneormore, Iterable):
                assert all(
                    isinstance(v, (int, float)) for v in value_oneormore
                ), "values must be numbers!"
                if len(which_shim) != len(value_oneormore):
                    raise ValueError(
                        "number of shim values must match target shims"
                    )
                for this_shim, this_value in zip(which_shim, value_oneormore):
                    self[this_shim] = this_value
                return
            for this_shim in which_shim:
                self[this_shim] = value_oneormore
            return
        else:
            hp_inst, ch = self._shim_dict[which_shim]
            v_limit = self._default_v_limit
            if isinstance(value_oneormore, tuple):
                if len(value_oneormore) != 2:
                    raise ValueError(
                        "single-shim assignment tuple must be"
                        "(current, v_limit)"
                    )
                value_oneormore, v_limit = value_oneormore
            if value_oneormore == 0.0:
                hp_inst.I_limit[ch] = 0.0
                hp_inst.V_limit[ch] = 0.0
                hp_inst.output[ch] = False
                logging.info(f"Shim {which_shim} is turned off")
                return
            else:
                hp_inst.V_limit[ch] = v_limit
                hp_inst.I_limit[ch] = value_oneormore
                hp_inst.output[ch] = True
                logging.info(
                    f"Shim {which_shim} is on with current"
                    f" set to {value_oneormore}."
                )

    def items(self):
        """Return an iterable of (name, current) pairs."""
        for name in self:
            yield name, self[name]

    def connections(self):
        """Return an iterable of (name, (instrument, channel)) pairs."""
        return self._shim_dict.items()


with prologix_connection() as p:
    with HP6623A(prologix_instance=p, address=3) as HP1:
        with HP6623A(prologix_instance=p, address=5) as HP2:
            HP1.safe_current_on_enable = 1.8
            HP2.safe_current_on_enable = 1.8

            shims = ShimCurrentMapping(
                OrderedDict(
                    {
                        "Z0": (HP1, 0),
                        "Y": (HP1, 1),
                        "Z1": (HP2, 0),
                        "Z2": (HP2, 1),
                        "X": (HP2, 2),
                    }
                ),
                overvoltage=15.0,
            )

            shims["Z0"] = 1.0
            shims["Y"] = 1.0
            shims["Z1"] = 0.0
            shims["Z2"] = 0.0
            shims["X"] = 0.0

            input()
            shims[:] = 0.0
