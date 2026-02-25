from .gpib_eth import gpib_eth
from .log_inst import logger
import time


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

        dev.voltage[ch]          # get channel ch
        dev.voltage[ch] = value  # set channel ch

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
    - Direct assignment `owner.voltage = ...` is disallowed; use indexing.
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


class HP6623A(gpib_eth):
    def __init__(self, prologix_instance=None, address=None):
        r"""initialize a new `HP6623A` power supply class"""
        super().__init__(prologix_instance, address)
        self.write("ID?")
        idstring = self.read()
        if idstring[0:2] == "HP":
            logger.debug(
                "Detected HP power supply with ID string %s" % idstring
            )
        else:
            raise ValueError(
                "Not detecting identity as HP power supply. "
                "Expected ID string to start with 'HP'. Check your "
                "connections and address settings, and make sure the "
                f"instrument is powered on. (Returned ID string: {idstring})"
            )

        self._known_output_state = []
        for j in range(8):
            try:
                x = self.get_output(j)
                self._known_output_state.append(x)
            except Exception:
                break

        if len(self._known_output_state) < 1:
            raise ValueError("I can't even get one channel!")
        self.safe_current_on_enable = 0.0
        return

    def check_id(self):
        self.write("ID?")
        retval = self.read()
        return retval

    def _require_channel(self, ch):
        if not isinstance(ch, int):
            raise TypeError(f"channel must be int, got {type(ch).__name__}")
        if not (0 <= ch < len(self._known_output_state)):
            raise IndexError(
                f"channel {ch} out of range for "
                f"{len(self._known_output_state)} outputs"
            )
        return ch + 1

    def _query(self, cmd):
        self.write(cmd)
        return self.read()

    def _query_float(self, cmd):
        return float(self._query(cmd))

    def _query_int(self, cmd):
        return int(float(self._query(cmd)))

    def set_voltage(self, ch, val):
        r"""set voltage (in Volts) on specific channel

        Parameters
        ==========
        ch : int
            Channel 1, 2, or 3
        val : float
            Voltage you want to set in Volts; check manual for limits on each
            channel.
        Returns
        =======
        None
        """
        self.write("VSET %s,%s" % (str(ch + 1), str(val)))
        if val != 0.0:
            time.sleep(5)
        return

    def get_voltage_setting(self, ch):
        r"""query voltage setting (VSET?) for specific channel"""
        self.write("VSET? %s" % str(ch + 1))
        return float(self.read())

    def get_voltage(self, ch):
        r"""get voltage (in Volts) on specific channel

        Parameters
        ==========
        ch : int
            Channel 1, 2, or 3
        Returns
        =======
        Voltage reading (in Volts) as float

        """
        self.write("VOUT? %s" % str(ch + 1))
        return float(self.read())

    def set_current(self, ch, val):
        r"""set current (in Amps) on specific channel

        Parameters
        ==========
        ch : int
            Channel 1, 2, or 3
        val : float
            Current you want to set in Amps; check manual for limits on each
            channel.
        Returns
        =======
        None

        """
        if abs(val) > 1.8:
            raise ValueError(
                f"Requested current {val} A exceeds max safe current 1.8 A"
            )
        self.write("ISET %s,%s" % (str(ch + 1), str(val)))
        return

    def get_current_setting(self, ch):
        r"""query current setting (ISET?) for specific channel"""
        self.write("ISET? %s" % str(ch + 1))
        return float(self.read())

    def get_current(self, ch):
        r"""get current (in Amps) on specific channel

        Parameters
        ==========
        ch : int
            Channel 1, 2, or 3
        Returns
        =======
        Current reading (in Amps) as float
        """
        self.write("IOUT? %s" % str(ch + 1))
        curr_reading = float(self.read())
        for i in range(30):
            self.write("IOUT? %s" % str(ch + 1))
            this_val = float(self.read())
            if curr_reading == this_val:
                break
            if i > 28:
                print(
                    "Not able to get stable meter reading after 30 tries. "
                    f"Returning: {curr_reading:0.3f}"
                )
        return curr_reading

    def set_output(self, ch, trigger):
        r"""turn on or off the set_output on specific channel

        Parameters
        ==========
        ch : int
            Channel 1, 2, or 3
        trigger : int
            To turn set_output off, set `trigger` to 0 (or False)
            To turn set_output on, set `trigger` to  1 (or True)
        Returns
        =======
        None

        """
        assert isinstance(trigger, int), "trigger must be int (or bool)"
        assert 0 <= trigger <= 1, "trigger must be 0 (False) or 1 (True)"
        trigger = 1 if trigger else 0
        self.write("OUT %s,%s" % (str(ch + 1), str(trigger)))
        self._known_output_state[ch] = trigger
        return

    def get_output(self, ch):
        r"""check the set_output status of a specific channel

        Parameters
        ==========
        ch : int
            Channel 1, 2, or 3
        Returns
        =======
        str stating whether the channel set_output is OFF or ON

        """
        self.write("OUT? %s" % str(ch + 1))
        retval = float(self.read())
        if retval == 0:
            print("Ch %s output is OFF" % ch)
        elif retval == 1:
            print("Ch %s output is ON" % ch)
        return retval

    def set_overvoltage(self, ch, val):
        """Set overvoltage trip point (OVSET)."""
        self.write("OVSET %s,%s" % (str(ch + 1), str(val)))
        return

    def get_overvoltage(self, ch):
        """Query overvoltage trip point (OVSET?)."""
        self.write("OVSET? %s" % str(ch + 1))
        return float(self.read())

    def reset_overvoltage(self, ch):
        """Reset overvoltage crowbar circuit (OVRST)."""
        self.write("OVRST %s" % str(ch + 1))
        return

    def set_ocp(self, ch, enable):
        """Enable/disable overcurrent protection (OCP)."""
        enable = 1 if enable else 0
        self.write("OCP %s,%s" % (str(ch + 1), str(enable)))
        return

    def get_ocp(self, ch):
        """Query overcurrent protection status (OCP?)."""
        self.write("OCP? %s" % str(ch + 1))
        return int(float(self.read()))

    def reset_overcurrent(self, ch):
        """Reset output after overcurrent protection (OCRST)."""
        self.write("OCRST %s" % str(ch + 1))
        return

    def set_unmask(self, ch, mask):
        """Set mask register for channel (UNMASK)."""
        self.write("UNMASK %s,%s" % (str(ch + 1), str(mask)))
        return

    def get_unmask(self, ch):
        """Query mask register for channel (UNMASK?)."""
        self.write("UNMASK? %s" % str(ch + 1))
        return int(float(self.read()))

    def set_delay(self, ch, seconds):
        """Set reprogramming delay in seconds (DLY)."""
        self.write("DLY %s,%s" % (str(ch + 1), str(seconds)))
        return

    def get_delay(self, ch):
        """Query reprogramming delay in seconds (DLY?)."""
        self.write("DLY? %s" % str(ch + 1))
        return float(self.read())

    def status(self, ch):
        """Query status register (STS?)."""
        self.write("STS? %s" % str(ch + 1))
        return int(float(self.read()))

    def accumulated_status(self, ch):
        """Query accumulated status register (ASTS?)."""
        self.write("ASTS? %s" % str(ch + 1))
        return int(float(self.read()))

    def fault(self, ch):
        """Query fault register (FAULT?)."""
        self.write("FAULT? %s" % str(ch + 1))
        return int(float(self.read()))

    def clear(self):
        """Return supply to power-on state (CLR)."""
        self.write("CLR")
        return

    def store(self, reg):
        """Store settings to register 1-10 (STO)."""
        self.write("STO %s" % str(reg))
        return

    def recall(self, reg):
        """Recall settings from register 1-10 (RCL)."""
        self.write("RCL %s" % str(reg))
        return

    def set_srq(self, setting):
        """Set SRQ cause mask (SRQ 0-3)."""
        self.write("SRQ %s" % str(setting))
        return

    def get_srq(self):
        """Query SRQ setting (SRQ?)."""
        self.write("SRQ?")
        return int(float(self.read()))

    def set_pon(self, enable):
        """Enable/disable power-on SRQ (PON)."""
        enable = 1 if enable else 0
        self.write("PON %s" % str(enable))
        return

    def get_pon(self):
        """Query power-on SRQ setting (PON?)."""
        self.write("PON?")
        return int(float(self.read()))

    def display_on(self, enable):
        """Enable/disable front panel display (DSP)."""
        enable = 1 if enable else 0
        self.write("DSP %s" % str(enable))
        return

    def display_status(self):
        """Query display on/off status (DSP?)."""
        self.write("DSP?")
        return int(float(self.read()))

    def display_message(self, msg):
        """Display a message (DSP \"string\"). Max 12 chars per manual."""
        self.write('DSP "%s"' % str(msg))
        return

    def test(self):
        """Run GP-IB self-test (TEST?)."""
        self.write("TEST?")
        return int(float(self.read()))

    def error(self):
        """Query error register (ERR?)."""
        self.write("ERR?")
        return int(float(self.read()))

    def idn(self):
        """Query identification string (ID?)."""
        self.write("ID?")
        return self.read()

    def set_cmode(self, enable):
        """Enable/disable calibration mode (CMODE)."""
        enable = 1 if enable else 0
        self.write("CMODE %s" % str(enable))
        return

    def get_cmode(self):
        """Query calibration mode (CMODE?)."""
        self.write("CMODE?")
        return int(float(self.read()))

    def set_dcpon(self, mode):
        """Set power-on output state (DCPON)."""
        self.write("DCPON %s" % str(mode))
        return

    def rom(self):
        """Query firmware revision (ROM?)."""
        self.write("ROM?")
        return self.read()

    def vmux(self, ch, input_num):
        """Query analog multiplexer input (VMUX?)."""
        self.write("VMUX? %s,%s" % (str(ch + 1), str(input_num)))
        return float(self.read())

    # Calibration commands (Appendix A)
    def vdata(self, ch, vlo, vhi):
        self.write("VDATA %s,%s,%s" % (str(ch + 1), str(vlo), str(vhi)))
        return

    def vhi(self, ch):
        self.write("VHI %s" % str(ch + 1))
        return

    def vlo(self, ch):
        self.write("VLO %s" % str(ch + 1))
        return

    def idata(self, ch, ilo, ihi):
        self.write("IDATA %s,%s,%s" % (str(ch + 1), str(ilo), str(ihi)))
        return

    def ihi(self, ch):
        self.write("IHI %s" % str(ch + 1))
        return

    def ilo(self, ch):
        self.write("ILO %s" % str(ch + 1))
        return

    def ovcal(self, ch):
        self.write("OVCAL %s" % str(ch + 1))
        return

    def close(self):
        for i in range(len(self._known_output_state)):
            # set voltage and current to 0 and turn off set_output on all
            # channels, before exiting
            self.set_voltage(i, 0)
            self.set_current(i, 0)
            self.set_output(i, 0)
        super().close()
        return

    # TODO ☐: After previous, write a basic example to use the current limit,
    #         with voltage limit set high, and test on the instrument
    #         (generally we will want to control the current, which is propto
    #         field)

    @channel_property
    def voltage(self, channel):
        "this allows self.voltage[channel] to evaluate properly"
        return self.get_voltage(channel)

    @voltage.setter
    def voltage(self, channel, value):
        """this causes self.voltage[channel] = value to yield a change on the
        instrument"""
        if value == 0:
            self.set_voltage(channel, 0)
            if self._known_output_state[channel] == 1:
                self.set_output(channel, 0)
        else:
            self.set_voltage(channel, value)
            if self._known_output_state[channel] == 0:
                self.set_output(channel, 1)
        return

    @channel_property
    def current(self, channel):
        "this allows self.current[channel] to evaluate properly"
        return self.get_current(channel)

    @current.setter
    def current(self, channel, value):
        """set the current limit for a channel"""
        if abs(value) > 1.8:
            raise ValueError(
                f"Requested current {value} A exceeds "
                f"max safe current value 1.8 A"
            )
        if value == 0:
            self.set_current(channel, 0)
            if self._known_output_state[channel] == 1:
                self.set_output(channel, 0)
            return

        if self._known_output_state[channel] == 0:
            if abs(value) > self.safe_current_on_enable:
                raise ValueError(
                    "Refusing to enable output with current limit "
                    f"{value} A > safe_current_on_enable "
                    f"{self.safe_current_on_enable} A. Set a smaller "
                    "current first."
                )
            self.set_current(channel, value)
            self.set_output(channel, 1)
            return

        self.set_current(channel, value)
        return

    @channel_property
    def output(self, channel):
        "this allows self.output[channel] to evaluate properly"
        return self.get_output(channel)

    @output.setter
    def output(self, channel, value):
        """turn output on/off for a channel"""
        self.set_output(channel, int(bool(value)))
        return
