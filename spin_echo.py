from Instruments import *
from winsound import *
from pyspecdata import *
import time
from timeit import default_timer as timer
from serial.tools.list_ports import comports
import serial
import pprint
from scipy import signal

Beep(7000,3000)
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
#{{{ spin echo function with phase cycling capability
def spin_echo(num_cycles, freq=14.46e6, p90=0.9e-6, d1=27.0e-6, T1=200e-3, max_delay=True, complex_exp=True, ph_cyc=True, field_sweep=False):
#{{{ documentation
    r'''generates spin echo (90 - delay - 180) pulse sequence, defined by
    the frequency, 90 time, and delay time, and outputs on scope.
    fr
    
    Parameters
    ==========
    freq : float

        Frequency of RF pulse; i.e., carrier frequency

    p90 : float

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
#{{{ calculating parameters for arbitrary waveform
    d_interseq = 5*T1       #[sec] time between sequence trigger 
    #{{{ this generates spin echo via complex exponential
    if complex_exp:
        freq_carrier = freq     #[Hz] rf pulse frequency
        points_total = 4096     #[pts] total points, property of AFG
        rate = freq_carrier*4   #[pts/sec] AFG requires for arb waveform
        time_spacing = 1/rate   #[sec/pt] time between two points
        time_total = time_spacing * points_total #[sec]
        t_90 = p90              #[sec] pulse length of 90
        t_180 = 2*t_90          #[sec] pulse length of 180
        points_90 = t_90/time_spacing #[pts] points in 90
        points_180 = t_180/time_spacing #[pts] points in 180
        if not max_delay:
            t_d1 = d1
            points_d1 = t_d1/time_spacing
            points_total = points_90 + points_d1 + points_180
        if max_delay:
            points_d1 = points_total - points_90 - points_180
            t_d1 = points_d1*time_spacing
        time_sequence = t_90 + t_d1 + t_180
        points_sequence = points_90 + points_d1 + points_180
        assert points_sequence < 4097
        #{{{ generating the arbitrary waveform
        t = r_[0:int(points_total)]
        freq_sampling = 0.25
        y = exp(1j*2*pi*t[1 : -1]*freq_sampling)
        y[int(points_90) : int(points_90+points_d1)] = 0
        y[0] = 0
        y[-1] = 0
        #}}}
    #}}}
    #{{{ this generates spin echo via alternating array (previous method)
    if not complex_exp:
        rate = freq*4                                           # rate set on AFG
        t_seq = p90 + d1 + 2*p90                                # time length of entire pulse sequence
        pts_seq = int(t_seq*rate/4 + 0.5)*4                     # no. points needed for this time length at given rate
        t_sp = t_seq/pts_seq                                    # time between each point in sequence
        pts_p90 = int(p90/t_sp/4 + 0.5)*4                       # no. points needed for 90 pulse (fit to integer of 4)
        pts_d1 = int(d1/t_sp/4 + 0.5)*4                         # no. points needed for tau (90-180 delay) (int of 4)
        pts_p180 = int(2*p90/t_sp/4 + 0.5)*4                    # no. points needed for 180 pulse (int of 4)
        pts_seq = int((pts_p90 + pts_d1 + pts_p180)/4 + 0.5)*4  # no. points for entire sequence as int of 4 
        assert pts_seq < 4097                                   # no. points total must be less than 4097
        #{{{ generating the arbitrary waveform
        y = zeros(pts_seq)
        y[0::4] = 0
        y[1::4] = 1
        y[2::4] = 0
        y[3::4] = -1
        y[-1] = 0
        y[pts_p90:(pts_seq-pts_p180)] = 0
        #}}}
    #}}}
#}}}
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
            #{{{ for phase cycling
            if ph_cyc:
                num_ph1_steps = 4 
                num_ph2_steps = 2
                start_ph = time.time()
                timer_index = 0
                for x in range(num_cycles):
                    if field_sweep:
                        Beep(7000,1000)
                        input('Update field, then continue')
                    for ph2 in range(0,4,num_ph2_steps):
                        for ph1 in range(num_ph1_steps):
                            y_ph = y.copy()
                            y_ph[1:int(points_90)] *= exp(1j*ph1*pi/2)
                            y_ph[int(points_90+points_d1):-1] *= exp(1j*ph2*pi/2)
                            a[this_ch].ampl = 20e-3
                            try :
                                a[this_ch].digital_ndarray(y_ph.real, rate=rate)
                            except :
                                print("Entering except statement...")
                                time.sleep(25)
                                a[this_ch].digital_ndarray(y_ph.real, rate=rate)
                            a[this_ch].burst = True
                            a[this_ch].ampl = 10
                            with GDS_scope() as g:
                                g.acquire_mode('average',2)
                                time.sleep(4*d_interseq)
                                print("Acquiring...")
                                ch1_wf = g.waveform(ch=1)
                                ch2_wf = g.waveform(ch=2)
                                time_acq = time.time()
                                this_time = int(time_acq - start_ph)
                                g.acquire_mode('sample')
                            #{{{ set up the nddata at the very beginning of the phase cycle
                            if (ph1 == 0 and ph2 == 0 and x == 0):
                                # initialize 'timer' axis to record time of each capture
                                timer_axis = empty(num_cycles*num_ph1_steps*num_ph2_steps)
                                t_axis = ch1_wf.getaxis('t')
                                data = ndshape([num_cycles,4,2,len(t_axis),2],
                                        ['full_cyc','ph1','ph2','t','ch']).alloc(dtype=float64)
                                data.setaxis('t',t_axis).set_units('t','s')
                                data.setaxis('ch',r_[1,2])
                                data.setaxis('ph1',r_[0:4])
                                data.setaxis('ph2',r_[0,2])
                                data.setaxis('full_cyc',empty(num_cycles))
                                #}}}
                            timer_axis[timer_index] = this_time
                            data['full_cyc',x]['ph1':ph1]['ph2':ph2]['ch',0] = ch1_wf
                            # alternative is to do ['ph1',ph1]['ph2',ph2/2]
                            data['full_cyc',x]['ph1':ph1]['ph2':ph2]['ch',1] = ch2_wf
                            # stores time of the entire cycle (overwrites until the last cyc step)
                            data.getaxis('full_cyc')[x] = timer_axis[timer_index]
                            print("**********")
                            print("CYCLE NO. INDEX",x)
                            print("ph1",ph1)
                            print("ph2",ph2)
                            print("**********")
                            print("Done acquiring")
                            print("*** PRINTING TIMER AXIS ***")
                            print(timer_axis)
                            timer_index += 1
            #}}}
    print("*** *** *** PRINTING FINAL TIMER AXIS *** *** ***")
    print(timer_axis)
    data.name("this_capture")
    data.hdf5_write(date+"_"+id_string+".h5")
    time_data = nddata(timer_axis,[-1],['t']).labels('t',r_[0:len(timer_axis)])
    time_data.name('timing_data')
    time_data.hdf5_write(date+"_"+id_string+".h5")
    end_ph = time.time() 
    return start_ph,end_ph 
#}}}
#{{{ nutation function increments t90 over specified range in spin echo 
def nutation(t_90_range, spin_echo = False, freq = 14.46e6, T1 = 200e-3):
#{{{ documentation
    r'''essentially a modification to the spin_echo(), but with enough changes to warrant
    separate function for now. Sweeps through a range of 90 times and generates a spin echo 
    for each using the same interpulse delay. Phase cycles through each pulse sequence. Saves 
    data to one node in an h5 file as a multidimensional nddata.

    Currently user must define the 90 time within the function.
    
    Parameters
    ==========
    t_90_range : ndarray

        A list of the desired 90-pulse lengths e.g., linspace(1e-6,10e-6,5)

    spin_echo : bool

        If True, pulse sequence is a spin echo.
        If False, pulse sequence is a single 90.

    freq : float

        Frequency of RF pulse; i.e., carrier frequency

    T1 : float

        T1 of sample, determines the burst period (i.e., the amount of time between output of pulse sequence)
        For 13 mM [NiSO4], T1 = 200ms; with this as input, the burst period is set to 1 second.

    '''
    #}}}
    t_90_range  = t_90_range # range of 90 times
    d_interseq = 5*T1       #[sec] time between sequence trigger 
    freq_carrier = freq     #[Hz] rf pulse frequency
    points_total = 4096     #[pts] total points, property of AFG
    rate = freq_carrier*4   #[pts/sec] AFG requires for arb waveform
    time_spacing = 1/rate   #[sec] time between points  
    time_total = time_spacing * points_total #[sec] total time of sequence, allowed by AFG
    # taking max 90 time
    t_90 = t_90_range[-1]
    points_90 = t_90/time_spacing
    if not spin_echo:
        assert (points_90 < 4097) 
    #{{{ For spin echo, calculating maximum interpulse delay, thereby setting 'tau'
        # 'interpulse' signifies from end of 90 to start of 180
        # 'tau' signifies the time interval [2t_90/pi , interpulse+t_90]
        # formally, [2t_90/pi , interpulse+t_180/2]
        # tau is defined in Cavanagh, Chp 4
    if spin_echo:
        t_180 = 2*t_90          
        t_tau = time_total - t_90 - t_180    # this must be held constant
        t_correction = (2*t_90/pi) + (t_180/2)
        t_interpulse = t_tau - t_correction    # decrease this until tau = constant
        print(t_tau)
        print(t_correction)
        print(t_interpulse)
        print("DETERMINING TAU...")
        points_180 = t_180/time_spacing 
        points_tau = t_tau/time_spacing
        points_correction = t_correction/time_spacing
        points_interpulse = t_interpulse/time_spacing
        print(points_tau)
        print(points_correction)
        print(points_interpulse)
        time_sequence = t_90 + t_interpulse + t_180
        points_sequence = points_90 + points_interpulse + points_180
        print(time_sequence)
        print(points_sequence) # needs to be less than 4097
        assert (points_sequence < 4097)
        #}}}
    for i,t_90 in enumerate(t_90_range):
        print("*** *** ENTERING INDEX %d *** ***"%i)
        t_90 = t_90
        points_90 = t_90/time_spacing
        print("LENGTH OF 90 PULSE:",t_90)
        #{{{ if single 90 pulse sequence
        if not spin_echo:
            points_seq = points_90
            print("LENGTH OF PULSE SEQUENCE:",t_90)
            print("POINTS IN 90 PULSE:",points_90)
            print("POINTS IN PULSE SEQUENCE:",points_90)
            #}}}
        #{{{ if spin echo pulse sequence
        if spin_echo:
            t_180 = 2*t_90
            t_correction = ((2/pi)*t_90) + 0.5*t_180
            t_interpulse = t_tau - t_correction
            t_total = t_90 + t_interpulse + t_180
            print("LENGTH OF 180 PULSE:",t_180)
            print("LEGNTH OF DELAY:",t_interpulse)
            print("LENGTH OF TAU:",t_tau)
            print("LENGTH OF PULSE SEQUENCE:",t_total)
            points_interpulse = t_interpulse/time_spacing
            points_180 = t_180/time_spacing
            points_seq = points_90 + points_interpulse + points_180
            print("POINTS IN 90 PULSE",points_90)
            print("POINTS IN 180 PULSE",points_180)
            print("POINTS IN DELAY",points_interpulse)
            print("POINTS IN TAU",points_interpulse+t_correction/time_spacing)
            print("POINTS IN SEQUENCE:",points_seq)
            #}}}
        print("*** *** GENERATING ARB WAVEFORM *** ***")
       #generating the arbitrary waveform
        t = r_[0 : int(points_seq)]
        freq_sampling = 0.25
        y = exp(1j*2*pi*t[1 : -1]*freq_sampling)
        if spin_echo:
            y[int(points_90) : int(points_90+points_interpulse)] = 0
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
                num_ph1_steps = 4 
                num_ph2_steps = 2
                #{{{ if single 90 pulse sequence
                if not spin_echo:
                    for ph1 in range(num_ph1_steps):
                        y_ph = y.copy()
                        y_ph[1:int(points_90)] *= exp(1j*ph1*pi/2)
                        a[this_ch].ampl = 20e-3
                        a[this_ch].digital_ndarray(y_ph.real, rate=rate)
                        a[this_ch].burst = True
                        a[this_ch].ampl = 10
                        with GDS_scope() as g:
                            #g.acquire_mode('average',2)
                            time.sleep(4*d_interseq)
                            print("**********")
                            print("ACQUIRING PH1",ph1)
                            print("**********")
                            ch1_wf = g.waveform(ch=1)
                            ch2_wf = g.waveform(ch=2)
                            #g.acquire_mode('sample')
                            if (ph1 == 0 and i == 0):
                                t_axis = ch1_wf.getaxis('t')
                                data = ndshape([len(t_90_range),4,len(t_axis),2],['t_90','ph1','t','ch']).alloc(dtype=float64)
                                data.setaxis('t',t_axis).set_units('t','s')
                                data.setaxis('ch',r_[1,2])
                                data.setaxis('ph1',r_[0:4])
                                data.setaxis('t_90',empty(len(t_90_range)))
                            data['t_90',i]['ph1':ph1]['ch',0] = ch1_wf
                            data['t_90',i]['ph1':ph1]['ch',1] = ch2_wf
                            data.getaxis('t_90')[i] = t_90
                            print("DONE ACQUIRING")
                            #}}}
                #{{{ if spin echo pulse sequence
                if spin_echo:
                    for ph2 in range(0,4,num_ph2_steps):
                        for ph1 in range(num_ph1_steps):
                            y_ph = y.copy()
                            y_ph[1:int(points_90)] *= exp(1j*ph1*pi/2)
                            y_ph[int(points_90+points_interpulse):-1] *= exp(1j*ph2*pi/2)
                            a[this_ch].ampl = 20e-3
                            a[this_ch].digital_ndarray(y_ph.real, rate=rate)
                            a[this_ch].burst = True
                            a[this_ch].ampl = 10
                            with GDS_scope() as g:
                                if (ph1 == 0 and ph2 == 0):
                                    Beep(9200,2000)
                                g.acquire_mode('average',2)
                                time.sleep(4*d_interseq)
                                print("**********")
                                print("ACQUIRING PH1",ph1,"PH2",ph2)
                                print("**********")
                                ch1_wf = g.waveform(ch=1)
                                ch2_wf = g.waveform(ch=2)
                                g.acquire_mode('sample')
                                if (ph1 == 0 and ph2 == 0 and i == 0):
                                    t_axis = ch1_wf.getaxis('t')
                                    data = ndshape([len(t_90_range),4,2,len(t_axis),2],['t_90','ph1','ph2','t','ch']).alloc(dtype=float64)
                                    data.setaxis('t',t_axis).set_units('t','s')
                                    data.setaxis('ch',r_[1,2])
                                    data.setaxis('ph1',r_[0:4])
                                    data.setaxis('ph2',r_[0,2])
                                    data.setaxis('t_90',empty(len(t_90_range)))
                                data['t_90',i]['ph1':ph1]['ph2':ph2]['ch',0] = ch1_wf
                                data['t_90',i]['ph1':ph1]['ph2':ph2]['ch',1] = ch2_wf
                                data.getaxis('t_90')[i] = t_90
                                print("DONE ACQUIRING")
                                #}}}
                    Beep(11000,2000)
    print("*** DATA COLLECTION FINISHED ***")
    data.name("this_capture")
    data.hdf5_write(date+"_"+id_string+".h5")
    return
#}}}
date = '181109'
#id_string = 'nutation_2'
id_string = 'spin_echo'
num_cycles = 1 
t1,t2 = spin_echo(num_cycles = num_cycles)
#t_90_range = linspace(0.5e-6,3.0e-6,25,endpoint=False)
#nutation(t_90_range, spin_echo=True)

