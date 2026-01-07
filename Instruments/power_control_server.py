# To be run from the computer connected to the EPR spectrometer
import time, socket, pickle, os, logging, sys
from Instruments import (
    Bridge12,
    prologix_connection,
    gigatronics,
    logobj,
    LakeShore475,
    genesys,
)
import SpinCore_pp
import numpy as np
from pyspecdata import strm

IP = "0.0.0.0"
PORT = 6002


def read_field_in_G(h):
    "helper function to give the field in Gauss"
    return h.field.to("T").magnitude * 1e4


def adjust_field(B0_des_G, config_dict, h, gen):
    true_B0_G = read_field_in_G(h)
    logging.debug(
        strm(
            "adjusting current_v_field_A_G from",
            config_dict["current_v_field_A_G"],
        )
    )
    config_dict["current_v_field_A_G"] *= B0_des_G / true_B0_G
    logging.debug(strm("to", config_dict["current_v_field_A_G"]))
    I_setting = B0_des_G * config_dict["current_v_field_A_G"]
    gen.I_limit = I_setting


def main():
    # {{{ set up log at ~/power_control_server.log
    log_filename = os.path.join(
        os.path.expanduser("~"), "power_control_server.log"
    )
    formatter = logging.Formatter(
        "--> %(filename)s(%(lineno)s):%(name)s %(funcName)20s"
        " %(asctime)20s\n%(levelname)s: %(message)s"
    )
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    file_handler = logging.FileHandler(
        log_filename, mode="w", encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    stdout_handler = logging.StreamHandler(sys.stdout)
    # can set levels independently with:
    stdout_handler.setLevel(logging.INFO)
    logger.addHandler(stdout_handler)
    logger.addHandler(file_handler)
    # }}}
    config_dict = SpinCore_pp.configuration("active.ini")
    with genesys(config_dict["genesys_ip"]) as gen:
        with prologix_connection() as p:
            with gigatronics(
                prologix_instance=p, address=config_dict["gigatronics_address"]
            ) as g:
                with Bridge12() as b:
                    with LakeShore475(p) as h:
                        sock = socket.socket(
                            socket.AF_INET, socket.SOCK_STREAM
                        )
                        sock.bind((IP, PORT))
                        this_logobj = logobj()

                        def process_cmd(cmd, this_logobj):
                            leave_open = True
                            cmd = cmd.strip()
                            print("I am processing", cmd)
                            if this_logobj.currently_logging:
                                this_logobj.add(
                                    Rx=b.rxpowerdbm_float(),
                                    power=g.read_power(),
                                    cmd=cmd,
                                )
                            args = cmd.split(b" ")
                            print("I split it to ", args)
                            if len(args) == 3:
                                if args[0] == b"DIP_LOCK":
                                    freq1 = float(args[1])
                                    freq2 = float(args[2])
                                    _, _, min_f = b.lock_on_dip(
                                        ini_range=(freq1 * 1e9, freq2 * 1e9)
                                    )
                                    b.set_freq(min_f)
                                    min_f = float(b.freq_int()) * 1e3
                                    conn.send(
                                        ("%0.6f" % min_f).encode("ASCII")
                                    )
                                    this_logobj.wg_has_been_flipped = True
                                else:
                                    raise ValueError(
                                        "I don't understand this 3 component"
                                        " command"
                                    )
                            if len(args) == 2:
                                match args[0]:
                                    case b"SET_POWER":
                                        logging.debug(
                                            f"SET_POWER to {args[1]}"
                                        )
                                        if not this_logobj.wg_has_been_flipped:
                                            # {{{ then I need to turn
                                            #     everything on
                                            b.set_wg(True)
                                            b.set_rf(True)
                                            b.set_amp(True)
                                            # }}}
                                            this_logobj.wg_has_been_flipped = (
                                                True
                                            )
                                        dBm_setting = float(args[1])
                                        last_power = b.power_float()
                                        if dBm_setting > last_power + 3:
                                            last_power += 3
                                            nsecs = -1 * time.time()
                                            logging.info(
                                                f"SETTING TO... {last_power}"
                                            )
                                            b.set_power(last_power)
                                            logging.debug(
                                                "returned from set power"
                                            )
                                            for j in range(30):
                                                if (
                                                    b.power_float()
                                                    < last_power
                                                ):
                                                    time.sleep(0.1)
                                                else:
                                                    break
                                            nsecs += time.time()
                                            logging.debug(
                                                f"took, {j}, tries and,"
                                                f"{nsecs}, seconds"
                                            )
                                            while dBm_setting > last_power + 3:
                                                last_power += 3
                                                nsecs = -1 * time.time()
                                                logging.info(
                                                    "SETTING TO..."
                                                    f" {last_power}"
                                                )
                                                b.set_power(last_power)
                                                logging.debug(
                                                    "returned from set power"
                                                )
                                                for j in range(30):
                                                    if (
                                                        b.power_float()
                                                        < last_power
                                                    ):
                                                        time.sleep(0.1)
                                                    else:
                                                        break
                                                nsecs += time.time()
                                                logging.debug(
                                                    f"took, {j}, tries and,"
                                                    f" {nsecs}, seconds"
                                                )
                                        logging.info(
                                            "FINALLY - SETTING TO DESIRED"
                                            "POWER of {dBm_setting}"
                                        )
                                        nsecs = -1 * time.time()
                                        b.set_power(dBm_setting)
                                        logging.debug(
                                            "returned from set power"
                                        )
                                        for j in range(30):
                                            if b.power_float() < last_power:
                                                time.sleep(0.1)
                                            else:
                                                break
                                        nsecs += time.time()
                                        logging.debug(
                                            f"took, {j}, tries and, {nsecs},"
                                            " seconds"
                                        )
                                    case b"SET_FREQ":
                                        logging.debug(f"SET_FREQ to {args[1]}")
                                        if not this_logobj.wg_has_been_flipped:
                                            raise ValueError(
                                                "Turn on the power (to a low"
                                                " value) before setting the"
                                                " frequency"
                                            )
                                        current_power = b.power_float()
                                        if current_power > 10:
                                            raise ValueError(
                                                "to manually set the"
                                                " frequency, you"
                                                " must be at 10 dBm or less!"
                                                " Otherwise, you risk leaving"
                                                " the low-reflection dip, and"
                                                " sending all your power back"
                                                " at the amp!!"
                                            )
                                        b.set_freq(float(args[1]))
                                    case b"SET_FIELD":
                                        B0_des_G = float(args[1])  # B in G
                                        I_setting = (
                                            B0_des_G
                                            * config_dict[
                                                "current_v_field_A_G"
                                            ]
                                        )
                                        # {{{ First, we ramp from whatever
                                        #     our current is (zero or not)
                                        #     to where we think we want to
                                        #     be, allowing for the
                                        #     possibility that it might be a
                                        #     large change
                                        if I_setting > 25:
                                            raise ValueError(
                                                "Current is too high."
                                            )
                                        try:
                                            if not gen.output:
                                                gen.V_limit = 25.0
                                                gen.output = True
                                                gen.I_limit = 0
                                                print(
                                                    "The power supply is on."
                                                )
                                        except Exception:
                                            raise TypeError(
                                                "The power supply is not"
                                                " connected."
                                            )
                                        temp_I_meas = gen.I_meas
                                        ramp_steps = int(
                                            abs(I_setting - temp_I_meas) * 2
                                        )
                                        logging.info(
                                            "Ramping the field from"
                                            f" {gen.I_meas} to {I_setting}"
                                        )
                                        for I in np.linspace(
                                            temp_I_meas, I_setting, ramp_steps
                                        ):
                                            gen.I_limit = I
                                            time.sleep(
                                                config_dict[
                                                    "magnet_settle_short"
                                                ]
                                            )
                                        if ramp_steps > 4:
                                            time.sleep(
                                                config_dict[
                                                    "magnet_settle_long"
                                                ]
                                            )
                                        # }}}
                                        # {{{ now, adjust current_v_field_A_G
                                        #     to get the field we want,
                                        #     just once at the beginning
                                        # {{{ try to stabilize the field
                                        #     within 0.8 G of our desired
                                        #     value
                                        num_field_matches = 0
                                        for j in range(30):
                                            time.sleep(
                                                config_dict[
                                                    "magnet_settle_short"
                                                ]
                                            )
                                            if (
                                                abs(
                                                    read_field_in_G(h)
                                                    - B0_des_G
                                                )
                                                > 2.0
                                            ):
                                                time.sleep(
                                                    config_dict[
                                                        "magnet_settle_medium"
                                                    ]
                                                )
                                            if (
                                                abs(
                                                    read_field_in_G(h)
                                                    - B0_des_G
                                                )
                                                > 0.8
                                            ):
                                                adjust_field(
                                                    B0_des_G,
                                                    config_dict,
                                                    h,
                                                    gen,
                                                )
                                                num_field_matches = 0
                                            else:
                                                num_field_matches += 1
                                                if num_field_matches > 2:
                                                    break
                                        if num_field_matches < 3:
                                            raise RuntimeError(
                                                "I tried 30 times to get my"
                                                " field to match within 0.8 G"
                                                " three times in a row, and it"
                                                " didn't work!"
                                            )
                                        # }}}
                                        if B0_des_G == 0:
                                            gen.output = False
                                            logging.info("The PS is off.")
                                        true_B0_G = read_field_in_G(h)
                                        logging.info(
                                            "Your field is"
                                            f" {true_B0_G} G, and"
                                            "the ratio of the field I want"
                                            " to the one I get is"
                                            f" {B0_des_G / true_B0_G}\nIn "
                                            " other words, the discrepancy"
                                            f" is{true_B0_G - B0_des_G} G"
                                        )
                                        conn.send(
                                            ("%0.2f" % true_B0_G).encode(
                                                "ASCII"
                                            )
                                        )
                                    case _:
                                        raise ValueError(
                                            "I don't understand this 2"
                                            " component"
                                            " command:" + str(args)
                                        )
                            elif len(args) == 1:
                                match args[0]:
                                    case b"CLOSE":
                                        print("closing connection")
                                        leave_open = False
                                        b.soft_shutdown()
                                        conn.close()
                                    case b"GET_POWER":
                                        result = b.power_float()
                                        conn.send(
                                            ("%0.1f" % result).encode("ASCII")
                                        )
                                    case b"MW_OFF":
                                        b.soft_shutdown()

                                    case b"QUIT":
                                        print("closing connection")
                                        conn.close()
                                        leave_open = False
                                        quit()
                                    case b"START_LOG":
                                        this_logobj.currently_logging = True
                                    case b"STOP_LOG":
                                        this_logobj.currently_logging = False
                                        retval = (
                                            pickle.dumps(this_logobj)
                                            + b"ENDTCPIPBLOCK"
                                        )
                                        conn.send(retval)
                                        this_logobj.reset()
                                    case b"MW_OFF":
                                        b.soft_shutdown()
                                    case b"GET_FIELD":
                                        result = read_field_in_G(h)
                                        conn.send(
                                            ("%0.2f" % result).encode("ASCII")
                                        )
                                    case _:
                                        raise ValueError(
                                            "I don't understand this 1"
                                            " component command" + str(args)
                                        )
                            return leave_open

                        while True:
                            sock.listen(1)
                            print("I am listening")
                            conn, addr = sock.accept()
                            print("I have accepted from", addr)
                            leave_open = True
                            oldtimeout = conn.gettimeout()
                            while leave_open:
                                conn.settimeout(0.001)
                                try:
                                    data = conn.recv(1024)
                                    timelist = []
                                    timelabels = []
                                    conn.settimeout(oldtimeout)
                                    timelist.append(time.time())
                                    if oldtimeout is None:
                                        timelabels.append(
                                            "set timeout to None on"
                                            " receiving command,"
                                            " '%s'" % (data)
                                        )
                                    else:
                                        timelabels.append(
                                            "set timeout to %g on receiving"
                                            " command, '%s'"
                                            % (oldtimeout, data)
                                        )
                                    if len(data) > 0:
                                        for cmd in data.strip().split(b"\n"):
                                            timelist.append(time.time())
                                            timelabels.append(
                                                "about to process"
                                            )
                                            leave_open = process_cmd(
                                                cmd, this_logobj
                                            )
                                            timelist.append(time.time())
                                            timelabels.append(
                                                "processed %s" % cmd
                                            )
                                    else:
                                        print("no data received")
                                        timelist.append(time.time())
                                        timelabels.append("no data received")
                                    print("time to process:")
                                    print(
                                        " --> ".join(
                                            [
                                                timelabels[j]
                                                + " --> "
                                                + str(
                                                    timelist[j + 1]
                                                    - timelist[j]
                                                )
                                                for j in range(
                                                    len(timelist) - 1
                                                )
                                            ]
                                            + [timelabels[-1]]
                                        )
                                    )
                                except socket.timeout:
                                    if this_logobj.currently_logging:
                                        this_logobj.add(
                                            Rx=b.rxpowerdbm_float(),
                                            power=g.read_power(),
                                        )
