import socket
import time
from .gpib_eth import gpib_eth
from .log_inst import logger

"""
Class for controlling LakeShore 475 Gaussmeter written by AG using ChatGPT and inferring
from HP6623A.py, HP8672A.py and gigatronics.py.
ChatGPT Conversation: https://chatgpt.com/share/6851b044-3030-800d-ae80-7943105f6a59
Refer to the user manual for the detailed explanations of the commands starting from
the page 6-28.
"""

class LakeShore475 (gpib_eth):
    """
    Context-managed Lake Shore 475 Gaussmeter via PrologixEthernet.
    Usage:
        with LakeShore475(prologix, gpib_addr) as gauss:
            ...
    """
    def __init__(self, prologix_instance=None, address=12,eos=0):
        """ınıtıalıze ınstance of connectıon to hall probe
        
        parameters
        ==========
        eos : ınt
            2 -- set ınstrument to IEEE Terms = LF
            0 -- set ınstrument to IEEE Terms = CR LF
        """
        super().__init__(prologix_instance,address,eos=eos)
        idstring = self.respond("*IDN?") 
        if idstring.startswith('LSCI,MODEL475'):
            logger.debug("Detected LakeShore Gaussmeter with ID string %s"%idstring)
        else:
            raise ValueError("Not detecting identity as Lakeshore Gaussmeter 475, returned ID string as %s"%idstring)
        return
        
    def identify(self):
        """Return the *IDN? string (manufacturer, model, serial, date)."""
        return self.respond("*IDN?")
    
    def set_field_units(self, unit_code: int):
        """
        Select field reading units:
            1 = Gauss, 2 = Tesla, 3 = Oersted, 4 = A/meter.
        """
        self.write(f"UNIT {unit_code}")

    def read_field(self):
        """Return the present magnetic field reading in gauss."""
        return float(self.respond("READ?"))
    
    def get_field_units(self) -> int:
        """Query the current field‐unit setting (returns the code)."""
        return int(self.respond("UNIT?"))
    
    def read_field(self) -> float:
        """
        Read the magnetic field in the current units.
        Returns a float (e.g. +273.150E+00).
        """
        resp = self.respond("RDGFIELD?")
        try:
            response = float(resp)  # field reading query :contentReference[oaicite:3]{index=3}
            return response

        except: #For error messages, refer Sec. 8.6 at page 8-3 in the manual.
            if resp == 'NO PROBE':
                raise ValueError('No Hall Probe is attached!')
            elif resp == 'OL':
                raise ValueError('The measured field is larger than the range. Increase the measurement range or check probe zero.')
            else: 
                raise ValueError('Other type of error: %s'%resp)
            
    def set_range(self, range_code: int):
        """
        Manually select a measurement range (1–5).
        Disables auto-ranging when invoked. 
        """
        if not 1 <= range_code <= 5:
            raise ValueError("Range must be an integer from 1 to 5")
        self.write(f"RANGE {range_code}")

    def get_range(self) -> int:
        """Query the present manual range (returns 1–5, field values are probe depended)."""
        return int(self.respond("RANGE?"))
    
    def enable_auto_range(self, enable: bool):
        """
        Turn auto-ranging on or off:
            True  → AUTO 1
            False → AUTO 0
        """
        self.write(f"AUTO {1 if enable else 0}")

    def is_auto(self) -> bool:
        """Query auto-ranging state (returns True if on). """

        return bool(int(self.respond("AUTO?")))

    def zero_probe(self):
        """Re-zero the probe before measurements."""
        self.write("ZPROBE")


