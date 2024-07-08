
# coding: utf-8

# In[1]:


get_ipython().magic(u'load_ext pyspecdata.ipy')
from scipy.linalg import expm


# In[2]:


import IPython.display as d
fl = figlist_var()


# In[3]:


Iz = 0.5*array([[1,0],[0,-1]],dtype=complex128)

Ix = 0.5*array([[0,1],[1,0]],dtype=complex128)

Iy = 0.5*array([[0,-1j],[1j,0]],dtype=complex128)

E = array([[1,0],[0,1]],dtype=complex128)

Iz = 0.5*array([[1,0],[0,-1]],dtype=complex128)
Ix = 0.5*array([[0,1],[1,0]],dtype=complex128)
Iy = 0.5*array([[0,-1j],[1j,0]],dtype=complex128)
E = array([[1,0],[0,1]],dtype=complex128)

Ip = Ix + 1j*Iy
Im = Ix - 1j*Iy

map(d.display,[Iz,Ix,Iy,E,Ip,Im])


# In[ ]:


# if we are on resonance
# what happens if magnetic field is slightly off the on-resonance condition /* --> OFFSET */ (\Omega)
# and what happens if the conversion factor is off /* --> MISMATCH */ such that B1 (as determined by rf pulse)
# does not correspond exactly to \omega1 (as determined by nutation frequency of nuclei), 
# such that the actual nutation is varied between diff values of omega1


# In[4]:


t90 = 7.45e-6
omega1_nominal = 2*pi/(4*t90)
tau = 48e-6
d.display(d.Markdown(r'$t_{90}$ chosen assuming a nominal $\omega_1/2\pi=%0.2f$ kHz'%(omega1_nominal/2/pi/1e3)))
results = ndshape([100,100],['omega1','Omega']).alloc()
omega1_axis = linspace(0,4*omega1_nominal,ndshape(results)['omega1'])
Omega_axis = linspace(-omega1_nominal*3,omega1_nominal*3,ndshape(results)['Omega'])
results.labels(['omega1','Omega'],[omega1_axis/2/pi,Omega_axis/2/pi])
for i,omega1 in enumerate(omega1_axis):
    for j,Omega in enumerate(Omega_axis):
        U90 = expm(-1j*omega1*t90*Ix-1j*Omega*t90*Iz)
        U180 = expm(-1j*omega1*2*t90*Ix-1j*Omega*2*t90*Iz)
        Uev = expm(-1j*Omega*tau*Iz)
        Uev_echo = expm(-1j*Omega*(tau+2*t90/pi)*Iz)
        Utot = Uev_echo.dot(U180).dot(Uev).dot(U90)
        rho = Utot.dot(Iz).dot(Utot.T.conj())
        results['omega1',i]['Omega',j] = rho[1,0]
results.set_units('omega1','Hz').set_units('Omega','Hz')
results.rename('omega1',r'$\omega_1/2\pi$').rename('Omega',r'$\Omega/2\pi$')


# In[5]:


with figlist_var() as fl:
    fl.next('Simulation, without phase cycling',figsize=(18,12))
    fl.image(results,black=True)


# In[6]:


with figlist_var() as fl:
    fl.next('abs(Simulation), without phase cycling',figsize=(18,12))
    fl.image(abs(results))


# In[7]:


# Now include phase cycling


# In[8]:


t90 = 7.45e-6
omega1_nominal = 2*pi/(4*t90)
tau = 48e-6
results = ndshape([4,4,100,100],['ph2','ph1','omega1','Omega']).alloc()
omega1_axis = linspace(0,4*omega1_nominal,ndshape(results)['omega1'])
Omega_axis = linspace(-omega1_nominal*3,omega1_nominal*3,ndshape(results)['Omega'])
results.labels(['omega1','Omega'],[omega1_axis/2/pi,Omega_axis/2/pi])
results.labels(['ph2','ph1'],[r_[0:4],r_[0:4]])
pul_rot = lambda I,ph: expm(-1j*pi/2*Iz*ph).dot(I).dot(expm(1j*pi/2*Iz*ph))# sense of rotation relative to propagators chosen so that signal shows up along -1
for ph2 in xrange(4):
    for ph1 in xrange(4):
        for i,omega1 in enumerate(omega1_axis):
            for j,Omega in enumerate(Omega_axis):
                U90 = expm(-1j*omega1*t90*pul_rot(Ix,ph1)-1j*Omega*t90*Iz)
                U180 = expm(-1j*omega1*2*t90*pul_rot(Ix,ph2)-1j*Omega*2*t90*Iz)
                Uev = expm(-1j*Omega*tau*Iz)
                Uev_echo = expm(-1j*Omega*(tau+2*t90/pi)*Iz)
                Utot = Uev_echo.dot(U180).dot(Uev).dot(U90)
                rho = Utot.dot(Iz).dot(Utot.T.conj())
                results['ph2',ph2]['ph1',ph1]['omega1',i]['Omega',j] = rho[1,0]
