"""
Measure magnetic field versus Z0 shim voltage
through the power control server (*i.e.* the
"lock coil").
This allows us to determine the Gauss/Volts
constant for our Z0 shim.
"""

import matplotlib.pyplot as plt
import numpy as np
import time

from Instruments import instrument_control


shim_name = "Z0"
requested_voltages_V = np.arange(0.0, 4.0 + 0.25 / 2, 0.25)
settle_s = 1.0

with instrument_control() as p:
    initial_voltage_V = p.get_shim()[shim_name][0]
    voltages_V = np.array(
        list(
            dict.fromkeys(
                p.round_shim_voltage(shim_name, requested_voltages_V)
            )
        )
    )
    fields_G = np.zeros_like(voltages_V)
    print("requested voltages:", requested_voltages_V)
    print("allowed voltages:", voltages_V)
    for idx, voltage_V in enumerate(voltages_V):
        p.shim[shim_name] = voltage_V
        applied_voltage_V = p.shim[shim_name]
        time.sleep(settle_s)
        fields_G[idx] = p.get_field()
        print(
            f"{shim_name} set to {applied_voltage_V:0.3f} V,"
            f" field = {fields_G[idx]:0.3f} G"
        )
    p.shim[shim_name] = initial_voltage_V
    print(f"Restored {shim_name} to {initial_voltage_V:0.3f} V")

fields_G = fields_G - fields_G[0]
slope_G_per_V, intercept_G = np.polyfit(voltages_V, fields_G, 1)
fit_G = slope_G_per_V * voltages_V + intercept_G

print(f"Slope: {slope_G_per_V:0.6f} G/V")

plt.figure()
plt.plot(voltages_V, fields_G, "o", label="Measured")
plt.plot(
    voltages_V,
    fit_G,
    "-",
    label=f"Linear fit ({slope_G_per_V:0.6f} G/V)",
)
plt.xlabel("Z0 voltage / V")
plt.ylabel("Magnetic field / G")
plt.title("Field vs Z0 Voltage")
plt.legend()
plt.tight_layout()
plt.show()
