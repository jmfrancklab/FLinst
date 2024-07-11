from pylab import *

# this is the calibration curve for our Rx amplifier (which was the original Tx
# amplifier before Thorsten's visit, and was switched to Tx after he visited)


figure(1)
PdBm = r_[-20,-15,-10,-5,0,2,4,6,8,10,12,14,16,18,20]
U = r_[0.002,0.0063,0.0183,0.0493,0.1209,0.1649,0.2255,0.3008,0.3933,0.5127,0.663,0.853,1.084,1.373,1.722]
plot(U,10**(PdBm/10.0),'o')

c = r_[2.78135,25.7302,5.48909]
x = linspace(0,1.8,500)
y = zeros(500)
for j in range(len(c)):
    y += c[j] * x**(3-j)
plot(x,y)
figure(2)
plot(U,PdBm,'o')
plot(x,log10(y)*10)
y = 0
x = 500.0e-3
for j in range(len(c)):
    y += c[j] * x**(3-j)
print "%f mV is %f dBm"%(x/1e-3,log10(y)*10)
show()
