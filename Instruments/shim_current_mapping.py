from collections import OrderedDict

from .HP6623A import HP6623A
from .inst_dict_property import inst_dict_property


class ShimDictMapping:
    """Dictionary-like shim controller with named-shim properties."""

    def __init__(
        self,
        shim_dict,
        prologix_instance=None,
        overvoltage=15.0,
        safe_current=None,
    ):
        # TODO ☐: standard numpy-style docstring
        """Create a named shim-to-channel mapping.

        `shim_dict` must map shim names to `(instrument_or_address, channel)`
        pairs. `instrument_or_address` may be either a live `HP6623A`
        instance or an integer GPIB address. Keys are sorted alphabetically
        and stored in an `OrderedDict`.
        """
        shim_dict = OrderedDict(sorted(dict(shim_dict).items(), key=lambda x: x[0]))
        for shim_name, connection in shim_dict.items():
            if not isinstance(connection, tuple) or len(connection) != 2:
                raise ValueError(
                    "Each shim entry must be an "
                    "(instrument_or_address, channel) tuple"
                )
            inst_or_address, channel = connection
            if not isinstance(inst_or_address, (int, HP6623A)):
                raise TypeError(
                    f"{shim_name} must map to an HP6623A instance or "
                    f"GPIB address int, not {type(inst_or_address).__name__}"
                )
            if not isinstance(channel, int):
                raise TypeError(
                    f"{shim_name} channel must be an int, not "
                    f"{type(channel).__name__}"
                )
        self._shim_dict = shim_dict
        self._prologix_instance = prologix_instance
        self._overvoltage = overvoltage
        self._safe_current = safe_current
        self._owned_instruments = {}

    def __enter__(self):
        for shim_name, (inst_or_address, ch) in list(self._shim_dict.items()):
            if isinstance(inst_or_address, int):
                if self._prologix_instance is None:
                    raise ValueError(
                        "prologix_instance is required when shim_dict "
                        "contains GPIB addresses"
                    )
                if inst_or_address not in self._owned_instruments:
                    self._owned_instruments[inst_or_address] = HP6623A(
                        prologix_instance=self._prologix_instance,
                        address=inst_or_address,
                    )
                inst_or_address = self._owned_instruments[inst_or_address]
                self._shim_dict[shim_name] = (inst_or_address, ch)
            if self._safe_current is not None:
                inst_or_address.safe_current = self._safe_current
            if self._overvoltage is not None:
                inst_or_address.overvoltage[ch] = self._overvoltage
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        for inst in self._owned_instruments.values():
            inst.close()
        self._owned_instruments.clear()
        return

    @inst_dict_property
    def I_limit(self, shim_name):
        which_inst, ch = self._shim_dict[shim_name]
        return which_inst.I_limit[ch]

    @I_limit.setter
    def I_limit(self, shim_name, value):
        which_inst, ch = self._shim_dict[shim_name]
        which_inst.I_limit[ch] = value

    @inst_dict_property
    def V_limit(self, shim_name):
        which_inst, ch = self._shim_dict[shim_name]
        return which_inst.V_limit[ch]

    @V_limit.setter
    def V_limit(self, shim_name, value):
        which_inst, ch = self._shim_dict[shim_name]
        which_inst.V_limit[ch] = value

    @inst_dict_property
    def I_read(self, shim_name):
        which_inst, ch = self._shim_dict[shim_name]
        return which_inst.I_read[ch]

    @inst_dict_property
    def V_read(self, shim_name):
        which_inst, ch = self._shim_dict[shim_name]
        return which_inst.V_read[ch]

    @inst_dict_property
    def output(self, shim_name):
        which_inst, ch = self._shim_dict[shim_name]
        return which_inst.output[ch]

    @output.setter
    def output(self, shim_name, value):
        which_inst, ch = self._shim_dict[shim_name]
        which_inst.output[ch] = value

    def __len__(self):
        return len(self._shim_dict)

    def __iter__(self):
        return iter(self._shim_dict)

    def __contains__(self, which_shim):
        return which_shim in self._shim_dict

    def instrument(self, which_shim):
        return self._shim_dict[which_shim][0]

    def channel(self, which_shim):
        return self._shim_dict[which_shim][1]

    def round_to_allowed(self, which_limit, key, value):
        which_inst, ch = self._shim_dict[key]
        return which_inst.round_to_allowed(which_limit, ch, value)
