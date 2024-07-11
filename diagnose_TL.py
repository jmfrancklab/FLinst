from pyspecdata import *
import winsound
#import logging
init_logging(level=logging.DEBUG)
fl = figlist_var()

atten_level = 10**(-42/20.)

def process_series(date,id_string,capture):
    """Process a series of pulse data.
    
    Lumping this as a function so we can do things like divide series, etc.

    Parameters
    ----------
    date: str
        date used in the filename
    id_string: str
        filename is called date_id_string
    V_AFG: array
        list of voltage settings used on the AFG

    Returns
    -------
    V_anal: nddata
        The analytic signal, filtered to select the fundamental frequency (this is manually set).
    V_harmonic: nddata
        The analytic signal, filtered to set the second harmonic (this is manually set)
    V_pp: nddata
        After using the analytic signal to determine the extent of the pulse, find the min and max.
    """
    j = capture 
    print("loading signal",j)
    j_str = str(j)
    d = nddata_hdf5(date+'_'+id_string+'.h5/capture'+j_str+'_'+date,
            directory=getDATADIR(exp_type='test_equip'))
    d.set_units('t','s')
    fl.next('Channel 1, 1')
    fl.plot(d['ch',0]/atten_level, alpha=0.5, label='%s'%id_string)
    ylabel('atten. accounted for')
    if id_string == 'duplexer_amp1':
        logger.debug("plotting unfiltered")
        logger.debug(strm('before figure switch: current name',fl.current,'and gca',id(gca())))
        fl.next('Compare filtered vs. unfiltered')
        logger.debug(strm('after figure switch: current name',fl.current,'and gca',id(gca())))
        logger.debug(strm('lines for this plot',gca().get_lines()))
        fl.plot(d['ch',0]/atten_level, alpha=0.5, label='unfiltered')
        ylabel('atten. accounted for')
        logger.debug(strm('lines for this plot',gca().get_lines()))
    d.ft('t',shift=True)
    fl.next('Raw FT')
    fl.plot(d['ch',0],alpha=0.15,label='%s'%id_string)
    d.ift('t')
    d.ft('t')
    if id_string == 'duplexer_amp1':
        d_filt = d.C
        d_filt['t':(None,-20e6)] = 0
        d_filt['t':(20e6,None)] = 0
    d_modsq = abs(d)['t':(-200e6,200e6)] # since we have nothing of significance beyond 200 MHz
    # {{{ go back and plot on the comparison plot
    if id_string == 'duplexer_amp1':
        logger.debug("plotting filtered")
        fl.next('Compare filtered vs. unfiltered')
        fl.plot(d_filt.ift('t')['ch',0]/atten_level, alpha=0.5, label='filtered')
    # }}}
    d_modsq = d_modsq*d_modsq
    d_fundamental = d_modsq.C['t':(-20e6,20e6)]
    d_harmonics = d_modsq.C
    d_harmonics['t':(-20e6,20e6)]=0
    print('integrating '+id_string+' fundamental')
    fundamental_sum = d_fundamental['ch',0].integrate('t')
    print(fundamental_sum)
    print('integrating '+id_string+' harmonics')
    harmonics_sum = d_harmonics['ch',0].integrate('t')
    print(harmonics_sum)
    print("done loading all signals for %s"%id_string)
    fl.next('Fundamental FT')
    fl.plot(d_fundamental['ch',0], alpha=0.3,
            label='%s'%id_string)
    fl.next('Harmonics FT')
    fl.plot(d_harmonics['ch',0], alpha=0.3, label='%s'%id_string)
    return 

for date,id_string in [
       ('180316','duplexer_pi1'),
       ('180316','duplexer_pi2')
        ]:
    process_series(date,id_string,capture=1)
fl.next('Compare filtered vs. unfiltered')# shouldn't be required
logger.debug(strm('before process series: current name',fl.current,'and gca',id(gca())))
process_series('180315','duplexer_amp1',capture=100)    
fl.next('Compare filtered vs. unfiltered')
logger.debug(strm('at the end: current name',fl.current,'and gca',id(gca())))
fl.show()

