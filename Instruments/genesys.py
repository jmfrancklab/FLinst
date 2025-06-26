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
