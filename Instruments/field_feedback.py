from pyspecdata import strm
import logging
import numpy as np
import time


_main_field_calibration_point = None


def update_main_field_slope(
    config_dict,
    field_G,
    current_A,
    z0_voltage_V,
    min_span_G=5.0,
    max_z0_change_V=1e-6,
    smoothing=0.2,
    min_slope_factor=0.5,
    max_slope_factor=2.0,
):
    """Update the local main-field slope from settled differential data.

    The update is intentionally conservative: it uses only two settled points,
    rejects points where Z0 changed, rejects small field spans, and smooths the
    accepted differential slope into ``current_v_field_A_G``.
    """
    global _main_field_calibration_point
    previous = _main_field_calibration_point
    current_point = {
        "field_G": float(field_G),
        "current_A": float(current_A),
        "z0_voltage_V": float(z0_voltage_V),
    }
    if previous is None:
        _main_field_calibration_point = current_point
        logging.debug(
            strm("stored main-field calibration point", current_point)
        )
        return False
    if abs(current_point["z0_voltage_V"] - previous["z0_voltage_V"]) > (
        max_z0_change_V
    ):
        _main_field_calibration_point = current_point
        logging.debug(
            strm(
                "reset main-field calibration point because Z0 changed from",
                previous["z0_voltage_V"],
                "to",
                current_point["z0_voltage_V"],
            )
        )
        return False
    delta_B_G = current_point["field_G"] - previous["field_G"]
    if abs(delta_B_G) < min_span_G:
        logging.debug(
            strm(
                "retaining main-field calibration point; span",
                delta_B_G,
                "G is below",
                min_span_G,
                "G",
            )
        )
        return False
    measured_slope = (
        current_point["current_A"] - previous["current_A"]
    ) / delta_B_G
    current_slope = config_dict["current_v_field_A_G"]
    min_slope = min_slope_factor * current_slope
    max_slope = max_slope_factor * current_slope
    if not (min_slope <= measured_slope <= max_slope):
        _main_field_calibration_point = current_point
        logging.debug(
            strm(
                "reset main-field calibration point because slope",
                measured_slope,
                "is outside",
                min_slope,
                "to",
                max_slope,
            )
        )
        return False
    config_dict["current_v_field_A_G"] = (
        (1 - smoothing) * current_slope + smoothing * measured_slope
    )
    _main_field_calibration_point = current_point
    logging.debug(
        strm(
            "updated current_v_field_A_G from",
            current_slope,
            "to",
            config_dict["current_v_field_A_G"],
            "using settled differential slope",
            measured_slope,
        )
    )
    return True


def adjust_main_field(B0_des_G, config_dict, h, gen):
    """Correct the main magnet current using the calibrated local slope.

    This applies an incremental current correction from the measured field
    error. It deliberately does not update ``current_v_field_A_G`` from a
    single I/B value; successful settled ramps update the local slope only from
    guarded differential measurements.

    Parameters
    ----------
    B0_des_G : float
        Desired magnetic field in Gauss.
    config_dict : dict
        Configuration dictionary containing ``current_v_field_A_G``.
    h : LakeShore475
        Hall probe used for the current field readback.
    gen : genesys
        Main magnet power supply. Its ``I_meas`` readback is used as the
        starting current and its ``I_limit`` property is updated.
    """
    true_B0_G = h.field_in_G
    field_error_G = B0_des_G - true_B0_G
    current_v_field_A_G = config_dict["current_v_field_A_G"]
    I_setting = (
        gen.I_meas
        + field_error_G * current_v_field_A_G
    )
    logging.debug(
        strm(
            "correcting main field from",
            true_B0_G,
            "G to",
            B0_des_G,
            "G with current setting",
            I_setting,
            "A",
        )
    )
    gen.I_limit = I_setting


