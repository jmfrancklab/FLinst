from .gpib_eth import gpib_eth
from .log_inst import logger
from .channel_property import channel_property
import time
import numpy as np


class HP6623A(gpib_eth):
    def __init__(self, prologix_instance=None, address=None):
        r"""Initialize a new `HP6623A` power supply instance.

        Parameters
        ==========
        prologix_instance : prologix_connection
            Active Prologix Ethernet-GPIB connection.
        address : int
            GPIB address of the HP6623A.
        """
        super().__init__(prologix_instance, address)
        # {{{ track the set of actual observed values,
        # in case we need to adjust the allowed values, below
        self.observed_I = [set(), set(), set()]
        self.observed_V = [set(), set(), set()]
        # }}}
        self.write("ID?")
        # {{{ these are just determined from the observed values
        self.allowed_I = [
            np.r_[
                0.083,
                0.107,
                0.13,
                0.154,
                0.178,
                0.201,
                0.225,
                0.248,
                0.272,
                0.296,
                0.319,
                0.343,
                0.366,
                0.39,
                0.413,
                0.437,
                0.461,
                0.484,
                0.508,
                0.531,
                0.555,
                0.579,
                0.602,
                0.626,
                0.649,
                0.673,
                0.696,
                0.72,
                0.744,
                0.767,
                0.791,
                0.814,
                0.838,
                0.862,
                0.885,
                0.909,
                0.932,
                0.956,
                0.979,
                1.003,
                1.027,
                1.05,
                1.074,
                1.097,
                1.121,
                1.145,
                1.168,
                1.192,
                1.215,
                1.239,
                1.262,
                1.286,
                1.31,
                1.333,
                1.357,
                1.38,
                1.404,
                1.428,
                1.451,
                1.475,
                1.498,
            ],
            np.r_[
                0.13,
                0.18,
                0.22,
                0.27,
                0.32,
                0.37,
                0.41,
                0.46,
                0.51,
                0.56,
                0.6,
                0.65,
                0.7,
                0.74,
                0.79,
                0.84,
                0.89,
                0.93,
                0.98,
                1.03,
                1.08,
                1.12,
                1.17,
                1.22,
                1.27,
                1.31,
                1.36,
                1.41,
                1.46,
                1.5,
            ],
            np.r_[0],
        ]
        self._voltage_rounding_offset = [-7.8e-05, 0.001922, None]
        self._voltage_rounding_interval = [0.00545861, 0.00545861, None]
        self.allowed_V = [
            np.r_[0],
            np.r_[0],
            np.r_[0],
        ]
        # }}}
        self.min_V = [0.000, 0.002, 0.018]
        self.max_V = [6, 10.5, 50.5]
        self.max_I = [5.15, 10.30, 2.06]
        idstring = self.read()
        if idstring[0:2] == "HP":
            logger.debug(
                "Detected HP power supply with ID string %s" % idstring
            )
        else:
            raise ValueError(
                "Not detecting identity as HP power supply. "x
                "Expected ID string to start with 'HP'. Check your "
                "connections and address settings, and make sure the "
                f"instrument is powered on. (Returned ID string: {idstring})"
            )
        self._known_output_state = []
        for j in range(8):
            try:
                # we use the raw command used by output to check if the channel
                # exists (use raw command to avoid dependence on
                # _known_output_state, which is what we're trying to populate
                # here)
                x = float(self.respond(f"OUT? {self._GPIB_index(j):d}"))
                self._known_output_state.append(x)
            except Exception:
                break
        self.safe_current = None
        return

    def _GPIB_index(self, channel):
        """Convert 0-based channel index to 1-based for GPIB commands."""
        return channel + 1

    def _round_voltage_to_allowed(self, channel, value):
        offset = self._voltage_rounding_offset[channel]
        interval = self._voltage_rounding_interval[channel]
        if offset is None or interval is None:
            the_values = self.allowed_V[channel]
            return the_values[np.argmin(abs(value - the_values))]
        return np.round(
            np.round((value - offset) / interval) * interval + offset,
            3,
        )

    def check_id(self):
        self.write("ID?")
        retval = self.read()
        return retval

    def set_voltage(self, ch, val):
        r"""set voltage (in Volts) on specific channel

        Parameters
        ==========
        ch : int
            Channel 1, 2, or 3
        val : float
            Voltage you want to set in Volts.
            Channel 1:
                0.006 V of resolution
                0 to 7.07 V -- 0.08 to 5.15 A
                0 to 20.2 V -- 0.08 to 2.06 A
            Channel 2:
                0.006 V of resolution
                0 to 7.07 V -- 0.13 to 10.30 A
                0 to 20.2 V -- 0.13 to 4.12 A
            Channel 3:
                0.015 V of resolution
                0 to 20.2 V -- 0.05 to 2.06 A
                0 to 50.5 V -- 0.05 to 0.824 A
        Returns
        =======
        None
        """
        self.write("VSET %s,%s" % (self._GPIB_index(ch), str(val)))
        if val != 0.0:
            time.sleep(5)
        return

    def get_voltage_setting(self, ch):
        r"""query voltage setting (VSET?) for specific channel"""
        self.write("VSET? %s" % self._GPIB_index(ch))
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
        self.write("VOUT? %s" % self._GPIB_index(ch))
        return float(self.read())

    def set_current(self, ch, val):
        r"""set current (in Amps) on specific channel

        Parameters
        ==========
        ch : int
            Channel 1, 2, or 3
        val : float
            Current you want to set in Amps.
            Channel 1:
                0.025 A of resolution
                0 to 7.07 V -- 0.08 to 5.15 A
                0 to 20.2 V -- 0.08 to 2.06 A
            Channel 2:
                0.050 A of resolution
                0 to 7.07 V -- 0.13 to 10.30 A
                0 to 20.2 V -- 0.13 to 4.12 A
            Channel 3:
                0.010 A of resolution
                0 to 20.2 V -- 0.05 to 2.06 A
                0 to 50.5 V -- 0.05 to 0.824 A
        Returns
        =======
        None

        """
        if val == 0:
            # shortcut the logic for I=0, so we can bypass the checks
            self.write("ISET %s,%s" % (self._GPIB_index(ch), str(val)))
            return
        if self.safe_current is None:
            raise ValueError(
                "safe_current_on_enable is not set.  You need to"
                " set it before you can do anything!"
            )
        else:
            if abs(val) > self.safe_current:
                raise ValueError(
                    "Refusing to enable output with current limit "
                    f"{val} A > safe_current_on_enable "
                    f"{self.safe_current} A. Set a smaller "
                    "current first."
                )
        if abs(val) > 1.8:
            raise ValueError(
                f"Requested current {val} A exceeds max safe current 1.8 A"
            )
        self.write("ISET %s,%s" % (self._GPIB_index(ch), str(val)))
        return

    def get_current_setting(self, ch):
        r"""query current setting (ISET?) for specific channel"""
        self.write("ISET? %s" % self._GPIB_index(ch))
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
        self.write("IOUT? %s" % self._GPIB_index(ch))
        curr_reading = float(self.read())
        for i in range(30):
            self.write("IOUT? %s" % self._GPIB_index(ch))
            this_val = float(self.read())
            if curr_reading == this_val:
                break
            if i > 28:
                print(
                    "Not able to get stable meter reading after 30 tries. "
                    f"Returning: {curr_reading:0.3f}"
                )
        return curr_reading

    def reset_overvoltage(self, ch):
        """Reset overvoltage crowbar circuit (OVRST)."""
        self.write("OVRST %s" % self._GPIB_index(ch))
        return

    def reset_overcurrent(self, ch):
        """Reset output after overcurrent protection (OCRST)."""
        self.write("OCRST %s" % self._GPIB_index(ch))
        return

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
        """Set which events can generate SRQ (SRQ).

        The SRQ setting determines the conditions under which the power
        supply will assert a service request. The manual defines four
        settings (0-3) that map to combinations of fault and error events.

        Parameters
        ==========
        setting : int
            One of 0, 1, 2, or 3 per the manual's SRQ <setting> table.

        Notes
        =====
        - Use SRQ? to query the current SRQ setting.
        - A serial poll clears the active SRQ condition.
        """
        self.write("SRQ %s" % str(setting))
        return

    def get_srq(self):
        """Query SRQ setting (SRQ?)."""
        self.write("SRQ?")
        return int(float(self.read()))

    def set_pon(self, enable):
        """Enable/disable power-on service request (PON).

        When enabled, the supply can assert SRQ at power-on or after a
        momentary loss of power. The setting is stored in non-volatile memory
        and persists across power cycles.

        Parameters
        ==========
        enable : bool or int
            Truthy to enable PON SRQ, falsy to disable. Sent as 1 or 0.

        Notes
        =====
        - Use PON? to query the current setting.
        - The manual lists conditions for which PON will generate an SRQ.
        """
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
        """Enable/disable calibration mode (CMODE).

        Calibration commands are only accepted when calibration mode is on.
        The manual notes that attempting calibration with CMODE off will
        generate a calibration error. Use this to explicitly gate access to
        calibration routines.

        Parameters
        ==========
        enable : bool or int
            Truthy to enable calibration mode, falsy to disable. Sent as 1 or 0

        Notes
        =====
        - Use CMODE? to query the current calibration mode state.
        - Calibration procedures are described in Appendix A of the manual.
        """
        enable = 1 if enable else 0
        self.write("CMODE %s" % str(enable))
        return

    def get_cmode(self):
        """Query calibration mode (CMODE?)."""
        self.write("CMODE?")
        return int(float(self.read()))

    def set_dcpon(self, mode):
        """Set power-on output state (DCPON).

        This command sets how outputs behave when AC power is applied.
        The manual defines the mode values and their effects (e.g., whether
        outputs wake up on or off and how current is biased at turn-on).

        Parameters
        ==========
        mode : int
            Mode value as defined by the manual's DCPON table.

        Notes
        =====
        - This setting affects all outputs.
        - The setting is stored in non-volatile memory.
        """
        self.write("DCPON %s" % str(mode))
        return

    def rom(self):
        """Query the firmware revision string (ROM?).

        This query returns the revision date of the power supply firmware.
        """
        self.write("ROM?")
        return self.read()

    def vmux(self, ch, input_num):
        """Query an analog multiplexer input (VMUX?).

        This command returns the measurement of the specified multiplexer
        input on the output board. It is primarily a service/diagnostic
        feature and is described in the Service Manual.

        Parameters
        ==========
        ch : int
            Channel index (0-based in this API; sent as 1-based to the
            instrument).
        input_num : int
            Multiplexer input number (1-8).
        """
        self.write("VMUX? %s,%s" % (self._GPIB_index(ch), str(input_num)))
        return float(self.read())

    # Calibration commands (Appendix A)
    def vdata(self, ch, vlo, vhi):
        """Send voltage calibration data for a channel (VDATA).

        This command supplies the measured low and high voltage values used
        to compute correction constants for the voltage setting/readback
        circuits. It is part of the calibration procedure described in
        Appendix A of the manual and requires CMODE to be enabled.

        Parameters
        ==========
        ch : int
            Channel index (0-based in this API; sent as 1-based to the
            instrument).
        vlo : float
            Measured low-voltage calibration value.
        vhi : float
            Measured high-voltage calibration value.
        """
        self.write(
            "VDATA %s,%s,%s" % (self._GPIB_index(ch), str(vlo), str(vhi))
        )
        return

    def vhi(self, ch):
        """Drive channel to the high voltage calibration point (VHI)."""
        self.write("VHI %s" % self._GPIB_index(ch))
        return

    def vlo(self, ch):
        """Drive channel to the low voltage calibration point (VLO)."""
        self.write("VLO %s" % self._GPIB_index(ch))
        return

    def idata(self, ch, ilo, ihi):
        """Send current calibration data for a channel (IDATA).

        This command supplies the measured low and high current values used
        to compute correction constants for the current setting/readback
        circuits. It is part of the calibration procedure described in
        Appendix A of the manual and requires CMODE to be enabled.

        Parameters
        ==========
        ch : int
            Channel index (0-based in this API; sent as 1-based to the
            instrument).
        ilo : float
            Measured low-current calibration value.
        ihi : float
            Measured high-current calibration value.
        """
        self.write(
            "IDATA %s,%s,%s" % (self._GPIB_index(ch), str(ilo), str(ihi))
        )
        return

    def ihi(self, ch):
        """Drive channel to the high current calibration point (IHI)."""
        self.write("IHI %s" % self._GPIB_index(ch))
        return

    def ilo(self, ch):
        """Drive channel to the low current calibration point (ILO)."""
        self.write("ILO %s" % self._GPIB_index(ch))
        return

    def ovcal(self, ch):
        """Run overvoltage calibration routine for a channel (OVCAL)."""
        self.write("OVCAL %s" % self._GPIB_index(ch))
        return

    def close(self):
        for i in range(len(self._known_output_state)):
            # set voltage and current to 0 and turn off set_output on all
            # channels, before exiting
            self.set_voltage(i, 0)
            self.set_current(i, 0)
            self.output[i] = 0
        super().close()
        return

    @channel_property
    def V_read(self, channel):
        "this retrieves the actual/read voltage"
        return self.get_voltage(channel)

    @channel_property
    def V_limit(self, channel):
        "this allows self.V_limit[channel] to evaluate properly"
        value = self.get_voltage_setting(channel)
        if self.output[channel] == 0 and np.isclose(
            value, self.min_V[channel]
        ):
            return 0
        return value

    def round_to_allowed(self, which, *args):
        """Round setpoints to the nearest instrument-supported discrete values.

        Parameters
        ----------
        which : {"I", "V"}
            Quantity to round.
        *args : tuple
            Either ``(channel, value)`` for a single zero-based channel, or a
            single iterable of per-channel values to round elementwise.

        Returns
        -------
        float or list of float
            Rounded value for a single channel, or a list of rounded values
            when an iterable is provided.
            A value of ``0`` is always allowed because it's possible
            by disabling the output.

        Raises
        ------
        ValueError
            If the arguments do not match one of the supported call forms.
        AssertionError
            If a requested value exceeds the instrument limit for its channel.
        """
        if len(args) == 2:
            channel, value = args
        elif len(args) == 1 and hasattr(args[0], "__iter__"):
            return [
                self.round_to_allowed(which, j, args[0][j])
                for j in range(len(args[0]))
            ]
        else:
            raise ValueError("I don't understand the arguments!")
        if which == "V" and channel in [0, 1]:
            if value == 0:
                return 0.0
            return self._round_voltage_to_allowed(channel, value)
        the_values = getattr(self, "allowed_" + which)[channel]
        return the_values[np.argmin(abs(value - the_values))]

    @V_limit.setter
    def V_limit(self, channel, value):
        """this causes self.V_limit[channel] = value to yield a change on the
        instrument"""
        if value == 0:
            self.set_voltage(channel, 0)
            if self._known_output_state[channel] == 1:
                self.output[channel] = 0
            self.observed_V[channel] |= {0}
        else:
            self.set_voltage(channel, value)
            if self._known_output_state[channel] == 0:
                self.output[channel] = 1
            self.observed_V[channel] |= {self.get_voltage_setting(channel)}
        return

    @channel_property
    def I_read(self, channel):
        "this retrieves the actual/read current"
        return self.get_current(channel)

    @channel_property
    def I_limit(self, channel):
        "this allows self.I_limit[channel] to evaluate properly"
        value = self.get_current_setting(channel)
        if self.output[channel] == 0 and np.isclose(
            value, self.min_I[channel]
        ):
            return 0
        return value

    @I_limit.setter
    def I_limit(self, channel, value):
        """set the current limit for a channel"""
        if abs(value) > 1.8:
            raise ValueError(
                f"Requested current {value} A exceeds "
                f"max safe current value 1.8 A"
            )
        if value == 0:
            self.set_current(channel, 0)
            if self._known_output_state[channel] == 1:
                self.output[channel] = 0
            self.observed_I[channel] |= {0}
        else:
            self.set_current(channel, value)
            if self._known_output_state[channel] == 0:
                self.output[channel] = 1
            self.observed_I[channel] |= {self.get_current_setting(channel)}
        return

    @channel_property
    def output(self, channel):
        r"""check the set_output status of a specific channel

        Parameters
        ==========
        channel : int
            Channel 1, 2, or 3
        Returns
        =======
        str stating whether the channel set_output is OFF or ON

        """
        retval = float(self.respond(f"OUT? {str(self._GPIB_index(channel))}"))
        return retval

    @output.setter
    def output(self, channel, value):
        r"""turn on or off the set_output on specific channel

        Parameters
        ==========
        channel : int
            Channel 1, 2, or 3
        value : int
            To turn set_output off, set `value` to 0 (or False)
            To turn set_output on, set `value` to 1 (or True)
        Returns
        =======
        None

        """
        assert isinstance(value, int), "value must be int (or bool)"
        assert 0 <= value <= 1, "value must be 0 (False) or 1 (True)"
        value = 1 if value else 0
        self.write(f"OUT {str(self._GPIB_index(channel))},{value}")
        self._known_output_state[channel] = value
        if value == 0:
            logger.debug("Ch %s output is OFF" % channel)
        elif value == 1:
            logger.debug("Ch %s output is ON" % channel)
        return

    @channel_property
    def status(self, channel):
        """Query status register (STS?)."""
        return int(
            float(self.respond(f"STS? {str(self._GPIB_index(channel))}"))
        )

    @channel_property
    def accumulated_status(self, channel):
        """Query accumulated status register (ASTS?)."""
        return int(
            float(self.respond(f"ASTS? {str(self._GPIB_index(channel))}"))
        )

    @channel_property
    def fault(self, channel):
        """Query fault register (FAULT?)."""
        return int(
            float(self.respond(f"FAULT? {str(self._GPIB_index(channel))}"))
        )

    @channel_property
    def overvoltage(self, channel):
        """Overvoltage trip point (OVSET)."""
        self.write(f"OVSET? {str(self._GPIB_index(channel))}")
        return float(self.read())

    @overvoltage.setter
    def overvoltage(self, channel, value):
        """Set overvoltage trip point (OVSET)."""
        self.write(f"OVSET {str(self._GPIB_index(channel))},{value}")
        return

    @channel_property
    def ocp(self, channel):
        """Overcurrent protection enable (OCP)."""
        self.write(f"OCP? {str(self._GPIB_index(channel))}")
        return int(float(self.read()))

    @ocp.setter
    def ocp(self, channel, value):
        """Enable/disable overcurrent protection (OCP)."""
        value = 1 if value else 0
        self.write(f"OCP {str(self._GPIB_index(channel))},{value}")
        return

    @channel_property
    def unmask(self, channel):
        """Mask register for a channel (UNMASK).

        The mask register works with the status register to determine which
        conditions set bits in the FAULT register. A FAULT bit is set only
        when the corresponding bit is set in both the STATUS register and
        the MASK register. Use this to enable/disable which status conditions
        are allowed to latch into FAULT for a given channel.

        Notes
        =====
        - Use this property to query the current mask value.
        - Per the manual, UNMASK sets the channel mask register directly.
        """
        self.write(f"UNMASK? {str(self._GPIB_index(channel))}")
        return int(float(self.read()))

    @unmask.setter
    def unmask(self, channel, value):
        """Set the mask register for a channel (UNMASK).

        The mask register works with the status register to determine which
        conditions set bits in the FAULT register. A FAULT bit is set only
        when the corresponding bit is set in both the STATUS register and
        the MASK register. Use this to enable/disable which status conditions
        are allowed to latch into FAULT for a given channel.

        Parameters
        ==========
        value : int
            Integer 0-255 representing the mask bits for the channel.

        Notes
        =====
        - Per the manual, UNMASK sets the channel mask register directly.
        - Read back the current mask via this same property.
        """
        self.write(f"UNMASK {str(self._GPIB_index(channel))},{value}")
        return

    @channel_property
    def delay(self, channel):
        """Reprogramming delay in seconds (DLY)."""
        self.write(f"DLY? {str(self._GPIB_index(channel))}")
        return float(self.read())

    @delay.setter
    def delay(self, channel, value):
        """Set reprogramming delay in seconds (DLY)."""
        self.write(f"DLY {str(self._GPIB_index(channel))},{value}")
        return
