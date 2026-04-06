"Reads the output from test_power_control_server.py"

import time, h5py
from pathlib import Path
import pylab as plt
from matplotlib.ticker import FuncFormatter
import matplotlib.transforms as transforms


@FuncFormatter
def thetime(x, position):
    result = time.localtime(x)
    return time.strftime("%I:%M:%S %p", result)


def _decode_list_node(h5group):
    item_names = sorted(
        (name for name in h5group.attrs if name.startswith("ITEM")),
        key=lambda name: int(name[4:]),
    )
    values = []
    for name in item_names:
        value = h5group.attrs[name]
        if isinstance(value, bytes):
            value = value.decode("utf-8")
        values.append(value)
    return values


output_path = Path(__file__).resolve().with_name("output.h5")

with h5py.File(output_path, "r") as f:
    log_group = f["log"]
    read_array = log_group["array"][:]
    read_dict = dict(
        zip(
            _decode_list_node(log_group["dictkeys"]),
            _decode_list_node(log_group["dictvalues"]),
        )
    )
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
fig, (ax_Rx, ax_power, ax_field) = plt.subplots(3, 1, figsize=(10, 8))
ax_Rx.xaxis.set_major_formatter(thetime)
ax_power.xaxis.set_major_formatter(thetime)
ax_field.xaxis.set_major_formatter(thetime)
ax_Rx.set_ylabel("Rx / mV")
ax_Rx.plot(read_array["time"], read_array["Rx"], ".")
ax_power.set_ylabel("power / dBm")
ax_power.plot(read_array["time"], read_array["power"], ".")
ax_field.set_ylabel("field / G")
ax_field.plot(read_array["time"], read_array["field"], ".")
mask = read_array["cmd"] != 0
n_events = len(read_array["time"][mask])
trans_power = transforms.blended_transform_factory(
    ax_power.transData, ax_power.transAxes
)
trans_Rx = transforms.blended_transform_factory(
    ax_Rx.transData, ax_Rx.transAxes
)
trans_field = transforms.blended_transform_factory(
    ax_field.transData, ax_field.transAxes
)
for j, thisevent in enumerate(read_array[mask]):
    ax_Rx.axvline(x=thisevent["time"])
    ax_power.axvline(x=thisevent["time"])
    ax_field.axvline(x=thisevent["time"])
    y_pos = j / n_events
    ax_Rx.text(
        thisevent["time"],
        y_pos,
        read_dict[thisevent["cmd"]],
        transform=trans_Rx,
    )
    ax_power.text(
        thisevent["time"],
        y_pos,
        read_dict[thisevent["cmd"]],
        transform=trans_power,
    )
    ax_field.text(
        thisevent["time"],
        y_pos,
        read_dict[thisevent["cmd"]],
        transform=trans_field,
    )
ax_power.legend(**dict(bbox_to_anchor=(1.05, 1), loc=2, borderaxespad=0.0))
plt.tight_layout()
plt.show()
