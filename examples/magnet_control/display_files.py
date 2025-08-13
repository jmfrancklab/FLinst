"""
Shows the data from magnet_response.py
"""


from pyspecdata import figlist_var, nddata_hdf5
import h5py

B0_str = "$B_0$"
file_name = "power_supply_test_250630.h5"
with h5py.File(file_name, "r") as fp:
    all_node_names = list(fp.keys())
# Iterate over the names of the fields in the structured data type of log.data
with figlist_var() as fl:
    for thisnode in all_node_names:
        log = nddata_hdf5(file_name + "/" + thisnode)
        fl.next(thisnode, legend=True)
        for j in log.data.dtype.names:
            if j == B0_str:
                fl.twinx()
                log.set_plot_color("k")
            else:
                fl.twinx(orig=True)
                log.set_plot_color(None)
            fl.plot(log.C.run(lambda x: x[j]), label=j,marker='.')
