import socket
import time
from .gpib_eth import gpib_eth
from .log_inst import logger

class LakeShore475 (gpib_eth):
    """
    Context-managed Lake Shore 475 Gaussmeter via PrologixEthernet.
    Usage:
        with LakeShore475(prologix, gpib_addr) as gauss:
            ...
    """
    def __init__(self, prologix_instance=None, address=None):
        super().__init__(prologix_instance,address)
        self.write("MODE 1") # Put the device in remote mode
        idstring = self.respond("*IDN?")
        if idstring[0:4] == 'LSCI':
            logger.debug("Detected LakeShore Gaussmeter with ID string %s"%idstring)
        else:
            raise ValueError("Not detecting identity as Lakeshore Gaussmeter, returned ID string as %s"%idstring)
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
        return float(self.plx.gpib_query("READ?"))
    
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

        except:
            if resp == 'NO PROBE':
                raise ValueError('No Hall Probe is attached!')
            elif resp == 'OL':
                raise ValueError('Measured field is above the present range!')
            
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
        self.plx.gpib_write("ZPROBE")


# Example usage with context managers
if __name__ == "__main__":
    PROLOGIX_IP = "192.168.0.162"  # replace with your Prologix IP
    GPIB_ADDR = 12                  # Lake Shore 475 address

    with LakeShore475(PROLOGIX_IP, GPIB_ADDR) as gauss:
        gauss.set_field_units(1) #Sets units to G. Use 2 to set units in T.
        if not gauss.is_auto(): #Makes sure that the auto range is enabled
            gauss.enable_auto_range(1)
        time.sleep(1)
        field = gauss.read_field()  #Reading the field
        print(f"Magnetic field: {field:.3f} G")