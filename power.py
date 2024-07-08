from pyspecdata import *
atten = 10**(-40./10)
Vpp = input('Enter Vpp from scope: ')
print(''+Vpp+' Vpp')
Vpp = float(Vpp)
Vpp = Vpp/2.
W = 10.0546+(Vpp/2./sqrt(2))**2/50./atten
print('Corresponding power is:')
W = str(W)
print(''+W+' Watts')


