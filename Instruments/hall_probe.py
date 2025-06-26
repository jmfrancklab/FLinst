import socket
import time
from .gpib_eth import gpib_eth
from .log_inst import logger
from pint import UnitRegistry

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
        return

    @property
    def IDN(self):
        """Return the *IDN? string (manufacturer, model, serial, date)."""
        return self.respond("*IDN?")

    @property
    def field(self):
        """
        Read the magnetic field as a pint.Quantity.

        Returns
        -------
        pint.Quantity
            Magnetic field with appropriate units.
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

        unit_code = int(self.respond("UNIT?"))
        unit_map = {
            1: ureg.gauss,
            2: ureg.tesla,
            3: ureg.oersted,
            4: ureg.ampere / ureg.meter,
        }
        return value * unit_map.get(unit_code, ureg.gauss)

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
