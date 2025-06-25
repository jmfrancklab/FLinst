import vxi11
import logging


class genesys(vxi11.Instrument):
    """
    Context-managed SCPI/VXI-11 client for a Genesys power supply.
    Inherits from python-vxi11's Instrument to leverage the built-in ask() method.
    """

    def __init__(self, host: str):
        super().__init__(host)
        try:
            retval = self.ask("*IDN?")
        except vxi11.vxi11.Vxi11Exception as e:
            if "another link" in str(e):
                raise IOError(
                    "Make sure you are not logged into the web interface on"
                    " the power supply!"
                )
            else:
                raise IOError("Unknown error")
        assert retval.startswith("LAMBDA,GEN80"), (
            f"{host} appears to be hooked up to {retval}, not the Genesys"
            " supply!!")
        logging.debug(f"connected to {retval}")

    def __enter__(self) -> "genesys":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.write(f"OUT 0") # turn off the output
        self.write(f"RMT 0")
        # Propagate any exceptions from close to notify of disconnect issues
        self.close()

    def respond(self, cmd: str) -> str:
        """
        Send a SCPI command and return the stripped reply.
        Uses the built-in ask() to handle write/read without manual delays.
        """
        return self.ask(cmd).strip()

    @property
    def I_limit(self) -> float:
        """Programmed current limit in A."""
        return float(self.respond("PC?"))

    @I_limit.setter
    def I_limit(self, amps: float) -> None:
        self.write(f"PC {amps:.3f}")

    @property
    def V_limit(self) -> float:
        """Programmed voltage limit in V."""
        return float(self.respond("PV?"))

    @V_limit.setter
    def V_limit(self, volts: float) -> None:
        self.write(f"PV {volts:.3f}")

    @property
    def remote(self) -> bool:
        """Remote mode: True if supply accepts SCPI commands."""
        return self.respond("RMT?") == "1"

    @remote.setter
    def remote(self, on: bool) -> None:
        self.write(f"RMT {1 if on else 0}")

    @property
    def output(self) -> bool:
        """Output state: True if output is ON, False if OFF."""
        return self.respond("OUT?") == "1"

    @output.setter
    def output(self, on: bool) -> None:
        self.write(f"OUT {1 if on else 0}")

    @property
    def V_over(self) -> float:
        """Over-voltage protection threshold in V."""
        return float(self.respond("OVP?"))

    @V_over.setter
    def V_over(self, volts: float) -> None:
        self.write(f"OVP {volts:.3f}")

    @property
    def V_under(self) -> float:
        """Under-voltage protection threshold in V."""
        return float(self.respond("UVL?"))

    @V_under.setter
    def V_under(self, volts: float) -> None:
        self.write(f"UVL {volts:.3f}")
