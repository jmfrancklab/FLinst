
# coding: utf-8

# # For Probe v1.0

# In[ ]:


get_ipython().magic(u'load_ext pyspecdata.ipy')
from pyspecdata import strm, gammabar_H, k_B, hbar
def mdown(x):
    import IPython.display as d
    d.display(d.Markdown(x))


# [1.] McDowell et al. (2007), [2.] Hoult et al. (1976), and [3.] JMF notebook.
# More recently [4.] Peck et al. (1995)
# [1.] 10.1016/j.jmr.2007.06.008
# [4.] 10.1006/jmrb.1995.1112 
# 
# ## Physical constants

# In[ ]:


mu0 = 4*pi*1e-7 #permeability of free space in Tm/A
gamma_H = 2*pi*gammabar_H #gyromagnetic ratio for H in Hz/T
k_B = 1.38e-23 #Boltzmann constant in J/K
h = hbar*2*pi #Planck constant in Js


# ## Geometric parameters
# 
# Parameters measured on solenoid of interest (second 0.55 uH solenoid)

# In[ ]:


L = 0.55e-6 #inductance in microHenries
l = 22.89e-3 #length of coil in mm
OD = 8.25e-3 #outer diameter of coil rings in mm
thick = 1.17e-3 #thickness of wire in mm
CD = OD-thick
tube_ID = 4.93e-3


# ## Design parameters
# 
# power, impedance, temperature, etc

# In[ ]:


P = 51.8 #pulse power in Watts
R = 50. #resistance in Ohms
Q = 18. # actually measure now
omega0 = 2*pi*14.4289e6
t90 = 7.45e-6


# # What is the actual conversion Factor
# so that we can compare to prediction, below
# 
# recall that $B_{1,rot} = \frac{1}{2} B_{1,lab\;frame}$ therefore requires multiplication by a factor of 2 coming to get correct conversion factor

# In[ ]:


nu1 = 1./(4*t90)
mdown((r'$\omega_1/2\pi=%0.1f$ kHz'%(nu1/1e3)))
B1_rotfr = nu1/gammabar_H
mdown(r'$B_1=%0.2e\;\text{T}$'%B1_rotfr)
B1_lf = B1_rotfr*2 # to convert to the lab frame
c_exp = B1_lf/sqrt(P)
mdown(r'$c=%0.2e\;\text{T}/\sqrt{\text{W}}$'%c_exp)


# # Use Mims to Calculate the Conversion Factor
# 
# We rearrange Eq. 9 from [3.]:
# $$F =
# B_{1,avg}
# \sqrt{
#     \frac{2 V_{sample} \omega
#     }{PQ \mu}
# }$$
# to get
# $$\frac{B_{1,avg}}{\sqrt{P}} = F\sqrt{\frac{Q \mu}{2 V_{sample} \omega}}$$
# Under these circumstances, it should be pretty reasonable to substitue $F = \sqrt{V_{sample}/V_c} \rightarrow \sqrt{\eta}$.
# 
# I think, *btw*, that it would probably be good to request the Mims chapter referenced in [3.] $\rightarrow$ ILL would probably send a PDF.

# In general, it's better to use longer and more clear/descriptive
# variable names $\rightarrow$ especially when you're using vim, and can
# do Ctrl-P and Ctrl-N

# ## I add this to clarify
# 
# For the purposes of calculating the ninety time, I'm just going to substitute our definition of $F$ to get:
# $$\frac{B_{1,avg}}{\sqrt{P}} = \sqrt{\frac{Q \mu}{2 V_c \omega}}$$
# and then approximate $V_c$ as the volume of the coil based off the center diameter

