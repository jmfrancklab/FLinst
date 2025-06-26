import vxi11
import logging


class genesys(vxi11.Instrument):
    """
    Full SCPI/VXI-11 interface for Genesys power supply.

    We used ChatGPT to comprehensively
    implement all SCPI commands described in
    the *Genesys Series LAN Interface
    Manual*.
    The implementation includes complete support for status
    monitoring, control, and diagnostic capabilities.

    References
    ----------
    Genesys Series LAN Interface Manual, TDK Lambda, Rev 0,
    Jan. 2008.

    Parameters
    ----------
    host : str
        IP address or hostname of the power
        supply to connect.
    """

    _status_flags_map = {
        # :STAT:OPER:COND? bits
        "CV": ("oper", 0),
        "CC": ("oper", 1),
        "OV": ("oper", 2),
        "OT": ("oper", 3),
        # :STAT:QUES:COND? bits
        "V_fault": ("ques", 0),
        "I_fault": ("ques", 1),
        "fan": ("ques", 2),
        "sense": ("ques", 3),
    }

    _status_byte_flags = {
        "QUES_summary": 0,
        "MAV": 4,
        "ESB": 5,
        "RQS": 6,
    }

    _event_status_flags = {
        "Operation Complete": 0,
        "Request Control": 1,
        "Query Error": 2,
        "Device Dependent Error": 3,
        "Execution Error": 4,
        "Command Error": 5,
        "User Request": 6,
        "Power On": 7,
    }

    def __init__(self, host: str):
        super().__init__(host)
        retval = self.ask("*IDN?")
        assert retval.startswith("LAMBDA,GEN"), f"{host} responded {retval}"
        logging.debug(f"Connected: {retval}")
        self.status = {"CV": True}  # ignore CC, alert on CV mode only

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.write(f"OUTP:STAT OFF")
        self.close()

    def write(self, message, check=True):
        if check: self.check_status()
        return super().write(message)

    def respond(self, cmd, check=True):
        """
        Wrapper around ask() with strip() for clean responses.

        Parameters
        ----------
        cmd : str
            SCPI command to send.

        Returns
        -------
        retval : str
            Response with trailing whitespace removed.
        """
        if check: self.check_status()
        return self.ask(cmd).strip()

    @property
    def IDN(self):
        """
        Identification string of the connected device.

        Returns
        -------
        retval : str
            Full identification string as returned
            by the instrument.

        Notes
        -----
        - **Reading**: Returns device identification
          information (see §6.3.1.1, p. 92).
        """
        return self.respond("*IDN?")

    def reset(self):
        """
        Reset the instrument to factory default state.

        Notes
        -----
        This clears configuration and restores
        startup defaults (see §6.3.1.6, p. 95).
        """
        self.write("*RST")

    def save(self, register: int):
        """
        Save current instrument state to memory.

        Parameters
        ----------
        register : int
            The register (think MEM 1, MEM 2
            on a calculator)

        Notes
        -----
        Saves all current settings for future recall
        (see §6.3.1.4, p. 94).
        """
        self.write(f"*SAV {register}")

    def recall(self, register: int):
        """
        Recall previously saved instrument state.

        Parameters
        ----------
        register : int
            The register (think MEM 1, MEM 2
            on a calculator)

        Notes
        -----
        Loads the last saved settings from memory
        (see §6.3.1.3, p. 94).
        """
        self.write(f"*RCL {register}")

    def self_test(self):
        """
        Run internal self-diagnostic test
        (see §6.3.1.7, p. 96).
        """
        assert self.respond("*TST?") == "0"

    @property
    def status(self):
        """
        Operational and fault status of the power supply.

        Returns
        -------
        retval : dict of bool
            Dictionary reporting live indicators for
            operating mode (e.g. constant voltage/current)
            and for fault states (e.g. overvoltage, fan
            failure, or sense line errors).

        Notes
        -----
        - **Reading**: Returns a dictionary of booleans
          indicating current operating mode and faults
          as described in §6.3.8.1–2 (pp. 111–112).
        - **Assignment**: Accepts a dictionary of booleans
          specifying which flags should be enabled to
          trigger summary conditions.
        - **Deletion**: Resets all active and latched
          status bits, returning the instrument to a
          cleared state.
        """
        result = {}
        oper = int(self.respond(":STAT:OPER:COND?"))
        ques = int(self.respond(":STAT:QUES:COND?"))
        for name, (group, bit) in self._status_flags_map.items():
            if group == "oper":
                result[name] = bool(oper & (1 << bit))
            elif group == "ques":
                result[name] = bool(ques & (1 << bit))
        return result

    @status.setter
    def status(self, flags):
        self.write(":STAT:PRES")  # start by clearing all
        oper_mask = sum(
            (1 << bit)
            for name, (g, bit) in self._status_flags_map.items()
            if g == "oper" and flags.get(name, False)
        )
        ques_mask = sum(
            (1 << bit)
            for name, (g, bit) in self._status_flags_map.items()
            if g == "ques" and flags.get(name, False)
        )
        self.write(f":STAT:OPER:ENAB {oper_mask}")
        self.write(f":STAT:QUES:ENAB {ques_mask}")

    @status.deleter
    def status(self):
        self.write("*CLS")

    # Voltage and current limits
    @property
    def V_limit(self):
        """
        Configured voltage limit.

        Returns
        -------
        retval : float
            Voltage limit in volts.

        Notes
        -----
        - **Reading**: Retrieves the current voltage limit.
        - **Assignment**: Sets the voltage limit for the device.
        - **Deletion**: Not supported.
        """
        return float(self.respond(":VOLT?"))

    @V_limit.setter
    def V_limit(self, V):
        self.write(f":VOLT {V:.3f}")

    @property
    def I_limit(self):
        """
        Configured current limit.

        Returns
        -------
        retval : float
            Current limit in amperes.

        Notes
        -----
        - **Reading**: Retrieves the current limit.
        - **Assignment**: Sets the current limit for the device.
        - **Deletion**: Not supported.
        """
        return float(self.respond(":CURR?"))

    @I_limit.setter
    def I_limit(self, A):
        self.write(f":CURR {A:.3f}")

    # Output enable
    @property
    def output(self):
        return self.respond("OUTP:STAT?") == "ON"

    @output.setter
    def output(self, on):
        if not isinstance(on, bool):
            raise TypeError("output must be set to a boolean")
        self.write(f"OUTP:STAT {'ON' if on else 'OFF'}")

    # Measured values
    @property
    def V_meas(self):
        """
        Measured output voltage.

        Returns
        -------
        retval : float
            Real-time measured voltage in volts.

        Notes
        -----
        - **Reading**: Returns actual voltage at output terminals.
        - **Assignment**: Not supported.
        - **Deletion**: Not supported.
        """
        return float(self.respond(":MEAS:VOLT?"))

    @property
    def I_meas(self):
        """
        Measured output current.

        Returns
        -------
        retval : float
            Real-time measured current in amperes.

        Notes
        -----
        - **Reading**: Returns actual current at output terminals.
        - **Assignment**: Not supported.
        - **Deletion**: Not supported.
        """
        return float(self.respond(":MEAS:CURR?"))

    # Operating mode
    @property
    def mode(self):
        """
        Operating mode of the power supply.

        Returns
        -------
        retval : str
            One of "CV" or "CC" indicating constant voltage
            or constant current mode.

        Notes
        -----
        - **Reading**: Returns operating mode.
        - **Assignment**: Not supported.
        - **Deletion**: Not supported.
        """
        return self.respond(":SOUR:MODE?")

    # Local/remote control
    @property
    def remote(self):
        # need description list of what these different modes mean (from the manual, with ref)
        """
        Remote/local control status.

        Returns
        -------
        retval : str
            One of "LOC", "REM", or "LLO".

        Notes
        -----
        - **Reading**: Returns current control status.
        - **Assignment**: Changes to specified control mode.
        - **Deletion**: Not supported.
        """
        return self.respond(":SYST:SET?")

    @remote.setter
    def remote(self, mode):
        val = {0: "LOC", 1: "REM", 2: "LLO"}.get(mode, mode)
        self.write(f":SYST:SET {val}")

    @property
    def auto_restart(self):
        # this needs a reference to a section of the manual
        """
        Auto-restart state after power-on.

        Returns
        -------
        retval : bool
            True if output is enabled automatically
            after power-on.

        Notes
        -----
        - **Reading**: Indicates if auto-restart is enabled.
        - **Assignment**: Sets whether output restarts
          automatically.
        - **Deletion**: Not supported.
        """
        return self.respond(":OUTP:PON?") == "ON"

    @auto_restart.setter
    def auto_restart(self, on):
        if not isinstance(on, bool):
            raise TypeError("auto_restart must be set to a boolean")
        self.write(f":OUTP:PON {'ON' if on else 'OFF'}")

    # Foldback protection
    @property
    def foldback(self):
        # this needs a description of foldback and also a reference to a section of the manual
        """
        Foldback protection enable.

        Returns
        -------
        retval : bool
            True if foldback protection is enabled.

        Notes
        -----
        - **Reading**: Returns status of foldback protection,
          which disables output in overcurrent situations.
        - **Assignment**: Enables or disables foldback.
        - **Deletion**: Not supported.
        """
        return self.respond(":CURR:PROT:STAT?") == "ON"

    @foldback.setter
    def foldback(self, on):
        if not isinstance(on, bool):
            raise TypeError("foldback must be set to a boolean")
        self.write(f":CURR:PROT:STAT {'ON' if on else 'OFF'}")

    @property
    def foldback_tripped(self):
        return self.respond(":CURR:PROT:TRIP?") == "1"

    # OVP
    @property
    def V_over(self):
        # this needs a reference to the manual and a description of what overvoltage protection is
        """
        Overvoltage protection level.

        Returns
        -------
        retval : float
            Trip voltage for overvoltage protection.

        Notes
        -----
        - **Reading**: Gets overvoltage threshold.
        - **Assignment**: Sets protection voltage or "MAX"
          to allow highest range.
        - **Deletion**: Not supported.
        """
        return float(self.respond(":VOLT:PROT:LEV?"))

    @V_over.setter
    def V_over(self, volts):
        if volts == "MAX":
            self.write(":VOLT:PROT:LEV MAX")
        else:
            self.write(f":VOLT:PROT:LEV {volts:.3f}")

    @property
    def V_over_tripped(self):
        """
        Overvoltage protection trip status.

        Returns
        -------
        retval : bool
            True if overvoltage protection has tripped.

        Notes
        -----
        - **Reading**: Indicates whether OVP condition
          occurred (see §6.3.8.10, p. 116).
        - **Assignment**: Not supported.
        - **Deletion**: Not supported.
        """
        return self.respond(":VOLT:PROT:TRIP?") == "1"

    @property
    def V_under(self):
        """
        Undervoltage limit (UVL) threshold.

        Returns
        -------
        retval : float
            Voltage level for undervoltage cutoff.

        Notes
        -----
        - **Reading**: Returns the UVL threshold.
        - **Assignment**: Sets the UVL threshold.
        - **Deletion**: Not supported.
        """
        return float(self.respond(":VOLT:LIM:LOW?"))

    @V_under.setter
    def V_under(self, volts):
        self.write(f":VOLT:LIM:LOW {volts:.3f}")

    def blink_lan(self, on=True):
        self.write(f":SYST:COMM:LAN:IDLED {'ON' if on else 'OFF'}")

    def blink_led(self):
        """
        Blink front panel LED for physical identification.

        Notes
        -----
        - **Call**: Blinks LED on front panel.
          See §6.3.1.8, p. 97.
        """
        self.write("SYST:LED:BLINK")

    @property
    def hostname(self):
        """
        Hostname assigned to LAN interface.

        Returns
        -------
        retval : str
            Current hostname configuration.

        Notes
        -----
        - **Reading**: Queries configured LAN hostname.
        - **Assignment**: Not supported.
        - **Deletion**: Not supported.
        """
        return self.respond(":SYST:COMM:LAN:HOST?")

    @property
    def ip(self):
        """
        Returns the IP address assigned to the LAN interface.

        Returns
        -------
        retval : str
            IP address in dotted quad format.

        Notes
        -----
        - **Reading**: Returns the current IP configuration.
        - **Assignment**: Not supported.
        - **Deletion**: Not supported.
        """
        return self.respond(":SYST:COMM:LAN:IP?")

    @property
    def mac(self):
        """
        Returns the MAC address of the LAN interface.

        Returns
        -------
        retval : str
            MAC address in standard colon-separated format.

        Notes
        -----
        - **Reading**: Returns the unique hardware address.
        - **Assignment**: Not supported.
        - **Deletion**: Not supported.
        """
        return self.respond(":SYST:COMM:LAN:MAC?")

    def reset_lan(self):
        """
        Resets LAN interface to DHCP and reboots.

        Notes
        -----
        - **Call**: Useful for resetting network config.
          See §6.3.2.4, p. 101.
        """
        self.write("SYST:COMM:LAN:REST")

    def pass_through(self, cmd):
        """
        Send arbitrary SCPI command using
        diagnostic pass-through.

        Parameters
        ----------
        cmd : str
            Raw command to send.

        Notes
        -----
        - **Call**: Allows manual SCPI control.
        """
        return self.respond(f":DIAG:COMM:PASS {cmd}")

    # Errors
    @property
    def error(self):
        """
        Notes
        -----
        - On **Retrieval**: Checks for error.  Manual page needed!
        - On **Delete**: Empties errors and resets
          summary bits. See §6.3.1.5, p. 95.
        """
        return self.respond(":SYST:ERR?")

    @error.deleter
    def error(self):
        self.write(":SYST:ERR:ENAB")
        self.write("*CLS")
        self.write("SYST:ERR:CLE")

    @property
    def scpi_version(self):
        """
        Returns the SCPI version supported by the instrument.

        Returns
        -------
        retval : str
            Version number string.

        Notes
        -----
        - **Reading**: Indicates firmware SCPI compliance version.
        - **Assignment**: Not supported.
        - **Deletion**: Not supported.
        """
        return self.respond(":SYST:VERS?")

    def check_status(self):
        """
        Check for summary or fault conditions.

        Returns
        -------
        retval : dict of bool
            Dictionary of bits from *STB? for QUES, MAV, etc.

        Notes
        -----
        - **Reading**: Queries the status byte (*STB?) and
          raises RuntimeError if any summary bits indicate
          error or warning states.
          See §6.3.1.1, p. 92 and §6.3.8.1–2, pp. 111–112.
        - **Assignment**: Not supported.
        - **Deletion**: Not supported.
        """
        val = int(self.respond("*STB?"))
        flags = {
            k: bool(val & (1 << b)) for k, b in self._status_byte_flags.items()
        }
        if flags.get("QUES_summary") and any(
            self.status.get(k)
            for k in ["V_fault", "I_fault", "fan", "sense"]
        ):
            raise RuntimeError(
                "Questionable condition"
                + "|".join(
                    k
                    for k in self.status.keys()
                    if self.status.get(k)
                )
                + "detected"
            )
        elif flags.get("QUES_summary"):
            raise RuntimeError("unknown questionalbe status!")
        if flags.get("ESB") and any(self.event_status.values()):
            raise RuntimeError(
                "Event status flag"
                + "|".join(
                    k
                    for k in self.event_status.keys()
                    if self.event_status.get(k)
                )
                + "active"
            )
        return flags

    @property
    def event_status(self):
        """
        Event status summary bits.

        Returns
        -------
        retval : dict of bool
            Dictionary indicating which event bits are set.

        Notes
        -----
        - **Reading**: Queries event register using *ESR?
          and returns a dict of named flags.
          See §6.3.1.2, p. 93.
        - **Assignment**: Use the setter to write a bitmask
          with, specifying which events to monitor.
        - **Deletion**: Not supported.
        """
        val = int(self.respond("*ESR?"))
        return {
            k: bool(val & (1 << b))
            for k, b in self._event_status_flags.items()
        }

    @event_status.setter
    def event_status(self, flags):
        val = sum(
            (1 << self._event_status_flags[k])
            for k, v in flags.items()
            if v and k in self._event_status_flags
        )
        self.write(f"*ESE {val}")

    @property
    def operation_complete(self):
        """
        Returns the operation complete bit.

        Returns
        -------
        retval : bool
            True if the instrument has finished
            all pending operations.

        Notes
        -----
        - **Reading**: Queries whether all operations
          are complete (see §6.3.1.2, p. 93).
        - **Assignment**: Setting to True inserts a
          synchronization point into the command
          queue. False has no effect.
        """
        return self.respond("*OPC?") == "1"

    @operation_complete.setter
    def operation_complete(self, val):
        if not isinstance(val, bool):
            raise TypeError("operation_complete must be set to a boolean")
        if val:
            self.write("*OPC")
