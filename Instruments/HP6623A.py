from .gpib_eth import gpib_eth
from .log_inst import logger
import time
from channel_proxy_and_property import channel_property


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
        """Set the mask register for a channel (UNMASK).

        The mask register works with the status register to determine which
        conditions set bits in the FAULT register. A FAULT bit is set only
        when the corresponding bit is set in both the STATUS register and
        the MASK register. Use this to enable/disable which status conditions
        are allowed to latch into FAULT for a given channel.

        Parameters
        ==========
        ch : int
            Channel index (0-based in this API; sent as 1-based to the
            instrument).
        mask : int
            Integer 0-255 representing the mask bits for the channel.

        Notes
        =====
        - Per the manual, UNMASK sets the channel mask register directly.
        - Use UNMASK? to query the current mask value.
        """
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
        self.write("VMUX? %s,%s" % (str(ch + 1), str(input_num)))
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
        self.write("VDATA %s,%s,%s" % (str(ch + 1), str(vlo), str(vhi)))
        return

    def vhi(self, ch):
        """Drive channel to the high voltage calibration point (VHI)."""
        self.write("VHI %s" % str(ch + 1))
        return

    def vlo(self, ch):
        """Drive channel to the low voltage calibration point (VLO)."""
        self.write("VLO %s" % str(ch + 1))
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
        self.write("IDATA %s,%s,%s" % (str(ch + 1), str(ilo), str(ihi)))
        return

    def ihi(self, ch):
        """Drive channel to the high current calibration point (IHI)."""
        self.write("IHI %s" % str(ch + 1))
        return

    def ilo(self, ch):
        """Drive channel to the low current calibration point (ILO)."""
        self.write("ILO %s" % str(ch + 1))
        return

    def ovcal(self, ch):
        """Run overvoltage calibration routine for a channel (OVCAL)."""
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

    @channel_property
    def V_limit(self, channel):
        "this allows self.V_limit[channel] to evaluate properly"
        return self.get_voltage(channel)

    @V_limit.setter
    def V_limit(self, channel, value):
        """this causes self.V_limit[channel] = value to yield a change on the
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
    def I_limit(self, channel):
        "this allows self.I_limit[channel] to evaluate properly"
        return self.get_current(channel)

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
