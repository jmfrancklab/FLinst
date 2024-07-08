
# coding: utf-8

# 

get_ipython().magic(u'load_ext pyspecdata.ipy')
from scipy.linalg import expm
# this next part is not something I expected you to do -- I provide it here to provide nice matrix printing
import IPython.display as d
fl = figlist_var()


# 

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


# 

t90 = 2.1e-6
omega1_nominal = 2*pi/(4*t90)
results = ndshape([100,1000],['omega1','Omega']).alloc()
omega1_axis = linspace(0,3*omega1_nominal,ndshape(results)['omega1'])
omega_axis = linspace(-omega1_nominal*3,omega1_nominal*3,ndshape(results)['Omega'])
results.labels(['omega1','Omega'],[omega1_axis/2/pi,omega_axis/2/pi])
tau = 50e-6
for i,omega1 in enumerate(omega1_axis):
    for j,Omega in enumerate(omega_axis):
        U90 = expm(-1j*omega1*t90*Ix-1j*Omega*t90*Iz)
        U180 = expm(-1j*omega1*2*t90*Ix-1j*Omega*2*t90*Iz)
        Uev = expm(-1j*Omega*tau*Iz)
        Uev_echo = expm(-1j*Omega*(tau+2*t90/pi)*Iz)
        Utot = Uev_echo.dot(U180).dot(Uev).dot(U90)
        rho = Utot.dot(Iz).dot(Utot.T.conj())
        results['omega1',i]['Omega',j] = rho[1,0]
results.set_units('omega1','Hz').set_units('Omega','Hz')
results.rename('omega1',r'$\omega_1/2\pi$').rename('Omega',r'$\Omega/2\pi$')


# 

fl.next('original simulation w phase',figsize=(14,14)) # I want figsize, and I need fl so that it handles the units
fl.image(results, black=True)


# 

fl.next('original simulation abs',figsize=(14,14)) # I want figsize, and I need fl so that it handles the units
fl.image(abs(results))


# try varying $B_1$ amplitude to get the 180 instead (half-amplitude 180 pulse for the 90)

t90 = 2.1e-6
omega1_nominal = 2*pi/(4*t90)
results = ndshape([100,1000],['omega1','Omega']).alloc()
omega1_axis = linspace(0,3*omega1_nominal,ndshape(results)['omega1'])
omega_axis = linspace(-omega1_nominal*3,omega1_nominal*3,ndshape(results)['Omega'])
results.labels(['omega1','Omega'],[omega1_axis/2/pi,omega_axis/2/pi])
tau = 50e-6
for i,omega1 in enumerate(omega1_axis):
    for j,Omega in enumerate(omega_axis):
        U90 = expm(-1j*omega1*t90*Ix-1j*Omega*2*t90*Iz)
        U180 = expm(-1j*omega1*2*t90*Ix-1j*Omega*t90*Iz)
        Uev = expm(-1j*Omega*tau*Iz)
        Uev_echo = expm(-1j*Omega*(tau+4*t90/pi)*Iz)
        Utot = Uev.dot(U180).dot(Uev).dot(U90)
        rho = Utot.dot(Iz).dot(Utot.T.conj())
        results['omega1',i]['Omega',j] = rho[1,0]
results.set_units('omega1','Hz').set_units('Omega','Hz')
results.rename('omega1',r'$\omega_1/2\pi$').rename('Omega',r'$\Omega/2\pi$')


# 

fl.next('two amps simulation w phase',figsize=(14,14)) # I want figsize, and I need fl so that it handles the units
fl.image(results, black=True)


# 

fl.next('two amps simulation abs',figsize=(14,14)) # I want figsize, and I need fl so that it handles the units
fl.image(abs(results))


# how far do we have to go to not see signal at all?

t90 = 2.1e-6
omega1_nominal = 2*pi/(4*t90)
results = ndshape([100,1000],['omega1','Omega']).alloc()
omega1_axis = linspace(0,3*omega1_nominal,ndshape(results)['omega1'])
omega_axis = linspace(-omega1_nominal*10,omega1_nominal*10,ndshape(results)['Omega'])
results.labels(['omega1','Omega'],[omega1_axis/2/pi,omega_axis/2/pi])
tau = 50e-6
for i,omega1 in enumerate(omega1_axis):
    for j,Omega in enumerate(omega_axis):
        U90 = expm(-1j*omega1*t90*Ix-1j*Omega*t90*Iz)
        U180 = expm(-1j*omega1*2*t90*Ix-1j*Omega*2*t90*Iz)
        Uev = expm(-1j*Omega*tau*Iz)
        Uev_echo = expm(-1j*Omega*(tau+2*t90/pi)*Iz)
        Utot = Uev.dot(U180).dot(Uev).dot(U90)
        rho = Utot.dot(Iz).dot(Utot.T.conj())
        results['omega1',i]['Omega',j] = rho[1,0]
results.set_units('omega1','Hz').set_units('Omega','Hz')
results.rename('omega1',r'$\omega_1/2\pi$').rename('Omega',r'$\Omega/2\pi$')

# What if we phase cycle?
# *Note:* I changed this from 2 step to 4 step on the 180, because I thought the signal should be cleaner
# However, that was for an older version of the simulation where there was a typo, but I like it better, so I leave it.