# We can actually derive this equation here in-place.
# 
# Let's say that we have $E$ [J] units of energy stored in the cavity.
# The cavity must be dissipating $E/Q$ [J/rad] units of energy every radian,
# and $E \omega_0/ Q$ [J/s] units of energy per second.
# This must match the power going into the cavity:
# $$P = \frac{E \omega_0}{Q}$$
# Now, what is $E$?
# There is a [standard formula for this](http://hyperphysics.phy-astr.gsu.edu/hbase/electric/engfie.html)
# $$E = \frac{1}{2} \frac{B_{1,lf}^2}{\mu_0} V_c$$
# Where $B_{1,lf}$ is the amplitude of the linearly polarized field in the  lab frame,
# and $V_c$ is Mims' "effective cavity volume," which we take to be the coil volume.
# Now, we have:
# $$P = \frac{1}{2} \frac{B_{1,lf}^2 \omega_0 V_c}{Q \mu_0}$$
# Rearranging to get a conversion factor
# $$\frac{B_{1,lf}}{\sqrt{P}} = \sqrt{\frac{2 Q \mu_0}{V_c \omega_0}}$$

# In[ ]:


V_sample = pi*(tube_ID/2)**2*l # replaced with 5mm diameter NMR tube
mdown("Sample volume %.2e $m^3$ "%V_sample)
Vc = pi*(CD/2)**2*l
mdown("Coil volume %.2e $m^3$ "%Vc)

c_calc = sqrt(2*Q*mu0/(Vc*omega0))
mdown(r"Calculated conversion factor %.2e $T/\sqrt{W}$ "%c_calc)
mdown(r"Calculated conversion factor %.2f $G/\sqrt{W}$ "%(c_calc/1e-4))
mdown(r"Experimental conversion factor %.5f $G/\sqrt{W}$ "%(c_exp))
mdown(r"Experimental conversion factor %.2f $G/\sqrt{W}$ "%(c_exp/1e-4))
Vol_ratio = (c_calc/c_exp)**2
mdown(r"Conversion factor %.2f $G/\sqrt{W}$ "%(c_calc/1e-4))
mdown(r"Ratio of the actual effective cavity volume to the calculated $V_{c,actual}/V_{c,calc}$: %0.3f"%(Vol_ratio))


# ## (chronologically earlier) Before starting experiments, guess the ninety time
# Now, we convert this to a ninety time

# In[ ]:


B1_lf = c_calc*sqrt(P)
B1_rotfr = B1_lf/2
omega_1 = gamma_H * B1_rotfr
mdown(u'Ninety time is %0.2f μs'%(pi/2./omega_1/1e-6))


# # Calculate the signal
# $[^1H \text{spins}/\text{m}^3] = [2
# \text{protons}][55 \text{M}][\text{1e3} \text{L}/\text{m}^3]$

# In[ ]:


N = 2.*55e3*N_A


# $M_0$ from Cavanagh
# $M_0 = \frac{N \gamma \hbar^2 \omega_0 I \left( I+1 \right)}{3 k_B T}$ 

# In[ ]:


T = 298.
I = 0.5
M0 = N * omega0  * gamma_H * hbar**2 * I * (I+1) / (3 * k_B * T)


# signal
# from Rinard1999, we see
# $$I V_{signal} = \omega_0 \int_{sample}
# \vec{M} \cdot \vec{B_1} dV$$
# (Note that the units here work, because $M_0$ has units like $H$ in Maxwell's equations, while $B_1$ has units of $B$ [T])
# so that we have
# $$V_{signal} = \frac{\omega_0 M_0 B_1 V_{sample}}{I}$$
# substituting $P = I^2 Z_0$, we get
# $$V_{signal} = \omega_0 M_0 c V_{sample}\sqrt{Z_0}$$
# 
# Definition of conversion factor assumes $B_{1}$ in rotating frame, however current expression for $V_{signal}$ (can be illustrated by emf induced in a solenoid) assumes a stiatic $B_{1}$ -- 
# 
# Thus,
# $$V_{signal} = \omega_0 M_0 c V_{sample} \sqrt{Z_0} $$

# In[ ]:


V_signal = M0 * omega0 * V_sample * c_exp * sqrt(50.)
mdown(r'$V_{signal} = %0.2f\;\mu\text{V}$'%(V_signal/1e-6))



