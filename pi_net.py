from pyspecdata import *

L = input ("L in uH: ")
C = input ("C in pF: ")
L = float(L)
C = float(C)

f = sqrt(1./(L*1e-6*C*1e-12))*(1./(2*pi))/1e6
Z = 1./(f*1e6*2*pi*C*1e-12)

print("Resonance f in MHz: %f"%f)
print("Characteristic impedance in ohm: %f"%Z)
