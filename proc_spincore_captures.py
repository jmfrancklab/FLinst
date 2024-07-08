from Instruments import *
from pyspecdata import *

fl = figlist_var()
filename = '181212_test_steps_2.h5'
for this_num in r_[1,2]:
    dataset = str(this_num)
    if dataset == '1':
        label = '0,2'
    elif dataset == '2':
        #label = '1,2'
        label = '1,3' # for *steps_2 only
    elif dataset == '3':
        label = '0,3'
    elif dataset == '4':
        label = '1,3'
    data = nddata_hdf5('%s/%s'%(filename,dataset))
    fl.next('raw signal')
    fl.plot(data,alpha=0.5,label=label)
    data.ft('t',shift=True)
    if dataset == '2':
        data *= exp(1j*(pi/2.))
        data.ift('t')
    elif dataset == '4':
        data *= exp(1j*(pi/2.))
        data.ift('t')
    else:
        data.ift('t')
    fl.next('phased?')
    fl.plot(data,alpha=0.5)
    data.ft('t')
    data['t':(None,0)] = 0
    print("type is",data.data.dtype)
    fl.next('analytic signal -- abs')
    data.ift('t')
    data *= exp(-1j*2*pi*data.fromaxis('t')*5e6)
    fl.plot(abs(data['ch',0]),alpha=0.5,label=label)
    fl.next('analytic signal -- phase',legend=True)
    fl.plot(data['ch',0].angle/pi/2,',',alpha=0.5,label=label)
fl.show()
