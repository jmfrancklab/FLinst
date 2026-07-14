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


def adjust_main_field(B0_des_G, config_dict, h, gen, true_B0_G=None):
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
    if true_B0_G is None:
        true_B0_G = h.field_in_G
    field_error_G = B0_des_G - true_B0_G
    current_v_field_A_G = config_dict["current_v_field_A_G"]
    I_setting = (
        gen.I_meas
        + field_error_G * current_v_field_A_G
    )
    if I_setting > 25:
        raise ValueError("Current is too high.")
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
    initial_I_A = gen.I_meas
    current_steps = max(1, int(np.ceil(abs(I_setting - initial_I_A) / 0.5)))
    for this_I_A in np.linspace(initial_I_A, I_setting, current_steps + 1)[1:]:
        gen.I_limit = this_I_A
        if current_steps > 1:
            time.sleep(config_dict["magnet_settle_short"])
    return I_setting


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
            corrected_B0_G = h.field_in_G
            logging.info(
                "Z0 response estimate: dV=%s V dB=%s G slope=%s G/V",
                desired_Z0_voltage_V - Z0_initial_voltage_V,
                corrected_B0_G - current_B0_G,
                (corrected_B0_G - current_B0_G)
                / (desired_Z0_voltage_V - Z0_initial_voltage_V),
            )
            return corrected_B0_G
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
        Field discrepancy above which we wait the medium settling time after
        a main-current correction.
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
    tolerance_G = (
        config_dict["tolerance_Hz"] * 1e-6 / config_dict["gamma_eff_mhz_g"]
    )
    # {{{ Bring the supply online if needed. Current moves below are
    #     incremental and bounded so small set-field calls do not perform a
    #     fresh absolute feed-forward ramp.
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
    if B0_des_G == 0:
        shims.V_limit["Z0"] = 0
        shims.output["Z0"] = 0
        logging.info("Z0 Shim is off")
        gen.I_limit = 0
        gen.output = False
        logging.info("The PS is off.")
        return h.field_in_G
    # }}}
    # {{{ Move only as much as needed. Z0 is the fast fine actuator whenever
    #     the target is inside its positive voltage range. The main supply is
    #     touched only to put the target back inside that range, biased below
    #     the target so positive-only Z0 can finish the approach.
    num_field_matches = 0
    required_field_matches = 2
    first_loop_field_G = h.field_in_G
    main_field_bias_G = 1.0
    for j in range(settling_attempts):
        if first_loop_field_G is None:
            time.sleep(config_dict["magnet_settle_short"])
            true_B0_G = h.field_in_G
        else:
            true_B0_G = first_loop_field_G
            first_loop_field_G = None
        field_error_G = B0_des_G - true_B0_G
        field_discrepancy = abs(field_error_G)
        if field_discrepancy < tolerance_G:
            logging.info(
                "field %s G is within %s G of desired %s G",
                true_B0_G,
                tolerance_G,
                B0_des_G,
            )
            num_field_matches += 1
            if num_field_matches >= required_field_matches:
                break
            continue
        num_field_matches = 0
        Z0_initial_voltage_V = shims.V_read["Z0"]
        desired_Z0_voltage_V = Z0_initial_voltage_V + (
            field_error_G / config_dict["z0_field_v_voltage_G_V"]
        )
        if not (Z0_min_voltage_V <= desired_Z0_voltage_V <= Z0_max_voltage_V):
            main_target_G = B0_des_G - main_field_bias_G
            I_setting = adjust_main_field(
                main_target_G,
                config_dict,
                h,
                gen,
                true_B0_G=true_B0_G,
            )
            if field_discrepancy > main_field_threshold_G:
                time.sleep(config_dict["magnet_settle_medium"])
            logging.info(
                "Z0 target %s V is outside %s to %s V; moved main "
                "current to %s A for %s G target with %s G Z0 bias",
                desired_Z0_voltage_V,
                Z0_min_voltage_V,
                Z0_max_voltage_V,
                I_setting,
                B0_des_G,
                main_field_bias_G,
            )
            continue
        # {{{ Apply one Z0 correction and log one response estimate. The next
        #     iteration recomputes from the post-command Hall readback instead
        #     of waiting in a nested stabilization loop.
        desired_Z0_voltage_V = shims.round_to_allowed(
            "V",
            "Z0",
            desired_Z0_voltage_V,
        )
        if np.isclose(desired_Z0_voltage_V, Z0_initial_voltage_V):
            I_setting = adjust_main_field(
                B0_des_G - main_field_bias_G,
                config_dict,
                h,
                gen,
                true_B0_G=true_B0_G,
            )
            logging.info(
                "Rounded Z0 target is unchanged at %s V while error is "
                "%s G; moved main current to %s A",
                Z0_initial_voltage_V,
                field_error_G,
                I_setting,
            )
            continue
        shims.V_limit["Z0"] = desired_Z0_voltage_V
        z0_command_delta_V = desired_Z0_voltage_V - Z0_initial_voltage_V
        first_loop_field_G = h.field_in_G
        logging.info(
            "Z0 response estimate: dV=%s V dB=%s G slope=%s G/V",
            z0_command_delta_V,
            first_loop_field_G - true_B0_G,
            (first_loop_field_G - true_B0_G) / z0_command_delta_V,
        )
        # }}}

    if num_field_matches < required_field_matches:
        raise RuntimeError(
            f"I tried {settling_attempts} times to get my"
            f" field to match within {tolerance_G} G"
            f" or {config_dict['tolerance_Hz']} Hz "
            f"{required_field_matches} times "
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
