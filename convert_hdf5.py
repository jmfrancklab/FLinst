
# coding: utf-8

# In[47]:


from pyspecdata import *
from pyspecdata.plot_funcs.image import imagehsv
import os
import sys
import matplotlib.style
import matplotlib as mpl


mpl.rcParams['image.cmap'] = 'jet'
fl = figlist_var()
gain_factor_dcasc12 = sqrt(114008.55204672)   #gain in units of V
max_window = 30e-6
carrier_f = 14.4289e6

indirect_range = None
s = nddata_hdf5('180725_SE.h5/this_capture',
#s = nddata_hdf5('180712_SE_exp_2.h5/this_capture',
        directory = getDATADIR(exp_type='test_equip'))

s.set_units('t','s')
s.ft('t',shift=True)
s = s['t':(10e6,25e6)]
s.ift('t')
is_nutation = False
if 't_90' in s.dimlabels:
    s.rename('t_90','indirect')
    is_nutation = True
    logger.info('This is a nutation curve')
if 'full_cyc' in s.dimlabels:
    s.rename('full_cyc','indirect')
if 'average' in s.dimlabels:
    s.rename('average','indirect')

    
print(ndshape(s))
s = s.mean('indirect',return_error=False)
signal = s['ph1',1]['ph2',0]['ch',0]
#signal = signal['t']
print(ndshape(signal))
plot(signal);show()


# In[50]:


q = open('spin_echo_180725.txt', 'wb')
increment = 1700
for i in range(2**11):
    data = signal.data[i+increment]
    time = signal.getaxis('t')[i+increment]
    q.write("%f %f\n" % (time, data))

q.close()


# In[53]:


data = []
time = []
increment = 1700
for i in range(2**11):
    data_val = signal.data[i+increment]
    time_val = signal.getaxis('t')[i+increment]
    data.append(data_val)
    time.append(time_val)
data = array(data)
time = array(time)
title('before')
show()


# In[78]:


from pandas import read_csv
import os

d = read_csv(os.path.expanduser('~/Desktop/spin_echo_coif17_denoised.dat'), sep='\t')
d = d.set_index(d.columns[0])
d.plot()
show()
             


# In[215]:


from pandas import read_csv
import os

d = read_csv(os.path.expanduser('~/Desktop/spin_echo_180725_coif3_denoised.dat'), sep='\t', header=None, index_col=False)
d = d.set_index(d.columns[0])
#d = d.columns[0]*1e6
d.plot(figsize=(14,14),title='Comparison',legend=True,label="NERD")
plot(time,data,alpha=0.3)
legend(["NERD","Filtered"])
xlabel("t / s")
show()

