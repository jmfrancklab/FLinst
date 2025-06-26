import socket
import time
from .gpib_eth import gpib_eth
from .log_inst import logger
from pint import UnitRegistry, Quantity

ureg = UnitRegistry()

"""
Class for controlling LakeShore 475 Gaussmeter written by AG using ChatGPT and inferring
from HP6623A.py, HP8672A.py and gigatronics.py.
ChatGPT Conversation: https://chatgpt.com/share/6851b044-3030-800d-ae80-7943105f6a59
Refer to the user manual for the detailed explanations of the commands starting from
the page 6-28.
"""


class LakeShore475(gpib_eth):
    """
    Context-managed Lake Shore 475 Gaussmeter via PrologixEthernet.
    Usage:
        with LakeShore475(prologix, gpib_addr) as gauss:
            ...
    """

    _status_byte_flags = {
        "error_queue": 2,      # Error queue not empty
        "message_available": 4,  # Message available
        "event_status": 5,    # Event status bit
        "request_service": 6, # Request service
    }

    _event_status_flags = {
        "operation_complete": 0,
        "request_control": 1,
        "query_error": 2,
        "device_error": 3,
        "execution_error": 4,
        "command_error": 5,
        "user_request": 6,
        "power_on": 7,
    }

    def __init__(self, prologix_instance=None, address=12, eos=0):
        """Initialize instance of connection to hall probe

        Parameters
        ----------
        eos : int
            2 -- set instrument to IEEE Terms = LF
            0 -- set instrument to IEEE Terms = CR LF
        """
        super().__init__(prologix_instance, address, eos=eos)
        idstring = self.respond("*IDN?")
        if idstring.startswith("LSCI,MODEL475"):
            logger.debug(
                "Detected LakeShore Gaussmeter with ID string %s" % idstring
            )
        else:
            raise ValueError(
                "Not detecting identity as Lakeshore Gaussmeter 475, returned"
                " ID string as %s" % idstring
            )
        self.write("HRESET")  # clear field_limits state so that readings are valid since initialization
        return

    @property
    def IDN(self):
        """Return the *IDN? string (manufacturer, model, serial, date)."""
        return self.respond("*IDN?")

    def _get_field_units(self):
        """
        Query the instrument for the current magnetic field units.

        Returns
        -------
        pint.Unit
            The unit corresponding to the instrument's current setting.
        """
        unit_code = int(self.respond("UNIT?"))
        unit_map = {
            1: ureg.gauss,
            2: ureg.tesla,
            3: ureg.oersted,
            4: ureg.ampere / ureg.meter,
        }
        return unit_map.get(unit_code, ureg.gauss)

    @property
    def field(self):
        """
        Read the magnetic field as a pint.Quantity.

        Returns
        -------
        pint.Quantity
            Magnetic field with appropriate units.

        Notes
        -----
        - **Reading**: Uses RDGFIELD? (manual §6.3.3.1, p. 106).
        - **Assignment**: Not supported.
        - **Deletion**: Not supported.
        """
        resp = self.respond("RDGFIELD?")
        try:
            value = float(resp)
        except:
            if resp == "NO PROBE":
                raise ValueError("No Hall Probe is attached!")
            elif resp == "OL":
                raise ValueError(
                    "The measured field is larger than the range. Increase the"
                    " measurement range or check probe zero."
                )
            else:
                raise ValueError("Other type of error: %s" % resp)

        units = self._get_field_units()
        return value * units

    @property
    def range(self) -> int:
        """Query the present manual range (returns 1–5, field values are probe depended)."""
        return int(self.respond("RANGE?"))

    @range.setter
    def range(self, range_code: int):
        """
        Manually select a measurement range (1–5).
        Disables auto-ranging when invoked.
        """
        if not 1 <= range_code <= 5:
            raise ValueError("Range must be an integer from 1 to 5")
        self.write(f"RANGE {range_code}")

    @property
    def auto_range(self) -> bool:
        """Query auto-ranging state (returns True if on)."""
        return bool(int(self.respond("AUTO?")))

    @auto_range.setter
    def auto_range(self, enable: bool):
        """
        Turn auto-ranging on or off:
            True  → AUTO 1
            False → AUTO 0
        """
        self.write(f"AUTO {1 if enable else 0}")

    def zero_probe(self):
        """Re-zero the probe before measurements."""
        self.write("ZPROBE")

    @property
    def status(self):
        """
        Status byte decoded into named flags.

        Returns
        -------
        dict of bool
            Dictionary of decoded status bits:
            - error_queue: Error queue not empty
            - message_available: Output queue has unread data
            - event_status: One or more IEEE events occurred
            - request_service: Instrument is requesting service

        Notes
        -----
        - **Reading**: Queries *STB? and returns decoded dictionary.
          See manual §6.3.1.1, p. 92.
        - **Deletion**: Clears event/status registers and error queue
          via *CLS (see §6.3.1.5, p. 95).
        - **Assignment**: Not supported.
        """
        val = int(self.respond("*STB?"))
        return {
            k: bool(val & (1 << b)) for k, b in self._status_byte_flags.items()
        }

    @status.deleter
    def status(self):
        self.write("*CLS")

    @property
    def event_status(self):
        """
        Event status register decoded into named flags.

        Returns
        -------
        dict of bool
            Dictionary of decoded *ESR? bits.

        Notes
        -----
        - **Reading**: Queries *ESR? and decodes flags.
          See manual §6.3.1.2, p. 93.
        - **Assignment**: Use the setter to write a bitmask
          specifying which events to monitor.
        - **Deletion**: Not supported.
        """
        val = int(self.respond("*ESR?"))
        return {
            k: bool(val & (1 << b)) for k, b in self._event_status_flags.items()
        }

    @event_status.setter
    def event_status(self, flags):
        val = sum(
            1 << self._event_status_flags[k]
            for k, v in flags.items()
            if v and k in self._event_status_flags
        )
        self.write(f"*ESE {val}")

    @property
    def operation_complete(self):
        """
        Indicates whether all prior operations have completed.

        Returns
        -------
        bool
            True if the instrument has finished processing all commands.

        Notes
        -----
        - **Reading**: Returns True if all prior operations are complete (see manual §6.3.1.2, p. 93).
        - **Assignment**: Setting to True inserts a synchronization point; False has no effect.
        - **Deletion**: Not supported.
        """
        return self.respond("*OPC?") == "1"

    @operation_complete.setter
    def operation_complete(self, value):
        if not isinstance(value, bool):
            raise TypeError("operation_complete must be set to a boolean")
        if value:
            self.write("*OPC")

    @property
    def time_constant(self):
        """
        Time constant of the field filter.

        Returns
        -------
        pint.Quantity
            Time constant with units of seconds.

        Notes
        -----
        - **Reading**: Returns current filter time constant (see manual §6.3.3.7, p. 108).
        - **Assignment**: Updates filter time constant; expects a pint Quantity.
        - **Deletion**: Not supported.
        """
        return float(self.respond("FILTER?")) * ureg.second

    @time_constant.setter
    def time_constant(self, value):
        if not isinstance(value, Quantity):
            raise TypeError("Expected a pint Quantity for time_constant")
        seconds = value.to(ureg.second).magnitude
        self.write(f"FILTER {seconds:.3f}")

    def reset(self):
        """
        Reset the instrument to its default state.

        Notes
        -----
        - Issues the `*RST` command (see manual §6.3.1.3, p. 94).
        - Equivalent to pressing the front-panel reset.
        - Clears the output queue and resets configuration.
        """
        self.write("*RST")

    @property
    def zoffset(self):
        """
        Probe zero offset in current field units.

        Returns
        -------
        float
            Current offset applied to field measurement.

        Notes
        -----
        - **Reading**: Query the probe zero offset using `ZOFFSET?` (manual §6.3.3.10, p. 109).
        - **Assignment**: Write a new offset value with `ZOFFSET`.
        - **Deletion**: Not supported.
        """
        return float(self.respond("ZOFFSET?"))

    @zoffset.setter
    def zoffset(self, value: float):
        self.write(f"ZOFFSET {float(value):.4f}")

    @property
    def read_mode(self):
        """
        Reading mode: determines how the field measurement is interpreted.

        Returns
        -------
        str
            One of "DC", "PEAK", or "RMS".

        Notes
        -----
        - **Reading**: Queries current reading mode via `RMODE?` (manual §6.3.3.8, p. 108).
        - **Assignment**: Use one of the valid mode strings to update.
        - **Deletion**: Not supported.
        """
        code = int(self.respond("RMODE?"))
        modes = {0: "DC", 1: "PEAK", 2: "RMS"}
        return modes[code]

    @read_mode.setter
    def read_mode(self, mode: str):
        modes = {"DC": 0, "PEAK": 1, "RMS": 2}
        if mode not in modes:
            raise ValueError("read_mode must be one of: DC, PEAK, RMS")
        self.write(f"RMODE {modes[mode]}")

    @property
    def relative_mode(self):
        """
        Indicates whether relative mode is enabled.

        In this mode, the instrument stores the current field
        value as an offset and subtracts it from future readings.

        Returns
        -------
        bool
            True if relative mode is enabled.

        Notes
        -----
        - **Reading**: Uses `REL?` to query state (manual §6.3.3.9, p. 109).
        - **Assignment**: Enable/disable relative mode using `REL`.
        - **Deletion**: Not supported.
        """
        return bool(int(self.respond("REL?")))

    @relative_mode.setter
    def relative_mode(self, enable: bool):
        self.write(f"REL {1 if enable else 0}")

    @property
    def analog_output(self):
        """
        Analog output voltage in volts.

        Returns
        -------
        float
            Current analog output voltage.

        Notes
        -----
        - **Reading**: Queries `AOUT?` to get analog output (manual §6.3.4.1, p. 110).
        - **Assignment**: Not supported (read-only).
        - **Deletion**: Not supported.
        """
        return float(self.respond("AOUT?"))

    @property
    def control_mode(self):
        """
        Control mode of the instrument.

        Returns
        -------
        str
            One of "local", "remote", or "locked".

        Notes
        -----
        - **Reading**: Queries `CMODE?` (manual §6.3.2.4, p. 104).
        - **Assignment**: Use `local`, `remote`, or `locked`.
        - **Deletion**: Not supported.
        """
        code = int(self.respond("CMODE?"))
        modes = {0: "local", 1: "remote", 2: "locked"}
        return modes[code]

    @control_mode.setter
    def control_mode(self, mode: str):
        modes = {"local": 0, "remote": 1, "locked": 2}
        if mode not in modes:
            raise ValueError("control_mode must be 'local', 'remote', or 'locked'")
        self.write(f"CMODE {modes[mode]}")

    @property
    def hold(self):
        """
        Hold mode status.

        When enabled, the display freezes the current field value
        and no longer reflects live measurements, although data
        output continues.

        Returns
        -------
        bool
            True if display updates are paused.

        Notes
        -----
        - **Reading**: Queries `HOLD?` to check hold mode (manual §6.3.3.11, p. 109).
        - **Assignment**: Use `True` to enable, `False` to disable.
        - **Deletion**: Not supported.
        """
        return bool(int(self.respond("HOLD?")))

    @hold.setter
    def hold(self, value: bool):
        self.write(f"HOLD {1 if value else 0}")

    @property
    def relay_state(self):
        """
        Indicates whether the instrument's rear-panel relay output is energized.

        The relay can be used to control external equipment or trigger devices. When
        energized, it closes the relay circuit; when de-energized, the circuit is open.

        Returns
        -------
        bool
            True if relay is energized, False otherwise.

        Notes
        -----
        - **Reading**: Uses `RELAY?` to query relay state (manual §6.3.4.2, p. 110).
        - **Assignment**: Use True or False to energize or de-energize relay.
        - **Deletion**: Not supported.
        """
        return bool(int(self.respond("RELAY?")))

    @relay_state.setter
    def relay_state(self, value: bool):
        self.write(f"RELAY {1 if value else 0}")

    @property
    def alarm_enabled(self):
        # Here, you need to explain which property controls the limits (you probably need to go ahead and add the property)
        """
        Indicates whether the alarm output function is enabled.

        When enabled, the alarm system monitors the magnetic field and compares it to
        user-specified limits. If the reading exceeds those thresholds, an alarm output
        can be activated.

        Returns
        -------
        bool
            True if alarm is enabled.

        Notes
        -----
        - **Reading**: Uses `ALARM?` to query status (manual §6.3.4.4, p. 111).
        - **Assignment**: Set True to enable, False to disable.
        - **Deletion**: Not supported.
        """
        return bool(int(self.respond("ALARM?")))

    @alarm_enabled.setter
    def alarm_enabled(self, enable: bool):
        self.write(f"ALARM {1 if enable else 0}")

    @property
    def field_limits(self):
        """
        Maximum and minimum magnetic field values recorded since
        the last time this property was deleted (or since
        initialization).

        The instrument continuously tracks the extremal field
        values and stores them until cleared. This is useful for
        monitoring field stability and bounds.
        (See manual §6.3.3.12–13, pp. 110–111.)

        Returns
        -------
        tuple of pint.Quantity
            (max, min) field values with units of magnetic field.

        Notes
        -----
        - **Reading**: Gives values as a tuple pair of pint quantities.
        - **Assignment**: Not supported.
        - **Deletion**: Reset both the min and max.
        """
        units = self._get_field_units()
        max_val = float(self.respond("MAXHOLD?")) * units
        min_val = float(self.respond("MINHOLD?")) * units
        return (max_val, min_val)

    @field_limits.deleter
    def field_limits(self):
        self.write("HRESET")
