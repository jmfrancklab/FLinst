from pylab import *
from .gpib_eth import gpib_eth
from .log_inst import logger

class HP6623A (gpib_eth):
    def __init__(self, prologix_instance=None, address=None):
        r"""initialize a new `HP6623A` power supply class
        """
        super().__init__(prologix_instance,address)
        self.write("ID?")
        idstring = self.read()
        if idstring[0:2] == 'HP':
            logger.debug("Detected HP power supply with ID string %s"%idstring)
        else:
            raise ValueError("Not detecting identity as HP power supply, returned ID string as %s"%idstring)
        return
    def check_id(self):
        self.write("ID?")
        retval =  self.read()
        return
    def set_voltage(self, ch, val):
        r"""set voltage (in Volts) on specific channel

        Parameters
        ==========
        ch : int
            Channel 1, 2, or 3
        val : float
            Voltage you want to set in Volts; check manual for limits on each
            channel.
        Returns
        =======
        None
        
        """
        self.write("VSET %s,%s"%(str(ch),str(val)))
        return
    def get_voltage(self, ch):
        r"""get voltage (in Volts) on specific channel

        Parameters
        ==========
        ch : int
            Channel 1, 2, or 3
        Returns
        =======
        Voltage reading (in Volts) as float
        
        """
        self.write("VOUT? %s"%str(ch))
        return float(self.read())
    def set_current(self, ch, val):
        r"""set current (in Amps) on specific channel

        Parameters
        ==========
        ch : int
            Channel 1, 2, or 3
        val : float
            Current you want to set in Amps; check manual for limits on each channel.
        Returns
        =======
        None
        
        """
        self.write("ISET %s,%s"%(str(ch),str(val)))
    def get_current(self, ch):
        r"""get current (in Amps) on specific channel

        Parameters
        ==========
        ch : int
            Channel 1, 2, or 3
        Returns
        =======
        Current reading (in Amps) as float
        
        """
        self.write("IOUT? %s"%str(ch))
        return float(self.read())
    def output(self, ch, trigger):
        r"""turn on or off the output on specific channel

        Parameters
        ==========
        ch : int
            Channel 1, 2, or 3
        trigger : int
            To turn output off, set `trigger` to 0 (or False)
            To turn output on, set `trigger` to  1 (or True)
        Returns
        =======
        None
        
        """
        assert (isinstance(trigger, int)), "trigger must be int (or bool)"
        assert(0 <= trigger <= 1), "trigger must be 0 (False) or 1 (True)"
        if trigger:
            trigger = 1
        elif not trigger:
            trigger = 0
        return self.write("OUT %s,%s"%(str(ch),str(trigger)))
        self.write("OUT %s,%s"%(str(ch),str(trigger)))
    def check_output(self, ch):
        r"""check the output status of a specific channel

        Parameters
        ==========
        ch : int
            Channel 1, 2, or 3
        Returns
        =======
        str stating whether the channel output is OFF or ON
        
        """
        self.write("OUT? %s"%str(ch))
        retval = float(self.read())
        if retval == 0:
            print("Ch %s output is OFF"%ch)
        elif retval == 1:
            print("Ch %s output is ON"%ch)
        return 
    def close(self):
        super().close()