t90 = 2.1e-6
omega1_nominal = 2*pi/(4*t90)
d.display(d.Markdown(r'$t_{90}$ chosen assuming an $\omega_1/2\pi=%0.2f$ kHz'%(omega1_nominal/2/pi/1e3)))
results = ndshape([4,4,20,200],['ph2','ph1','omega1','Omega']).alloc()
omega1_axis = linspace(0,3*omega1_nominal,ndshape(results)['omega1'])
omega_axis = linspace(-omega1_nominal*10,omega1_nominal*10,ndshape(results)['Omega'])
results.labels(['ph2','ph1'],[r_[0:4],r_[0:4]])
results.labels(['omega1','Omega'],[omega1_axis/2/pi,omega_axis/2/pi])
pul_rot = lambda I,ph: expm(1j*pi/2*Iz*ph).dot(I).dot(expm(-1j*pi/2*Iz*ph))# sense of rotation relative to propagators chosen so that signal shows up along -1
tau = 50e-6
for ph2 in xrange(4):
    for ph1 in xrange(4):
        for i,omega1 in enumerate(omega1_axis):
            for j,Omega in enumerate(omega_axis):
                U90 = expm(-1j*omega1*t90*pul_rot(Ix,ph1)-1j*Omega*t90*Iz)
                U180 = expm(-1j*omega1*2*t90*pul_rot(Ix,ph2)-1j*Omega*2*t90*Iz)
                Uev = expm(-1j*Omega*tau*Iz)
                Uev_echo = expm(-1j*Omega*(tau+2*t90/pi)*Iz)
                Utot = Uev_echo.dot(U180).dot(Uev).dot(U90)
                rho = Utot.dot(Iz).dot(Utot.T.conj())
                results['ph2',ph2]['ph1',ph1]['omega1',i]['Omega',j] = rho[1,0]
results.set_units('omega1','Hz').set_units('Omega','Hz')
results.rename('omega1',r'$\omega_1/2\pi$').rename('Omega',r'$\Omega/2\pi$')
results.ft(['ph1','ph2'])


# 

with figlist_var() as fl:
    fl.next('show relative size of phcyc channels',figsize=(14,28)) # I want figsize, and I need fl so that it handles the units
    fl.image(abs(results))

# Now, using the same type of experiment ask -- what happens if I run a nutation curve off resonance

t90_guess = 2.1e-6
t_max = 4*t90_guess
omega1 = 2*pi/(4*t90_guess)
d.display(d.Markdown(r'$\omega_1/2\pi=%0.2f$ kHz'%(omega1/2/pi/1e3)))
results = ndshape([4,4,20,200],['ph2','ph1','t_pulse','Omega']).alloc()
t_pulse_axis = linspace(0,t_max,ndshape(results)['t_pulse'])
omega_axis = linspace(-omega1_nominal*4,omega1_nominal*4,ndshape(results)['Omega'])
results.labels(['ph2','ph1'],[r_[0:4],r_[0:4]])
results.labels(['t_pulse','Omega'],[t_pulse_axis,omega_axis/2/pi])
pul_rot = lambda I,ph: expm(1j*pi/2*Iz*ph).dot(I).dot(expm(-1j*pi/2*Iz*ph))# sense of rotation relative to propagators chosen so that signal shows up along -1
tau = 50e-6
for ph2 in xrange(4):
    for ph1 in xrange(4):
        for i,t_pulse in enumerate(t_pulse_axis):
            for j,Omega in enumerate(omega_axis):
                U90 = expm(-1j*omega1*t_pulse*pul_rot(Ix,ph1)-1j*Omega*t_pulse*Iz)
                U180 = expm(-1j*omega1*2*t_pulse*pul_rot(Ix,ph2)-1j*Omega*2*t_pulse*Iz)
                Uev = expm(-1j*Omega*tau*Iz)
                Uev_echo = expm(-1j*Omega*(tau+2*t_pulse/pi)*Iz)
                Utot = Uev_echo.dot(U180).dot(Uev).dot(U90)
                rho = Utot.dot(Iz).dot(Utot.T.conj())
                results['ph2',ph2]['ph1',ph1]['t_pulse',i]['Omega',j] = rho[1,0]
results.rename('Omega',r'$\Omega/2\pi$').set_units('t_pulse','s').set_units('Omega','Hz')
results.ft(['ph1','ph2'])


# 

with figlist_var() as fl:
    fl.next('show relative size of phcyc channels',figsize=(14,28)) # I want figsize, and I need fl so that it handles the units
    fl.image(abs(results))


# pull the part filtered by the second pulse, to see if we can figure out -1 vs. +1

with figlist_var() as fl:
    fl.next('filter desired channel',figsize=(14,14)) # I want figsize, and I need fl so that it handles the units
    figure(figsize=(14,14))
    fl.image(results['ph2',2]['ph1',+1])


# 

150e3/gammabar_H/1e-4


# 

1e6/gammabar_H/1e-4


# 

500e-4*gammabar_H/1e6


# 

500e-4/4.258e7


# Somewhat arbitrarily mixed in -- how do we actually construct the phase cycled pulses?

t = r_[0:2*128]
f = 0.25
figure(figsize=(20,10))
wform_noph = exp(1j*2*pi*f*t)
wform_noph[55:150] = 0
plot_offset = 0
for ph_2 in xrange(0,4,2):
    for ph_1 in xrange(4):
        wform = wform_noph.copy()
        wform[0:56] *= exp(1j*pi/2*ph_1)
        wform[140:] *= exp(1j*pi/2*ph_2)
        plot(wform.real+plot_offset)
        plot_offset += 2

