class channel_proxy:
    r"""
    Per-instance bound view returned by channel_property.__get__.

    Python evaluates `owner.prop[idx]` as:
        tmp = owner.prop            # attribute access -> descriptor __get__
        tmp.__getitem__(idx)        # indexing on tmp

    Therefore indexing runs on the object returned by __get__. This proxy
    captures `owner` so __getitem__/__setitem__ can call fget/fset with the
    correct instance.

    `size` is determined from `len(owner._known_output_state)` at proxy
    construction time. This enables len(), iteration, and slice.indices(size).

    Indexing:
      - int:        proxy[i]              -> single value
      - slice:      proxy[i:j:k]          -> list of values
      - list/tuple: proxy[[1,3,4]]        -> list of values

    Assignment:
      - int:        proxy[i] = v
      - slice:      proxy[i:j:k] = v            (scalar broadcast)
                   proxy[i:j:k] = iterable      (length must match)
      - list/tuple: proxy[[...]] = v            (scalar broadcast)
                   proxy[[...]] = iterable      (length must match)
    """

    __slots__ = ("_owner", "_prop", "size")

    def __init__(self, owner, prop):
        self._owner = owner
        self._prop = prop
        self.size = len(owner._known_output_state)

    def _norm_int_index(self, i):
        n = self.size
        if not isinstance(i, int):
            raise TypeError(
                f"channel index must be int, got {type(i).__name__}"
            )
        if i < 0:
            i += n
        if not (0 <= i < n):
            raise IndexError(f"channel index {i} out of range for size {n}")
        return i

    def _indices(self, idx):
        """Normalize idx -> (list[int], is_scalar)."""
        if isinstance(idx, int):
            return [self._norm_int_index(idx)], True
        if isinstance(idx, slice):
            return list(range(*idx.indices(self.size))), False
        if isinstance(idx, (list, tuple)):
            return [self._norm_int_index(x) for x in idx], False
        raise TypeError(f"unsupported index type: {type(idx).__name__}")

    def __getitem__(self, idx):
        inds, is_scalar = self._indices(idx)
        if is_scalar:
            return self._prop._fget(self._owner, inds[0])
        return [self._prop._fget(self._owner, i) for i in inds]

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
            for i in inds:
                fset(self._owner, i, value)
            return

        vals = list(value)
        if len(vals) != len(inds):
            raise ValueError(
                f"assignment length mismatch: {len(vals)} "
                f"values for {len(inds)} indices"
            )
        for i, v in zip(inds, vals):
            fset(self._owner, i, v)

    def __len__(self):
        return self.size

    def __iter__(self):
        for ch in range(self.size):
            yield self[ch]

    def __eq__(self, other):
        # Compare the proxy to another iterable as a full channel vector.
        if not hasattr(other, "__iter__") or isinstance(other, (str, bytes)):
            return False
        return list(self) == list(other)

    def __repr__(self):
        name = self._prop._name or "<unnamed>"
        return (
            f"<channel_proxy {name} bound to {type(self._owner).__name__}"
            f" at {hex(id(self._owner))}>"
        )


class channel_property:
    r"""
    Descriptor similar to @property, but "channel-aware" via indexing:

        dev.V_limit[ch]          # get channel ch
        dev.V_limit[ch] = value  # set channel ch

    WHY THE PROXY CLASS IS NEEDED
    -----------------------------
    Python evaluates:

        owner.property[idx]

    as:

        tmp = owner.property          # attribute access
        tmp.__getitem__(idx)          # indexing

    Attribute access triggers the descriptor protocol:

        channel_property.__get__(owner, type(owner))

    and whatever __get__ returns becomes `tmp`. Indexing then calls
    __getitem__ on that returned object.

    If __get__ returned the descriptor itself, __getitem__ would run on the
    shared descriptor instance, but __getitem__(self, idx) would not know
    which `owner` instance it should operate on (and caching the last owner
    inside the descriptor is unsafe under interleaving / threads / reentrancy).

    Therefore __get__ returns a channel_proxy that stores `owner` and the
    descriptor, so the proxy can call fget(owner, idx) and fset(owner, idx,
    val).

    ITERATION / LENGTH
    ------------------
    Iteration is performed on the proxy object returned by attribute access.
    The proxy has a `.size` attribute (default None). If `size` is None,
    attempting to iterate or take len() raises AttributeError. If `size` is
    set to an integer, the proxy yields values for channels [0..size-1].

    EXPECTED SIGNATURES
    -------------------
      fget(owner, channel) -> value
      fset(owner, channel, value) -> None         (optional)

    NOTES
    -----
    - Direct assignment `owner.V_limit = ...` is disallowed; use indexing.
    - Slices are intentionally not implemented (raise TypeError).
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
        return channel_proxy(owner, self)

    def __set__(self, owner, value):
        is_iterable = hasattr(value, "__iter__") and not isinstance(
            value, (str, bytes)
        )
        if not is_iterable:
            raise AttributeError(
                "can't set attribute directly; use indexing: owner.attr[ch] = "
                "value"
            )
        # Allow vector-style assignment across all channels when an iterable is
        # provided.
        proxy = channel_proxy(owner, self)
        proxy[:] = value
        return

    # Decorator-style configuration, modeled on property
    def setter(self, fset):
        self._fset = fset
        return self
