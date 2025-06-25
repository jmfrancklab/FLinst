import vxi11
import logging


class genesys(vxi11.Instrument):
    """
    Full SCPI/VXI-11 interface for Genesys power supply.
    Includes all commands from SCPI Reference section.
    """

    def __init__(self, host: str):
        super().__init__(host)
        retval = self.ask("*IDN?")
        assert retval.startswith("LAMBDA,GEN"), f"{host} responded {retval}"
        logging.debug(f"Connected: {retval}")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def respond(self, cmd):
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

    def clear_status(self):
        self.write("*CLS")

    # Voltage and current limits
    @property
    def V_limit(self):
        return float(self.respond("VOLT?"))

    @V_limit.setter
    def V_limit(self, V):
        self.write(f"VOLT {V:.3f}")

    @property
    def I_limit(self):
        return float(self.respond("CURR?"))

    @I_limit.setter
    def I_limit(self, A):
        self.write(f"CURR {A:.3f}")

    # Output enable
    @property
    def output(self):
        return self.respond("OUTP:STAT?") == "ON"

    @output.setter
    def output(self, on):
        self.write(f"OUTP:STAT {'ON' if on else 'OFF'}")

    # Measured values
    @property
    def V_meas(self):
        return float(self.respond("MEAS:VOLT?"))

    @property
    def I_meas(self):
        return float(self.respond("MEAS:CURR?"))

    # Operating mode
    @property
    def mode(self):
        return self.respond("SOUR:MODE?")

    # Local/remote control
    @property
    def remote(self):
        return self.respond("SYST:SET?")

    @remote.setter
    def remote(self, mode):
        val = {0: "LOC", 1: "REM", 2: "LLO"}.get(mode, mode)
        self.write(f"SYST:SET {val}")

    # Auto-restart
    @property
    def auto_restart(self):
        return self.respond("OUTP:PON?") == "ON"

    @auto_restart.setter
    def auto_restart(self, on):
        self.write(f"OUTP:PON {'ON' if on else 'OFF'}")

    # Foldback protection
    @property
    def foldback(self):
        return self.respond("CURR:PROT:STAT?") == "ON"

    @foldback.setter
    def foldback(self, on):
        self.write(f"CURR:PROT:STAT {'ON' if on else 'OFF'}")

    @property
    def foldback_tripped(self):
        return self.respond("CURR:PROT:TRIP?") == "1"

    # OVP
    @property
    def V_over(self):
        return float(self.respond("VOLT:PROT:LEV?"))

    @V_over.setter
    def V_over(self, volts):
        if volts == "MAX":
            self.write("VOLT:PROT:LEV MAX")
        else:
            self.write(f"VOLT:PROT:LEV {volts:.3f}")

    @property
    def V_over_tripped(self):
        return self.respond("VOLT:PROT:TRIP?") == "1"

    # UVL
    @property
    def V_under(self):
        return float(self.respond("VOLT:LIM:LOW?"))

    @V_under.setter
    def V_under(self, volts):
        self.write(f"VOLT:LIM:LOW {volts:.3f}")

    # LAN blink
    def blink_led(self, on=True):
        self.write(f"SYST:COMM:LAN:IDLED {'ON' if on else 'OFF'}")

    # Network identity
    @property
    def hostname(self):
        return self.respond("SYST:COMM:LAN:HOST?")

    @property
    def ip(self):
        return self.respond("SYST:COMM:LAN:IP?")

    @property
    def mac(self):
        return self.respond("SYST:COMM:LAN:MAC?")

    def reset_lan(self):
        self.write("SYST:COMM:LAN:RES")

    # Diagnostic serial pass-through
    def pass_through(self, cmd):
        return self.respond(f"DIAG:COMM:PASS {cmd}")

    # Errors
    def read_error(self):
        return self.respond("SYST:ERR?")

    def clear_errors(self):
        self.write("SYST:ERR:ENAB")

    # SCPI version
    @property
    def scpi_version(self):
        return self.respond("SYST:VERS?")

    # Status byte
    @property
    def status_byte(self):
        return int(self.respond("*STB?"))

    @property
    def event_status(self):
        return int(self.respond("*ESR?"))

    def enable_event_status(self, val):
        self.write(f"*ESE {val}")

    def read_op_complete(self):
        return int(self.respond("*OPC?"))

    def set_op_complete(self):
        self.write("*OPC")

    # Condition/event registers
    def read_oper_cond(self):
        return int(self.respond("STAT:OPER:COND?"))

    def read_oper_event(self):
        return int(self.respond("STAT:OPER:EVEN?"))

    def set_oper_enable(self, val):
        self.write(f"STAT:OPER:ENAB {val}")

    def read_ques_cond(self):
        return int(self.respond("STAT:QUES:COND?"))

    def read_ques_event(self):
        return int(self.respond("STAT:QUES:EVEN?"))

    def set_ques_enable(self, val):
        self.write(f"STAT:QUES:ENAB {val}")

    def enable_all_events(self):
        self.write("STAT:PRES")