results.set_units('omega1','Hz').set_units('Omega','Hz')
results.rename('omega1',r'$\omega_1/2\pi$').rename('Omega',r'$\Omega/2\pi$')


# In[9]:


# Go to the coherence domain along the phase cycle domain for each pulse
results.ift(['ph1','ph2'])


# In[10]:


# Observe each pulse on the -1 coherence level of its coherence domain
# For this pulse sequence, signal appears 2 coherence levels down from the 90 pulse
# can determine this from the coherence transfer pathway
with figlist_var() as fl:
    fl.next('Simulation, with phase cycling',figsize=(18,12))
    fl.image(results,black=True)


# In[11]:


# Plot this way to show the relative sizes of the artifacts compared to signal
with figlist_var() as fl:
    fl.next('abs(Simulation), with phase cycling',figsize=(18,12))
    fl.image(abs(results),black=True)


# In[12]:


# Pull the signal from its coherence level
signal = results['ph2',2]['ph1',1]


# In[13]:


with figlist_var() as fl:
    fl.next('Signal, phase cycled',figsize=(18,12)) # I want figsize, and I need fl so that it handles the units
    fl.image(abs(signal),black=True)


# In[14]:


# Pull the artifacts from the 90 pulse
pulse_90 = results['ph1',-1]['ph2',0]


# In[15]:


with figlist_var() as fl:
    fl.next('Artifacts from 90 pulse',figsize=(18,12)) # I want figsize, and I need fl so that it handles the units
    fl.image(abs(pulse_90),black=True)


# In[16]:


# Pull the artifacts from the 180 pulse
pulse_180 = results['ph1',0]['ph2',-1]


# In[17]:


with figlist_var() as fl:
    fl.next('Artifacts from 180 pulse',figsize=(18,12)) # I want figsize, and I need fl so that it handles the units
    fl.image(abs(pulse_180),black=True)


# In[18]:


# Discussion of simulation


# The point of this simulation is to test the **fidelity of the pulse sequence** given the parameters specified above. 
# 
# We are simulating how much signal we can expect over a range of different values for the nutation frequency, $\omega_{1}$, and the offset $\Omega = \omega_{0} - \omega_{rf}$ where $\omega_{0}$ is the frequency of the magnet (which should be the Larmor frequency) and $\omega_{rf}$ is the frequency of the pulse.
# 
# Below we span 100 values of $\omega_{1}$ from 0 to three times the value of $\omega_{1}$ calculated above.
# 
# We also span 1000 values of $\Omega$ from three times below resonance ($\Omega = 0$) to three times above resonance.
# 
# Additionally, the pulse sequence contains a delay $\tau$ which is here the time between the end of the 90 pulse and the beginning of the 180 pulse.
# 
# Below we define four operators for the 90 and 180 pulses, as well as operators for **(1)** the time evolution under the Zeeman during the delay $\tau$, and **(2)** the time evolution following the 180 up to the point where the spin echo occurs.
# 
# Two things to note:
# 
# (1) Normally we say the echo occurs at twice the pulse delay, $\tau$, but here we apply a correction factor noted later in Cavanagh that is equivalent to saying the echo will occur a tiny bit _earlier_ that exactly $\tau$ after the 180, because a majority of the spins will have been flipped into the transverse plane at a time of _not exactly_ $\tau_{90}$ but rather $\frac{2 \tau_{90}}{\pi}$, which is about 64% of the $\tau_{90}$ -- **i.e., a little more than halfway through the 90 pulse, many of the spins have been tipped and we account for this with a correction factor below**.
# 
# (2) We allow for Zeeman evolution during the rf pulses, which has so far not been included in Cavanagh.
# 
# 
# $$\hat{U}_{90} = e^{-i \omega_{1} \tau_{90} \hat{I}_{x} - i \Omega \tau_{90} \hat{I}_{z}} $$
# $$\hat{U}_{180} = e^{-i \omega_{1} 2\tau_{90} \hat{I}_{x} - i \Omega 2\tau_{90} \hat{I}_{z}} $$
# $$\hat{U}_{evolution} = e^{-i \Omega \tau \hat{I}_{z}} $$
# $$\hat{U}_{evolution,echo} = e^{-i \Omega (\tau + \frac{2\tau_{90}}{\pi}) \hat{I}_{z}} $$
# 
# Define an operator for the entire pulse sequence as:
# 
# $$\hat{U}_{total} = \hat{U}_{evolution,echo} \bullet \hat{U}_{180} \bullet \hat{U}_{evolution} \bullet \hat{U}_{90} $$
# 
# We can then find the detectable component of the spin density matrix:
# 
# $$\rho = \hat{U}_{total} \bullet \hat{I}_{z} \bullet {\hat{U}}^{-1}_{total} $$
# 
# which becomes, because we are dealing with unitary operators:
# 
# $$\rho = \hat{U}_{total} \bullet \hat{I}_{z} \bullet {\hat{{U}^\intercal}^{*}_{total}} $$

# In[ ]:




