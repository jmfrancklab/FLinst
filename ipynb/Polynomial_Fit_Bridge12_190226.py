
# coding: utf-8

# 


get_ipython().magic(u'pylab inline')
sys.path.append('..')
from itertools import cycle
from Instruments.bridge12 import Bridge12
#a dBm_increment of 0.1 does not work but 0.5 does


# 


freq = linspace(9.849e9,9.853e9, 200)
with Bridge12() as b:
    b.set_wg(True)
    b.set_amp(True)
    b.set_rf(True)
    b.set_power(10)
    b.freq_sweep(freq)
    for j in range(5):
        tuning_curve_data = b.tuning_curve_data
        b.increase_power_zoom(dBm_increment=2,n_freq_steps=20)
    for j in range(5):
        tuning_curve_data = b.tuning_curve_data
        b.increase_power_zoom(dBm_increment=1,n_freq_steps=10)
    for j in range(5):
        tuning_curve_data = b.tuning_curve_data
        b.increase_power_zoom(dBm_increment=0.5,n_freq_steps=10)
    for j in range(5):
        tuning_curve_data = b.tuning_curve_data
        b.increase_power_zoom(dBm_increment=0.5,n_freq_steps=5)


# 


x = '190222_Tuning_Curves_success'
from scipy.io import savemat, loadmat

series_names = [j.split('_')[0] for j in tuning_curve_data.keys() if '_freq' in j]
for this_series in series_names:
    figure(1)
    plot(tuning_curve_data[this_series+'_freq'],
         tuning_curve_data[this_series+'_rx'],
         'o-',
         markersize=3,
         alpha=0.5,
         label=this_series)
    figure(2)
    plot(tuning_curve_data[this_series+'_freq'],
         tuning_curve_data[this_series+'_tx'], 
         'o-',
         markersize=3,
         label=this_series)
figure(1)
legend(**dict(bbox_to_anchor=(1.05,1),loc=2,borderaxespad=0.))
title('Rx power (mV)')


# xlim(9.8495e9,9.851e9)
# ylim(-0.2,1.0)

# 


figure(2)
legend(**dict(bbox_to_anchor=(1.05,1),loc=2,borderaxespad=0.))
title('Tx power (mV)')
savemat(x+'.mat',tuning_curve_data)


# # working with pre-saved data
# 
# this is for loading from the bruker computer

# 


x = '190227_Tuning_Curves_after_update_run7'
power_array = r_[11:19+1:1]
from scipy.io import savemat, loadmat
rpi = True
if rpi:
    tuning_curve_data = loadmat('%s.mat'%x)
else:
    tuning_curve_data = loadmat('/home/xuser/Downloads/Sams_Downloads/%s.mat'%x)


# 


series_names = [j.split('_')[0] for j in tuning_curve_data.keys() if '_freq' in j]
for this_series in series_names:
    figure(1)
    plot(tuning_curve_data[this_series+'_freq'].ravel(),
         tuning_curve_data[this_series+'_rx'].ravel(),
         'o-',
         markersize=3,
         alpha=0.5,
         label=this_series)
    figure(2)
    plot(tuning_curve_data[this_series+'_freq'].ravel(),
         tuning_curve_data[this_series+'_tx'].ravel(), 
         'o-',
         markersize=3,
         label=this_series)
figure(1)
legend(**dict(bbox_to_anchor=(1.05,1),loc=2,borderaxespad=0.))
title('Rx power (mV)')
#xlim(9.8511e9,9.8515e9)
#ylim(-0.3,2.2)
figure(2)
legend(**dict(bbox_to_anchor=(1.05,1),loc=2,borderaxespad=0.))
title('Tx power (mV)')
#xlim(9.8511e9,9.8515e9)
#ylim(-0.3,2.2)


# savefig("TC_10dBm_20dBm_190222_2.png")

# ## Polynomial fitting
# 
# Now we see if we can polynomial fit these guys.
# 
# We can, and also assuming the voltage reading is similar to power, we can predict the next curve up somewhat reasonably, *until* we hit a 22 dBm, and then the power read at the center of the dip is much higher than expected.
# 
# #### A note on the dB scaling parameter
# this is set empirically, so our prediction is ideally higher than
# the actual Rx voltage we see when we increase the power
# if Rx voltage were proportional to power, and Rx Voltage only changed in response to power,
# this should theoretically be 10.0; if Rx Voltage were proportional to incident voltage,
# this would be 20.0

# 