V_signal = M0 * omega0 * V_sample * c_calc * sqrt(50.)
mdown(r'$V_{calc signal} = %0.2f\;\mu\text{V}$'%(V_signal/1e-6))


# # For probe v1.5

# ## Physical constants

# In[ ]:


mu0 = 4*pi*1e-7 #permeability of free space in Tm/A
gamma_H = 2*pi*gammabar_H #gyromagnetic ratio for H in Hz/T
k_B = 1.38e-23 #Boltzmann constant in J/K
h = hbar*2*pi #Planck constant in Js


# ## Geometric parameters
# 
# Parameters measured on solenoid of interest (second 0.55 uH solenoid)

# In[ ]:


coil_len = 42.28e-3
coil_diam = 2.93e-3
coil_wire = 0.4e-3
coil_CD = coil_diam - coil_wire


# In[ ]:


sample_len = 40.73e-3
sample_diam = 2.15e-3
sample_wall = 0.38e-3
sample_ID = sample_diam - (2*sample_wall)


# ## Design parameters
# 
# power, impedance, temperature, etc

# In[ ]:


P = 43.1 #pulse power in Watts
R = 50. #resistance in Ohms
Q = 26. # actually measure now
omega0 = 2*pi*14.46e6
t90 = 0.9e-6


# # What is the actual conversion Factor
# so that we can compare to prediction, below
# 
# recall that $B_{1,rot} = \frac{1}{2} B_{1,lab\;frame}$ therefore requires multiplication by a factor of 2 coming to get correct conversion factor

# In[ ]:


nu1 = 1./(4*t90)
mdown((r'$\omega_1/2\pi=%0.1f$ kHz'%(nu1/1e3)))
B1_rotfr = nu1/gammabar_H
mdown(r'$B_1=%0.2e\;\text{T}$'%B1_rotfr)
B1_lf = B1_rotfr*2 # to convert to the lab frame
c_exp = B1_lf/sqrt(P)
mdown(r'$c=%0.2e\;\text{T}/\sqrt{\text{W}}$'%c_exp)


# # Use Mims to Calculate the Conversion Factor
# 
# We rearrange Eq. 9 from [3.]:
# $$F =
# B_{1,avg}
# \sqrt{
#     \frac{2 V_{sample} \omega
#     }{PQ \mu}
# }$$
# to get
# $$\frac{B_{1,avg}}{\sqrt{P}} = F\sqrt{\frac{Q \mu}{2 V_{sample} \omega}}$$
# Under these circumstances, it should be pretty reasonable to substitue $F = \sqrt{V_{sample}/V_c} \rightarrow \sqrt{\eta}$.
# 
# I think, *btw*, that it would probably be good to request the Mims chapter referenced in [3.] $\rightarrow$ ILL would probably send a PDF.

# In general, it's better to use longer and more clear/descriptive
# variable names $\rightarrow$ especially when you're using vim, and can
# do Ctrl-P and Ctrl-N

# ## I add this to clarify
# 
# For the purposes of calculating the ninety time, I'm just going to substitute our definition of $F$ to get:
# $$\frac{B_{1,avg}}{\sqrt{P}} = \sqrt{\frac{Q \mu}{2 V_c \omega}}$$
# and then approximate $V_c$ as the volume of the coil based off the center diameter

# We can actually derive this equation here in-place.
# 
# Let's say that we have $E$ [J] units of energy stored in the cavity.
# The cavity must be dissipating $E/Q$ [J/rad] units of energy every radian,
# and $E \omega_0/ Q$ [J/s] units of energy per second.
# This must match the power going into the cavity:
# $$P = \frac{E \omega_0}{Q}$$
# Now, what is $E$?
# There is a [standard formula for this](http://hyperphysics.phy-astr.gsu.edu/hbase/electric/engfie.html)
# $$E = \frac{1}{2} \frac{B_{1,lf}^2}{\mu_0} V_c$$
# Where $B_{1,lf}$ is the amplitude of the linearly polarized field in the  lab frame,
# and $V_c$ is Mims' "effective cavity volume," which we take to be the coil volume.
# Now, we have:
# $$P = \frac{1}{2} \frac{B_{1,lf}^2 \omega_0 V_c}{Q \mu_0}$$
# Rearranging to get a conversion factor
# $$\frac{B_{1,lf}}{\sqrt{P}} = \sqrt{\frac{2 Q \mu_0}{V_c \omega_0}}$$

