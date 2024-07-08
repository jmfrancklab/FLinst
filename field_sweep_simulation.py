from pyspecdata import *
import pprint
pp = pprint.PrettyPrinter(indent=2)
fl = figlist_var()
mpl.rcParams['image.cmap'] = 'jet'
#{{{ SNR calculation
## Physical constants
mu = 4*pi*1e-7 #[T*m/Amp]
gH = 2*pi*gammabar_H #[rad*Hz/T]
kB = 1.381e-23 #[J/K]
hbar = 6.626e-34/2/pi #[J*s]
nuclear_spin = 0.5 #angular momentum
## Solenoid geometry
length = 22.89e-3
outer_diameter = 8.25e-3
volume_coil = pi*length*(outer_diameter/2)**2 #[m**3]
print("Volume of solenoid in probe",volume_coil,"m^3")
## Quality factor
f_resonant = 14.4495e6 #[Hz]
omega_resonant = f_resonant*2*pi
df = (14.9353e6 - 14.0719e6) #[Hz]
Q = f_resonant/df
print(Q)
quit()
## Other parameters
pulse_power = 51.87 #[W]
temperature = 290 #[K]
resistance = 50. #[Ohms]
bandwidth = 22e6 #[Hz]
N = 2*55*6.02e23*1e3 #[1H spins/m^3]
M = N*gH*omega_resonant*hbar**2*(nuclear_spin*(nuclear_spin+1))/2/kB/temperature #[Magnetization]
## Calculating B1, 90-time, signal
B1 = sqrt(pulse_power*Q*mu/volume_coil/2/omega_resonant)
omega1 = B1*gH
time90 = pi/2/omega1
print(time90)
volume_sample = pi*length*((4.93e-3-2*0.53e-3)/2)**2
V_signal = omega_resonant*M*(B1/sqrt(pulse_power))*volume_sample*sqrt(resistance)
#}}}
### Where simulation begins
time_space = linspace(1e-6,5e-6,50) #Initially, I wanted 25,000 pulse lengths
#{{{ generating the frequency axis so that centers out at resonant f
f_center = f_resonant                   #center of freq axis
f_len = 100                             #want 500 frequency points
f_spacer = 10.e3                        #axis spacing of 10[kHz]
f_start = f_center - (f_len/2)*f_spacer #determine starting freq
f_space = []
for x in range(f_len):
    f_x = f_start + (x*f_spacer)
    f_space.append(f_x)
#}}}
freq_space = array(f_space)

offset_space = freq_space - f_resonant

nd_time90 = nddata((time_space),('90 time'))
nd_offset = nddata((offset_space),('offset'))
#{{{ Practice axes - save for troubleshooting
#this_t = linspace(1,26,25)
#this_f = linspace(-5,5,60)
# Practice axes, but more realistic
#this_t = linspace(1e-6,9e-6,25)
#this_f = linspace(-1e6,1e6,60)
#}}}
this_t = time_space
this_f = freq_space 

### Most important part of simulation below --
column = []
signal_array = []
b1 = sqrt(pulse_power*Q*mu/volume_coil/2/(f_resonant*2*pi))
for f in this_f:
    delta_f0 = f - f_resonant
    delta_b0 = delta_f0*2*pi/gH
    b_rot = sqrt(delta_b0**2 + b1**2) 
    argument = b1/b_rot
    angle = math.asin(argument)
    print(angle)
    column = []
    for t in this_t:
        this_b1 = b_rot*math.sin(b_rot*gH*t)
        signal = (f_resonant*2*pi)*M*(this_b1/sqrt(pulse_power))*volume_sample*sqrt(resistance)
        column.append(signal)
        print(shape(column))
        print(shape(signal_array))
    signal_array.append(column)
    print(shape(signal_array))
print(signal_array)
nd_signal = nddata(array(signal_array),['offset','90 time'])
nd_signal.setaxis('90 time',nd_time90.getaxis('90 time'))
nd_signal.setaxis('offset',nd_offset.getaxis('offset'))
print(nd_signal)
input('proceed')
nd_signal.set_units('90 time','s')
nd_signal.set_units('offset','Hz')
nd_signal.name('signal')
print(nd_signal)
print("finished")
nd_signal.reorder('90 time')
fl.next('image')
fl.image(nd_signal)
fl.show()
quit()
