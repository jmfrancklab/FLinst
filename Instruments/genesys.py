# Manual: scanned manual (Genesys IEEE User Manual)
# SCPI Command Reference: see Appendix commands (IDN p.6; RMT p.8; OUTP p.19; PV/PC p.21-22; OVP/UVL & Protection p.52-54)
import vxi11
import logging

class genesys(vxi11.Instrument):
    """
    Context-managed SCPI/VXI-11 client for a Genesys power supply.
    Implements all page 52–54 protection & limit commands.
    """

    def __init__(self, host: str):
        super().__init__(host)
        # *IDN? query (p.6)
        retval = self.ask("*IDN?")  # SCPI: *IDN? (p.6)
        assert retval.startswith("LAMBDA,GEN80"), (
            f"{host} responded {retval}, expected Genesys model"
        )
        logging.debug(f"Connected: {retval}")

    def __enter__(self) -> "genesys":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def respond(self, cmd: str) -> str:
        """SCPI query via ask()"""
        return self.ask(cmd).strip()

    @property
    def I_limit(self) -> float:
        return float(self.respond("PC?"))  # SCPI: PC? (p.22)
    @I_limit.setter
    def I_limit(self, amps: float) -> None:
        self.write(f"PC {amps:.3f}")  # SCPI: PC <level> (p.22)

    @property
    def V_limit(self) -> float:
        return float(self.respond("PV?"))  # SCPI: PV? (p.21)
    @V_limit.setter
    def V_limit(self, volts: float) -> None:
        self.write(f"PV {volts:.3f}")  # SCPI: PV <level> (p.21)

    @property
    def remote(self) -> bool:
        """Remote mode: True if supply accepts SCPI commands."""
        return self.respond("RMT?") == "1"  # SCPI: RMT? (p.8)
    @remote.setter
    def remote(self, on: bool) -> None:
        self.write(f"RMT {1 if on else 0}")  # SCPI: RMT <0|1> (p.8)

    @property
    def output(self) -> bool:
        return self.respond("OUTP?") == "1"  # SCPI: OUTP? (p.19)
    @output.setter
    def output(self, on: bool) -> None:
        self.write(f"OUTP {1 if on else 0}")  # SCPI: OUTP <0|1> (p.19)

    # Over-Voltage Protection (OVP?) p.52
    @property
    def V_over(self) -> float:
        return float(self.respond("OVP?"))  # SCPI: OVP? (p.52)
    @V_over.setter
    def V_over(self, volts: float) -> None:
        self.write(f"OVP {volts:.3f}")  # SCPI: OVP <level> (p.52)
    def set_V_over_max(self) -> None:
        """Set OVP to maximum trip level (OVM)"""
        self.write("OVM")  # SCPI: OVM (p.53)

    # Under-Voltage Limit (UVL?) p.52
    @property
    def V_under(self) -> float:
        return float(self.respond("UVL?"))  # SCPI: UVL? (p.52)
    @V_under.setter
    def V_under(self, volts: float) -> None:
        self.write(f"UVL {volts:.3f}")  # SCPI: UVL <level> (p.52)
    def set_V_under_min(self) -> None:
        """Set UVL to minimum trip level (UVM)"""
        self.write("UVM")  # SCPI: UVM (p.53)

    # Over-Current Protection (OCP?) p.54
    @property
    def I_over(self) -> float:
        return float(self.respond("OCP?"))  # SCPI: OCP? (p.54)
    @I_over.setter
    def I_over(self, amps: float) -> None:
        self.write(f"OCP {amps:.3f}")  # SCPI: OCP <level> (p.54)
    def set_I_over_max(self) -> None:
        """Set OCP to maximum trip level (OCM)"""
        self.write("OCM")  # SCPI: OCM (p.54)

    # Output Inhibit (OHM?) p.54
    @property
    def inhibit(self) -> bool:
        return self.respond("OHM?") == "1"  # SCPI: OHM? (p.54)
    @inhibit.setter
    def inhibit(self, on: bool) -> None:
        self.write(f"OHM {1 if on else 0}")  # SCPI: OHM <0|1> (p.54)
