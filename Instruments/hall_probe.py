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
