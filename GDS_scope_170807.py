
# coding: utf-8

# In[4]:

%pylab inline
from serial.tools.list_ports import comports
import serial


# What serial ports are available?
# --> this is not used, but just shows what the results of ``comports()`` looks like

# In[7]:

[j for j in comports()]


# Here, I search through the comports in order to identify the instrument that I'm interested in.  This (or something like this) should work on either Windows or Mac/Linux.
# I can use this to initialize a class.

# In[ ]:

def id_instrument(textidn):
    """Identify the instrument that returns an ID string containing ``textidn``
    """
    for j in comports():
        port_id = j[0] # based on the previous, this is the port number
        with serial.Serial(port_id) as s:
            s.write('*idn?\n')
            result = s.readline()
            if textidn in result:
                return port_id
def instrument_instance(textidn, **kwargs):
    """Return an instance of the ``Serial`` class corresponding to the instrument that returns ``textidn`` as part of the id string.
    
    Parameters
    ==========

    textidn : str
        
        A string used to identify the instrument.
        Specifically, the instrument responds to the ``*idn?`` command
        with a string that includes ``textidn``.
    """
    return serial.Serial(id_instrument(textidn), **kwargs)
with instrument_instance('GDS-3254') as s:
    s.write('*idn?\n')
    print s.readline()

# Note that I can now use ``instrument_instance`` in place of ``serial.Serial``, except that ``instrument_instance`` accepts a string identifying the instrument.
# I paste your code with minimal modification  and some reorganization below.

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
        s.write(':ACQ1:MEM?\n')
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

# The previous cell only ***defines*** the function ``retrieve_waveform``.  Now I have to actually call (run) it!:

x_axis,data,param = retrieve_waveform()

# Next, show what the ``param`` dictionary looks like (note that the items that we've popped have been removed)

param

# Plots waveform data → I manually scale by μs

title(param['Source'])
plot(x_axis/1e-6,data)
xlabel(r'$t$ / $\mu s$')


# I'm not worrying about automatically interpreting the units here, because that will all be handled when we make our special data object.
# 
# I do want to check that I'm interpreting the y scale correctly, so let's look at the peak to peak voltage here, and compare to what we measure with cursors on the screen:

data.max()-data.min()
