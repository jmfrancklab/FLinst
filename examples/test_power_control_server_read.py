"""
Reads the output from test_power_control_server.py
==================================================

Note that you can set pull_old_data to either read old data (stored on Box) or
new data that was just generated using test_power_control_server.py in the local directory.
"""

import time, h5py, os
import pylab as plt
from matplotlib.ticker import FuncFormatter
import matplotlib.transforms as transforms
from Instruments.logobj import logobj
import pyspecdata as psd


@FuncFormatter
def thetime(x, position):
    result = time.localtime(x)
    return time.strftime("%I:%M:%S %p", result)


# am I pulling previously stored data, or something I just ran
pull_old_data = True
if pull_old_data:
    fname = psd.search_filename(
        "260409_power_control_server_test.h5", exp_type="B27/Test", unique=True
    )
else:
    fname = "output.h5"
if not os.path.exists(fname):
    raise IOError(f"{fname} not found.  Check that you've set the pull_old_data flag as you intend")
with h5py.File(fname, "r") as f:
    thislog = logobj.from_group(f["log"])
    read_array = thislog.total_log
    read_dict = thislog.log_dict
print(read_array)
for j in range(len(read_array)):
    thistime, thisrx, thispower, thisfield, thiscmd = read_array[j]
    print(
        "%-04d" % j,
        time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(thistime)),
        thisrx,
        thispower,
        thisfield,
        read_dict[thiscmd],
    )
fig, ax_list = plt.subplots(3, 1, figsize=(10, 8))
(ax_Rx, ax_power, ax_field) = ax_list
for thisax in ax_list:
    thisax.xaxis.set_major_formatter(thetime)
ax_Rx.set_ylabel("Rx / mV")
ax_Rx.plot(read_array["time"], read_array["Rx"], ".")
ax_power.set_ylabel("power / dBm")
ax_power.plot(read_array["time"], read_array["power"], ".")
ax_field.set_ylabel("field / G")
ax_field.plot(read_array["time"], read_array["field"], ".")
mask = read_array["cmd"] != 0
n_events = len(read_array["time"][mask])
trans_list = []
for thisax in ax_list:
    trans_list.append( transforms.blended_transform_factory(
        thisax.transData, thisax.transAxes
    ))
for j, thisevent in enumerate(read_array[mask]):
    for thisax in ax_list:
        thisax.axvline(x=thisevent["time"])
    y_pos = j / n_events
    for j, thisax in enumerate(ax_list):
        thisax.text(
            thisevent["time"],
            y_pos,
            read_dict[thisevent["cmd"]],
            transform=trans_list[j],
        )
ax_power.legend(**dict(bbox_to_anchor=(1.05, 1), loc=2, borderaxespad=0.0))
plt.tight_layout()
plt.show()
