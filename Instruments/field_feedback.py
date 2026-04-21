from pyspecdata import strm
import logging
import numpy as np
import time

FIELD_CURRENT_STEP_A = 0.003115
FIELD_CURRENT_OFFSET_A = 0.0016
FIELD_CURRENT_TO_FIELD_C0 = 178.66095
FIELD_CURRENT_TO_FIELD_C1 = -358.56219


def field_to_current_request(B0_des_G):
    """Return the current request that best matches the desired field."""
    if np.isclose(B0_des_G, 0.0):
        return 0.0
    field_step_G = FIELD_CURRENT_TO_FIELD_C0 * FIELD_CURRENT_STEP_A
    lattice_index = np.round(
        (B0_des_G - FIELD_CURRENT_TO_FIELD_C1) / field_step_G
    )
    return float(FIELD_CURRENT_STEP_A * lattice_index + FIELD_CURRENT_OFFSET_A)


def adjust_main_field(B0_des_G, config_dict, h, gen):
    """Adjust the current setting to achieve the desired B0 field.

    Parameters
    ----------
    B0_des_G : float
        Desired magnetic field in Gauss.
    config_dict : dict
        Unused configuration dictionary kept for API compatibility.
    h : object
        LakeShore Hall sensor instance.
    gen : object
        Genesys power supply instance with I_limit property.
    """
    I_req = field_to_current_request(B0_des_G)
    logging.debug(
        strm(
            "adjusting main field to",
            B0_des_G,
            "G using requested current",
            I_req,
            "A",
        )
    )
    gen.I_limit = I_req


