"""test the instrument control server

run this while running `python -m Instruments.instrument_control_server`
(or `instrument_control_server` as a command)
on the same computer

generates hdf output to be read by the companion readout example"""

from pyspecdata import init_logging
from Instruments import instrument_control
from SpinCore_pp import configuration
import os, time, h5py
from pyspecdata.file_saving.hdf_save_dict_to_group import (
    hdf_save_dict_to_group,
)

logger = init_logging(level="debug")
config_dict = configuration("active.ini")

time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time()))
assert not os.path.exists("output.h5"), (
    "later we can just check that the node doesn't exist, but in this example,"
    " we're writing a fresh h5 file"
)
with instrument_control() as ic:
    # since part of what we're doing is testing the field logging,
    # and this is a test, rather than something where we might expect
    # we've already set ourselves to a calibrated field, we
    # initialize to a reasonable field
    ic.set_field(
        config_dict["carrierfreq_mhz"] / config_dict["gamma_eff_MHz_G"]
    )
    ic.set_power(10)
    ic.set_freq(config_dict["uw_dip_center_GHz"] * 1e9)
    # {{{ run a loop that should take about 50s + execution time.  Step through
    #     3 powers -- unmodified (0 dB?), 10.5 dBm and 12 dBm
    for j in range(100):
        print(j)
        time.sleep(0.5)
        if j == 0:
            logger.info("starting the log")
            ic.start_log()
            ic.set_field(
                config_dict["carrierfreq_mhz"] / config_dict["gamma_eff_MHz_G"]
            )
        elif j == 30:
            logger.info("set first power")
            ic.set_power(10.5)
            ic.set_field(3000)
        elif j == 60:
            logger.info("set second power")
            ic.set_power(12)
            ic.set_field(2900)
    this_log = ic.stop_log()
    # }}}
log_array = this_log.total_log
logger.debug("log array:\n" + repr(log_array))
logger.debug(f"log array shape {log_array.shape}")
log_dict = this_log.log_dict
logger.debug("log dict:\n" + repr(log_dict))
with h5py.File("output.h5", "a") as f:
    hdf_save_dict_to_group(
        f, {"log": this_log.__getstate__()}
    )  # normally, I would actually put this under the node with the data
