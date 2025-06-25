import vxi11
import time

HOST = "192.168.0.199"  # replace with your instrument’s IP or hostname

def main():
    inst = vxi11.Instrument(HOST)
    try:
        # the following gives:
        # *IDN? → LAMBDA,GEN80-187.5-LAN,S/N:27L3802,REV:3U:4.3-AP17
        print("*IDN? →", inst.ask("*IDN?").strip())
        # The following causes the "remote" light on the front panel to appear 
        inst.write("*RST")
        # I repeat, to make sure it's not a line termination, etc, issue
        # → works fine.
        print("*IDN? →", inst.ask("*IDN?").strip())
        # as an example, the following times out
        inst.write("RMT 1")
        print(inst.ask("RMT?"))
    finally:
        inst.close()

if __name__ == "__main__":
    main()
