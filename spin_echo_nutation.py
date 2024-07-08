from Instruments import *
from pyspecdata import *
import time
from timeit import default_timer as timer
from serial.tools.list_ports import comports
import serial
import pprint
from scipy import signal

fl = figlist_var()
#{{{ Initialize instruments
print("These are the instruments available:")
SerialInstrument(None)
print("done printing available instruments")

with SerialInstrument('GDS-3254') as s:
    print(s.respond('*idn?'))
    
with SerialInstrument('AFG-2225') as s:
    print(s.respond('*idn?'))
    #}}}
#{{{ nutation curve with spin echo
def se_nutation(freq = 14.4289e6, min_t_90, max_t_90, step, T1 = 200e-3, ph_cyc = True):
#{{{ documentation
    r'''generates spin echo (90 - delay - 180) pulse sequence, defined by
    the frequency, 90 time, and delay time, and outputs on scope.
    fr
    
    Parameters
    ==========
    freq : float

        Frequency of RF pulse; i.e., carrier frequency

    t_90 : float

        90 time of RF pulse

    d1 : float

        Delay time between 90 and 180 pulse, akin to 'tau'; at minimum, should set to deadtime. 
        This delay time is only applicable if max_delay = False.

    T1 : float

        T1 of sample, determines the burst period (i.e., the amount of time between output of pulse sequence)
        For 13 mM [NiSO4], T1 = 200ms; with this as input, the burst period is set to 1 second.

    max_delay : boolean 

        Currently only set for complex_exp waveform generation.
        If set to True, then program maximizes the delay time between the 90 pulse and the 180 pulse, which is
        constrained by the sampling rate of the arbitrary waveform on the scope.
        If set to False, then delay time between the 90 pulse and the 180 pulse
        T1 of sample, determines the burst period (i.e., the amount of time between output of pulse sequence)
        For 13 mM [NiSO4], T1 = 200ms; with this as input, the burst period is set to 1 second.
    
    complex_exp : boolean 

        If set to True, then program generates arbitrary waveform via a complex exponential. This is the only waveform that supports 
        phase cycling. This is used as of July 2018.
        If set to False, then program generates arbitrary waveform by setting the values of an array via 4-step slicing. This was
        the previous waveform used for generating pulses.

    ph_cyc : boolean

        If set to True, then program will phase shift the 180 pulse and the 90 pulse separately, capturing each shift. The phase cycle cannot
        be set through commands yet. Note that with this set to True, there is no need to call acquire.
        If set to False, then program does not phase shift; to capture signal, will need to call acquire (for field sweeps). 

    '''
    #}}}
    points_total = 4096     #[pts] total points, property of AFG
    freq_carrier = freq     #[Hz] rf pulse frequency
    rate = freq_carrier*4   #[pts/sec] AFG requires for arb waveform
    freq_sampling = 0.25    #effectively the 'step' of the time axis
    time_spacing = 1/rate   #[sec/pt] time between two points

    #{{{ calculate the maximum allowable delay, given that it must be held constant
        # for all sequences generating the nutation curve
    points_max_90 = max_t_90/time_spacing
    points_max_180 = 2*max_t_90/time_spacing
    points_max_d1 = points_total - points_max_90 - points_max_180
    t_d1 = points_max_d1*time_spacing
    #}}}

    t_90_range = linspace(min_t_90,max_t_90,step)

    # ready to start 
    start_nutation = time.time()
    for x,t_90 in enumerate(t_90_range):
        t_180 = 2*t_90
        t_total = t_90 + t_d1 + t_180

        points_90 = t_90/time_spacing
        points_d1 = t_d1/time_spacing
        points_180 = t_180/time_spacing
        points_seq = points_90 + points_d1 + points_180
        assert (points_seq < 4097), "Too many points"
        # generate waveform
        t = r_[0:int(points_seq)]
        y = exp(1j*2*pi*t[1 : -1]*freq_sampling)
        y[int(points_90) : int(points_90+points_d1)] = 0
        y[0] = 0
        y[-1] = 0

        with AFG() as a:
            a.reset()
            ch_list = [0]
            for this_ch in ch_list:
                a[this_ch].ampl = 20.e-3
                a[this_ch].digital_ndarray(y, rate=rate)
                a[this_ch].output = True
                a[this_ch].burst = True
                a.set_burst(per=d_interseq)
                a[this_ch].ampl = 10.
                if ph_cyc:
                    num_ph1_steps = 4
                    num_ph2_steps = 2
                    for ph2 in range(0,4,num_ph2_steps):
                        for ph1 in range(num_ph1_steps):
                            y_ph = y.copy()
                            y_ph[1:int(points_90)] *= exp(1j*ph1*pi/2)
                            y_ph[int(points_90+points_d1):-1] *= exp(1j*ph2*pi/2)
                            a[this_ch].ampl = 20e-3
                            a[this_ch].burst = True
                            a[thic_ch].ampl = 10
                            with GDS_scope() as g:
                                g.acquire_mode('average',2)
                                time.sleep(4*d_interseq) # 4 seconds to average
                                print("Acquiring...")
                                ch1_wf = g.waveform(ch=1)
                                ch2_wf = g.waveform(ch=2)
                                time_acq = time.time()
                                g.acquire_mode('sample')
                            if (ph1 == 0 and ph2 == 0 and x == 0):
                                t_axis = ch1_wf.getaxis('t')
                                data = ndshape([step,num_ph1_steps,num_ph2_steps,len(t_axis),2],
                                        ['t90_values','ph1','ph2','t','ch']).alloc(dtype=float64)
                                data.setaxis('t',t_axis).set_units('t','s')
                                data.setaxis('ch',r_[1,2])
                                data.setaxis('ph1',r_[0:4])
                                data.setaxis('ph2',r_[0,2])
                                data.setaxis('t90_values',t_90_range)
                            data['t90_values',t_90]['ph1':ph1]['ph2':ph2]['ch',0] = ch1_wf
                            data['t90_values',t_90]['ph1':ph1]['ph2':ph2]['ch',1] = ch1_wf
                            print("**********")
                            print("90 TIME ",t_90,",INDEX NO.",x)
                            print("ph1",ph1)
                            print("ph2",ph2)
                            print("Done acquiring") 
    data.name("this_capture")
    data.hdf5_write(date+"_"+id_string+".h5")
    return end 
#}}}

date = '180720'
id_string = 'SE_sweep_nutation'
num_cycles = 10 
t1,t2 = spin_echo(num_cycles = num_cycles)
print("Time:",t2-t1,"s")
