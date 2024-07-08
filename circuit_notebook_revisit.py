from pyspecdata import *
L = 0.54e-6
C_tune = 200e-12
C_tune2 = 9e-12
C_match = 9e-12
print("Main C_tune =",C_tune*1e12)
print("*** OUTPUT IS ***")
print("*** f_0, Z ***")
print("As I increase the variable tune capacitor")
print("Match at its lowest setting")
for C_tune2 in range(9,50,10):
    C_tune2 *= 1e-12
    C_TUNE = C_tune + C_tune2
    corr = (1.+(C_match/C_TUNE))**2
    omega = 1./(sqrt(L*(C_match + C_TUNE)))
    Z = (omega**2)*(L**2)/50.
    Z /= corr
    print(1e-6*omega/(2*pi), Z)
print("***")
C_match = 45e-12
print("As I increase the variable tune capacitor,")
print("Match at its highest setting")
for C_tune2 in range(9,50,10):
    C_tune2 *= 1e-12
    C_TUNE = C_tune + C_tune2
    corr = (1.+(C_match/C_TUNE))**2
    omega = 1./(sqrt(L*(C_match + C_TUNE)))
    Z = (omega**2)*(L**2)/50.
    Z /= corr
    print(1e-6*omega/(2*pi), Z)
print("***")
print("If I remove the variable tune capacitor")
print("Match at its lowest setting")
C_match = 9e-12
C_tune2 = 0
C_tune2 *= 1e-12
C_TUNE = C_tune + C_tune2
corr = (1.+(C_match/C_TUNE))**2
omega = 1./(sqrt(L*(C_match + C_TUNE)))
Z = (omega**2)*(L**2)/50.
Z /= corr
print(1e-6*omega/(2*pi), Z)
print("***")
print("If I remove the variable tune capacitor")
print("Match at its highest setting")
C_match = 50e-12
C_tune2 = 0
C_tune2 *= 1e-12
C_TUNE = C_tune + C_tune2
corr = (1.+(C_match/C_TUNE))**2
omega = 1./(sqrt(L*(C_match + C_TUNE)))
Z = (omega**2)*(L**2)/50.
Z /= corr
print(1e-6*omega/(2*pi), Z)
