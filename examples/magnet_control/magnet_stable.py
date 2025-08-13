"""
Generating a stable magnetic field for the desired
duration
"""

from Instruments import genesys
import numpy as np
import time


def ramp_up_and_hold(g, max_current, steps=50, delay=0.05, hold_time=10.0):
    """
    Ramp the power supply current from 0 to max_current in `steps` increments,
    then hold at max_current for `hold_time` seconds.

    Parameters
    ----------
    g : Genesys
        An open Genesys instrument instance.
    max_current : float
        The target current in amperes.
    steps : int, optional
        Number of discrete steps between 0 and max_current (default: 50).
    delay : float, optional
        Delay in seconds after setting each current (default: 0.05).
    hold_time : float, optional
        Total time in seconds to hold at max_current (default: 10.0).
    """
    # Ramp up
    for I in np.linspace(0, max_current, steps):
        g.I_limit = I
        time.sleep(delay)
    # Hold at max_current for the desired duration
    g.I_limit = max_current
    print("Current is at the limit")
    time.sleep(hold_time)


def ramp_down_and_turn_off(g, max_current, steps=50, delay=0.05):
    """
    Ramp the power supply current down from max_current to 0 in `steps`
    increments, then disable the output.

    Parameters
    ----------
    g : Genesys
        An open Genesys instrument instance.
    max_current : float
        The starting current in amperes.
    steps : int, optional
        Number of discrete steps between max_current and 0 (default: 50).
    delay : float, optional
        Delay in seconds after setting each current (default: 0.05).
    """
    # Ramp down
    print("Ramping down in progress")
    for I in np.linspace(max_current, 0, steps):
        g.I_limit = I
        time.sleep(delay)
    # Turn off output
    g.output = False


if __name__ == "__main__":
    des_field = 0.3499295
    fieldI_ratio = 60.9053 / 0.34995 * 0.3499295
    max_current = fieldI_ratio * des_field
    hold_secs = 600.0  # hold at max_current for 15 seconds

    with genesys("192.168.0.199") as g:
        # Set voltage limit and ensure starting current is zero
        g.V_limit = 25.0

        # Turn output on, with error handling
        try:
            g.output = True
            print("The power supply is on.")
        except Exception:
            raise TypeError("The power supply is not connected.")

        # Ramp up to max_current and hold
        ramp_up_and_hold(
            g, max_current, steps=50, delay=0.05, hold_time=hold_secs
        )

        # (Insert any logging/measurement here while held)

        ramp_down_and_turn_off(g, max_current, steps=50, delay=0.05)
        print("Ramp-down complete; output turned off.")
