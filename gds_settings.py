from Instruments import *
from pyspecdata import *
import time
from serial.tools.list_ports import comports
import serial
from scipy import signal

fl = figlist_var()

print("These are the instruments available:")
SerialInstrument(None)
print("done printing available instruments")

#with SerialInstrument('GDS-3254') as s:
#    print s.respond('*idn?')
#    
#with SerialInstrument('AFG-2225') as s:
#    print s.respond('*idn?')


with GDS_scope() as g:
     #print "attempting to call volt scale f'n" 
     #g.CH1.disp=True
     #g.CH2.disp=True
     #g.write(':CHAN1:DISP OFF')
     #g.write(':CHAN2:DISP OFF')
     g.CH1.voltscal=100E-3
     g.CH2.voltscal=100E-3
#      g.timscal(500e-9)
#      print "Trigger response"
#      print g.respond(':TRIG:MOD?')
#      print "Trigger frequency"
#      print g.respond(':TRIG:FREQ?')
#      print "Trigger source"
#      print g.respond(':TRIG:SOUR?') 
#      print "Set trig source to ch2"
#      g.write('TRIG:SOUR CH2')
#      print "Trigger source"
#      print g.respond(':TRIG:SOUR?')
#commented code below I anticipate will help me write code for more setting features

# with GDS_scope() as g:
#       print "attempt to call channel scale"
#       vs = 5E-3
#       vs_str = '%0.3E'%vs
#       print "query volt scale in volt/div"
#       print g.respond(':chan1:scal?')
#       print "setting volt scale to %s volt/div"%vs_str
#       chn = 
#       g.write(':chan1:scal ',vs)
#       print "query volt scale set correctly"
#       print g.respond(':chan1:scal?')
    #print "query volt scale in volt/dev"
    #print g.respond(':chan1:scal?')
    

# with gds_scope() as g:
#     g.reset()
#     print "query time scale in sec/div"
#     print g.respond(':tim:scal?')
#     ts = 100e-9
#     ts_str = '%0.6e'%ts
#     print "setting time scale to %s sec/div"%ts_str
#     g.write(':tim:scal ',ts)
#     print g.demand(':tim:scal?',ts_str)




