from Instruments import GDS_scope
import os
import SpinCore_pp as spc
from datetime import datetime
import pyspecdata as psd
import numpy as np

my_exp_type = "test_equipment"
assert os.path.exists(psd.getDATADIR(exp_type=my_exp_type))
# {{{ import acquisition parameters
config_dict = spc.configuration("active.ini")
(
    nPoints,
    config_dict["SW_kHz"],
    config_dict["acq_time_ms"],
) = spc.get_integer_sampling_intervals(
    config_dict["SW_kHz"], config_dict["acq_time_ms"]
)
# }}}
sqrt_P = config_dict["amplitude"] * np.sqrt(75)  # we have a 75 W amplifier
prog_beta = np.linspace(10, 70, 50, endpoint=False)
prog_p90s = prog_beta / sqrt_P
# {{{ add file saving parameters to config dict
config_dict["type"] = "pulse_calib"
config_dict["date"] = datetime.now().strftime("%y%m%d")
config_dict["misc_counter"] += 1
# }}}
tx_phases = np.r_[0.0, 90.0, 180.0, 270.0]
Rx_scans = 1
# {{{ set up settings for GDS
with GDS_scope() as gds:
    gds.reset()
    gds.CH2.disp = True
    gds.write(":CHAN1:DISP OFF")
    gds.write(":CHAN2:DISP ON")
    gds.write(":CHAN3:DISP OFF")
    gds.write(":CHAN4:DISP OFF")
    gds.CH2.voltscal = 100e-3  # set voltscale to 100 mV
    gds.timescal(20e-6, pos=0)  # set timescale to 20 us
    gds.write(":TIM:MOD WIND")
    gds.write(":CHAN2:IMP 5.0E+1")  # set impedance to 50 ohm
    gds.write(":TRIG:SOUR CH2")
    gds.write(":TRIG:MOD NORMAL")  # set trigger mode to normal
    gds.write(":TRIG:HLEV 7.5E-2")  # used in gds_for_tune which seems reasonable
    # }}}
    for idx, p90 in enumerate(prog_p90s):
        spc.configureTX(
            config_dict["adc_offset"],
            config_dict["carrierFreq_MHz"],
            tx_phases,
            config_dict["amplitude"],
            nPoints,
        )
        acq_time = spc.configureRX(
            config_dict["SW_kHz"], nPoints, Rx_scans, config_dict["nEchoes"], 1
        )  # Not phase cycling so setting nPhaseSteps to 1
        config_dict["acq_time_ms"] = acq_time
        spc.init_ppg()
        spc.load(
            [
                ("marker", "thisstart", 1),
                ("phase_reset", 1),
                ("delay_TTL", 1.0),
                ("pulse_TTL", p90, 0),
                ("delay", config_dict["deadtime_us"]),
                ("acquire", config_dict["acq_time_ms"]),
                ("delay", config_dict["repetition_us"]),
                ("jumpto", "thisstart"),
            ]
        )
        spc.stop_ppg()
        spc.runBoard()
        calib_data = np.concat([gds.waveform(ch=2)], "ch").reorder("t")
        if idx == 0:
            p90s = ((psd.ndshape(calib_data)) + ("p_90", len(prog_p90s))).alloc(
                dtype=np.float64
            )
            p90s.setaxis("t", calib_data.getaxis("t")).set_units("t", "s")
            p90s.setaxis("ch", calib_data.getaxis("ch"))
        p90s["p_90", idx] = calib_data
        spc.stopBoard()
data = p90s["ch", 0]
data.set_units("t", "s")
data.set_prop("set_p90s", prog_p90s)
data.set_prop("set_beta", prog_beta)
data.set_prop("acq_params", config_dict.asdict())
config_dict = spc.save_data(data, my_exp_type, config_dict, "misc")
config_dict.write()
# {{{ calculate actual beta
measured_betas = []
for j in range(len(data.getaxis('p_90'))):
    s = data['p_90',j]
    s *= 101 # attenuation ratio
    s /= np.sqrt(2) #Vrms
    s /= np.sqrt(50) # V/sqrt(R) = sqrt(P)
    with psd.figlist_var() as fl:
        fl.basename = "$\Beta$ set to %s"%str(s.get_prop('set_beta')[j])
        fl.next(fl.basename)
        fl.plot(s, alpha = 0.2, color = 'blue')
        # {{{ make analytic
        s.ft('t',shift = True)
        s =s['t':(0,None)]
        s *= 2
        s['t':0] *= 0.5
        s.ift('t')
        # }}}
        # {{{ frequency filter
        s.ft('t')
        s['t':(0,8e6)] *= 0
        s['t':(24e6,None)] *= 0
        s.ift('t')
        # }}}
        fl.plot(s, alpha = 0.5, color = 'orange')
        s = abs(s)
        fl.plot(s, alpha = 0.5, color = 'red')
        pulse_range = s.contiguous(lambda x: x> 0.1*x.data.max())
        beta_actual = s['t':pulse_range].integrate('t').item()
        plt.axvline(pulse_range[0], ls = ":")
        plt.axvline(pulse_range[-1], ls = ":")
        measured_betas.append(beta_actual)
    fl.next('programmed vs measured beta')
    fl.plot(s.get_prop('set_beta'),measured_betas,'o')
    plt.xlabel('programmed $\Beta$ / $\mathrm{\mu s \sqrt{W}}$')
    plt.ylabel('measured $\Beta$ / $\mathrm{\mu s \sqrt{W}}$')
