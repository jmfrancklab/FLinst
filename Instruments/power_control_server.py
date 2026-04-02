# To be run from the computer connected to the EPR spectrometer
import time, socket, pickle, os, logging, sys
from Instruments import (
    Bridge12,
    prologix_connection,
    gigatronics,
    logobj,
    LakeShore475,
    genesys,
    ShimDictMapping,
)
from Instruments.field_feedback import ramp_field
import SpinCore_pp

IP = "0.0.0.0"
PORT = 6002


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
    with (
        genesys(config_dict["genesys_ip"]) as gen,
        prologix_connection(
            ip=config_dict["prologix_ip"], port=config_dict["prologix_port"]
        ) as p,
        gigatronics(
            prologix_instance=p, address=config_dict["gigatronics_address"]
        ) as g,
        Bridge12() as b,
        LakeShore475(p) as h,
        ShimDictMapping(
            config_dict["shim_address"],
            prologix_instance=p,
            safe_current=1.8,
            overvoltage=16.0,
        ) as sh_map,
    ):
        sh_map.I_limit[:] = 1.5
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind((IP, PORT))
        this_logobj = logobj()

        def set_shim_limit(
            limit_proxy, limit_type, shim_name, requested_value
        ):
            rounded_value = sh_map.round_to_allowed(
                limit_type, shim_name, requested_value
            )
            if not sh_map.output[shim_name] and requested_value != 0:
                limit_proxy[shim_name] = 0
                sh_map.output[shim_name] = 1
            limit_proxy[shim_name] = rounded_value
            return rounded_value

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
                match args[0]:
                    case b"DIP_LOCK":
                        freq1 = float(args[1])
                        freq2 = float(args[2])
                        _, _, min_f = b.lock_on_dip(
                            ini_range=(
                                freq1 * 1e9,
                                freq2 * 1e9,
                            )
                        )
                        b.set_freq(min_f)
                        min_f = float(b.freq_int()) * 1e3
                        conn.send(("%0.6f" % min_f).encode("ASCII"))
                        this_logobj.wg_has_been_flipped = True
                    case b"SET_SHIM_CURRENT":
                        shim_name = args[1].decode("ASCII")
                        current_A = set_shim_limit(
                            sh_map.I_limit, "I", shim_name, float(args[2])
                        )
                        conn.send(("%0.3f" % current_A).encode("ASCII"))
                    case b"SET_SHIM_VOLTAGE":
                        shim_name = args[1].decode("ASCII")
                        voltage_V = set_shim_limit(
                            sh_map.V_limit, "V", shim_name, float(args[2])
                        )
                        conn.send(("%0.3f" % voltage_V).encode("ASCII"))
                    case _:
                        raise ValueError(
                            "I don't understand this 3 component command"
                        )
            if len(args) == 2:
                match args[0]:
                    case b"SET_POWER":
                        logging.debug(f"SET_POWER to {args[1]}")
                        if not this_logobj.wg_has_been_flipped:
                            # {{{ then I need to turn
                            #     everything on
                            b.set_wg(True)
                            b.set_rf(True)
                            b.set_amp(True)
                            # }}}
                            this_logobj.wg_has_been_flipped = True
                        dBm_setting = float(args[1])
                        last_power = b.power_float()
                        if dBm_setting > last_power + 3:
                            last_power += 3
                            nsecs = -1 * time.time()
                            logging.info(f"SETTING TO... {last_power}")
                            b.set_power(last_power)
                            logging.debug("returned from set power")
                            for j in range(30):
                                if b.power_float() < last_power:
                                    time.sleep(0.1)
                                else:
                                    break
                            nsecs += time.time()
                            logging.debug(
                                f"took, {j}, tries and,{nsecs}, seconds"
                            )
                            while dBm_setting > last_power + 3:
                                last_power += 3
                                nsecs = -1 * time.time()
                                logging.info(f"SETTING TO... {last_power}")
                                b.set_power(last_power)
                                logging.debug("returned from set power")
                                for j in range(30):
                                    if b.power_float() < last_power:
                                        time.sleep(0.1)
                                    else:
                                        break
                                nsecs += time.time()
                                logging.debug(
                                    f"took, {j}, tries and, {nsecs}, seconds"
                                )
                        logging.info(
                            "FINALLY - SETTING TO DESIRED"
                            "POWER of {dBm_setting}"
                        )
                        nsecs = -1 * time.time()
                        b.set_power(dBm_setting)
                        logging.debug("returned from set power")
                        for j in range(30):
                            if b.power_float() < last_power:
                                time.sleep(0.1)
                            else:
                                break
                        nsecs += time.time()
                        logging.debug(
                            f"took, {j}, tries and, {nsecs}, seconds"
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
                        true_B0_G = ramp_field(
                            B0_des_G,
                            config_dict,
                            h,
                            gen,
                            sh_map.instrument("Z0"),
                        )
                        conn.send(("%0.2f" % true_B0_G).encode("ASCII"))
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
                        conn.send(("%0.1f" % result).encode("ASCII"))
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
                        retval = pickle.dumps(this_logobj) + b"ENDTCPIPBLOCK"
                        conn.send(retval)
                        this_logobj.reset()
                    case b"MW_OFF":
                        b.soft_shutdown()
                    case b"GET_FIELD":
                        result = h.field_in_G
                        conn.send(("%0.2f" % result).encode("ASCII"))
                    case b"GET_SHIM":
                        retval = (
                            pickle.dumps(
                                {
                                    shim_name: (
                                        sh_map.V_read[shim_name],
                                        sh_map.I_read[shim_name],
                                    )
                                    for shim_name in sh_map
                                }
                            )
                            + b"ENDTCPIPBLOCK"
                        )
                        conn.send(retval)
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
                            " command, '%s'" % (oldtimeout, data)
                        )
                    if len(data) > 0:
                        for cmd in data.strip().split(b"\n"):
                            timelist.append(time.time())
                            timelabels.append("about to process")
                            leave_open = process_cmd(cmd, this_logobj)
                            timelist.append(time.time())
                            timelabels.append("processed %s" % cmd)
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
                                + str(timelist[j + 1] - timelist[j])
                                for j in range(len(timelist) - 1)
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
