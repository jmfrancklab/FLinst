from Instruments import genesys, LakeShore475, prologix_connection
import matplotlib.pyplot as plt
import numpy as np
import time
from SpinCore_pp import configuration
from pyspecdata import T_per_G

config_dict = configuration("active.ini")

# {{{ changeable parameters
SET_CURRENT_STEP_A = 0.1 * config_dict["current_v_field_A_G"]
REPEATS_PER_STEP = 1
NUM_STEPS = 100
ZERO_WAIT_S = 40.0
OUTPUT_FILENAME = "Irounding.txt"
des_current = 21.1
hold_secs = 20.0
# }}}

with (
    genesys(config_dict["genesys_ip"]) as g,
    prologix_connection() as pro_log,
    LakeShore475(pro_log) as h,
):
    print("Zeroing Hall probe.")
    h.zero_probe()
    print(f"Waiting {ZERO_WAIT_S:.0f} s after Hall probe zero.")
    time.sleep(ZERO_WAIT_S)
    g.V_limit = 25.0
    g.output = True
    print("The power supply is on.")
    g.I_limit = 0.0
    for current_limit in np.linspace(0, des_current, 50):
        g.I_limit = current_limit
        time.sleep(0.05)
    g.I_limit = des_current
    print("Current is at the limit")
    time.sleep(hold_secs)
    I_des = []
    B_field = []
    for idx in range(NUM_STEPS):
        I_set = des_current + idx * SET_CURRENT_STEP_A
        g.I_limit = I_set
        print(
            f"\n Set current step: {SET_CURRENT_STEP_A:.4f} A\n "
            "Current I set: {I_set}"
        )
        time.sleep(15)
        I_des.append(I_set)
        B_field.append((h.field.to("T") / T_per_G).to("G").magnitude)


    # TODO ☐: this look different vs. the file that you specify in
    #         plot_current_rounding.py, which I really don't understand.
    #         Also, this is mis-labeled.
    with open(OUTPUT_FILENAME, "w", encoding="utf-8") as fp:
        fp.write(" I_desired(A)   B0(G)\n")
        for des, B in zip(I_dex, B_field):
            fp.write(f"{des:8.4f} {B:8.3f}\n")

    fig, ax = plt.subplots()
    ax.plot(I_des, B_field, "o-", color="C1", label="Hall probe")
    ax.set_xlabel("Set current value (A)")
    ax.set_ylabel("Hall probe reading (G)")
    ax.set_title("Hall Probe vs Set Current")
    fig.tight_layout()
    plt.show()
    print("Ramping down in progress")
    for current_limit in np.linspace(des_current, 0, 50):
        g.I_limit = current_limit
        time.sleep(0.05)
    g.output = False
    print("Ramp-down complete; output turned off.")
