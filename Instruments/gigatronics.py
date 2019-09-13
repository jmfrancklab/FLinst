from pylab import *
from .gpib_eth import gpib_eth


class gigatronics_powermeter ():

    def __init__(self,gpibaddress=15):
        super(self.__class__,self).__init__()
        self.gpibaddress=gpibaddress

        idstring = self.respond(self.gpibaddress,'ID') # Check ID command
        if idstring[0:4] == 'GIGA':
            print 'idstring is',idstring
            self.write(self.gpibaddress,'TR3')        # Set Free Run Trigger Mode
            self.write(self.gpibaddress,'LG')         # Set Log units in dBm
            #self.write(self.gpibaddress,'DD')         # Display Disable
        else:
            raise ValueError('Not a Gigatronics power meter, returned ID string %s'%idstring)
        
    def read_power(self):
        try:
            retval = float(self.readline(self.gpibaddress))
        except:
            retval = -999.9
        counter = 0
        while (counter < 4) & (retval == -999.9):
            #print 'reading...'
            #self.write(self.gpibaddress,'RS')# "reset" which apparently takes a reading
            tempstr = self.readline(self.gpibaddress)
            if len(tempstr)>0:
                retval = float(tempstr)
            else:
                retval = -999.9
            counter += 1
            print '/',
            time.sleep(1e-4)
        if retval == -999.9:
            print 'failed to read a power!'
        return retval
    
    def close(self):
        #self.write(self.gpibaddress,'DE')         # Display Enable
     
        
##        self.write(self.gpibaddress,'HP')# if we don't do this, the display freezes
##        self.write(self.gpibaddress,'RP')# no longer output only mode
##        self.write(self.gpibaddress,'FP')# turn off "fast mode"??
##        self.write(self.gpibaddress,'R0')# switch back to high res
        self.close()
