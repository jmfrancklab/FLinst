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
        prop : inst_dict_property
            Descriptor supplying the bound getter and optional setter used
            to read and write values by shim name.
        """
        self._owner = owner
        self._prop = prop
        # Different owner classes expose the same canonical shim-name set
        # through different attributes. In our setup these key sets are
        # expected to agree whenever more than one exists, so they are not
        # meant to get out of sync. We branch only because ShimDictMapping
        # stores shim names in `_shim_dict`, while power_control stores them
        # in the shim caches.
        if hasattr(self._owner, "_shim_dict"):
            key_source = self._owner._shim_dict
        elif hasattr(self._owner, "_shim_voltage_cache"):
            key_source = self._owner._shim_voltage_cache
        elif hasattr(self._owner, "_shim_current_cache"):
            key_source = self._owner._shim_current_cache
        else:
            raise AttributeError(
                f"{type(self._owner).__name__!r} object has no shim key source"
            )
        self._keys = list(key_source.keys())

    def _verify_iskey(self, idx):
        if isinstance(idx, str):
            if idx not in self._keys:
                raise KeyError(idx)
            return idx
        raise TypeError(f"unsupported shim index type: {type(idx).__name__}")

    def _indices(self, idx):
        r"""
        Normalize a shim selector into explicit shim names.

        Parameters
        ----------
        idx : str | slice | sequence[str]
            Selector naming one shim, a slice over the stored shim order, or
            an explicit sequence of shim names.

        Returns
        -------
        tuple[list[str], bool]
            The expanded shim-name list and a flag indicating whether the
            original selector addressed exactly one shim.
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
        Read one or more shim values through the bound descriptor.

        Parameters
        ----------
        idx : str | slice | sequence[str]
            Shim selector accepted by :meth:`_indices`.

        Returns
        -------
        object | np.ndarray
            A scalar when ``idx`` names one shim, otherwise a NumPy array
            ordered to match the expanded shim-name sequence.
        """
        inds, is_scalar = self._indices(idx)
        if is_scalar:
            return self._prop._fget(self._owner, inds[0])
        return np.array(
            [self._prop._fget(self._owner, shim_name) for shim_name in inds]
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
        r"""Return the number of addressable shim entries."""
        return len(self._keys)

    def __iter__(self):
        r"""Iterate over shim values in the proxy's stored key order."""
        for shim_name in self._keys:
            yield self[shim_name]

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
        Initialize the descriptor from its getter function.

        Parameters
        ----------
        fget : callable
            Function called as ``fget(owner, shim_name)`` by the bound proxy.
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
        Return the descriptor itself on the class, or a bound proxy on
        instances.
        """
        if owner is None:
            return self
        return inst_dict_proxy(owner, self)

    def __set__(self, owner, value):
        r"""
        Support whole-vector assignment for iterable values.

        Direct scalar assignment is rejected so callers use indexed writes for
        individual shims.
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
        r"""Register the write handler and return this descriptor."""
        self._fset = fset
        return self
