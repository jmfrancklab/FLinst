from Instruments import genesys, hall_probe, prologix_connection
from numpy import r_, dtype, zeros_like
from pyspecdata import ndshape, figlist_var
import time

I_program = r_[r_[0:21.7:50j], [21.7] * 50, r_[21.7:0:50j]]
log = (
    ndshape([("t", len(I_program))])
    .alloc(dtype([("I", "double"), ("V", "double"), ("B₀", "double")]))
    .setaxis("t", zeros_like(I_program))
    .set_units("t", "s")
)
with genesys("192.168.0.199") as g:
    # also nest inside a context block to allow communication with the LakeShore Hall probe
    with prologix_connection() as p:
        with hall_probe(p) as h:
            g.V_limit = 25.0
            g.I_limit = 0.0
            g.output = True
            for j, thisI in enumerate(I_program):
                g.I_limit = thisI
                time.sleep(0.1)
                log["t", j].data["I"] = g.I_meas
                log["t", j].data["V"] = g.V_meas
                # use the Hall probe to measure the magnetic field
                log["t", j].data["B₀"] = h.B_meas
                log["t", j] = time.time()
log["t"] -= log["t"][0]
# Save the logged data to an HDF5 file with a name based on the current date.
# The `hdf5_write` method writes the data structure to the specified file in HDF5 format.
log.name("PS_test").hdf5_write(
    f"power_supply_test_{time.strftime('%y%m%d')}.h5"
)
# Iterate over the names of the fields in the structured data type of log.data
with figlist_var() as fl:
    fl.next("magnet response")
    for j in log.data.dtype.names:
        fl.plot(log.C.run(lambda x: x[j]), label=j)
