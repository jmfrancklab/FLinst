from pyspecdata import strm
import logging
import numpy as np
import time


def adjust_field(B0_des_G, config_dict, h, gen):
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


def ramp_field(B0_des_G, config_dict, h, gen):
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
    for I in np.linspace(temp_I_meas, I_setting, ramp_steps):
        gen.I_limit = I
        time.sleep(config_dict["magnet_settle_short"])
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
    for j in range(30):
        time.sleep(config_dict["magnet_settle_short"])
        field_discrepancy = abs(h.field_in_G - B0_des_G)
        if field_discrepancy > 2.0:
            time.sleep(config_dict["magnet_settle_medium"])
        # TODO ☐: I edited the flow of the following a little.
        #         Unfortunately, this does mean that we need a quick test
        #         that you can still set the field as desired.
        if (
            field_discrepancy
            < config_dict["tolerance_Hz"]
            * 1e-05
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
            or (B0_des_G >= 20 and field_discrepancy > 0.8)
        ):
            adjust_field(
                B0_des_G,
                config_dict,
                h,
                gen,
            )
            num_field_matches = 0
        elif (B0_des_G < 20 and field_discrepancy <= 5) or (
            B0_des_G >= 20 and field_discrepancy <= 0.8
        ):
            logging.info(
                "You are trying to adjust the field in an intermediate region."
                "This will be handled by shimstack later. I am leaving field "
                "as is."
            )
            num_field_matches += 1
            if num_field_matches > 2:
                break
        else:
            raise ValueError(
                "I've encountered a condition where B0_des_G"
                f" = {B0_des_G} and field_discrepancy ="
                f" {field_discrepancy}.  I don't know what to"
                "do about this!!"
            )
    if num_field_matches < 3:
        raise RuntimeError(
            "I tried 30 times to get my"
            " field to match within 0.8 G"
            " three times in a row, and it"
            " didn't work!"
        )
    # }}}
    if B0_des_G < 20:
        gen.I_limit = 0
        gen.output = False
        logging.info("The PS is off.")
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
