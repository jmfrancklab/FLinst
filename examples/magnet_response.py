"""
This script performs a magnet response measurement by controlling a Genesys
power supply and recording the resulting current, voltage, and magnetic field
using a LakeShore Hall probe. The measurement sequence ramps the current up,
holds it, and then ramps it down, logging all relevant data at each step.

Workflow:

- Establishes communication with the Genesys power supply and the Hall probe
  via a Prologix GPIB-USB controller.
- Sets up a current program (`I_program`) to ramp the current up, hold, and
  ramp down.
- Allocates an nddata object (`log`) to store current (I), voltage (V), and
  magnetic field (B₀) measurements, as well as the time coordinate axis.
- For each current setpoint:

    - Sets the power supply current limit.
    - Waits briefly for stabilization.
    - Logs measured current, voltage, and magnetic field (converted to Tesla
      and stripped of units for compatibility).
    - Records the absolute wall-clock time for each measurement point. # NOTE:
      Unlike the other fields, the time axis is set to the absolute wall-clock
      time (in seconds since the epoch) at each step, rather than a measured
      value from the instrument. This is necessary for accurate time alignment
      in nddata objects.

- Normalizes the time axis to start at zero.
- Saves the data to an HDF5 file named with the current date.
- Plots each field (I, V, B₀) as a function of time using pyspecdata's
  figlist_var.

Dependencies:

- Instruments (genesys, hall_probe, prologix_connection)
- numpy
- pyspecdata
- time

Note:

- The time axis in the nddata object is set using absolute wall-clock time,
  which differs from the other fields that are populated with instrument
  measurements. This ensures proper time alignment for subsequent analysis and
  plotting.
"""

from Instruments import genesys, LakeShore475, prologix_connection
from numpy import r_, dtype, zeros_like
from pyspecdata import ndshape, figlist_var, Q_
import time
import os, h5py

I_program = r_[r_[0:21.7:50j], [21.7] * 50, r_[21.7:0:50j]]
B0_str = "$B_0$"
log = (
    ndshape([("t", len(I_program))])
    .alloc(dtype([("I", "double"), ("V", "double"), (B0_str, "double")]))
    .setaxis("t", zeros_like(I_program))
    .set_units("t", "s")
)
with genesys("192.168.0.199") as g:
    # also nest inside a context block to allow communication with the
    # LakeShore Hall probe
    g.V_limit = 25.0
    g.I_limit = 0.0
    g.output = True
    with prologix_connection() as p:
        with LakeShore475(p) as h:
            # adjust the time constant of the Hall probe to 5 milliseconds
            h.time_constant = Q_(5, "ms")
            for j, thisI in enumerate(I_program):
                g.I_limit = thisI
                time.sleep(0.1)
                log["t", j].data["I"] = g.I_meas
                log["t", j].data["V"] = g.V_meas
                # Use the Hall probe to measure the magnetic field, and convert
                # the Hall probe measurement to Tesla (T) to ensure consistency
                # with the expected units in the data structure. Dropping the
                # units (using `.magnitude`) ensures that the value can be
                # stored as a plain numerical type, which is required for
                # compatibility with the structured array format of `log.data`.
                log["t", j].data[B0_str] = h.field.to("T").magnitude
                # The following line sets the value of the "t" axis at index j
                # to the current wall-clock time (in seconds since the epoch).
                # This is different from the other fields, which are stored in
                # the structured data array; here, we are setting the axis
                # coordinate value.
                log["t"][j] = time.time()
log["t"] -= log["t"][0]
# Save the logged data to an HDF5 file with a name based on the current date.
# The `hdf5_write` method writes the data structure to the specified file in
# HDF5 format.
num_dataset = 1
dataset_name = f"PS_test{num_dataset:02d}"
file_name = f"power_supply_test_{time.strftime('%y%m%d')}.h5"
if os.path.exists(file_name):
    # use h5py to see if the dataset already exists if it does, start
    # incrementing num_dataset
    with h5py.File(file_name) as f:
        while dataset_name in f:
            num_dataset += 1
            dataset_name = f"PS_test{num_dataset:02d}"
log.name(dataset_name).hdf5_write(file_name)
# Iterate over the names of the fields in the structured data type of log.data
with figlist_var() as fl:
    fl.next("magnet response", legend=True)
    for j in log.data.dtype.names:
        if j == B0_str:
            fl.twinx()
        else:
            fl.twinx(orig=True)
        fl.plot(log.C.run(lambda x: x[j]), label=j)