# In[ ]:


V_sample = pi*(sample_ID/2.)**2*sample_len
mdown("Sample volume %.2e $m^3$ "%V_sample)
Vc = pi*(coil_CD/2.)**2*coil_len
mdown("Coil volume %.2e $m^3$ "%Vc)


# In[ ]:


c_calc = sqrt(2*Q*mu0/(Vc*omega0))
mdown(r"Calculated conversion factor %.2e $T/\sqrt{W}$ "%c_calc)
mdown(r"Calculated conversion factor %.2f $G/\sqrt{W}$ "%(c_calc/1e-4))
mdown(r"Experimental conversion factor %.5f $G/\sqrt{W}$ "%(c_exp))
mdown(r"Experimental conversion factor %.2f $G/\sqrt{W}$ "%(c_exp/1e-4))
Vol_ratio = (c_calc/c_exp)**2
mdown(r"Conversion factor %.2f $G/\sqrt{W}$ "%(c_calc/1e-4))
mdown(r"Ratio of the actual effective cavity volume to the calculated $V_{c,actual}/V_{c,calc}$: %0.3f"%(Vol_ratio))


# ## (chronologically earlier) Before starting experiments, guess the ninety time
# Now, we convert this to a ninety time

# In[ ]:


B1_lf = c_calc*sqrt(P)
B1_rotfr = B1_lf/2
omega_1 = gamma_H * B1_rotfr
mdown(u'Ninety time is %0.2f μs'%(pi/2./omega_1/1e-6))


# # Calculate the signal
# $[^1H \text{spins}/\text{m}^3] = [2
# \text{protons}][55 \text{M}][\text{1e3} \text{L}/\text{m}^3]$

# In[ ]:


N = 2.*55e3*N_A


# $M_0$ from Cavanagh
# $M_0 = \frac{N \gamma \hbar^2 \omega_0 I \left( I+1 \right)}{3 k_B T}$ 

# In[ ]:


T = 298.
I = 0.5
M0 = N * omega0  * gamma_H * hbar**2 * I * (I+1) / (3 * k_B * T)


# signal
# from Rinard1999, we see
# $$I V_{signal} = \omega_0 \int_{sample}
# \vec{M} \cdot \vec{B_1} dV$$
# (Note that the units here work, because $M_0$ has units like $H$ in Maxwell's equations, while $B_1$ has units of $B$ [T])
# so that we have
# $$V_{signal} = \frac{\omega_0 M_0 B_1 V_{sample}}{I}$$
# substituting $P = I^2 Z_0$, we get
# $$V_{signal} = \omega_0 M_0 c V_{sample}\sqrt{Z_0}$$
# 
# Definition of conversion factor assumes $B_{1}$ in rotating frame, however current expression for $V_{signal}$ (can be illustrated by emf induced in a solenoid) assumes a stiatic $B_{1}$ -- 
# 
# Thus,
# $$V_{signal} = \omega_0 M_0 c V_{sample} \sqrt{Z_0} $$

# In[ ]:


V_signal = M0 * omega0 * V_sample * c_exp * sqrt(50.)
mdown(r'$V_{signal} = %0.2f\;\mu\text{V}$'%(V_signal/1e-6))


# In[ ]:


V_signal = M0 * omega0 * V_sample * c_calc * sqrt(50.)
mdown(r'$V_{signal} = %0.2f\;\mu\text{V}$'%(V_signal/1e-6))


# In[ ]:




