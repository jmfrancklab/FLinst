
# coding: utf-8

# *I would specifically propose* -- if you were to use the values of your
# two capacitances, and determined the resistance that gave you
# approximately the $Q$ value that you observe, then you should get the
# same results using the current to field conversion as you do using the
# Mims equations.
# It may be easier to look at the equivalent circuits given in
# [Poole](https://drive.google.com/open?id=1NMAvy5vup6LKWefblQmi5A6AFPLvLRxP)
# where he relates resonators of a particular $Q$ and impedance to lumped
# circuit elements.

# In[ ]:


get_ipython().magic(u'load_ext pyspecdata.ipy')
from pyspecdata import strm, gammabar_H, k_B, hbar
def mdown(x):
    import IPython.display as d
    d.display(d.Markdown(x))


# ## Physical constants

# In[ ]:


mu0 = 4*pi*1e-7 #permeability of free space in Tm/A
gamma_H = 2*pi*gammabar_H #gyromagnetic ratio for H in Hz/T
k_B = 1.38e-23 #Boltzmann constant in J/K
h = hbar*2*pi #Planck constant in Js
K = 1.12 #to adjust the pulse length's inverse (from [3.])


# ## Geometric parameters
# 
# Parameters measured on solenoid of interest (second 0.55 uH solenoid)

# In[ ]:


L = 0.55e-6 #inductance in microHenries
l = 27.48e-3 #length of coil in mm 
n = 18 #number of turns
OD = 8.25e-3 #outer diameter of coil rings in mm
thick = 1.17e-3 #thickness of wire in mm
ID = OD-(2*thick) #inner diameter of coil rings in mm


# ## Design parameters
# 
# power, impedance, temperature, etc

# In[ ]:


P = 40. #pulse power in Watts
R = 50. #resistance in Ohms
T = 298. #temperature in Kelvin
df = (1000e6-0.1e6) #bandwidth of LNA in Hz
f = 11.663e6 #resonant frequenct in Hz
omega0 = 2*pi*f
Q = 18.161 #from "20180219_findingQ.h5"
Q_SW = 0.640e6 #in Hz


# $N$: Number density of spins (2 $^1$H/water molecule)(55 mole water/Liter)($N_A$ molecules/mole)(1000 Liters/m$^3$)
# 
# to give units of $^1$H/m$^3$:

# In[ ]:


N = 2*55*6.02e23*1e3


# # Finding Pulse times for given pulse power
# 
# From [3.], filling factor $F$:
# $$F = \sqrt{\frac{V_{sample}}{V_{coil}}}$$
# 

# $$F = B_{1,avg}\sqrt{\frac{2 V_{sample} \omega}{PQ \mu}}$$

# Rearrange for B1,avg as a function of power:
# $$B_{1,avg} = F\sqrt{\frac{PQ \mu}{2 V_{sample} \omega}}$$

# In[ ]:


V_sample = pi*(5e-3/2)**2*l # replaced with 5mm diameter NMR tube
mdown("Sample volume: %.2e $m^3$ "%V_sample)
V_coil = pi*(OD/2)**2*l
mdown("Coil volume: %.2e $m^3$ "%V_coil)
F = sqrt(V_sample/V_coil)
mdown("Filling factor or F: %f"%F)
B1avg_40 = F*sqrt((P*Q*mu0)/(2*V_sample*omega0))
mdown("Average B1 field for 40 Watt pulse: %f $T$"%B1avg_40)
P_75 = 75.
B1avg_75 = F*sqrt((P_75*Q*mu0)/(2*V_sample*omega0))
mdown("Average B1 field for 75 Watt pulse: %f $T$"%B1avg_75)


# For time of 90 arbitrary pulse from [5.]:
# 
# $$t_{p} = \frac{\pi}{B_{1} \gamma_{H}} $$

# In[ ]:


tp_40 = pi/(B1avg_40*gamma_H)
mdown("Pulse time for 40 Watt pulse: %f $\mu sec$"%(tp_40*1e6))
tp_75 = pi/(B1avg_75*gamma_H)
mdown("Pulse time for 75 Watt pulse: %f $\mu sec$"%(tp_75*1e6))


# Conversion factor $\kappa$ from [3.]:
# $$\kappa = \frac{B_{1}}{\sqrt{Q P}}$$

# Using definition of filling factor from [3.]:
# $$F = \kappa \sqrt{\frac{2 V_{sample} \omega_{0}}{\mu}}$$
# $$F = \frac{B_{1}}{\sqrt{Q P}} \sqrt{\frac{2 V_{sample} \omega_{0}}{\mu}}$$
# 
# Solve for new conversion factor, magnetic field over square root of power:
# $$\frac{B_{1}}{\sqrt{P}} = F\sqrt{\frac{Q \mu_{0}}{2 V_{sample} \omega_{0}}} $$

# In[ ]:


conversion = F*sqrt(Q*mu0/(2*V_sample*omega0))
mdown(r"Conversion factor %.2e $T/\sqrt{W}$ "%conversion)
mdown(r"Conversion factor %.2f $G/\sqrt{W}$ "%(conversion*1e4))


# # Noise calculation
# From [1.]:
# $$V_{noise}^{rms} = \sqrt{4 k_{B} T R \Delta f}$$

# In[ ]:


NOISE = sqrt(4*k_B*T*R*df)
mdown(r"Vrms noise %.2e $\mu V$"%(NOISE*1e6))


# # Signal calculation

# From [3.]:
# $$V_{signal}^{rms} = \omega_{0} M \frac{B_{1}}{\sqrt{P}} V_{sample} \sqrt{R}$$
# where M:
# $$M = \frac{ N \omega_{0} \gamma_{H} (\frac{h}{2 \pi})^2 S(S+1)}{2 k_{B} T}$$

# In[ ]:


S = 0.5
M = N * omega0 * gamma_H * hbar**2 * S*(S+1) / (2*k_B*T)
R = 50. # to get the signal voltage at the 50 Ohm output of the probe
V_signal = omega0 * M * conversion * V_sample * sqrt(R)
mdown(r"Signal %.2f $\mu$V "%(V_signal/1e-6))


# Steady-state condition (eq 121a) relating power, quality factor, and cavity volume from [5.]:
# 
# $$P_{0} = \frac{V_{coil}(H_{1})^2\omega_{0}}{8 \pi Q} $$
# 
# Rearrange for magnetic field needed as a function of power:
# 
# $$H_{1} = \sqrt{\frac{P 8 \pi Q}{V_{coil} \omega_{0}}}$$
# 
# 
# Equation (136) from [5.]:
# 
# $$M_{0} = \frac{\frac{1}{3} N_{0} \mu H_{0} S(S+1)}{k T} $$
# 

# # References
# [1.] McDowell et al. (2007) 10.1016/j.jmr.2007.06.008
# 
# [2.] Hoult et al. (1976)
# 
# [3.] JMF notebook (EPR power)
# 
# [4.] Peck et al. (1995) 10.1006/jmrb.1995.1112
# 
# [5.] Mims, W.B. "Chapter 4, Electron Spin Echoes" *Electron Paramagnetic Resonance* **1972**

# In[ ]:


#Using B1 from [4.], from [1.] calculate Vrms(signal)
SIGNAL = B1avg_40*V_sample*N*gamma_H*hbar*hbar*(0.5*(1+0.5))*omega0*omega0
SIGNAL = SIGNAL/(3*k_B*T)
mdown(r"Signal %f $\mu$V "%(SIGNAL*1e6))


# In[ ]:




