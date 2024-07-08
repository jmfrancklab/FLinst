from pyspecdata import *
from scipy.optimize import leastsq,minimize
fl = figlist_var()
color_gen = (j for j in ['k','orange','r'])
id_string,label_string = ('191008_HP_calib_2','HP source')

data = load(getDATADIR(exp_type='test_equip')+id_string+'.npz')

x_axis = data[data.files[0]]
y_axis = data[data.files[1]]

figure('Calib curve')
title('Calibration curve')
power_data = nddata(y_axis,[-1],['set_power']).setaxis('set_power',x_axis)
if 'b12' in id_string:
    power_data.setaxis('set_power',lambda x: x - 35.0)
print(ndshape(power_data))
fl.next('calib curve')
low_power = power_data['set_power':(None,-15)]
high_power = power_data['set_power':(-15,None)]
test_settings = r_[-60,-35,-17,-19,-15,-10]
for label_string, power_data,lowest,highest in [
        ('low coarse setting',low_power,-100,-16),
        ('high coarse setting',high_power,-21,100),
        ]:
    # I'm gearing up for 2 calibrated modes of operation
    # 
    # "high coarse setting operation" means that:
    #   demand that dBm > -21
    #   if dBm < -6, coarse_setting --> -10
    # "low coarse setting operation" means that:
    #   demand that dBm < -16
    #   if dBm > -27, coarse_setting --> -20
    thiscolor = next(color_gen)
    fl.plot(power_data,'o',label=label_string,c=thiscolor)
    _,fitdata = power_data.polyfit('set_power',order=3)
    fl.plot(fitdata,'-',c=thiscolor)
    what_to_set = fitdata.invinterp('set_power',test_settings,
            fill_value='extrapolate')
    print(what_to_set)
    for j in range(what_to_set.data.size):
        set_this = what_to_set.getaxis('set_power')[j].real
        get_this = what_to_set['set_power',j].item()
        if set_this < lowest or set_this > highest:
            print("you can't get",get_this,"with",label_string)
        else:
            print("for",label_string,"operation, set a power of", set_this, "to get", get_this)
legend()
xlabel('programmed power (dBm)')
ylabel('output power (dBm)')
gridandtick(gca())
fl.show()
show()
