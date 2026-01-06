"""test the power control server

run this while running `python -m Instruments.power_control_server`
(or `power_control_server` as a command)
on the same computer

generates hdf output to be read by test_power_control_server_read.py"""

from pyspecdata import init_logging
from Instruments import power_control
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
with power_control() as p:
    p.set_power(10)
    p.set_freq(config_dict["uw_dip_center_GHz"] * 1e9)
    input("press enter once the waveguide has switched")
    # {{{ run a loop that should take about 50s + execution time.  Step through
    #     3 powers -- unmodified (0 dB?), 10.5 dBm and 12 dBm
    for j in range(100):
        print(j)
        time.sleep(0.5)
        if j == 0:
            logger.info("starting the log")
            p.start_log()
        elif j == 30:
            logger.info("set first power")
            p.set_power(10.5)
        elif j == 60:
            logger.info("set second power")
            p.set_power(12)
    this_log = p.stop_log()
    # }}}
    # p.arrange_quit()
log_array = this_log.total_log
logger.debug("log array:\n" + repr(log_array))
logger.debug(f"log array shape {log_array.shape}")
log_dict = this_log.log_dict
logger.debug("log dict:\n" + repr(log_dict))
with h5py.File("output.h5", "a") as f:
    log_grp = f.create_group(
        "log"
    )  # normally, I would actually put this under the node with the data
    hdf_save_dict_to_group(log_grp, this_log.__getstate__())
