from pylab import *
from .gpib_eth import gpib_eth
from .log_inst import logger

class HP8672A (gpib_eth):
    def __init__(self, prologix_instance=None, address=None):
        super(self.__class__,self).__init__(prologix_instance,address)
        self.stepsize = 0.5e6 # this is a lie, but it's used as a default by wobbandmin
    def set_frequency(self,frequency):
        self.write('P%08dZ0'%int(round(frequency*1e-3)))# just use the 10 GHz setting, and fill out all the other decimal places with zeros
        return
    def set_power(self,dBm):
        assert dBm <= 3 and dBm >= -120, "dBm value must be between -120 and 3 dBm"
        # {{{ all of the following is based off fig 15-6 from the programming manual
        ascii_set = list('013456789:;<=')
        coarse_values = r_[0:-120:-10]
        vernier = r_[3:-11:-1]
        # }}}
        coarse_idx = argmin(abs(dBm - coarse_values))
        residual = dBm - coarse_values[coarse_idx]
        vernier_idx = argmin(abs(residual - vernier))
        logger.debug("I'm going to set the coarse value to %f and the vernier to %f"%(coarse_values[coarse_idx],vernier[vernier_idx]))
        cmd = 'K' + ascii_set[coarse_idx] + ascii_set[vernier_idx]
        self.write(cmd)
        return