figure(1,figsize=(10,10))
series_names = [j.split('_')[0] for j in tuning_curve_data.keys() if '_freq' in j]
safe_voltage = 4 # you would actually use the safe voltage attribute of the class here
thesecolors = cycle(list('bgrcmyk'))
nextcolor = cycle(list('grcmykb'))
afternextcolor = cycle(list('rcmykbg'))
def polycurve(fdata,p):
    "return the polynomial fit"
    currorder = len(p)-1
    retval = zeros_like(fdata)
    for c in p:
        retval += c * fdata**currorder
        currorder -= 1
    return retval
dB_scaling = 6.0
#for this_series in series_names:
for power_level in power_array:
    dB_step = 2. # ideally, this should be smaller -- 0.5?
    # -- again, this is hard coded, but is an argument of
    # the zoom function inside the class
    this_series = '%ddBm'%power_level
    thiscolor = thesecolors.next()
    thisnextcolor = nextcolor.next()
    thisafternextcolor = afternextcolor.next()
    figure(1)
    fdata = tuning_curve_data[this_series+'_freq'].ravel()
    fdata_smooth = r_[fdata[0]:fdata[-1]:500j]
    rxdata = tuning_curve_data[this_series+'_rx'].ravel()
    p = polyfit(fdata,rxdata,2)
    c,b,a = p
    print "for power level %g, center frequency is %g"%(power_level,-b/2/c)
    a,b,c = p * 10**(dB_step/dB_scaling) # quadratic equation to predict next power up
    c -= 0.5*safe_voltage # want quadratic equation where it intercepts the safe voltage
    intercepts = (-b+r_[-sqrt(b**2-4*a*c),sqrt(b**2-4*a*c)])/2/a
    # VERY IMPORTANT: not allowed to *increase* the range in frequencies, ever
    intercepts.sort()
    print ("looking at power level %g, we think that for power level %g, "
           +"the range of frequencies should be from %g to %g")%(
        power_level,power_level+dB_step,intercepts[0],intercepts[1])
    print "0: current intercepts",intercepts
    if intercepts[0] < fdata[0]: intercepts[0]=fdata[0]
    if intercepts[1] > fdata[-1]: intercepts[1]=fdata[-1]
    plot(fdata/1e9,
         rxdata,
         'o',
         color=thiscolor,
         markersize=3,
         alpha=0.5,
         label=this_series)
    plot(fdata_smooth/1e9,
         polycurve(fdata_smooth,p),
         '-',
         color=thiscolor,
         alpha=0.5)
    plot(fdata_smooth/1e9,
         polycurve(fdata_smooth,p)*10**(dB_step/dB_scaling),
         '--',
         color=thisnextcolor,
         alpha=0.5,
         label='at %f predict %f'%(power_level,power_level+dB_step))
    plot(intercepts/1e9,
         polycurve(intercepts,p)*10**(dB_step/dB_scaling),
         'x',
         color=thisnextcolor,
         alpha=0.5,
         label='at %f in.cep. for %f'%(power_level,power_level+dB_step))
    plot(fdata_smooth/1e9,
         polycurve(fdata_smooth,p)*10**(2*dB_step/dB_scaling),
         '-.',
         color=thisafternextcolor,
         alpha=0.5,
         label='at %f predict %f'%(power_level,power_level+2*dB_step))
    figure(2)
    plot(fdata/1e9,
         tuning_curve_data[this_series+'_tx'].ravel(), 
         'o',
         color=thiscolor,
         markersize=3,
         label=this_series)
figure(1)
legend(**dict(bbox_to_anchor=(1.05,1),loc=2,borderaxespad=0.))
title('Rx power (mV)')
#xlim(9.8511e9,9.8515e9)
axis('tight')
#ylim(0,1.0)
plt.gca().get_xaxis().get_major_formatter().set_useOffset(False)
xticks(rotation=45)
xlabel('freq / GHz')
figure(2)
legend(**dict(bbox_to_anchor=(1.05,1),loc=2,borderaxespad=0.))
title('Tx power (mV)')
xlim(9.8511,9.8515)
xlabel('freq / GHz')
plt.gca().get_xaxis().get_major_formatter().set_useOffset(False)
#ylim(-0.3,2.2)


# 


thesecolors = cycler(color='bgrcmyk')
for j in range(20):
    print next(thesecolors)


# 


from itertools import cycle
thesecolors = cycle(list('bgrcmyk'))
for j in range(20):
    print thesecolors.next()


# 


a = r_[-2,3,1]
a.sort()
a

