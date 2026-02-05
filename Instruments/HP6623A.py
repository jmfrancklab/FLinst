from pylab import *
from .gpib_eth import gpib_eth
from .log_inst import logger
import time

class ChannelAware(object):
    """Build a class that we can use to decorate -- similar to @property, except that the decorated object can have many channels:

    self.voltage[0] = 3 # set the voltage of channel 0 to 3
    print(self.voltage) # print the voltage of channel 3
    """
    def num_channels(self,*args):
        raise ValueError("you need to define num_channels")
    def channel_set_func(self,channel,val):
        raise ValueError("you need to define channel_set_func")
    def channel_get_func(self,channel):
        raise ValueError("you need to define channel_get_func")
    def set_num_channels(self,number):
        def ret_num_channels():
            return number
        self.num_channels = ret_num_channels
    def setter(self,setter_func):
        "if called as a decorator, define the set function"
        self.channel_set_func = setter_func
        return
    def __init__(self,getter_func):
        """The name function that is decorated becomes
        the instance, and the decorated function should
        accept one argument -- the channel -- and contain code on how to
        retrieve the relevant info for the given
        channel"""
        self.channel_get_func = getter_func
        return
    def __getitem__(self,channel,val):
        return self.channel_get_func(channel,val)
    def __getslice__(self,*args):
        raise ValueError("we probably could define slices, but that's not implemented yet")
    def __setitem__(self,channel,val):
        self.channel_set_func(channel,val)
    def __len__(self):
        return self.num_channels()
    def __iter__(self):
        for thischannel in range(self.num_channels()):
            yield self.channel_get_func(thischannel)

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
        if val == 0.0:
            return
        else:
            time.sleep(5)
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
        curr_reading = float(self.read())
        for i in range(30):
            self.write("IOUT? %s"%str(ch))
            this_val = float(self.read())
            if curr_reading == this_val:
                break
            if i > 28:
                print("Not able to get stable meter reading after 30 tries. Returning: %0.3f"%curr_reading)
        return curr_reading 
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
        self.write("OUT %s,%s"%(str(ch),str(trigger)))
        return 
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
        for i in [1,2,3]:
            # set voltage and current to 0 and turn off output on all channels,
            # before exiting
            self.set_voltage(i,0)
            self.set_current(i,0)
            self.output(i,False)
        super().close()
