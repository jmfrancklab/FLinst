
# coding: utf-8

# 

get_ipython().magic(u'load_ext pyspecdata.ipy')
from IPython.display import Markdown as md
md('test *yes*')
import pandas as pd


# 

d = pd.read_excel('bridge12_diode_calib.xlsx')
d = d.loc[2:] #truncate the stuff that's too low in power


# 

d = nddata(d['"Rx" reading'].values,['dBm']).labels({'dBm':double(d['Expected Real Value'].values)})
d


# 

print d.data.min()


# ## since I want to use inverse interpolation, check that it looks OK

# 

plot(d,'o')
yvals = linspace(3,390,100)
xvals = d.C.invinterp('dBm',yvals)
plot(xvals)


# 

readings = r_[13.4,13.8,277.9,320.9,11.6,99.4,40.2,24.5,16.2,11.4,6.5,4.3]
for reading in readings:
    dBm_val = d.C.invinterp('dBm',reading).getaxis('dBm').item().real
    display(md('A reading of %f mV corresponds to %f dBm, if dir. coup %f dBm total, if before amp appropriate for %f dBm total'%(reading,dBm_val,dBm_val+20,dBm_val+35)))


# ## show how the source readings are off
set_read_pairs = [(35,40.2),
        (32,24.5),
        (30,16.2),
        (28,11.4),
        (25,6.5),
        (22.5,4.3),
        ]
settings,readings = zip(*set_read_pairs)
dBm_val = d.C.invinterp('dBm',readings).getaxis('dBm').item().real
dBm_val += 35. # what setting is the appropriate for
plot(settings,dBm_val,'o')
xlabel('setting / dBm')
ylabel('(source ouput + 35 dB) / dBm')