def maintain_field(
    B0_des_G,
    current_B0_G,
    config_dict,
    h,
    gen,
    shims,
    Z0_min_voltage_V=0.0,
    Z0_max_voltage_V=6.0,
):
    """Apply one fine Z0 correction, falling back to a full field ramp.

    This is intended for log-time field maintenance after the main field has
    already been set. If the requested correction fits inside the allowed Z0
    voltage window, only the Z0 shim is moved. If Z0 lacks enough headroom, the
    full ramping algorithm is used so the main supply can be corrected too.

    Parameters
    ----------
    B0_des_G : float
        Desired magnetic field in Gauss.
    current_B0_G : float
        Current Hall probe readback in Gauss. Passing this in avoids taking a
        second pre-correction readback in the server logging path.
    config_dict : dict
        Configuration dictionary containing ``z0_field_v_voltage_G_V`` and the
        values required by ``ramp_field`` if fallback is needed.
    h : LakeShore475
        Hall probe used to read the field after the correction.
    gen : genesys
        Main magnet power supply, passed through to ``ramp_field`` if needed.
    shims : ShimDictMapping
        Shim mapping used to read, round, and set the Z0 voltage.
    Z0_min_voltage_V : float, optional
        Minimum allowed Z0 voltage.
    Z0_max_voltage_V : float, optional
        Maximum allowed Z0 voltage.

    Returns
    -------
    float
        Hall probe readback after the fine correction or fallback ramp.
    """
    Z0_initial_voltage_V = shims.V_read["Z0"]
    desired_Z0_voltage_V = Z0_initial_voltage_V + (
        B0_des_G - current_B0_G
    ) / config_dict["z0_field_v_voltage_G_V"]
    # {{{ Use the shim for small log-time corrections when it has enough
    #     voltage headroom. This avoids running the slower main-field ramp
    #     during ordinary logging drift correction.
    if Z0_min_voltage_V <= desired_Z0_voltage_V <= Z0_max_voltage_V:
        desired_Z0_voltage_V = shims.round_to_allowed(
            "V", "Z0", desired_Z0_voltage_V
        )
        if not np.isclose(desired_Z0_voltage_V, Z0_initial_voltage_V):
            shims.V_limit["Z0"] = desired_Z0_voltage_V
        return h.field_in_G
    # }}}
    return ramp_field(B0_des_G, config_dict, h, gen, shims)


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
    Z0_max_voltage_V: float or None
        The maximum voltage we allow for the Z0 shim coil. If None, use the
        hardware maximum for the mapped Z0 channel.
    """
    z0_inst = shims.instrument("Z0")
    z0_channel = shims.channel("Z0")
    if Z0_max_voltage_V is None:
        Z0_max_voltage_V = z0_inst.max_V[z0_channel]
    Z0_initial_voltage_V = shims.V_read["Z0"]
    main_target_G = B0_des_G - (
        Z0_initial_voltage_V * config_dict["z0_field_v_voltage_G_V"]
    )
    I_setting = main_target_G * config_dict["current_v_field_A_G"]
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
    ramp_steps = max(1, int(abs(I_setting - temp_I_meas) * 2))
    logging.info(
        "Ramping the field from %s to %s A, accounting for Z0=%s V",
        gen.I_meas,
        I_setting,
        Z0_initial_voltage_V,
    )
    for thisI in np.linspace(temp_I_meas, I_setting, ramp_steps + 1)[1:]:
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
        true_B0_G = h.field_in_G
        field_discrepancy = abs(true_B0_G - B0_des_G)
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
        elif field_discrepancy > main_field_threshold_G:
            # {{{ Large discrepancies belong to the main magnet supply. The
            #     Z0 shim is reserved for the final small correction so it
            #     keeps enough headroom for later log-time maintenance.
            adjust_main_field(
                B0_des_G,
                config_dict,
                h,
                gen,
            )
            num_field_matches = 0
            # }}}
        else:
            # {{{ if it's not within tolerance, and it's not asking for a big
            #     step, then it's asking for an intermediate step
            #     so we need to adjust the Z0 field.
            # {{{ the desired voltage is the combination of the change we want
            #     to make and the voltage that's running through Z0 before the
            #     change (and we want to save the latter)
            desired_Z0_voltage_V = (B0_des_G - true_B0_G) / config_dict[
                "z0_field_v_voltage_G_V"
            ]
            Z0_initial_voltage_V = shims.V_read["Z0"]
            desired_Z0_voltage_V += Z0_initial_voltage_V
            # }}}
            # {{{ we can only use Z0 to increase the voltage, and we don't want
            #     to ask for an unreasonable voltage
            if desired_Z0_voltage_V < Z0_min_voltage_V:
                # {{{ If Z0 would need to go negative, bias the main field
                #     slightly low so the positive-only Z0 correction can
                #     finish the approach on a later pass.
                adjust_main_field(B0_des_G - 1.0, config_dict, h, gen)
                num_field_matches = 0
                # }}}
                continue
            elif desired_Z0_voltage_V > Z0_max_voltage_V:
                # {{{ If Z0 is out of positive headroom, move the main field
                #     toward the target and retry the fine correction.
                adjust_main_field(B0_des_G, config_dict, h, gen)
                num_field_matches = 0
                # }}}
                continue
            # }}}
            desired_Z0_voltage_V = shims.round_to_allowed(
                "V",
                "Z0",
                desired_Z0_voltage_V,
            )
            if not np.isclose(desired_Z0_voltage_V, Z0_initial_voltage_V):
                shims.V_limit["Z0"] = desired_Z0_voltage_V
                # {{{ Check if the field is stabilizing
                num_field_matches = 0
                B0_last_G = h.field_in_G
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
    update_main_field_slope(
        config_dict,
        true_B0_G,
        gen.I_meas,
        shims.V_read["Z0"],
    )
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
