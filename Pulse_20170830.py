
# coding: utf-8

# In[ ]:

get_ipython().magic('pylab inline')
from serial.tools.list_ports import comports
import serial

[j for j in comports()]


#  Rather than doing the following, we should just 
#  use the serial class that we previously created

# In[ ]:

port_id = j[0]
with serial.Serial(port_id) as s:
    s.write('*idn?\n')
    result = s.readline()
result


# OUTPUT TEST WAVE

# In[ ]:

with serial.Serial(port_id) as s:
    s.write('SOUR1:APPL:SIN 2KHZ,1,0\n')
    


# RESET INSTRUMENT

# In[ ]:

with serial.Serial(port_id) as s:
    s.write('*rst\n')
    


# Communicating with GDS
#  *here, there were some unnecessary repeats from above*

# In[ ]:

def id_instrument(textidn):
    for j in comports():
        port_id = j[0] # based on the previous, this is the port number

    with serial.Serial(port_id) as s:
        s.write('*idn?\n')
        result = s.readline()
        if textidn in result:
            return port_id


# Checking id_instrument runs

# In[ ]:

idn = id_instrument('GDS-3254')
print(idn)


# In[ ]:

def instrument_instance(textidn):
    return serial.Serial(id_instrument(textidn))

with instrument_instance('GDS-3254') as s:
    s.write('*idn?\n')
    print(s.readline())
    
def retrieve_waveform(instname='GDS-3254'):
    """Retrieve waveform and associated parameters form the scope.

    Comprises the following steps:

    * opens the port to the scope
    * acquires what is saved in memory as string
    * Divides this string at hashtag which separates settings from waveform

    Parameters
    ==========

    instname : str

        The instrument name.  Specifically, a string that's returned as
        part of the response to the ``*idn?`` command.

    Returns
    =======

    x_axis : ndarray

        The *x*-axis (time-base) of the data.

    data : ndarray

        A 1-d array containing the scope data.

    params : dict

        A dictionary of the parameters returned by the scope.
    """
    params = {}
    with instrument_instance(instname) as s:
        s.write(':ACQ2:MEM?\n') #ACQ2 instead of ACQ1 bc AFG is CH2 of GDS
        def upto_hashtag():
            this_char = s.read(1)
            this_line = ''
            while this_char != '#':          
                this_line += this_char
                this_char = s.read(1)
            return this_line

        #Further divides settings
        preamble = upto_hashtag().split(';')
        
        #Retrieves 'memory' of 25000 from settings
        #Waveform data is 50,000 bytes of binary data (2*mem)
        mem = int(preamble[0].split(',')[1])
        
        #Generates list of parameters in the preamble
        param = dict([tuple(x.split(',')) for x in preamble if len(x.split(',')) == 2])
        
        #Reads waveform data of 50,000 bytes
        s.read(6)# length of 550000
        data = s.read(50001)
        assert data[-1] == '\n', "data is not followed by newline!"
        data = data[:-1]

    # convert the binary string
    data_array = fromstring(data,dtype='i2')
    data_array =  double(data_array)/double(2**(2*8-1))

    # I could do the following
    #x_axis = r_[0:len(data_array)] * float(param['Sampling Period'])
    # but since I'm "using up" the sampling period, do this:
    x_axis = r_[0:len(data_array)] * float(param.pop('Sampling Period'))
    # r_[... is used by numpy to construct arrays on the fly

    # Similarly, use V/div scale to scale the y values of the data
    data_array *= float(param.pop('Vertical Scale'))/0.2 # we saw
    #              empirically that 0.2 corresponds to about 1 division

    return x_axis,data_array,param

x_axis,data,param = retrieve_waveform()

title(param['Source'])
plot(x_axis/1e-6,data)
xlabel(r'$t$ / $\mu s$')


# In[ ]:



