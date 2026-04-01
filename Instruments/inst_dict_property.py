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
        self._owner = owner
        self._prop = prop
        self._keys = list(owner._shim_dict)

    def _normalize_scalar(self, idx):
        if isinstance(idx, int):
            return self._keys[idx]
        if isinstance(idx, str):
            if idx not in self._owner._shim_dict:
                raise KeyError(idx)
            return idx
        raise TypeError(f"unsupported shim index type: {type(idx).__name__}")

    def _indices(self, idx):
        if isinstance(idx, (int, str)):
            return [self._normalize_scalar(idx)], True
        if isinstance(idx, slice):
            return self._keys[idx], False
        if isinstance(idx, (list, tuple)):
            return [self._normalize_scalar(x) for x in idx], False
        raise TypeError(f"unsupported shim index type: {type(idx).__name__}")

    def __getitem__(self, idx):
        inds, is_scalar = self._indices(idx)
        if is_scalar:
            return self._prop._fget(self._owner, inds[0])
        return [self._prop._fget(self._owner, shim_name) for shim_name in inds]

    def __setitem__(self, idx, value):
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
        return len(self._keys)

    def __iter__(self):
        for shim_name in self._keys:
            yield self[shim_name]

    def __eq__(self, other):
        if not hasattr(other, "__iter__") or isinstance(other, (str, bytes)):
            return False
        return list(self) == list(other)

    def __repr__(self):
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
        self._fget = fget
        self._fset = None
        self._name = getattr(fget, "__name__", None)
        self.__doc__ = getattr(fget, "__doc__", None)

    def __set_name__(self, owner, name):
        self._name = name

    def __get__(self, owner, owner_type=None):
        if owner is None:
            return self
        return inst_dict_proxy(owner, self)

    def __set__(self, owner, value):
        is_iterable = hasattr(value, "__iter__") and not isinstance(
            value, (str, bytes)
        )
        if not is_iterable:
            raise AttributeError(
                "can't set attribute directly; use indexing: owner.attr[key] = "
                "value"
            )
        proxy = inst_dict_proxy(owner, self)
        proxy[:] = value
        return

    def setter(self, fset):
        self._fset = fset
        return self
