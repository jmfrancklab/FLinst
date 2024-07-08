from pyspecdata import *
#import logging
#init_logging(level=logging.DEBUG)
mixdown = 15e6
capture_num = 1
f_axis = linspace(100e3,500e3,100) # must match sweep_frequencies_sqw
with figlist_var(filename='chirp.pdf') as fl:
    expno=0
    for date, id_string in [
            ('180227','controlchirp'),
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
        if expno == 0:
            # {{{ CDF the values of the data to see if it's really digitizing with 14 bit
            vals = d.data.flatten()
            myhist = nddata(linspace(-3,3,1000),'val')
            fl.next('PDF of values (check digitization)')
            # {{{ calculate the CDF
            for j,testval in enumerate(myhist.getaxis('val')):
                myhist['val',j] = sum(vals < testval)
            # }}}
            myhist.diff('val') # to get the PDF
            num_values = len(myhist[lambda x: x>1e-8].data)
            print("number of values along dynamic range",num_values,"log_2 ->",log(num_values)/log(2),"bits")
            fl.plot(myhist, label='Diversity of data matches %0.3f bits'%(log(num_values)/log(2)))
            # }}}
        fl.next('chirp')
        fl.plot(d['ch',0],color='violet')
        d -= d['t':(0,3.5e-6)].runcopy(mean,'t')
        d.ft('t',shift=True)
        d = d['t':(0,100e6)] # throw out negative frequencies and low-pass
        d.reorder('ch', first=False) # move ch last
        d.ift('t')
        if expno == 0:
            fl.next('analytic signal, abs')
            fl.plot(abs(d))
        ranges = abs(d)['ch',0].contiguous(lambda x: x > 0.2*x.data.max())
        #if ranges.shape[0] > 1:
        #    raise ValueError("When I try to pull out the waveform, I get more than one range that's greater than 9%")
        ranges = tuple(ranges[0,:].tolist())
        d = d['t':ranges]
        d.setaxis('t', lambda x: x-d.getaxis('t')[0])
        d.setaxis('t', lambda x: 25e6-x*25e6/4096e-8).set_units('t','Hz')
        if expno == 0:
            fl.next('analytic signal, phase')
            fl.plot(d.angle)
#        if id_string == 'open_control':
#            fl.next('ratio analytic, pi short', legend=True)
#            fl.plot(abs(2*d['ch',1]/d['ch',0]), alpha=0.8, label=id_string)
#        if id_string == 'short_pi':
#            fl.next('ratio analytic, pi short', legend=True)
#            fl.plot(abs(2*d['ch',1]/d['ch',0]), alpha=0.8, label=id_string)
#        if id_string == 'short_control':
#            fl.next('ratio analytic, pi open', legend=True)
#            fl.plot(abs(2*d['ch',1]/d['ch',0]), alpha=0.8, label=id_string)
#        if id_string == 'open_pi':
#            fl.next('ratio analytic, pi open', legend=True)
#            fl.plot(abs(2*d['ch',1]/d['ch',0]), alpha=0.8, label=id_string)
        fl.next('analytic signal, ratio', legend=True)
#        d.setaxis('t', lambda x: x-d.getaxis('t')[0])
        fl.plot(abs(2*d['ch',1]/d['ch',0]), alpha=0.38, label=id_string)
        fl.next('analytic signal, phase difference', legend=True)
#        d.setaxis('t', lambda x: x-d.getaxis('t')[0])
        fl.plot((d['ch',1]/d['ch',0]).angle/pi, '.', alpha=0.38, label=id_string)
        expno += 1
