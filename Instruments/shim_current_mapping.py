from collections import OrderedDict
from collections.abc import Iterable, MutableMapping

from .HP6623A import HP6623A


class _ShimAttributeMapping(MutableMapping):
    __slots__ = ("_mapping", "_attr")

    def __init__(self, mapping, attr):
        self._mapping = mapping
        self._attr = attr

    def _ordered_names(self):
        return list(self._mapping._shim_dict)

    def _normalize(self, which_shim):
        if isinstance(which_shim, slice):
            return self._ordered_names()[which_shim], False
        if isinstance(which_shim, int):
            return [self._ordered_names()[which_shim]], True
        if isinstance(which_shim, Iterable) and not isinstance(
            which_shim, (str, bytes)
        ):
            return list(which_shim), False
        return [which_shim], True

    def __getitem__(self, which_shim):
        shim_names, is_scalar = self._normalize(which_shim)
        if is_scalar:
            return self._mapping._get_attr(self._attr, shim_names[0])
        return [
            self._mapping._get_attr(self._attr, shim_name)
            for shim_name in shim_names
        ]

    def __setitem__(self, which_shim, value):
        shim_names, is_scalar = self._normalize(which_shim)
        if is_scalar:
            self._mapping._set_attr(self._attr, shim_names[0], value)
            return
        is_iterable = hasattr(value, "__iter__") and not isinstance(
            value, (str, bytes)
        )
        if not is_iterable:
            for shim_name in shim_names:
                self._mapping._set_attr(self._attr, shim_name, value)
            return
        values = list(value)
        if len(values) != len(shim_names):
            raise ValueError(
                f"assignment length mismatch: {len(values)} "
                f"values for {len(shim_names)} shims"
            )
        for shim_name, this_value in zip(shim_names, values):
            self._mapping._set_attr(self._attr, shim_name, this_value)

    def __delitem__(self, which_shim):
        raise TypeError("Shim mappings do not support deleting keys")

    def __iter__(self):
        return iter(self._mapping._shim_dict)

    def __len__(self):
        return len(self._mapping._shim_dict)


class shim_property:
    """Descriptor for shim-name-based access on a shim selection view."""

    def __init__(self, fget):
        self._fget = fget
        self._fset = None
        self._name = getattr(fget, "__name__", None)
        self.__doc__ = getattr(fget, "__doc__", None)

    def __set_name__(self, owner, name):
        self._name = name

    def __get__(self, owner, owner_type=None):
        if owner is None:
            return self
        return self._fget(owner)

    def __set__(self, owner, value):
        if self._fset is None:
            raise AttributeError("can't set (no setter defined)")
        self._fset(owner, value)

    def setter(self, fset):
        self._fset = fset
        return self


class _ShimSelection:
    __slots__ = ("_mapping", "_shim_names")

    def __init__(self, mapping, shim_names):
        self._mapping = mapping
        self._shim_names = shim_names

    def _scalar(self):
        return len(self._shim_names) == 1

    def _get_attr(self, attr):
        if self._scalar():
            return self._mapping._get_attr(attr, self._shim_names[0])
        return [self._mapping._get_attr(attr, name) for name in self._shim_names]

    def _set_attr(self, attr, value):
        is_iterable = hasattr(value, "__iter__") and not isinstance(
            value, (str, bytes)
        )
        if self._scalar():
            self._mapping._set_attr(attr, self._shim_names[0], value)
            return
        if not is_iterable:
            for name in self._shim_names:
                self._mapping._set_attr(attr, name, value)
            return
        values = list(value)
        if len(values) != len(self._shim_names):
            raise ValueError(
                f"assignment length mismatch: {len(values)} "
                f"values for {len(self._shim_names)} shims"
            )
        for name, this_value in zip(self._shim_names, values):
            self._mapping._set_attr(attr, name, this_value)

    @shim_property
    def I_limit(self):
        return self._get_attr("I_limit")

    @I_limit.setter
    def I_limit(self, value):
        self._set_attr("I_limit", value)

    @shim_property
    def V_limit(self):
        return self._get_attr("V_limit")

    @V_limit.setter
    def V_limit(self, value):
        self._set_attr("V_limit", value)

    @shim_property
    def I_read(self):
        return self._get_attr("I_read")

    @shim_property
    def V_read(self):
        return self._get_attr("V_read")

    @shim_property
    def output(self):
        return self._get_attr("output")

    @output.setter
    def output(self, value):
        self._set_attr("output", value)


