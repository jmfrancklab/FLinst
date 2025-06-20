import socket
import time

class LakeShore475:
    """
    Context-managed Lake Shore 475 Gaussmeter via PrologixEthernet.
    Usage:
        with LakeShore475(prologix, gpib_addr) as gauss:
            ...
    """
    def __init__(self, prologix: PrologixEthernet, gpib_addr: int):
        self.plx = prologix
        self.gpib_addr = gpib_addr

    def __enter__(self):
        # Set controller mode and select address
        self.plx.send("++mode 1")
        self.plx.send(f"++addr {self.gpib_addr}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Nothing special to clean up for the 475
        return False

    def read_field(self) -> float:
        """Return the present magnetic field reading in gauss."""
        return float(self.plx.gpib_query("READ?"))

    def set_range(self, gauss_range: float):
        """Set the measurement range (e.g., 3500 for 3.5 kG)."""
        self.plx.gpib_write(f"RANGE {gauss_range}")

    def zero_probe(self):
        """Re-zero the probe before measurements."""
        self.plx.gpib_write("ZPROBE")


# Example usage with context managers
if __name__ == "__main__":
    PROLOGIX_IP = "192.168.0.162"  # replace with your Prologix IP
    GPIB_ADDR = 5                  # Lake Shore 475 address

    with PrologixEthernet(PROLOGIX_IP) as plx:
        with LakeShore475(plx, GPIB_ADDR) as gauss:
            # Zero probe and allow settling
            gauss.zero_probe()
            time.sleep(1)

            # Set range and read field
            gauss.set_range(3500)
            field = gauss.read_field()
            print(f"Magnetic field: {field:.3f} G")

