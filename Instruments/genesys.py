import socket
import time

class genesys(socket.socket):
    """
    Context-managed SCPI/TCP client for a Genesys power supply,
    using a read-and-chop helper that strips the terminating CR only,
    preserves/restores the original timeout, and retries if no CR received.

    According to the Genesys manual, every response is terminated with a single CR (ASCII 13),
    and any LF (ASCII 10) is ignored by the supply fileciteturn9file12.
    """

    def __init__(self, host, port=8003, timeout_s=5, delay_s=0.1):
        super().__init__(socket.AF_INET, socket.SOCK_STREAM)
        self.host = host
        self.port = port
        self.delay = delay_s
        self.connect((self.host, self.port))
        # settimeout expects milliseconds per user requirement
        self.settimeout(timeout_s)
        print(self.respond('*IDN?'))

    def __enter__(self):
        # Open TCP connection
        self.connect((self.host, self.port))
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Ensure socket is closed on context exit
        self.close()

    def readandchop(self, bufsize=1024, timeout_s=5, max_attempts=3):
        """
        Read up to `bufsize` bytes, decode using ASCII, strip the terminating CR,
        and retry up to `max_attempts` if no CR was received.
        Temporarily sets a short timeout (in ms) then restores the original.

        :param bufsize: maximum bytes to read per attempt (default 1024)
        :param timeout_s: timeout in milliseconds for each recv (default 5)
        :param max_attempts: how many times to retry if CR isn't found (default 3)
        :returns: full response string without trailing CR
        """
        # Save current timeout (ms)
        original_to = self.gettimeout()
        # Apply short timeout
        self.settimeout(timeout_s)
        data = ""
        try:
            for _ in range(max_attempts):
                chunk = self.recv(bufsize).decode("ascii", errors="ignore")
                data += chunk
                # Check if terminator CR received
                if data.endswith("\r"):
                    break
        finally:
            # Restore prior timeout
            self.settimeout(original_to)
        # Strip the final CR
        return data.rstrip("\r")

    def respond(self, cmd, delay=None):
        """
        Send a SCPI command (appending CR) and read back the reply,
        chopping off the trailing CR automatically.
        """
        if delay is None:
            delay = self.delay
        # Send command + CR using ASCII
        self.sendall((cmd + "\n").encode("ascii"))
        # Give the supply time to process
        time.sleep(delay)
        # Read and strip terminator, retrying if needed
        return self.readandchop()

    # Convenience wrappers for common tasks
    def remote(self):
        """Enter remote mode so the supply accepts SCPI commands."""
        return self.respond("RMT 1")

    def set_current(self, amps):
        """Program the current limit (in A)."""
        return self.respond(f"PC {amps:.3f}")

    def enable_output(self, on=True):
        """Turn the output ON (True) or OFF (False)."""
        return self.respond("OUT 1" if on else "OUT 0")

    def measure_current(self):
        """Query the actual output current (in A)."""
        return self.respond("MC?")

    def set_voltage(self, volts):
        """Program the voltage limit (in V)."""
        return self.respond(f"PV {volts:.3f}")

    def measure_voltage(self):
        """Query the actual output voltage (in V)."""
        return self.respond("MV?")
