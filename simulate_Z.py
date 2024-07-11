from pylab import *
f = r_[5:20:5000j]*1e6
C_tune = 220e-12
C_match = 1 
L = 0.455e-6 
R = 5.0
for C_match in r_[2e-12:40e-12:5j]:
    Z = 1./(1/(1j*2*pi*f*L+R) + 1./(1./(1j*2*pi*f*C_tune)+R)) +1./(1j*2*pi*f*C_match)+R
    Gamma = (Z-50.)/(Z+50)
    figure(1)
    plot(f,abs(Gamma),
            alpha=0.5)
    figure(2)
    plot(f,angle(Gamma*exp(1j*pi)),label='%0.2fpF'%(C_match/1e-12),
            alpha=0.5)
    figure(3)
    plot(Gamma.real, Gamma.imag, '.')
figure(1)
title('absolute value of refl.')
legend()
figure(2)
title('phase of refl.')
legend()
figure(3)
title("Smith Chart")
legend()
plot(0,0,'ro')
ylim(-1,1)
xlim(-1,1)
show()
