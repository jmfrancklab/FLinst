# To be run from the computer connected to the EPR spectrometer
import time, socket, pickle
from Instruments import (
    Bridge12,
    prologix_connection,
    gigatronics,
    logobj,
    LakeShore475,
    genesys,
)
import SpinCore_pp
import logging
import numpy as np

IP = "0.0.0.0"
PORT = 6002


def read_field_in_G(h):
    "helper function to give the field in Gauss"
    return h.field.to("T").magnitude * 1e4


def adjust_and_settle(B0_des_G, config_dict, h, gen):
    true_B0_G = read_field_in_G(h)
    logging.info(
        "adjusting current_v_field_A_G from",
        config_dict["current_v_field_A_G"],
    )
    config_dict["current_v_field_A_G"] *= B0_des_G / true_B0_G
    logging.info(
        "to",
        config_dict["current_v_field_A_G"],
        "and settling again for",
        config_dict["settle_initial_s"],
        "s",
    )
    time.sleep(config_dict["settle_initial_s"])
    I_setting = B0_des_G * config_dict["current_v_field_A_G"]
    gen.I_limit = I_setting


def main():
    # ☐ TODO:
    #         NOTE -- make sure the yaml branch is tested and merged first
    # ☐ TODO: add settle_initial_s, ramp_dt, genesys_ip, gigatronics_adress to config_parser
    config_dict = SpinCore_pp.configuration("active.ini")
    with genesys(config_dict["genesys_ip"]) as gen:
        with prologix_connection() as p:
            with gigatronics(
                prologix_instance=p, address=config_dict["gigatronics_adress"]
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
                                else:
                                    raise ValueError(
                                        "I don't understand this 3 component"
                                        " command"
                                    )
                            if len(args) == 2:
                                match args[0]:
                                    case b"SET_POWER":
                                        dBm_setting = float(args[1])
                                        last_power = b.power_float()
                                        if dBm_setting > last_power + 3:
                                            last_power += 3
                                            nsecs = -1 * time.time()
                                            print("SETTING TO...", last_power)
                                            b.set_power(last_power)
                                            for j in range(30):
                                                if (
                                                    b.power_float()
                                                    < last_power
                                                ):
                                                    time.sleep(0.1)
                                                else:
                                                    break
                                            nsecs += time.time()
                                            print(
                                                "took",
                                                j,
                                                "tries and",
                                                nsecs,
                                                "seconds",
                                            )
                                            while dBm_setting > last_power + 3:
                                                last_power += 3
                                                nsecs = -1 * time.time()
                                                print(
                                                    "SETTING TO...", last_power
                                                )
                                                b.set_power(last_power)
                                                for j in range(30):
                                                    if (
                                                        b.power_float()
                                                        < last_power
                                                    ):
                                                        time.sleep(0.1)
                                                    else:
                                                        break
                                                nsecs += time.time()
                                                print(
                                                    "took",
                                                    j,
                                                    "tries and",
                                                    nsecs,
                                                    "seconds",
                                                )
                                        print(
                                            "FINALLY - SETTING TO DESIRED POWER"
                                        )
                                        nsecs = -1 * time.time()
                                        b.set_power(dBm_setting)
                                        for j in range(30):
                                            if b.power_float() < last_power:
                                                time.sleep(0.1)
                                            else:
                                                break
                                        nsecs += time.time()
                                        print(
                                            "took",
                                            j,
                                            "tries and",
                                            nsecs,
                                            "seconds",
                                        )
                                    case b"SET_FIELD":
                                        B0_des_G = (
                                            config_dict["carrierFreq_MHz"]
                                            / config_dict["gamma_eff_mhz_g"]
                                        )  # B in G
                                        I_setting = (
                                            B0_des_G
                                            * config_dict[
                                                "current_v_field_A_G"
                                            ]
                                        )
                                        ramp_steps = I_setting * 2
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
                                        except:
                                            raise TypeError(
                                                "The power supply is not"
                                                " connected."
                                            )
                                        logging.info("Ramping up the field")
                                        for I in np.linspace(
                                            gen.I_meas, I_setting, ramp_steps
                                        ):
                                            gen.I_limit = I
                                            time.sleep(config_dict["ramp_dt"])
                                        # }}}
                                        # {{{ now, adjust current_v_field_A_G
                                        #     to get the field we want,
                                        #     just once at the beginning
                                        time.sleep(
                                            config_dict["settle_initial_s"]
                                        )
                                        if (
                                            abs(read_field_in_G(h) - B0_des_G)
                                            > 0.8
                                        ):
                                            adjust_and_settle(B0_des_G)
                                        true_B0_G = read_field_in_G(h)
                                        logging.info(
                                            "Your field is"
                                            f" {true_B0_G} G, and"
                                            "the ratio of the field I want to the"
                                            " one I get is"
                                            f" {B0_des_G / true_B0_G}\nIn other"
                                            " words, the discrepancy"
                                            f" is{true_B0_G - B0_des_G} G"
                                        )
                                        conn.send(
                                            ("%0.2f" % true_B0_G).encode(
                                                "ASCII"
                                            )
                                        )
                                    case _:
                                        raise ValueError(
                                            "I don't understand this 2 component"
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
                                        # ☐ TODO: this is not right.  All the
                                        #         stuff printed is typically
                                        #         ignored.  What you want to do
                                        #         is reply to the client
                                        #         program (the pulse program)
                                        #         --> so conn.send (read other
                                        #         usages in this file for
                                        #         examples)
                                        #         ALSO! This does not have an
                                        #         argument, so it goes in the
                                        #         next len(args) block
                                        result = read_field_in_G(h)
                                        conn.send(
                                            ("%0.2f" % result).encode("ASCII")
                                        )
                                    case _:
                                        raise ValueError(
                                            "I don't understand this 1 component"
                                            " command" + str(args)
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
                                            "set timeout to None on receiving"
                                            " command, '%s'" % (data)
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
