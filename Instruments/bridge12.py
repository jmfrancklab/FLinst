## coding: utf-8
# ## Initialization
#
# To run on a different computer, run ``jupyter notebook --ip='*'`` copy and paste address and replace ``localhost`` with
# ``jmfranck-pi2.syr.edu`` (if on the internet) or ``192.168.1.20`` (if on local network)
from serial.tools.list_ports import comports
from serial import Serial
from numpy import r_
import numpy as np
import time, winsound
from .log_inst import logger


def generate_beep(f, dur):
    # do nothing -- can be used to generate a beep, but platform-dependent
    return


class Bridge12(Serial):
    def __init__(self, *args, **kwargs):
        # Grab the port labeled as Arduino (since the Bridge12 microcontroller is an Arduino)
        cport = comports()
        if type(cport) is list and hasattr(cport[0], "device"):
            portlist = [j.device for j in comports() if "Arduino Due" in j.description]
        elif type(next(cport)) is tuple:
            logger.debug("using fallback comport method")
            portlist = [j[0] for j in comports() if "Arduino Due" in j[1]]
        else:
            raise RuntimeError("Not sure how how to grab the USB ports!!!")
        assert (
            len(portlist) == 1
        ), "I need to see exactly one Arduino Due hooked up to the Raspberry Pi"
        thisport = portlist[0]
        super().__init__(thisport, timeout=3, baudrate=115200)
        # this number represents the highest possible reasonable value for the
        # Rx power -- it is lowered as we observe the Tx values
        # 1/8/24 updated to give as a 10*dBm value
        self.safe_rx_level_int = 180  # see https://jmfrancklab.slack.com/archives/CLMMYDD98/p1704996597531449?thread_ts=1704981852.441149&cid=CLMMYDD98
        self.frq_sweep_10dBm_has_been_run = False
        self.tuning_curve_data = {}
        self._inside_with_block = False
        self.fit_data = {}
        print("init done")

    def bridge12_wait(self):
        # time.sleep(5)
        def look_for(this_str):
            for j in range(1000):
                a = self.read_until((this_str + "\r\n").encode("utf-8")).decode("utf-8")
                time.sleep(0.1)
                logger.debug("look for " + this_str + " try" + str(j + 1))
                if this_str in a:
                    logger.debug("found: " + this_str)
                    break

        look_for("MPS Started")
        print("MPS Started")
        look_for("System Ready")
        print("System Ready")
        look_for("Synthesizer detected")
        print("Synthesizer detected")
        look_for("Power updated")
        print("Power updated")
        return

    def help(self):
        self.write(b"help\r")  # command for "help"
        logger.info("after help:")
        entire_response = ""
        start = time.time()
        entire_response += self.readline()
        time_to_read_a_line = time.time() - start
        grab_more_lines = True
        while grab_more_lines:
            time.sleep(3 * time_to_read_a_line)
            more = self.read_all()
            entire_response += more
            if len(more) == 0:
                grab_more_lines = False
        logger.info(repr(entire_response))

    def wgstatus_int_singletry(self):
        return self.robust_int_response(b"wgstatus?\r")

    def wgstatus_int(self):
        "need two consecutive responses that match"
        c = self.wgstatus_int_singletry()
        d = self.wgstatus_int_singletry()
        while c != d:
            c = d
            d = self.wgstatus_int_singletry()
        return c

    def set_wg(self, setting):
        """set *and check* waveguide

        Parameters
        ==========
        s: Serial object
            gives the connection
        setting: bool
            Waveguide setting appropriate for:
            True: DNP
            False: ESR
        """
        print("SETTING WG...")
        self.write(b"wgstatus %d\r" % setting)
        self.read_until(b"Power updated\r\n")
        print("SET WG...")
        for j in range(10):
            result = self.wgstatus_int()
            if result == setting:
            print("Press a key to indicate that you have set the waveguide switch to the "
                    ("ODNP" if setting else "ESR")
                    "position")
            while True:
                winsound.Beep(260, 0.5)
                # Check if a key is pressed
                if msvcrt.kbhit():
                    msvcrt.getch()  # This consumes the key press, so the loop ends
        break
                return
        raise RuntimeError(
            "After checking status 10 times, I can't get the waveguide to change"
        )

    def ampstatus_int_singletry(self):
        return self.robust_int_response(b"ampstatus?\r")

    def ampstatus_int(self):
        "need two consecutive responses that match"
        a = self.ampstatus_int_singletry()
        b = self.ampstatus_int_singletry()
        while a != b:
            a = b
            b = self.ampstatus_int_singletry()
        return a

    def set_amp(self, setting):
        """set *and check* amplifier

        Parameters
        ==========
        s: Serial object
            gives the connection
        setting: bool
           Amplifier setting appropriate for:
            True: On
            False: Off
        """
        self.write(b"ampstatus %d\r" % setting)
        for j in range(10):
            result = self.ampstatus_int()
            if result == setting:
                return
        raise RuntimeError(
            "After checking status 10 times, I can't get the amplifier to turn on/off"
        )

    def rfstatus_int_singletry(self):
        return self.robust_int_response(b"rfstatus?\r")

    def rfstatus_int(self):
        "need two consecutive responses that match"
        f = self.rfstatus_int_singletry()
        g = self.rfstatus_int_singletry()
        while f != g:
            f = g
            g = self.rfstatus_int_singletry()
        return f

    def set_rf(self, setting):
        """set *and check* microwave power
        Parameters
        ==========
        s: Serial object
            gives the connection
        setting: bool
            Microwave Power setting appropriate for:
            True: On
            False: Off
        """
        self.write(b"rfstatus %d\r" % setting)
        for j in range(10):
            result = self.rfstatus_int()
            if result == setting:
                return
        raise RuntimeError(
            "After checking status 10 times, I can't get the mw power to turn on/off"
        )

    def power_int_singletry(self):
        return self.robust_int_response(b"power?\r")

    def power_float(self):
        return self.power_int() / 10

    def power_int(self):
        "need two consecutive responses that match"
        h = self.power_int_singletry()
        i = self.power_int_singletry()
        while h != i:
            h = i
            i = self.power_int_singletry()
        return h

    def calit_power(self, dBm):
        """This bypasses all safeties of the bridge12 and is to be used ONLY
        for running a calibration curve -- this is because we are not actually
        measuring any amplified output power, we are only looking at TX OUT. TX
        IN should not lead to anything. Be sure these are the operational
        conditions before proceeding."""
        setting = int(10 * round(dBm * 2) / 2.0 + 0.5)
        self.write(b"power %d\r" % setting)
        _ = self.readline()  # gobble the power updated statement

    def set_power(self, dBm):
        """set *and check* power.  On successful completion, set `self.cur_pwr_int` to 10*(power in dBm).

        Need to have 2 safeties for set_power:

        1. When power is increased above 10dBm, the power is not allowed to increase by more than 3dBm above the current power.
        2. When increasing the power, call the power reading function.

        Parameters
        ==========
        s: Serial object
            gives the connection
        dBm: float
            power values -- give a dBm (not 10*dBm) as a floating point number
        """
        if not self._inside_with_block:
            raise ValueError(
                "you MUST use a with block so the error handling works well"
            )
        setting = int(
            10 * round(dBm * 2) / 2.0 + 0.5
        )  # find closest 0.5 dBm, and round
        if setting > 400:
            raise ValueError(
                "You are not allowed to use this function to set a power of greater than 40 dBm for safety reasons"
            )
        elif setting < 0:
            raise ValueError("Negative dBm -- not supported")
        elif setting > 100:
            if not self.frq_sweep_10dBm_has_been_run:
                raise RuntimeError(
                    "Before you try to set the power above 10 dBm, you must first run a tuning curve at 10 dBm!!!"
                )
            if not hasattr(self, "cur_pwr_int"):
                raise RuntimeError(
                    "Before you try to set the power above 10 dBm, you must first set a lower power!!!"
                )
            if setting > 30 + self.cur_pwr_int:
                raise RuntimeError(
                    "Once you are above 10 dBm, you must raise the power in MAX 3 dB increments.  The power is currently %g, and you tried to set it to %g -- this is not allowed!\nNote that if you are running from the power control server, you shouldn't encounter this error!"
                    % (self.cur_pwr_int / 10.0, setting / 10.0)
                )
        self.write(b"power %d\r" % setting)
        self.read_until(b"Power updated\r\n")
        if setting > 0:
            self.rxpowerdbm_float()  # doing this just for safety interlock
        for j in range(10):
            result = self.power_int()
            if setting > 0:
                self.rxpowerdbm_float()  # doing this just for safety interlock
            if result == setting:
                self.cur_pwr_int = result
                return
            time.sleep(10e-3)
        raise RuntimeError(
            (
                "After checking status 10 times, I can't get the"
                "power to change: I'm trying to set to %d/10 dBm, but the Bridge12"
                "keeps replying saying that it's set to %d/10"
                "dBm"
            )
            % (setting, result)
        )

    def rxpowerdbm_float(self):
        """read the integer value for the Rx power -- loops three times to
        check a consistent Rx is being read.

        If all three tries are above safe_rx_level_int, triggers a safety interlock."""
        self.reset_input_buffer()

        def grab_consist_value():
            rx_try1 = self.robust_int_response(b"rxpowerdbm?\r")
            rx_try2 = self.robust_int_response(b"rxpowerdbm?\r")
            for j in range(20):
                rx_try3 = self.robust_int_response(b"rxpowerdbm?\r")
                if (
                    abs(rx_try1 - rx_try2) < 2
                    and abs(rx_try2 - rx_try3) < 2
                    and abs(rx_try3 - rx_try1) < 2
                ):
                    return (rx_try1 + rx_try2 + rx_try3) / 3.0
                else:
                    rx_try1, rx_try2 = rx_try2, rx_try3
            raise ValueError(
                "I tried 20 times to grab a consistent power, and could not (most recent %f, %f, %f)"
                % (rx_try1, rx_try2, rx_try3)
            )

        retval = grab_consist_value()
        assert retval < self.safe_rx_level_int, "safety interlock triggered"
        return retval / 10.0  # above is in units of 10*dBm, return as dBm

    def txpowerdbm_int_singletry(self):
        return self.robust_int_response(b"txpowerdbm?\r")

    def txpowerdbm_float(self):
        "need two consecutive responses that match"
        for j in range(3):
            # burn a few measurements
            self.txpowerdbm_int_singletry()
        h = self.txpowerdbm_int_singletry()
        i = self.txpowerdbm_int_singletry()
        while h != i:
            h = self.txpowerdbm_int_singletry()
            i = self.txpowerdbm_int_singletry()
        return float(h) / 10.0

    def calib_set_freq(self, Hz):
        """Use only for setting frequency of the Bridge12 for calibration
        curve. Based off original set_freq function."""
        setting = int(Hz / 1e3 + 0.5)
        self.write(b"freq %d\r" % (setting))

    def set_freq(self, Hz):
        """set frequency

        Parameters
        ==========
        s: Serial object
            gives the connection
        Hz: float
            frequency values -- give a Hz as a floating point number
        """
        if hasattr(self, "freq_bounds"):
            assert Hz >= self.freq_bounds[0], (
                "You are trying to set the frequency outside the frequency bounds, which are: "
                + str(self.freq_bounds)
            )
            assert Hz <= self.freq_bounds[1], (
                "You are trying to set the frequency outside the frequency bounds, which are: "
                + str(self.freq_bounds)
            )
        setting = int(Hz / 1e3 + 0.5)
        self.write(b"freq %d\r" % (setting))
        if self.freq_int() != setting:
            for j in range(10):
                result = self.freq_int()
                if result == setting:
                    return
            raise RuntimeError(
                "After checking status 10 times, I can't get the "
                "frequency to change -- result is %d setting is %d" % (result, setting)
            )

    def get_freq(self):
        return self.freq_int() * 1e3

    def freq_int(self):
        "return the frequency, in kHz (since it's set as an integer kHz)"
        return self.robust_int_response(b"freq?\r")

    def robust_int_response(self, cmd, numtries=10):
        """Flushes the buffer and sends the command/query to the B12 and looks
        for a response that it can interpret as an integer.

        Importantly, it ensures that the returned message is an
        integer and if not (implying there is junk left over in the
        buffer), it resets the input buffer and asks again until an
        integer value is received

        Parameters
        ----------
        cmd: str
            Query for the B12.  The routine handles encoding, so this is a
            normal string.
        numtries: int
            How many times should I try to get a sane response?

        Returns
        -------
        retval: int
            The value that the B12 responded with.
        """
        if self.in_waiting > 0:
            temp = self.read(self.in_waiting)
            print("WARNING, I found junk in the buffer:", temp)
        self.reset_input_buffer()
        for j in range(10):
            success = False
            self.write(cmd)
            retval = self.readline()
            if retval.startswith(b"E001"):
                print("Got error E001, trying again")
            elif len(retval) == 0:
                print("Got an empty string")
            else:
                try:
                    retval = int(retval)
                    success = True
                except:
                    print(
                        "WARNING (robust try",
                        j,
                        '): B12 is spewing garbage!!: "' + retval.decode() + '"',
                    )
            if success:
                return retval
            else:
                self.reset_input_buffer()  # we want to be able to change the power using the MPS front panel,
                #                           and when we do this, the MPS likes to spew garbage
                #                           NOTE: I can check for stuff by looking at in_waiting,
                #                                 but I need to remember that it takes time after a write
                #                                 command for stuff to move into the buffer
        raise ValueError("I tried running 10 times and couldn't get an integer!!!")

    def freq_sweep(self, freq, dummy_readings=1, fast_run=False):
        """Sweep over an array of frequencies.
        **Must** be run at 10 dBm the first time around; will fail otherwise.

        Add arrays to the `self.tuning_curve_data` dictionary,
        stored with keys XXXdBm_rx XXXdBm_tx and XXXdBm_freq
        which store the tuning curve data.

        Parameters
        ==========
        s: Serial object
            gives the connection
        freq: array of floats
            frequencies in Hz
        Returns
        =======
        rxvalues: array
            An array of floats, same length as freq, containing the receiver (reflected) power in dBm at each frequency.
        txvalues: array
            An array of floats, same length as freq, containing the transmitted power in dBm at each frequency.
        """
        self.write(b"screen 2\r")  # change to the screen that shows the reflection
        rxvalues = np.zeros(len(freq))
        txvalues = np.zeros(len(freq))
        if not self.frq_sweep_10dBm_has_been_run:
            if self.cur_pwr_int != 100:
                raise ValueError(
                    "You must run the frequency sweep for the first time at 10 dBm"
                )
        # FREQUENCY AND RXPOWER SWEEP
        for j in range(dummy_readings):
            print("*** *** ***")
            print(freq)
            print(freq[0])
            print("*** *** ***")
            self.set_freq(freq[0])  # is this what I would put here (the 'f')?
            time.sleep(10e-3)  # allow synthesizer to settle
            _ = self.txpowerdbm_float()
            _ = (
                self.rxpowerdbm_float()
            )  # 1/8/24: didn't know why this was here, probably for safety interlock
        self.reset_input_buffer()
        for j, f in enumerate(freq):
            generate_beep(500, 300)
            self.set_freq(f)  # is this what I would put here (the 'f')?
            rxvalues[j] = self.rxpowerdbm_float()
            txvalues[j] = self.txpowerdbm_float()
        if self.cur_pwr_int == 100:
            self.frq_sweep_10dBm_has_been_run = True
            # reset the safe rx level to the top of the tuning curve at 10 dBm
            # (this is the condition where we are reflecting 10 dBm onto the Rx diode)
            # self.safe_rx_level_int = int(10*rxvalues.max())
        sweep_name = "%gdBm" % (self.cur_pwr_int / 10.0)
        self.tuning_curve_data[sweep_name + "_tx"] = txvalues
        self.tuning_curve_data[sweep_name + "_rx"] = rxvalues
        self.tuning_curve_data[sweep_name + "_freq"] = freq
        self.last_sweep_name = sweep_name
        return rxvalues, txvalues

    def lock_on_dip(
        self,
        ini_range=(9.81e9, 9.83e9),
        ini_step=0.5e6,  # should be half 3 dB width for Q=10,000
        dBm_increment=3,
        n_freq_steps=15,
    ):
        """
        1.  Retrieves the 10 dBm if it has been run, or runs one if it has not.
        2.  Makes sure that the first point of the tuning curve gives a
            reflection that's high enough (i.e. that we're not starting in the
            middle of the dip)
        3.  Make sure that we actually see a *dip* in the middle.

            For this and the previous step, we use the middle of the middle of
            the y-axis values (which we call the "midpoint") -- the dip is the stuff
            that falls under the "midpoint"
        4.  Run a new frequency sweep over just the dip.
        5.  Call the zoom function to zoom in on the dip.
        """
        wg_engaged = False
        while not wg_engaged:
            if not self.frq_sweep_10dBm_has_been_run:
                self.set_wg(True)  # If the dip fails wg_engaged will be False
                # and it will loop back to here to try again
                self.set_rf(True)
                self.set_amp(True)
                freq = r_[ini_range[0] : ini_range[1] : ini_step]
                logger.info(
                    "ini range: " + str(ini_range) + "ini step: " + str(ini_step)
                )
                logger.info("Did not find previous 10 dBm run, running now")
                self.set_power(10.0)
                rx, tx = self.freq_sweep(freq)
            rx_dBm, freq = [
                self.tuning_curve_data["%gdBm_%s" % (10.0, j)] for j in ["rx", "freq"]
            ]
            rx_midpoint = (max(rx_dBm) + min(rx_dBm)) / 2.0
            # is the first rx_dBm higher than the midpoint (rx_dBm of
            # dip/2)? If not this means we are not looking at a
            # dip - ex. if the wg didn't switch on our rx_dBm would
            # be a straight line and we would not have a dip
            over_bool = (
                rx_dBm > rx_midpoint
            )  # Contains False everywhere rx_dBm is under
            if over_bool[0]:
                wg_engaged = True
            else:
                # if the dip doesn't look good,
                # flag an error so that we need
                # to try to reengage the wg.
                result = input(
                    "Couldn't find the midpoint; maybe the wg didn't turn on completely. If you'd like me to try again type 'y', if not type 'n' or CTRL-C"
                )
                if result.lower().startswith("y"):
                    wg_engaged = False
                    self.frq_sweep_10dBm_has_been_run = False # we don't trust the 10dBm guy that was run
                else:
                    self.set_rf(False)
                    self.set_wg(False)
                    raise ValueError(
                        "The reflection of the first point is the same or lower than the rx_dBm of the dip, which doesn't make sense -- check %gdBm_%s"
                        % (10.0, rx_dBm)
                    )
        assert (
            self.frq_sweep_10dBm_has_been_run
        ), "I should have run the 10 dBm curve -- not sure what happened"
        over_diff = r_[
            0, np.diff(np.int32(over_bool))
        ]  # should indicate whether this position has lifted over (+1) or dropped under (-1) the midpoint
        over_idx = r_[0 : len(over_diff)]
        # store the indices at the start and stop of a dip
        start_dip = (
            over_idx[over_diff == -1] - 1
        )  # because this identified the point *after* the crossing
        stop_dip = over_idx[over_diff == 1]
        # be sure to check for the condition where we end on a dip
        # i.e., if we find more than one -1 to +1 region in over_diff
        if len(stop_dip) < len(start_dip) and stop_dip[-1] < start_dip[-1]:
            stop_dip = r_[stop_dip, over_idx[-1]]  # end on a dip
        if len(stop_dip) != len(start_dip):
            raise ValueError(
                "the dip starts and stops don't line up, and I'm not sure why!!"
            )
        largest_dip_idx = (stop_dip - start_dip).argmax()
        if (largest_dip_idx == len(start_dip) - 1) and (stop_dip[-1] == over_idx[-1]):
            raise ValueError(
                "The trace ends in the largest dip -- this is not allowed -- check %gdBm_%s"
                % (10.0, "rx")
            )
        self.set_power(11.0)  # move to 11 dBm, just to distinguish the trace name
        self.freq_bounds = freq[
            r_[start_dip[largest_dip_idx], stop_dip[largest_dip_idx]]
        ]
        freq_axis = r_[self.freq_bounds[0] : self.freq_bounds[1] : 15j]
        print("*** *** *** *** ***")
        print(freq_axis)
        print("*** *** *** *** ***")
        rx_dBm, tx = self.freq_sweep(freq_axis, fast_run=True)
        return self.zoom(dBm_increment=2, n_freq_steps=n_freq_steps)

    def zoom(self, dBm_increment=2, n_freq_steps=15):
        """
        1.  Pull the last frequency sweep that was run, and fit it to a 2^nd^ order polynomial:
            :math:`rx(\\nu) = a+b\\nu+c\\nu^2`
        2.  Use the polynomial to determine the center frequency (:math:`-\\frac{b}{2c}`).
        3.  Find the roots of :math:`rx(\\nu)-rx_{target}`, where :math:`rx_{target}` gives
            the rx reading, at the current power setting, that we predict will correspond to
            the max "safe" level (`safe_rx`) of the rx *after* we have increased by :math:`dBm_{increment}`
            -- *i.e.* this targets the result noted in step #4
        4.  Run a new frequency sweep between the two frequencies where we predict :math:`rx(\\nu)` to be equal to :math:`rx_{safe}`.
            **If everything went well, the new reflection profile will run over a more limited (zoomed) frequency range,
            starting with a reflection profile corresponding to approximately `safe_rx`, falling to a minimum reflection
            at `min_f`, and rise back to approximately `safe_rx`**

        Return
        ======
        rx: array
            the rx readings of the zoomed frequency sweep conducted at current power + dBm_increment
        tx: array
            the tx readings of the zoomed frequency sweep conducted at current power + dBm_increment
        min_f: float
            the frequency at which the zoomed frequency sweep is minimized
        """
        assert (
            self.frq_sweep_10dBm_has_been_run
        ), "You're trying to run zoom before you ran a frequency sweep at 10 dBm -- something is wonky!!!"
        assert hasattr(
            self, "freq_bounds"
        ), "you probably haven't run lock_on_dip, which you need to do before zoom"
        # {{{ fit the mV values
        # start by pulling the data from the last tuning curve
        rx, tx, freq = [
            self.tuning_curve_data[self.last_sweep_name + "_" + j]
            for j in ["rx", "tx", "freq"]
        ]
        p = np.polyfit(freq, rx, 2)
        c, b, a = p
        # polynomial of form a+bx+cx^2
        self.fit_data[self.last_sweep_name + "_func"] = lambda x: a + b * x + c * x**2
        self.fit_data[self.last_sweep_name + "_range"] = freq[r_[0, -1]]
        # the following should be decided from doing algebra (I haven't double-checked them)
        center = -b / 2 / c
        logger.info("Predicted center frequency: " + str(center * 1e-9))
        # }}}
        # {{{ use the parabola fit to determine the new "safe" bounds for the next sweep
        safe_rx = 7.0  # dBm, setting based off of values seeing in tests
        a_new = a - (safe_rx - dBm_increment)  # following the
        #                                     docstring
        #                                     above the
        #                                     (safe_rx-dBm_increment
        #                                     is the target
        #                                     rx before stepping
        #                                     up in power
        safe_crossing = (
            (-b + r_[-np.sqrt(b**2 - 4 * a_new * c), np.sqrt(b**2 - 4 * a_new * c)])
            / 2
            / c
        )
        safe_crossing.sort()
        start_f, stop_f = safe_crossing
        info_str = "dB value should be %g at %g and %g" % (safe_rx, start_f, stop_f)
        if start_f < self.freq_bounds[0]:
            start_f = self.freq_bounds[0]
            info_str += ", leaving start_f at %g" % start_f
        if stop_f > self.freq_bounds[1]:
            stop_f = self.freq_bounds[1]
            info_str += ", leaving stop_f at %g" % stop_f
        logger.info(info_str)
        # }}}
        # {{{ run the frequency sweep with the new limits
        freq = np.linspace(start_f, stop_f, n_freq_steps)
        self.set_power(dBm_increment + self.cur_pwr_int / 10.0)
        # with the new time constant added for freq_sweep, should we eliminate fast_run?
        rx, tx = self.freq_sweep(freq, fast_run=True)
        # }}}
        min_f = freq[rx.argmin()]
        if abs(center - min_f) > 0.2e6:
            center = min_f
            print(
                "WARNING: The min Rx is measured at %d "
                "but the polynomial shows the center "
                "should be at %d " % (min_f, center)
            )
        self.set_freq(center)
        return rx, tx, center

    def __enter__(self):
        self.bridge12_wait()
        self._inside_with_block = True
        return self

    def soft_shutdown(self):
        """do everything to shut the B12 down, but don't break out of the
        with block or close the USB connection"""
        self.set_power(0)
        self.set_rf(False)
        self.set_amp(False)
        self.set_wg(False)
        self.frq_sweep_10dBm_has_been_run = False
        del self.freq_bounds
        return

    def safe_shutdown(self):
        print("Entering safe shut down...")
        try:
            self.set_power(0)
        except Exception as e:
            print(
                "error on standard shutdown during set_power -- running fallback shutdown"
            )
            print("original error:")
            print(e)
            self.write(b"power %d\r" % 0)
            self.readline()  # gobble power string
            self.write(b"rfstatus %d\r" % 0)
            self.write(b"wgstatus %d\r" % 0)
            self.close()
            return
        try:
            self.set_rf(False)
            self.set_amp(False)
        except Exception as e:
            print(
                "error on standard shutdown during set_rf -- running fallback shutdown"
            )
            print("original error:")
            print(e)
            self.write(b"power %d\r" % 0)
            self.readline()  # gobble power string
            self.write(b"rfstatus %d\r" % 0)
            self.write(b"wgstatus %d\r" % 0)
            self.close()
            return
        try:
            self.set_wg(False)
        except Exception as e:
            print(
                "error on standard shutdown during set_wg -- running fallback shutdown"
            )
            print("original error:")
            print(e)
            self.write(b"power %d\r" % 0)
            self.readline()  # gobble power string
            self.write(b"rfstatus %d\r" % 0)
            self.write(b"wgstatus %d\r" % 0)
            self.close()
            return
        self.close()
        return

    def __exit__(self, exception_type, exception_value, traceback):
        if exception_type:
            print("exception type", exception_type)
            self.safe_shutdown()
        else:
            self.safe_shutdown()
        return
