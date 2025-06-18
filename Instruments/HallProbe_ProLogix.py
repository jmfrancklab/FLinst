import time

class HallProbeController:
    """
    Controls a discrete Lake Shore Hall probe via a user-programmable HMCBL-6 cable
    attached to a Prologix GPIB-USB controller.

    Usage:
        gpib = Prologix(port='/dev/ttyUSB0', address=5)
        probe = HallProbeController(gpib)
        probe.program_user_cable(
            serial_number=1234567890,
            current_mA=100,
            sensitivity_mV_per_kG=1.00
        )
        probe.zero_probe()
        field = probe.read_field()  # returns field in kG
        Generated with ChatGBT: https://chatgpt.com/share/6851b044-3030-800d-ae80-7943105f6a59
        Note: method previously named as "_query" is renamed as "_respond".
    """

    def __init__(self, prologix: Prologix):
        self.gpib = prologix #Code saves GPIB-USB instance so all methods can call self.gpib.write(...) or self.gpib.read()
        self.sensitivity = None  # mV/kG, filled after programming

    def _write(self, cmd: str):
        """Helper to send Prologix commands."""
        self.gpib.write(f"{cmd}\n") #A write command as you suggested
    
    def _respond(self, cmd: str) -> str: #Takes the responses with a write command. Returns the stripped response.
        """Helper to send a query and return the response."""
        self._write(cmd)
        return self.gpib.read().strip()

    def program_user_cable(self, serial_number: int, current_mA: int, sensitivity_mV_per_kG: float):
        
        """
        Programs a blank HMCBL-6 cable with:
          1) sensor serial number,
          2) excitation current (1, 10, or 100 mA),
          3) sensitivity (mV per kG).
        Follows the Lake Shore manual §2.1 sequence.
        """
        
        # Enter user-cable programming mode
        self._write("++mode 0")  # Put ProLogix into direct-pass-through
        self._write("++savecfg 0")  # Don't save the ProLogix config yet
        self._write("++addr 0")  # Cable programming livese at GPIB address 0

        # Start MCBL(user-cable) programming
        self._write("++help")  # ensure controller is in CLI (optional -says ChatGPT)
        self._write("MCBL program")  # this assumes terminal mode; adjust if wrapping raw commands. 
        
        # 1) Serial number as ASCII
        self._write(f"{serial_number}")

        # 2) Control current
        assert current_mA in (1, 10, 100) #Cheks if the desired current value is suitable. Raises an error if not and halts the operation.
        """Hall “control current” is not a free‐form value but must be chosen
        from the three discrete settings of 1 mA, 10 mA, or 100 mA. 100 mA in most cases -->Manual"""
        self._write(str(current_mA))

        # 3) Sensitivity. Program the sensitivity in 5 decimal places.
        self._write(f"{sensitivity_mV_per_kG:.5f}")

        # Commit and exit
        self._write("++savecfg 1") #Commit the Prologix side. Save the configuration.
        time.sleep(0.1) #A short delay for EEPROM write
        self.sensitivity = sensitivity_mV_per_kG

    def zero_probe(self):
        """
        Zeros the probe offset. Assumes the probe tip is in a zero‐Gauss chamber.
        Implements the Zero Probe sequence from the Model 475 manual :contentReference[oaicite:2]{index=2}.
        """
        # Enter Controller mode & point to Model 475 emulator
        self._write("++mode 1")  # Controller mode
        self._write("++auto 0")  # Turn off read-after-write
        # Null probe offset
        self._write("++clr")  # send device clear
        self._write("ZERO PROBE")  # assuming passthrough into 475
        time.sleep(2)  # allow time for calibration

    def read_field(self) -> float:
        """
        Reads the Hall voltage and converts to field (kG).
        Expects the instrument to be in DC read‐after‐write mode.
        """
        self._write("++auto 1")     # Enable read-after-write
        raw = self._respond("MEAS:VOLT?")  # Query Hall voltage in mV
        vh = float(raw)  #Converts ASCII to float
        if abs(vh) > 0.2:  # sanity check for offset :contentReference[oaicite:3]{index=3}. Manual says any offset greater than \pm 0.2 mV is suspicious
            raise RuntimeError(f"Probe offset too large: {vh} mV")
        # Convert: field(kG) = vh (mV) / sensitivity (mV/kG)
        return vh / self.sensitivity

    def close(self):
        """Cleanup: restore Prologix defaults if needed."""
        self._write("++auto 0")
        self._write("++mode 1")
        self.gpib.close()
