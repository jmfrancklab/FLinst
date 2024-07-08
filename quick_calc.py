from pyspecdata import *

#Cm = 0#330e-12
impedance = False
if impedance:
    for Cm in [0,100e-12,220e-12,330e-12]:
        C_add = 460e-12
        Ct = 1040e-12+C_add

        L = 80e-9
        factor = 1+(Cm/Ct)
        L_ = L/factor

        w = sqrt(1./(L_*(Cm+Ct)))
        f = w/2/pi
        print(f*1e-6)

        Z = w*w*L_*L_/50.
        print(Z)

# for calculating cap

Cm = 100e-12
Ct = 1000e-12+100e-12
print((Cm+Ct)*1e12)
L = 80e-9
factor = 1+(Cm/Ct)
L_ = L/factor

w = sqrt(1./(L_*(Cm+Ct)))
f = w/2/pi
print(f*1e-6)

Z = w*w*L_*L_/50.
print(Z)
