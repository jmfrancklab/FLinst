from pyspecdata import *
#import logging
#init_logging(level=logging.DEBUG)
mixdown = 15e6
capture_num = 1
f_axis = linspace(100e3,500e3,100) # must match sweep_frequencies_sqw
with figlist_var(filename='chirp.pdf') as fl:
    expno=0
    for date, id_string in [
            ('180131','p23test'),
            ]:
        try:
            try:
                # capture2 only present when capture1 was bad
                d = nddata_hdf5(date+'_'+id_string+'.h5/capture2_'+date,
                            directory=getDATADIR(exp_type='test_equip'))
            except:
                d = nddata_hdf5(date+'_'+id_string+'.h5/capture1_'+date,
                            directory=getDATADIR(exp_type='test_equip'))
        except:
            try:
                # capture2 only present when capture1 was bad
                d = nddata_hdf5(date+'_'+id_string+'.h5/capture2',
                            directory=getDATADIR(exp_type='test_equip'))
            except:
                d = nddata_hdf5(date+'_'+id_string+'.h5/capture1',
                            directory=getDATADIR(exp_type='test_equip'))

        d.set_units('t','s')
#        d -= d['t':(0,3.5e-6)].runcopy(mean,'t')
        fl.next('capture')
        fl.plot(d['ch',0],alpha=0.2)
        d.ft('t',shift=True)
        fl.next('FT')
        fl.plot(abs(d)['ch',0],alpha=0.2,label='pi')
        fl.plot(abs(d)['ch',1],alpha=0.2,label='control')
        d.ift('t')
        #analytic
        d.ft('t')
        d = d['t':(0,None)]
        d['t':(60e6,None)] = 0
        fl.next('analytic')
        fl.plot(abs(d)['ch',0],alpha=0.2,label='FT and IFT')
        d.ift('t')
        d *= 2
        fl.next('analytic abs')
        fl.plot(abs(d)['ch',0],alpha=0.5,label='anl abs')
        fl.plot(d['ch',0],alpha=0.5,label='anl R')
        d = d['t':(0,100e6)] # throw out negative frequencies and low-pass
        d.reorder('ch', first=False) # move ch last
        #d.ift('t')
#        ranges = abs(d)['ch',0].contiguous(lambda x: x > 0.4*x.data.max())
#        if ranges.shape[0] > 1:
#            raise ValueError("When I try to pull out the waveform, I get more than one range that's greater than 9%")
#        ranges = tuple(ranges[0,:].tolist())
#        d = d['t':ranges]
#        d.setaxis('t', lambda x: x-d.getaxis('t')[0])
#        d.setaxis('t', lambda x: 25e6-x*25e6/4096e-8).set_units('t','Hz')
#        if expno == 0:
#            fl.next('analytic signal, phase')
#            fl.plot(d['ch',0].angle)
#        fl.next('analytic signal, ratio', legend=True)
#        #d.setaxis('t', lambda x: x-d.getaxis('t')[0])
#        fl.plot(abs(2*d['ch',1]/d['ch',0]), alpha=0.38, label=id_string)
#        fl.next('analytic signal, phase difference', legend=True)
#        #d.setaxis('t', lambda x: x-d.getaxis('t')[0])
#        fl.plot((d['ch',1]/d['ch',0]).angle/pi, '.', alpha=0.38, label=id_string)
#        expno += 1
