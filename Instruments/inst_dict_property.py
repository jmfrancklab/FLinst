import numpy as np


class inst_dict_proxy:
    r"""
    Per-instance bound view returned by inst_dict_property.__get__.
    This represents the vector-like object associated with each named shim.

    Python evaluates `owner.prop[idx]` as:
        tmp = owner.prop
        tmp.__getitem__(idx)

    Therefore indexing runs on the object returned by __get__. This proxy
    captures `owner` so __getitem__/__setitem__ can call fget/fset with the
    correct instance.
    """

    __slots__ = ("_owner", "_prop", "_keys")

    def __init__(self, owner, prop):
        r"""
        Initialize a proxy bound to one instrument-like owner instance.

        Parameters
        ----------
        owner : object
            Instance that owns the descriptor. It must expose one of
            ``_shim_dict``, ``_shim_voltage_cache``, or
            ``_shim_current_cache`` so the proxy can determine shim names.
            (See PR note below, however)
        prop : inst_dict_property
            Descriptor supplying the bound getter and optional setter used
            to read and write values by channel name
            (most immediately, here "channel" is a shim, though in the
            future, it could be any named instrument channel).
        """
        self._owner = owner
        self._prop = prop
        # {{{ the power_control instance uses _shim_voltage_cache and
        #     _shim_current_cache while the shim_current_dict uses
        #     _shim_dict to store the relevant properties, so we need to
        #     consider all of them.
        #     In a future PR, it would be good to clean this up by
        #     passing the name of the relevant attribute to
        #     inst_dict_property decorator
        if hasattr(self._owner, "_shim_dict"):
            key_source = self._owner._shim_dict
        elif hasattr(self._owner, "_shim_voltage_cache"):
            key_source = self._owner._shim_voltage_cache
        elif hasattr(self._owner, "_shim_current_cache"):
            key_source = self._owner._shim_current_cache
        else:
            raise AttributeError(
                f"{type(self._owner).__name__!r} object has no channel key source"
            )
        # }}}
        self._keys = list(key_source.keys())

    def _verify_iskey(self, idx):
        if isinstance(idx, str):
            if idx not in self._keys:
                raise KeyError(idx)
            return idx
        raise TypeError(f"unsupported shim index type: {type(idx).__name__}")

    def _indices(self, idx):
        r"""
        Check that we have a valid key, an note whether it refers to one
        or more channels.

        Parameters
        ----------
        idx : str | slice | sequence[str]
            Selector naming one channel, a slice over the stored channel order, or
            an explicit sequence of channel names.

        Returns
        -------
        tuple[list[str], bool]
            The expanded channel-name list and a flag indicating whether
            the original selector addressed exactly one channel.
        """
        if isinstance(idx, str):
            return [self._verify_iskey(idx)], True
        if isinstance(idx, slice):
            return self._keys[idx], False
        if isinstance(idx, (list, tuple)):
            return [self._verify_iskey(x) for x in idx], False
        raise TypeError(f"unsupported shim index type: {type(idx).__name__}")

    def __getitem__(self, idx):
        r"""
        Use the _fget function from the inst_dict_property definition to
        retrieve the current value of the relevant channel(s).

        Parameters
        ----------
        idx : str | slice | sequence[str]
            Channel selector accepted by :meth:`_indices`.

        Returns
        -------
        object | np.ndarray
            A scalar when ``idx`` names one channel, otherwise a NumPy array
            ordered to match the expanded channel-name sequence.
        """
        inds, is_scalar = self._indices(idx)
        if is_scalar:
            return self._prop._fget(self._owner, inds[0])
        return np.array(
            [self._prop._fget(self._owner, ch_name) for ch_name in inds]
        )

    def __setitem__(self, idx, value):
        r"""
        Write one or more shim values through the bound descriptor.

        Scalar indexing assigns one value to one shim. Non-scalar indexing
        accepts either a broadcast scalar or an iterable whose length matches
        the number of selected shims.
        """
        fset = self._prop._fset
        if fset is None:
            raise AttributeError("can't set (no setter defined)")
        inds, is_scalar = self._indices(idx)
        if is_scalar:
            fset(self._owner, inds[0], value)
            return
        is_iterable = hasattr(value, "__iter__") and not isinstance(
            value, (str, bytes)
        )
        if not is_iterable:
            for shim_name in inds:
                fset(self._owner, shim_name, value)
            return
        vals = list(value)
        if len(vals) != len(inds):
            raise ValueError(
                f"assignment length mismatch: {len(vals)} "
                f"values for {len(inds)} indices"
            )
        for shim_name, val in zip(inds, vals):
            fset(self._owner, shim_name, val)

    def __len__(self):
        r"""Return the number of addressable channel entries."""
        return len(self._keys)

    def __iter__(self):
        r"""Iterate over shim values in the proxy's stored key order."""
        for ch_name in self._keys:
            yield self[ch_name]

    def __eq__(self, other):
        r"""Compare the proxy by value against another non-string iterable."""
        if not hasattr(other, "__iter__") or isinstance(other, (str, bytes)):
            return False
        return list(self) == list(other)

    def __repr__(self):
        r"""
        Return a debug representation with values, name, and bound owner.
        """
        name = self._prop._name or "<unnamed>"
        return (
            f"{str(list(self))} <inst_dict_proxy {name}"
            f" bound to {type(self._owner).__name__}"
            f" at {str(hex(id(self._owner)))} >"
        )


class inst_dict_property:
    r"""
    Descriptor similar to @property, but shim-dictionary-aware via indexing:

        shims.V_limit["Y"]          # get shim Y
        shims.V_limit["Y"] = value  # set shim Y
        shims.V_limit[:]            # vector across all shims in key order
    """

    def __init__(self, fget):
        r"""
        Store the _fget function from the inst_dict_property decorator call.
        (This function is the property's getter.)

        Parameters
        ----------
        fget : callable
            Function that is decorated with @inst_dict_property.
            Its name and docstring seed the descriptor metadata.
        """
        self._fget = fget
        self._fset = None
        self._name = getattr(fget, "__name__", None)
        self.__doc__ = getattr(fget, "__doc__", None)

    def __set_name__(self, owner, name):
        r"""Record the attribute name assigned by the owning class."""
        self._name = name

    def __get__(self, owner, owner_type=None):
        r"""
        when we ask for an property of the class, assume that the
        property is the "owner" instance, and pass it to the proxy class.
        """
        if owner is None:
            return self
        return inst_dict_proxy(owner, self)

    def __set__(self, owner, value):
        r"""
        When we try to set a property, again assume the property is the
        owner instance, then create a proxy class, and activate vector
        assignment.
        """
        is_iterable = hasattr(value, "__iter__") and not isinstance(
            value, (str, bytes)
        )
        if not is_iterable:
            raise AttributeError(
                "can't set attribute directly; use indexing: owner.attr[key] ="
                " value"
            )
        proxy = inst_dict_proxy(owner, self)
        proxy[:] = value
        return

    def setter(self, fset):
        r"""
        Store the function that we decorate with @propertyname.setter in
        _fset.
        (This function is the property's setter.)
        """
        self._fset = fset
        return self
