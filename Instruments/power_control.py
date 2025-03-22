"""This class provides a class that acts as a client for the
power_control_server.

It should handle:

-   B12 communications
-   GPIB communications

and it provides the capability to start and stop the log.

"""

import socket
import sys
import time
import pickle

IP = "127.0.0.1"
# IP = "jmfrancklab-bruker.syr.edu"
# IP = "128.230.29.95"
if len(sys.argv) > 1:
    IP = sys.argv[1]
PORT = 6002
short_sleep = 0.01
slow_sleep = 0.5
buffer_size = 1024


class power_control(object):
    """wraps the ethernet connection to the XEPR server and allows you to send
    commands (provides a with block)"""

    do_quit = False

    def __init__(self, ip=IP, port=PORT):
        print("target IP:", IP)
        print("target port:", PORT)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((IP, PORT))

    def __enter__(self):
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        if self.do_quit:
            self.send("QUIT")
        else:
            self.send("CLOSE")
        self.sock.close()
        return

    def arrange_quit(self):
        "quit once we leave the block"
        self.do_quit = True

    def get(self, n_slow_tries=0, slow_wait=slow_sleep):
        data = self.sock.recv(buffer_size).decode("ASCII").strip()
        success = False
        for j in range(n_slow_tries):
            if len(data) == 0:
                data = self.sock.recv(buffer_size).decode("ASCII").strip()
                time.sleep(slow_wait)
            else:
                success = True
                break
        for j in range(30):
            if len(data) == 0:
                data = self.sock.recv(buffer_size).decode("ASCII").strip()
                time.sleep(short_sleep)
            else:
                success = True
                break
        if not success:
            raise ValueError("no response after 30 tries!!")
        return data

    def get_bytes(self, ending):
        """Transfers data from socket to buffer for storage. Will
        continue to acquire/transfer until either 300 tries have been
        attempted to grab data with more than 0 bytes or until the data
        acquired ends in the byte string "ending"."""
        data = b""
        while not data.endswith(ending):
            counter = 0
            new_data = ""
            while not len(new_data) > 0:
                new_data = self.sock.recv(buffer_size)
                counter += 1
                if counter > 300:
                    raise ValueError("No data acquired after 300 tries!!")
                time.sleep(short_sleep)
            data += new_data
        return data

    def send(self, msg):
        self.sock.send(msg.encode("ASCII") + b"\n")
        return

    def set_power(self, dBm):
        "Sets the power of the Bridge12"
        self.send("SET_POWER %0.2f" % dBm)
        return

    def dip_lock(self, start_f, stop_f):
        """Runs dip lock using start_f and stop_f as freq range, leaves
        Bridge12 at resonance frequency"""
        raise ValueError("error! we no longer use dip lock since we want a persistent frequency, which you get by running the tuning GUI.  You need to edit the script where this was thrown")
        self.send("DIP_LOCK %0.3f %0.3f" % (start_f, stop_f))
        retval = self.get(n_slow_tries=10)
        retval = float(retval)
        return retval

    def get_power_setting(self):
        self.send("GET_POWER")
        retval = self.get()
        retval = float(retval)
        return retval

    def start_log(self):
        self.send("START_LOG")
        return

    def stop_log(self):
        """stop the log and return a
        `logobj`
        type object directly, which has
        `log_dict` and `total_log`
        attributes"""
        self.send("STOP_LOG")
        retval = self.get_bytes(b"ENDTCPIPBLOCK")
        return pickle.loads(retval[: -len("ENDTCPIPBLOCK")])

    def mw_off(self):
        """power down rf and amp"""
        self.send("MW_OFF")
        return
