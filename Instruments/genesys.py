import vxi11
import logging


class genesys(vxi11.Instrument):
    """
    Full SCPI/VXI-11 interface for Genesys power supply.

    We used ChatGPT to automatically include all functionality
    documented in the SCPI Reference section
    of the *Genesys Series LAN Interface Manual*, which is referenced
    below.
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
        """
        Initialize and validate connection to Genesys
        power supply.

        Parameters
        ----------
        host : str
            IP address or hostname of the power
            supply.
        """
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

    def write(self, message):
        self.check_status()
        return super().write(message)

    def respond(self, cmd):
        """
        Wrapper around ask() with strip() for clean responses.

        Parameters
        ----------
        cmd : str
            SCPI command to send.

        Returns
        -------
        retval : str
            Stripped string returned from instrument.
        """
        return self.ask(cmd).strip()

    @property
    def IDN(self):
        return self.respond("*IDN?")

    def reset(self):
        self.write("*RST")

    def save(self):
        self.write("*SAV 0")

    def recall(self):
        self.write("*RCL 0")

    def self_test(self):
        return self.respond("*TST?") == "0"

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
          as described in §6.3.8.1–2 (pp. 111–112) of the
          *Genesys Series LAN Interface Manual*.
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
        return float(self.respond(":VOLT?"))

    @V_limit.setter
    def V_limit(self, V):
        self.write(f":VOLT {V:.3f}")

    @property
    def I_limit(self):
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
        return float(self.respond(":MEAS:VOLT?"))

    @property
    def I_meas(self):
        return float(self.respond(":MEAS:CURR?"))

    # Operating mode
    @property
    def mode(self):
        return self.respond(":SOUR:MODE?")

    # Local/remote control
    @property
    def remote(self):
        return self.respond(":SYST:SET?")

    @remote.setter
    def remote(self, mode):
        val = {0: "LOC", 1: "REM", 2: "LLO"}.get(mode, mode)
        self.write(f":SYST:SET {val}")

    # Auto-restart
    @property
    def auto_restart(self):
        return self.respond(":OUTP:PON?") == "ON"

    @auto_restart.setter
    def auto_restart(self, on):
        if not isinstance(on, bool):
            raise TypeError("auto_restart must be set to a boolean")
        self.write(f":OUTP:PON {'ON' if on else 'OFF'}")

    # Foldback protection
    @property
    def foldback(self):
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
        return float(self.respond(":VOLT:PROT:LEV?"))

    @V_over.setter
    def V_over(self, volts):
        if volts == "MAX":
            self.write(":VOLT:PROT:LEV MAX")
        else:
            self.write(f":VOLT:PROT:LEV {volts:.3f}")

    @property
    def V_over_tripped(self):
        return self.respond(":VOLT:PROT:TRIP?") == "1"

    # UVL
    @property
    def V_under(self):
        return float(self.respond(":VOLT:LIM:LOW?"))

    @V_under.setter
    def V_under(self, volts):
        self.write(f":VOLT:LIM:LOW {volts:.3f}")

    # LAN blink
    def blink_led(self, on=True):
        self.write(f":SYST:COMM:LAN:IDLED {'ON' if on else 'OFF'}")

    # Network identity
    @property
    def hostname(self):
        return self.respond(":SYST:COMM:LAN:HOST?")

    @property
    def ip(self):
        return self.respond(":SYST:COMM:LAN:IP?")

    @property
    def mac(self):
        return self.respond(":SYST:COMM:LAN:MAC?")

    def reset_lan(self):
        self.write(":SYST:COMM:LAN:RES")

    # Diagnostic serial pass-through
    def pass_through(self, cmd):
        return self.respond(f":DIAG:COMM:PASS {cmd}")

    # Errors
    @property
    def error(self):
        return self.respond(":SYST:ERR?")

    @error.deleter
    def error(self):
        self.write(":SYST:ERR:ENAB")

    # SCPI version
    @property
    def scpi_version(self):
        return self.respond(":SYST:VERS?")

    def check_status(self):
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
        return self.respond("*OPC?") == "1"

    @operation_complete.setter
    def operation_complete(self, val):
        if not isinstance(val, bool):
            raise TypeError("operation_complete must be set to a boolean")
        if val:
            self.write("*OPC")
