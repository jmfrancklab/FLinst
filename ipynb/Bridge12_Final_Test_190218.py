# 


get_ipython().magic(u'pylab inline')
sys.path.append('..')
from itertools import cycle
from Instruments.bridge12 import Bridge12
import time
#a dBm_increment of 0.1 does not work but 0.5 does


# # our basic test to see that Bridge12 behaves reasonably
# 
# (frequency range is appropriate when NMR probe is in cavity)

# 


freq = linspace(9.816e9,9.825e9, 100)
with Bridge12() as b:
    b.set_wg(True)
    b.set_amp(True)
    b.set_rf(True)
    b.set_power(10)
    b.freq_sweep(freq)
    tuning_curve_data = b.tuning_curve_data
    for j in range(6):
        print "power currently at %f and increasing by 1 dB"%(b.cur_pwr_int/10.0)
        tuning_curve_data = b.tuning_curve_data
        b.increase_power_zoom(dBm_increment=1,n_freq_steps=15)


# 


# check the zero point of the mV reading -- was giving some -0.2 mV before update

with Bridge12() as b:
    time.sleep(5)
    print "power Rx",b.rxpowermv_float()
    print "power Tx",b.txpowermv_float()
    b.write('rxdiodesn?\r')
    print "serial number for rx serial:"
    print b.readline()
    b.write('txdiodesn?\r')
    print "serial number for tx serial:"
    print b.readline()
    time.sleep(5)


# 


x = '190227_Tuning_Curves_after_update_run8'
def convert_to_power(x):
    y = 0
    c = r_[2.78135,25.7302,5.48909]
    for j in range(len(c)):
        y += c[j] * (x*1e-3)**(3-j)
    return log10(y)*10.0+2.2
from scipy.io import savemat, loadmat
series_names = [j.split('_')[0] for j in tuning_curve_data.keys() if '_freq' in j]
for this_series in series_names:
    figure(1)
    plot(tuning_curve_data[this_series+'_freq']/1e9,
         convert_to_power(tuning_curve_data[this_series+'_rx']),
         'o-',
         markersize=3,
         alpha=0.5,
         label=this_series)
    figure(2)
    plot(tuning_curve_data[this_series+'_freq']/1e9,
         tuning_curve_data[this_series+'_tx'], 
         'o-',
         markersize=3,
         label=this_series)
figure(1)
legend(**dict(bbox_to_anchor=(1.05,1),loc=2,borderaxespad=0.))
title('Rx power (dBm)')
# xlim(9.8495e9,9.851e9)
# ylim(-0.2,3)
plt.gca().get_xaxis().get_major_formatter().set_useOffset(False)
xticks(rotation=45)
xlim((9.82,9.821))
xlabel('freq / GHz')
figure(2)
legend(**dict(bbox_to_anchor=(1.05,1),loc=2,borderaxespad=0.))
title('Tx power (mV)')
plt.gca().get_xaxis().get_major_formatter().set_useOffset(False)
xticks(rotation=45)
xlabel('freq / GHz')
savemat(x+'.mat',tuning_curve_data)


# ## crank up the power, and then hold frequency

# 


#freq = (linspace(-0.005,0.005,100)+9.82046)*1e9
freq = linspace(9.816e9,9.825e9, 70)
with Bridge12() as b:
    b.set_wg(True)
    b.set_amp(True)
    b.set_rf(True)
    b.set_power(10)
    b.freq_sweep(freq)
    tuning_curve_data = b.tuning_curve_data
    for j in range(9):
        tuning_curve_data = b.tuning_curve_data
        print "power currently at %f and increasing by 1 dB"%(b.cur_pwr_int/10.0)
        b.increase_power_zoom(dBm_increment=1,n_freq_steps=15)
    center_freq = tuning_curve_data[b.last_sweep_name+'_freq'].mean()
    print "setting frequency to %f GHz"%(center_freq/1e9)
    b.set_freq(center_freq)
    for j in range(19*2):
        new_power = float(b.cur_pwr_int) / 10.0 + 0.5
        print "%d increasing power to %f dBm"%(j,new_power)
        b.set_power(new_power)
        print "read power of %f mV"%b.rxpowermv_float()
        if b.cur_pwr_int > 270:
            print "let's see if it drifts"
            for k in range(10):
                time.sleep(1)
                print "read power of %f mV"%b.rxpowermv_float()
    time.sleep(2.0)


# # working with pre-saved data
# 
# this is for loading from the bruker computer

# 


x = '190222_Tuning_Curves_success'
from scipy.io import savemat, loadmat
tuning_curve_data = loadmat('/home/xuser/Downloads/Sams_Downloads/190222_Tuning_Curves4.mat')

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
xlim(9.8511e9,9.8515e9)
ylim(-0.3,2.2)
figure(2)
legend(**dict(bbox_to_anchor=(1.05,1),loc=2,borderaxespad=0.))
title('Tx power (mV)')
xlim(9.8511e9,9.8515e9)
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
for power_level in r_[12:26:2]:
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

