from pylab import *
from .gpib_eth import gpib_eth
import time


class gigatronics(gpib_eth):
    def __init__(self, prologix_instance=None, address=13):
        super().__init__(prologix_instance, address)
        try:
            idstring = self.respond("*IDN?", lines=2)  # Check ID command
        except TimeoutError:
            raise TimeoutError(
                "I am not getting a response from the"
                " Gigatronics!!\nFirst, check to make sure it's on!!!"
            )
        print(idstring[0])
        print(idstring[1])
        if idstring[0][0:4] == "GIGA":
            print("idstring is", idstring)
            self.write("TR3")  # Set Free Run Trigger Mode
            self.write("LG")  # Set Log units in dBm
            # self.write(self.gpibaddress,'DD')         # Display Disable
        else:
            raise ValueError(
                "Not a Gigatronics power meter, returned ID string %s"
                % idstring
            )

    def read_power(self):
        try:
            retval = float(self.readline())
        except Exception:
            retval = -999.9
        counter = 0
        while (counter < 4) & (retval == -999.9):
            print("reading...")
            # self.write(self.gpibaddress,'RS')# "reset" which
            # apparently takes a reading
            tempstr = self.readline()
            if len(tempstr) > 0:
                retval = float(tempstr)
            else:
                retval = -999.9
            counter += 1
            print("/", end=" ")
            time.sleep(1e-4)
        if retval == -999.9:
            print("failed to read a power!")
        return retval

    def close(self):
        super().close()
