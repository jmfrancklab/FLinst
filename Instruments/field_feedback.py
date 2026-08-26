from pyspecdata import strm
import logging
import numpy as np
import time


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


def ramp_field(
    B0_des_G,
    config_dict,
    h,
    gen,
    shims,
    settling_attempts=60,
    main_field_threshold_G=2.0,
    Z0_min_voltage_V=0.0,
):
    # TODO ☐:  this returns something that's not documented
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
    """
    field_tolerance_G = (
        config_dict["tolerance_Hz"] * 1e-6 / config_dict["gamma_eff_mhz_g"]
    )
    z0_inst = shims.instrument("Z0")
    z0_channel = shims.channel("Z0")
    hardware_Z0_max_voltage_V = z0_inst.max_V[z0_channel]
    if not 0 < config_dict["z0_max_voltage_V"] <= hardware_Z0_max_voltage_V:
        raise ValueError(
            "z0_max_voltage_V must be positive and no greater than the "
            f"hardware maximum of {hardware_Z0_max_voltage_V} V"
        )
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
    ramp_steps = max(
        2, # make sure we take at least 2 steps so linspace doesn't choke
        int(
            abs(I_setting - temp_I_meas)
            / config_dict["magnet_current_step_size_A"]
            + 0.5 # for rounding
        ),
    )
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
    # {{{ now, adjust current_v_field_A_G
    #     to get the field we want,
    #     just once at the beginning
    # {{{ try to stabilize the field within the configured tolerance
    num_field_matches = 0
    for j in range(settling_attempts):
        time.sleep(config_dict["magnet_settle_short"])
        field_discrepancy = abs(h.field_in_G - B0_des_G)
        if field_discrepancy > 2.0:
            time.sleep(config_dict["magnet_settle_medium"])
        if field_discrepancy < field_tolerance_G:
            logging.info(
                "your match to the desired field is within tolerance!"
            )
            num_field_matches += 1
            if num_field_matches > 2:
                break
        elif (
            # as we approach lower fields, we encounter a no-current
            # discrepancy that can't be calibrated out.
            field_discrepancy
            > main_field_threshold_G
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
                shims.V_limit["Z0"] = 0
                time.sleep(config_dict["magnet_settle_short"])
                # The field we can set with Z0 is about 2 G.
                # We cannot set the current through Z0 exactly to 0 (the
                # minimum is a small positive value).
                # If we calculate that we need the Z0 to be less than that
                # minimum, we need to push the main field down.
                # To avoid further adjustment, we attempt to target setting Z0
                # to its midpoint.
                main_field_target_G = (
                    B0_des_G
                    - config_dict["z0_midpoint_setting_G"]
                )
                adjust_main_field(main_field_target_G, config_dict, h, gen)
                num_field_matches = 0
                continue
            fallback_reason = None
            if desired_Z0_voltage_V > config_dict["z0_max_voltage_V"]:
                # Z0 exceeds max allowed value
                fallback_reason = "requested voltage exceeds maximum"
            elif desired_Z0_voltage_V > Z0_initial_voltage_V:
                # Z0 needs to increase
                if (
                    Z0_initial_voltage_V
                    >= 0.98 * config_dict["z0_max_voltage_V"] # we never want to quite hit the max, so only allow 98% of max
                ):
                    # Z0 needs to increase, but is voltage limited
                    fallback_reason = "voltage is already near maximum"
                else:
                    # Z0 needs to increase, and is NOT voltage limited
                    Z0_current_limit_A = shims.I_limit["Z0"]
                    if Z0_current_limit_A > 0:
                        Z0_current_A = shims.I_read["Z0"]
                        if (
                            Z0_current_A
                            # TODO ☐:  in response to previous todo -- I think I understand now.  This is just a slop factor? if so, why not just hard-code the 0.98 and say it's a slop factor
                            >= 0.98 * Z0_current_limit_A # we never want to quite hit the max, so only allow 98% of max
                        ):
                            # Z0 needs to increase and is not voltage limited,
                            # but it is current limited.
                            fallback_reason = "current is already near limit"
            # TODO ☐:  the following comment doesn't make sense -- what is a "negative request"???
            # A negative request means the main field is too high. Here the
            # main field is too low, but Z0 cannot reliably add enough field.
            # Reset Z0 and leave configured headroom for a fresh shim request.
            if fallback_reason is not None:
                # TODO ☐:  why is this a different number vs. z0_midpoint_setting_G?
                main_field_target_G = (
                    B0_des_G - config_dict["z0_limited_main_field_offset_G"]
                )
                logging.debug(
                    "Z0 fallback because %s: desired %0.3f V with max "
                    "%0.3f V (current Z0 %0.3f V); "
                    "zeroing Z0 before moving main field toward %0.3f G",
                    fallback_reason,
                    desired_Z0_voltage_V,
                    config_dict["z0_max_voltage_V"],
                    Z0_initial_voltage_V,
                    main_field_target_G,
                )
                shims.V_limit["Z0"] = 0
                time.sleep(config_dict["magnet_settle_short"])
                adjust_main_field(main_field_target_G, config_dict, h, gen)
                num_field_matches = 0
                # The main-field move invalidates the old shim request. Read
                # the field again and calculate a new request on the next pass.
                continue
            # }}}
            shims.V_limit["Z0"] = shims.round_to_allowed(
                "V",
                "Z0",
                desired_Z0_voltage_V,
            )
            if (shims.V_read["Z0"] - Z0_initial_voltage_V) != 0:
                # {{{ Check if the field is stabilizing at the target
                num_field_matches = 0
                B0_last_G = 0
                for j in range(settling_attempts):
                    time.sleep(config_dict["magnet_settle_short"])
                    B0_now_G = h.field_in_G
                    field_change_G = abs(B0_now_G - B0_last_G)
                    field_error_G = abs(B0_now_G - B0_des_G)
                    if (
                        field_change_G < field_tolerance_G
                        and field_error_G < field_tolerance_G
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