def ramp_field(
    B0_des_G,
    config_dict,
    h,
    gen,
    shims,
    settling_attempts=60,
    main_field_threshold_G=2.0,
    Z0_min_voltage_V=0.0,
    Z0_max_voltage_V=6,
):
    """Ramp the field from where we are to where we want to be.

    **If we start at 0**: Calibrate the zero-point of the hall sensor

    **If we end at 0 G**: Turn off the current supply

    Parameters
    ----------
    B0_des_G : float
        Desired magnetic field in Gauss.
    config_dict : dict
        Configuration dictionary with magnet settling times.
    h : object
        LakeShore Hall sensor instance.
    gen : object
        Genesys power supply object with output, V_limit, I_limit, and I_meas
        properties.
    shims : ShimDictMapping
        Shim mapping object used to access the Z0 shim by name.
    settling_attempts: int (default 60)
        How many times should we attempt to observe a stable field.
    main_field_threshold_G: float (default 2.0)
        If the field discrepancy is above this threshold, we consider it a
        "main field" discrepancy and adjust the main field.  Otherwise, we
        consider it a "Z0" discrepancy and adjust Z0.
    Z0_min_voltage_V: float (default 0)
        The minimum voltage we allow for the Z0 shim coil.
    Z0_max_voltage_V: float or None
        The maximum voltage we allow for the Z0 shim coil. If None, use the
        hardware maximum for the mapped Z0 channel.
    """
    z0_inst = shims.instrument("Z0")
    z0_channel = shims.channel("Z0")
    if Z0_max_voltage_V is None:
        Z0_max_voltage_V = z0_inst.max_V[z0_channel]
    I_setting = field_to_current_request(B0_des_G)
    # {{{ First, we ramp from whatever
    #     our current is (zero or not)
    #     to where we think we want to
    #     be, allowing for the
    #     possibility that it might be a
    #     large change
    if I_setting > 25:
        raise ValueError("Current is too high.")
    try:
        if not gen.output:
            h.zero_probe()
            logging.info("Zero calibration of hall probe for 40s")
            time.sleep(40)  # It takes 40s to calibrate
            logging.info("Calibration finished")
            gen.V_limit = 25.0
            gen.output = True
            gen.I_limit = 0
            logging.info("The power supply is on.")
    except Exception:
        raise TypeError("The power supply is not connected.")
    temp_I_meas = gen.I_meas
    ramp_steps = int(abs(I_setting - temp_I_meas) * 2)
    logging.info(f"Ramping the field from {gen.I_meas} to {I_setting}")
    for thisI in np.linspace(temp_I_meas, I_setting, ramp_steps):
        gen.I_limit = thisI
        time.sleep(config_dict["magnet_settle_short"])
    if B0_des_G == 0:
        shims.V_limit["Z0"] = 0
        shims.output["Z0"] = 0
        logging.info("Z0 Shim is off")
        gen.I_limit = 0
        gen.output = False
        logging.info("The PS is off.")
        return h.field_in_G
    if ramp_steps > 4:
        time.sleep(config_dict["magnet_settle_long"])
    # }}}
    # {{{ try to stabilize the field
    #     within 0.8 G of our desired
    #     value
    num_field_matches = 0
    for j in range(settling_attempts):
        time.sleep(config_dict["magnet_settle_short"])
        field_discrepancy = abs(h.field_in_G - B0_des_G)
        if field_discrepancy > 2.0:
            time.sleep(config_dict["magnet_settle_medium"])
        if (
            field_discrepancy
            < config_dict["tolerance_Hz"]
            * 1e-6
            / config_dict["gamma_eff_mhz_g"]
        ):
            logging.info(
                "your match to the desired field is within tolerance!"
            )
            num_field_matches += 1
            if num_field_matches > 2:
                break
        elif (
            # as we approach lower fields, we encounter a no-current
            # discrepancy that can't be calibrated out.
            field_discrepancy > main_field_threshold_G
        ):
            adjust_main_field(
                B0_des_G,
                config_dict,
                h,
                gen,
            )
            num_field_matches = 0
        else:
            # {{{ if it's not within tolerance, and it's not asking for a big
            #     step, then it's asking for an intermediate step
            #     so we need to adjust the Z0 field.
            # {{{ the desired voltage is the combination of the change we want
            #     to make and the voltage that's running through Z0 before the
            #     change (and we want to save the latter)
            desired_Z0_voltage_V = (B0_des_G - h.field_in_G) / config_dict[
                "z0_field_v_voltage_G_V"
            ]
            Z0_initial_voltage_V = shims.V_read["Z0"]
            desired_Z0_voltage_V += Z0_initial_voltage_V
            # }}}
            # {{{ we can only use Z0 to increase the voltage, and we don't want
            #     to ask for an unreasonable voltage
            if desired_Z0_voltage_V < Z0_min_voltage_V:
                adjust_main_field(B0_des_G - 1.0, config_dict, h, gen)
            elif desired_Z0_voltage_V > Z0_max_voltage_V:
                adjust_main_field(B0_des_G, config_dict, h, gen)
            # }}}
            shims.V_limit["Z0"] = shims.round_to_allowed(
                "V",
                "Z0",
                desired_Z0_voltage_V,
            )
            if (shims.V_read["Z0"] - Z0_initial_voltage_V) != 0:
                # {{{ Check if the field is stabilizing
                num_field_matches = 0
                B0_last_G = 0
                for j in range(settling_attempts):
                    time.sleep(config_dict["magnet_settle_short"])
                    B0_now_G = h.field_in_G
                    field_discrepancy = abs(B0_now_G - B0_last_G)
                    if (
                        field_discrepancy
                        < config_dict["tolerance_Hz"]
                        * 1e-6
                        / config_dict["gamma_eff_mhz_g"]
                    ):
                        num_field_matches += 1
                    else:
                        B0_last_G = B0_now_G
                        num_field_matches = 0
                    if num_field_matches > 2:
                        break
                if not (num_field_matches > 2):
                    print(
                        " ".join(
                            ["WARNING! "] * 3 + ["field is not stabilizing!"]
                        )
                    )
                # }}}
            # }}}
            num_field_matches = 0

    if num_field_matches < 3:
        temp = (
            config_dict["tolerance_Hz"] * 1e-6 / config_dict["gamma_eff_mhz_g"]
        )

        raise RuntimeError(
            f"I tried {settling_attempts} times to get my"
            f" field to match within {temp} G"
            f" or {config_dict['tolerance_Hz']} Hz three times"
            "in a row, and it didn't work!"
        )
    # }}}
    true_B0_G = h.field_in_G
    logging.debug(
        "Your field is"
        f" {true_B0_G} G, and"
        "the ratio of the field I want"
        " to the one I get is"
        f" {B0_des_G / true_B0_G}\nIn "
        " other words, the discrepancy"
        f" is{true_B0_G - B0_des_G} G"
    )
    return true_B0_G
