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


def main():
    # ☐ TODO: since we are using the config dict, add the IP addresses as entries.
    #         NOTE -- make sure the yaml branch is tested and merged first
    config_dict = SpinCore_pp.configuration("active.ini")
    with genesys("192.168.0.199") as gen:
        with prologix_connection() as p:
            with gigatronics(prologix_instance=p, address=7) as g:
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
                                            while dBm_setting > last_power + 3:
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
                                        print("FINALLY - SETTING TO DESIRED POWER")
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
                                            * config_dict["current_v_field_A_G"]
                                        )
                                        # ☐ TODO: this needs to be in
                                        #         active.ini, not hardcoded
                                        ramp_dt = 0.05  # Settling time at each ramping step (s)
                                        ramp_steps = I_setting * 2
                                        # ☐ TODO: here, you need some type of
                                        #         statement that throws an
                                        #         error if we are asking for an
                                        #         unreasonable current (i.e. we
                                        #         need a software interlock).
                                        #         This takes the place of
                                        #         asking the user if they are
                                        #         sure, which for a
                                        #         continuously running server
                                        #         isn't a reasonable mode of
                                        #         operation
                                        # ☐ TODO: this needs to be in
                                        #         active.ini, not hardcoded
                                        settle_initial_s = 60
                                        # ☐ TODO: we don't want to do the
                                        #         following *every* time we set
                                        #         the field.
                                        #         Rather, track a variable as
                                        #         to whether or not we have
                                        #         turned on the field, and then
                                        #         do this.  ALSO: in a server
                                        #         context, when turning on the
                                        #         PS for the first time, we
                                        #         should turn the current to
                                        #         zero.
                                        try:
                                            g.V_limit = 25.0
                                            g.output = True
                                            print("The power supply is on.")
                                        except:
                                            raise TypeError(
                                                "The power supply is not"
                                                " connected."
                                            )
                                        # ☐ TODO: we do not always want to ramp
                                        # from 0.  Rather, we should ramp from
                                        # where we are at now to where we want
                                        # to be.  This might be just one step.
                                        # {{{ Ramping up the field
                                        logging.info("Ramping up the field")
                                        for I in np.linspace(
                                            0.0, I_setting, ramp_steps
                                        ):
                                            gen.I_limit = I
                                            time.sleep(ramp_dt)
                                        # }}}
                                        # ☐ TODO: we are going to want to do
                                        #         the following more than once,
                                        #         so it probably makes sense to
                                        #         define a function (up top in
                                        #         the module) that does this --
                                        #         accepting the config dict and
                                        #         hall probe instance, or
                                        #         whatever we need.
                                        #         Then, in particular, if our
                                        #         current was already at a
                                        #         somewhat reasonable value
                                        #         (e.g. say we're doing a field
                                        #         sweep experiment)
                                        # {{{ now, adjust current_v_field_A_G
                                        #     to get the field we want,
                                        #     just once at the beginning
                                        true_B0_G = h.field.to("T").magnitude * 1e4
                                        logging.info(
                                            "adjusting current_v_field_A_G from",
                                            config_dict["current_v_field_A_G"],
                                        )
                                        config_dict["current_v_field_A_G"] *= (
                                            B0_des_G / true_B0_G
                                        )
                                        logging.info(
                                            "to",
                                            config_dict["current_v_field_A_G"],
                                            "and settling again",
                                        )
                                        # ☐ TODO: this needs to come from active.ini
                                        time.sleep(settle_initial_s)
                                        I_setting = (
                                            B0_des_G
                                            * config_dict["current_v_field_A_G"]
                                        )
                                        gen.I_limit = I_setting
                                        logging.info(
                                            "Your field is"
                                            f" {h.field.to('T').magnitude * 1e4} G, and"
                                            "the ratio of the field I want to the"
                                            " one Iget is"
                                            f" {B0_des_G / true_B0_G}\nIn other"
                                            " words, the discrepancy"
                                            f" is{true_B0_G - B0_des_G} G"
                                        )
                                        # ☐ TODO: here I would reply with the
                                        #         field too.  But see next
                                        #         comment before trying this.
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
                                        try:
                                            print(
                                                "Your field is"
                                                f" {h.field.to('T').magnitude * 1e4} G"
                                            )
                                        except:
                                            raise ValueError(
                                                "Hall probe is not connected",
                                                "or the power supply is off",
                                            )
                                    case _:
                                        raise ValueError(
                                            "I don't understand this 2 component"
                                            " command:"
                                            + str(args)
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
                                    case _:
                                        raise ValueError(
                                            "I don't understand this 1 component"
                                            " command"
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
