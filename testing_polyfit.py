from pylab import *
result = {}
result['10dBm_freq'] = r_[8.4:8.7:50j]*1e9
result['10dBm_rx'] = zeros_like(result['10dBm_freq'])
for x in range(len(result['10dBm_rx'])):
    result['10dBm_rx'][x] = 2.0
f0 = result['10dBm_freq'][25]
result['10dBm_rx'][25] = -10
result['10dBm_rx'][24] = -6
result['10dBm_rx'][26] = -6
result['10dBm_rx'][23] = -2
result['10dBm_rx'][27] = -2
figure()
plot(result['10dBm_freq'],result['10dBm_rx'],'.')
def polycurve(fdata,p):
    currorder = len(p)-1
    retval = zeros_like(fdata)
    for c in p:
        retval += c * fdata**curroder
        currorder -= 1
    return retval
fdata = result['10dBm_freq'].ravel()
fdata_smooth = r_[fdata[0]:fdata[-1]:500j]
rxdata = result['10dBm_rx'].ravel()
rx_min = min(rxdata)
rx_max = max(rxdata)
half_max = (rx_min + rx_max) / 2.0
this_r = rxdata > half_max
print(len(this_r))
print(len(rxdata))
print(this_r)
quit()
print(rx_min,rx_max,half_max)
under_midpoint = []
over_bool = rxdata > half_max
currently_over = True
for j,val in enumerate(over_bool):
    if currently_over:
        if not val:
            start_under = j
            currently_over = False
    else:
        if val:
            under_midpoint.append([start_under,j])
            currently_over = True
under_midpoint_lengths = diff(array(under_midpoint),axis=0)
if len(under_midpoint_lengths) > 1:
    longest_under_range = under_midpoint_lengths.argmax()
else:
    longest_under_range = 0

p = polyfit(fdata,rxdata,2)
c,b,a = p
def plot_func(x_val):
    return c*x_val**2 + b*x_val + a
plot(fdata_smooth,plot_func(fdata_smooth))
safe_rx = max(result['10dBm_rx'])
a -= safe_rx
safe_crossing = (-b+r_[-sqrt(b**2-4*a*c),sqrt(b**2-4*a*c)])/2/c
print("Original safe crossing",safe_crossing)
ddB = 3.0
dBs = 6.0
c,b,a = p * ddB
plot(fdata_smooth,plot_func(fdata_smooth))
safe_rx = max(result['10dBm_rx'])
a -= safe_rx
safe_crossing = (-b+r_[-sqrt(b**2-4*a*c),sqrt(b**2-4*a*c)])/2/c
print("New safe crossing",safe_crossing)
quit()
center = -b/(2*c)
print("Predicted center frequency:",center)
safe_rx = max(result['10dBm_rx'])
a -= safe_rx
safe_crossing = (-b+r_[-sqrt(b**2-4*a*c),sqrt(b**2-4*a*c)])/2/c
safe_crossing.sort()
print(b**2)
print(-4*a*c)
print(c,b,a);quit()
axvline(safe_crossing[0],c='k',linestyle=':')
axvline(safe_crossing[1],c='k',linestyle=':')

print(safe_crossing,center)

new_f = r_[safe_crossing[0]:center:10j]
new_f = r_[center:safe_crossing[1]:10j]

show()