class ShimDictMapping:
    """Dictionary-like shim controller with per-attribute shim mappings."""

    def __init__(
        self,
        shim_dict,
        prologix_instance=None,
        overvoltage=15.0,
        safe_current=None,
    ):
        """Create a named shim-to-channel mapping.

        `shim_dict` must be an `OrderedDict` mapping shim names to
        `(instrument_or_address, channel)` pairs. `instrument_or_address`
        may be either a live `HP6623A` instance or an integer GPIB address.
        When an address is provided, `__enter__` creates the corresponding
        instrument using `prologix_instance` and `__exit__` closes only the
        instances created by this mapping.
        """
        shim_dict = OrderedDict(shim_dict)
        for shim_name, (inst_or_address, channel) in shim_dict.items():
            if (
                not isinstance((inst_or_address, channel), tuple)
                or len((inst_or_address, channel)) != 2
            ):
                raise ValueError(
                    "Each shim entry must be an "
                    "(instrument_or_address, channel) tuple"
                )

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
        self._shim_dict = shim_dict.copy()
        self._prologix_instance = prologix_instance
        self._overvoltage = overvoltage
        self._safe_current = safe_current
        self._owned_instruments = {}

    def __enter__(self):
        for shim_name, (inst_or_address, ch) in self._shim_dict.items():
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
                # Replace the GPIB address with the live instrument instance
                # for future use
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

    @property
    def I_limit(self):
        return _ShimAttributeMapping(self, "I_limit")

    @property
    def V_limit(self):
        return _ShimAttributeMapping(self, "V_limit")

    @property
    def I_read(self):
        return _ShimAttributeMapping(self, "I_read")

    @property
    def V_read(self):
        return _ShimAttributeMapping(self, "V_read")

    @property
    def output(self):
        return _ShimAttributeMapping(self, "output")

    def __len__(self):
        return len(self._shim_dict)

    def __iter__(self):
        return iter(self._shim_dict)

    def __contains__(self, which_shim):
        return which_shim in self._shim_dict

    def __getitem__(self, which_shim):
        return _ShimSelection(self, self._normalize(which_shim))

    def __setitem__(self, which_shim, value_oneormore):
        raise TypeError(
            "Use an explicit shim property such as "
            "shims[shim_name].I_limit = value or shims[:].V_limit = value"
        )

    def _normalize(self, which_shim):
        ordered_names = list(self._shim_dict)
        if isinstance(which_shim, slice):
            return ordered_names[which_shim]
        if isinstance(which_shim, int):
            return [ordered_names[which_shim]]
        if isinstance(which_shim, Iterable) and not isinstance(
            which_shim, (str, bytes)
        ):
            return list(which_shim)
        return [which_shim]

    def _get_attr(self, attr, which_shim):
        hp_inst, ch = self.connection(which_shim)
        return getattr(hp_inst, attr)[ch]

    def _set_attr(self, attr, which_shim, value):
        hp_inst, ch = self.connection(which_shim)
        getattr(hp_inst, attr)[ch] = value

    def round_to_allowed(self, which_limit, key, value):
        hp_inst, ch = self.connection(key)
        return hp_inst.round_to_allowed(which_limit, ch, value)

    def connection(self, which_shim):
        return self._shim_dict[which_shim]

    def instrument(self, which_shim):
        return self.connection(which_shim)[0]

    def channel(self, which_shim):
        return self.connection(which_shim)[1]

    def connections(self):
        return self._shim_dict.items()
