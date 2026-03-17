from pyspecdata import strm
import logging
import numpy as np
import time


def Z0_adjustment(B0_des_G, config_dict, h, HP1, gen):
    """Adjust the current setting to achieve the desired Z0 field.

    Use the actual measured field to scale the current_v_field_A_G
    configuration parameter.

    This is typically called *after* we've ramped to the field of interest.

    Parameters
    ----------
    B0_des_G : float
        Desired magnetic field in Gauss.
    config_dict : dict
        Configuration dictionary containing 'z0_field_v_current_G_A' parameter.
    h : object
        LakeShore Hall sensor instance.
    HP1 : object
        HP1 Power Supply instance with I_read property.
    """
    assert (
        HP1.V_limit[config_dict["Z0_channel"]] > 14.0
        and hasattr(HP1, "safe_current")
        and HP1.safe_current < 1.81
    ), (
        "The Z0 channel wasn't properly set up!!."
        "  This is the fault of the containing program"
    )
    initial_field_G = h.field_in_G
    dif_field_G = B0_des_G - initial_field_G
    # {{{ the desired current is the combination of the change we want
    #     to make and the current that's running through Z0 before the
    #     change (and we want to save the latter)
    desired_Z0_current_A = dif_field_G / config_dict["z0_field_v_current_G_A"]
    Z0_initial_current_A = HP1.I_read[config_dict["Z0_channel"]]
    desired_Z0_current_A += Z0_initial_current_A
    # }}}
    # {{{ we can only use Z0 to increase the current, and we don't want
    #     to ask for an unreasonable current
    main_field_adjusted = False
    if desired_Z0_current_A < 0:
        adjust_main_field(B0_des_G - 1.5, config_dict, h, gen)
        main_field_adjusted = True
    elif desired_Z0_current_A > 1.5:
        adjust_main_field(B0_des_G, config_dict, h, gen)
        main_field_adjusted = True
    # }}}
    HP1.I_limit[config_dict["Z0_channel"]] = HP1.round_to_allowed(
        "I", 0, desired_Z0_current_A
    )
    if (HP1.I_read[config_dict["Z0_channel"]] - Z0_initial_current_A) != 0:
        logging.debug(
            strm(
                "adjusting z0_field_v_current_G_A from",
                config_dict["z0_field_v_current_G_A"],
            )
        )
        # In order to get the G/A value, use the current flowing through the
        # shim stack NOW and the field NOW
        # {{{ BUT, we need to make sure the field has settled before
        #     doing so.  Use the same schema as elsewhere for this
        num_field_matches = 0
        B0_last_G = 0
        for j in range(30):
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
            print(" ".join(["WARNING! "] * 3 + ["field is not stabilizing!"]))
        # }}}
        # {{{ If we have changed the main field, or if we have not
        #     changed our Z0 field by much, we don't have the info we
        #     need to update our proportionality constant.  Otherwise,
        #     let's update it.
        delta_I = HP1.I_read[config_dict["Z0_channel"]] - Z0_initial_current_A
        delta_B = B0_last_G - initial_field_G
        print(B0_last_G)
        if not main_field_adjusted and abs(delta_I) > 0.5 and abs(delta_B) > 0:
            logging.debug(
                strm(
                    "Changed current by",
                    delta_I,
                    "to get a change in field of",
                    delta_B,
                    "so update z0_field_v_current_G_A from",
                    config_dict["z0_field_v_current_G_A"],
                )
            )
            config_dict["z0_field_v_current_G_A"] = delta_B / delta_I
            logging.debug(strm("to", config_dict["z0_field_v_current_G_A"]))
        # }}}


def adjust_main_field(B0_des_G, config_dict, h, gen):
    """Adjust the current setting to achieve the desired B0 field.

    Use the actual measured field to scale the current_v_field_A_G
    configuration parameter.

    This is typically called *after* we've ramped to the field of interest.

    Parameters
    ----------
    B0_des_G : float
        Desired magnetic field in Gauss.
    config_dict : dict
        Configuration dictionary containing 'current_v_field_A_G' parameter.
    h : object
        LakeShore Hall sensor instance.
    gen : object
        Genesys power supply instance with I_limit property.
    """
    true_B0_G = h.field_in_G
    logging.debug(
        strm(
            "adjusting current_v_field_A_G from",
            config_dict["current_v_field_A_G"],
        )
    )
    # In order to get the A/G value, use the current flowing through the
    # magnet NOW and the field NOW
    config_dict["current_v_field_A_G"] = gen.I_meas / true_B0_G
    logging.debug(strm("to", config_dict["current_v_field_A_G"]))
    I_setting = B0_des_G * config_dict["current_v_field_A_G"]
    gen.I_limit = I_setting


def ramp_field(B0_des_G, config_dict, h, gen, HP1):
    """Ramp the field from where we are to where we want to be.

    **If we start at 0**: Calibrate the zero-point of the hall sensor

    **If we end at 0 G**: Turn off the current supply

    Parameters
    ----------
    B0_des_G : float
        Desired magnetic field in Gauss.
    config_dict : dict
        Configuration dictionary with magnet settling times and
        current_v_field_A_G.
    h : object
        LakeShore Hall sensor instance.
    gen : object
        Genesys power supply object with output, V_limit, I_limit, and I_meas
        properties.
    """
    I_setting = B0_des_G * config_dict["current_v_field_A_G"]
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
        HP1.I_limit[config_dict["Z0_channel"]] = 0
        HP1.output[config_dict["Z0_channel"]] = 0
        logging.info("Z0 Shim is off")
        gen.I_limit = 0
        gen.output = False
        logging.info("The PS is off.")
        return h.field_in_G
    if ramp_steps > 4:
        time.sleep(config_dict["magnet_settle_long"])
    # }}}
    # {{{ now, adjust current_v_field_A_G
    #     to get the field we want,
    #     just once at the beginning
    # {{{ try to stabilize the field
    #     within 0.8 G of our desired
    #     value
    num_field_matches = 0
    for j in range(60):
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
            (B0_des_G < 20 and field_discrepancy > 5)
            or (B0_des_G >= 20 and field_discrepancy > 2)
        ):
            adjust_main_field(
                B0_des_G,
                config_dict,
                h,
                gen,
            )
            num_field_matches = 0
        else:
            # if it's not within tolerance, and it's not asking for a big
            # step, then it's asking for an intermediate step
            Z0_adjustment(B0_des_G, config_dict, h, HP1, gen)
            num_field_matches = 0

    if num_field_matches < 3:
        temp = (
            config_dict["tolerance_Hz"] * 1e-6 / config_dict["gamma_eff_mhz_g"]
        )

        logging.info(
            "I tried 60 times to get my"
            f" field to match within {temp} G"
            f" or {config_dict['tolerance_Hz']} Hz three times"
            "in a row, and it didn't work! Now the field is {h.field_in_G} G, "
            f"and the discrepancy is {h.field_in_G - B0_des_G} G"
        )
        return h.field_in_G
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
