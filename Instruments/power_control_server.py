# To be run from the computer connected to the EPR spectrometer
import time, socket, pickle
from Instruments import Bridge12, prologix_connection, gigatronics, logobj, LakeShore475, genesys
import SpinCore_pp
import logging

IP = "0.0.0.0"
PORT = 6002


def main():
    with genesys("192.168.0.199") as gen:
        with prologix_connection() as p:
            with gigatronics(prologix_instance=p, address=7) as g:
                with Bridge12() as b:
                    with LakeShore475(p) as h:
                        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        sock.bind((IP, PORT))
                        this_logobj = logobj()
                        config_dict = SpinCore_pp.configuration("active.ini")

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
                                    conn.send(("%0.6f" % min_f).encode("ASCII"))
                                else:
                                    raise ValueError(
                                        "I don't understand this 3 component command"
                                    )
                            if len(args) == 2:
                                if args[0] == b"SET_POWER":
                                    dBm_setting = float(args[1])
                                    last_power = b.power_float()
                                    if dBm_setting > last_power + 3:
                                        last_power += 3
                                        nsecs = -1 * time.time()
                                        print("SETTING TO...", last_power)
                                        b.set_power(last_power)
                                        for j in range(30):
                                            if b.power_float() < last_power:
                                                time.sleep(0.1)
                                            else:
                                                break
                                        nsecs += time.time()
                                        print("took", j, "tries and", nsecs, "seconds")
                                        while dBm_setting > last_power + 3:
                                            last_power += 3
                                            nsecs = -1 * time.time()
                                            print("SETTING TO...", last_power)
                                            b.set_power(last_power)
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
                                    print("FINALLY - SETTING TO DESIRED POWER")
                                    nsecs = -1 * time.time()
                                    b.set_power(dBm_setting)
                                    for j in range(30):
                                        if b.power_float() < last_power:
                                            time.sleep(0.1)
                                        else:
                                            break
                                    nsecs += time.time()
                                    print("took", j, "tries and", nsecs, "seconds")
                                elif args[0] == b"SET_FIELD":
                                    B0_des_G = (config_dict["carrierFreq_MHz"]) / config_dict["gamma_eff_mhz_g"])  # B in G
                                    I_setting = B0_des_G * config_dict["current_v_field_A_G"]
                                    ramp_dt = 0.05  #Settling time at each ramping step (s)
                                    ramp_steps = I_setting*2
                                    myinput = input(strm("Your field is:", B0_des_G, "\nDoes this look okay?"))
                                    settle_initial_s = 60 
                                    if myinput.lower().startswith("n"):
                                        raise ValueError("You said no!!!")
                                    try:
                                        g.V_limit = 25.0
                                        g.output = True
                                        print("The power supply is on.")
                                    except:
                                        raise TypeError("The power supply is not connected.")
                                    # {{{Ramping up the field
                                    print("Ramping up the field")
                                    for I in np.linspace(0.0, I_setting, ramp_steps):
                                        gen.I_limit = I
                                        time.sleep(ramp_dt)
                                    # }}}
                                    # {{{ now, adjust  current_v_field_A_G to get the field we want,
                                    #     just once at the beginning
                                    true_B0_G = h.field.to("T").magnitude * 1e4
                                    print(
                                        "adjusting current_v_field_A_G from", config_dict["current_v_field_A_G"]
                                    )
                                    config_dict["current_v_field_A_G"] *= B0_G / true_B0_G
                                    print("to", config_dict["current_v_field_A_G"], "and settling again")
                                    time.sleep(settle_initial_s)
                                    I_setting = B0_des_G * config_dict["current_v_field_A_G"]
                                    gen.I_limit = I_setting
                                    print(f"Your field is {h.field.to("T").magnitude * 1e4} G")
                                    logging.info(
                                    "The ratio of the field I want to the one I"
                                    f"get is {B0_des_G / true_B0_G}\n"
                                    "In other words, the discrepancy is"
                                    f"{true_B0_G - B0_des_G} G"
                                    )

                                elif args[0] == b"GET_FIELD":
                                    try:
                                        print(f"Your field is {h.field.to("T").magnitude * 1e4} G")
                                    except:
                                        raise ValueError("Hall probe is not connected",
                                                         "or the power supply is off")
                                        
                                else:
                                    raise ValueError(
                                        "I don't understand this 2 component command:"
                                        + str(args)
                                    )
                            elif len(args) == 1:
                                if args[0] == b"CLOSE":
                                    print("closing connection")
                                    leave_open = False
                                    b.soft_shutdown()
                                    conn.close()
                                elif args[0] == b"GET_POWER":
                                    result = b.power_float()
                                    conn.send(("%0.1f" % result).encode("ASCII"))
                                elif args[0] == b"MW_OFF":
                                    b.soft_shutdown()

                                elif args[0] == b"QUIT":
                                    print("closing connection")
                                    conn.close()
                                    leave_open = False
                                    quit()
                                elif args[0] == b"START_LOG":
                                    this_logobj.currently_logging = True
                                elif args[0] == b"STOP_LOG":
                                    this_logobj.currently_logging = False
                                    retval = (
                                        pickle.dumps(this_logobj) + b"ENDTCPIPBLOCK"
                                    )
                                    conn.send(retval)
                                    this_logobj.reset()
                                elif args[0] == b"MW_OFF":
                                    b.soft_shutdown()
                                else:
                                    raise ValueError(
                                        "I don't understand this 1 component command"
                                        + str(args)
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
                                            "set timeout to None on receiving command,"
                                            " '%s'" % (data)
                                        )
                                    else:
                                        timelabels.append(
                                            "set timeout to %g on receiving command,"
                                            " '%s'" % (oldtimeout, data)
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
                                        