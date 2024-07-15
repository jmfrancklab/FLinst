"""test the power control server

run this while running `python -m Instruments.power_control_server`
(or `power_control_server` as a command)
on the same computer

generates hdf output to be read by test_power_control_server_read.py"""
from pyspecdata import init_logging
from Instruments import power_control
import os, time, h5py
from numpy import empty
from matplotlib.ticker import FuncFormatter
from pyspecdata.file_saving.hdf_save_dict_to_group import (
    hdf_save_dict_to_group,
)

init_logging(level="debug")

time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time()))
assert not os.path.exists(
    "output.h5"
), "later we can just check that the node doesn't exist, but in this example, we're writing a fresh h5 file"
with power_control() as p:
    retval = p.dip_lock(9.81, 9.83)
    print(retval)
    for j in range(100):
        print(j)
        if j == 0:
            p.start_log()
        time.sleep(0.5)
        if j == 30:
            p.set_power(10.5)
        elif j == 60:
            p.set_power(12)
        elif j == 99:
            this_log = p.stop_log()
    # p.arrange_quit()
log_array = this_log.total_log
print("log array", repr(log_array))
print("log array shape", log_array.shape)
log_dict = this_log.log_dict
print("log dict", repr(log_dict))
with h5py.File("output.h5", "a") as f:
    log_grp = f.create_group(
        "log"
    )  # normally, I would actually put this under the node with the data
    hdf_save_dict_to_group(log_grp, this_log.__getstate__())
