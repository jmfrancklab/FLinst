
# coding: utf-8

# In[15]:

get_ipython().magic(u'load_ext pyspecdata.ipy')
from pyspecdata import strm, gammabar_H, k_B, hbar
def mdown(x):
    import IPython.display as d
    d.display(d.Markdown(x))


# In[16]:

## Physical constants




mu = 4*pi*1e-7 #[T*m/Amp]
gH = 2*pi*gammabar_H #[Hz/T]
kB = 1.381e-23 #[J/K]
hbar = 6.626e-34/2/pi #[J*s]
nuclear_spin = 0.5 #angular momentum
print gH
print gammabar_H


# In[17]:

## Solenoid geometry




length = 22.89e-3
outer_diameter = 8.25e-3
volume_coil = pi*length*(outer_diameter/2)**2 #[m**3]
print "Volume of solenoid in probe",volume_coil,"m^3"


# In[18]:

## Quality factor




f_resonant = 14.4289e6 #[Hz]
omega_resonant = f_resonant*2*pi
df = (14.8882e6 - 14.0879e6) #[Hz]
print f_resonant
print df
Q = f_resonant/df
print Q


# In[19]:

## Other parameters




pulse_power = 51.87 #[W]
temperature = 290 #[K]
resistance = 50. #[Ohms]
bandwidth = 22e6 #[Hz]
N = 2*55*6.02e23*1e3 #[1H spins/m^3]


# In[20]:

## Calculating B1




B1 = sqrt(pulse_power*Q*mu/volume_coil/2/omega_resonant)
print "Magnetic field of nutation:",B1,"Tesla"
print "Magnetic field of nutation:",B1*1e4,"Gauss"


# In[21]:

## Calculating 90-time




tau_90 = (pi/2)/B1/gH
print "Time needed for pulse to supply desired power,",tau_90,"seconds"


# In[14]:

## V_rms noise




V_noise = sqrt(4*kB*temperature*resistance*bandwidth)
print V_noise


# In[ ]:

## V_rms signal




M = N*gH*omega_resonant*hbar**2*(nuclear_spin*(nuclear_spin+1))/2/kB/temperature
print "Magnetization via Curie's Law",M




V_sample_new = pi*length*((4.93e-3-2*0.53e-3)/2)**2
V_sample_old = pi*(5e-3/2)**2*length


V_signal_old = omega_resonant*M*(B1/sqrt(pulse_power))*V_sample_old*sqrt(resistance)
print "Using previous volume, signal voltage",V_signal_old,"V_RMS"


V_signal_new = omega_resonant*M*(B1/sqrt(pulse_power))*V_sample_new*sqrt(resistance)
print "Using new volume, signal voltage",V_signal_new,"V_RMS"


# In[ ]:



