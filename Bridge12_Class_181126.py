
# coding: utf-8

# ## Initialization
#  
# To run on a different computer, run ``jupyter notebook --ip='*'`` copy and paste address and replace ``localhost`` with
# ``jmfranck-pi2.syr.edu`` (if on the internet) or ``192.168.1.20`` (if on local network)

# 


get_ipython().magic(u'pylab inline')
from serial.tools.list_ports import comports, grep
import serial
import time
#import winsound
print serial.VERSION
from scipy.io import savemat, loadmat


# 


def generate_beep(freq,duration):
    "Generates a beep -- used winsound.Beep under windows -- use pygame under linux"
    return
class Bridge12 (serial.Serial):
    def __init__(self, *args, **kwargs):
        # Grab the port labeled as Arduino (since the Bridge12 microcontroller is an Arduino)
        portlist = [j.device for j in comports() if u'Arduino Due' in j.description]
        assert len(portlist)==1
        thisport = portlist[0]
        super(self.__class__, self).__init__(thisport, timeout=3, baudrate=115200)
    def bridge12_wait(self):
        #time.sleep(5)
        def look_for(this_str):
            for j in range(1000):
                a = self.read_until(this_str+'\r\n')
                time.sleep(0.1)
                #print "a is",repr(a)
                print "look for",this_str,"try",j+1
                if this_str in a:
                    print "found: ",this_str
                    break
        look_for('MPS Started')
        look_for('System Ready')
        return
    def help(self):
        self.write("help\r") #command for "help"
        print "after help:"
        entire_response = ''
        start = time.time()
        entire_response += self.readline()
        time_to_read_a_line = time.time()-start
        grab_more_lines = True
        while grab_more_lines:
            time.sleep(3*time_to_read_a_line)
            more = self.read_all()
            entire_response += more
            if len(more) == 0:
                grab_more_lines = False
        print repr(entire_response)
    def wgstatus_int_singletry(self):
        self.write('wgstatus?\r')
        return int(self.readline())
    def wgstatus_int(self):
        "need two consecutive responses that match"
        c = self.wgstatus_int_singletry()
        d = self.wgstatus_int_singletry()
        while c != d:
            c = d
            d = self.wgstatus_int_singletry()
        return c
    def set_wg(self,setting):
        """set *and check* waveguide

        Parameters
        ==========
        s: Serial object
            gives the connection
        setting: bool
            Waveguide setting appropriate for:
            True: DNP
            False: ESR
        """
        self.write('wgstatus %d\r'%setting)
        for j in range(10):
            result = self.wgstatus_int()
            if result == setting:
                return
        raise RuntimeError("After checking status 10 times, I can't get the waveguide to change")
        
    def ampstatus_int_singletry(self):
        self.write('ampstatus?\r')
        return int(self.readline())
    def ampstatus_int(self):
        "need two consecutive responses that match"
        a = self.ampstatus_int_singletry()
        b = self.ampstatus_int_singletry()
        while a != b:
            a = b
            b = self.ampstatus_int_singletry()
        return a
    def set_amp(self,setting):
        """set *and check* amplifier

        Parameters
        ==========
        s: Serial object
            gives the connection
        setting: bool
           Amplifier setting appropriate for:
            True: On
            False: Off
        """
        self.write('ampstatus %d\r'%setting)
        for j in range(10):
            result = self.ampstatus_int()
            if result == setting:
                return
        raise RuntimeError("After checking status 10 times, I can't get the amplifier to turn on/off")
        
    def rfstatus_int_singletry(self):
        self.write('rfstatus?\r')
        retval = self.readline()
        if retval.strip() == 'ERROR':
            print "got an error from rfstatus, trying again"
            self.write('rfstatus?\r')
            retval = self.readline()
            if retval.strip() == 'ERROR':
                raise RuntimeError("Tried to read rfstatus twice, and got 'ERROR' both times!!")
        return int(retval)
    def rfstatus_int(self):
        "need two consecutive responses that match"
        f = self.rfstatus_int_singletry()
        g = self.rfstatus_int_singletry()
        while f != g:
            f = g
            g = self.rfstatus_int_singletry()
        return f
    def set_rf(self,setting):
        """set *and check* microwave power

        Parameters
        ==========
        s: Serial object
            gives the connection
        setting: bool
            Microwave Power setting appropriate for:
            True: On
            False: Off
        """
        self.write('rfstatus %d\r'%setting)
        for j in range(10):
            result = self.rfstatus_int()
            if result == setting:
                return
        raise RuntimeError("After checking status 10 times, I can't get the mw power to turn on/off")

    def power_int_singletry(self):
        self.write('power?\r')
        return int(self.readline())
    def power_int(self):
        "need two consecutive responses that match"
        h = self.power_int_singletry()
        i = self.power_int_singletry()
        while h != i:
            h = i
            i = self.power_int_singletry()
        return h
    def set_power(self,dBm):
        """set *and check* power

        Parameters
        ==========
        s: Serial object
            gives the connection
        dBm: float
            power values -- give a dBm (not 10*dBm) as a floating point number
        """
        setting = int(10*dBm+0.5)
        if setting > 150:
            raise ValueError("You are not allowed to use this function to set a power of greater than 15 dBm for safety reasons")
        elif setting < 0:
            raise ValueError("Negative dBm -- not supported")
        self.write('power %d\r'%setting)
        for j in range(10):
            result = self.power_int()
            if result == setting:
                return
        raise RuntimeError("After checking status 10 times, I can't get the power to change")
    def rxpowermv_int_singletry(self):
        self.write('rxpowermv?\r')
        retval = self.readline()
        #print retval
        return int(retval)
    def rxpowermv_float(self):
        "need two consecutive responses that match"
        for j in range(3):
            # burn a few measurements
            self.rxpowermv_int_singletry()
        h = self.rxpowermv_int_singletry()
        i = self.rxpowermv_int_singletry()
        while h != i:
            h = self.rxpowermv_int_singletry()
            i = self.rxpowermv_int_singletry()
        return float(h)/10.
    def txpowermv_int_singletry(self):
        self.write('txpowermv?\r')
        return int(self.readline())
    def txpowermv_float(self):
        "need two consecutive responses that match"
        for j in range(3):
            # burn a few measurements
            self.txpowermv_int_singletry()
        h = self.txpowermv_int_singletry()
        i = self.txpowermv_int_singletry()
        while h != i:
            h = self.txpowermv_int_singletry()
            i = self.txpowermv_int_singletry()
        return float(h)/10.
#insert set_freq here
    def set_freq(self,Hz):
        """set frequency

        Parameters
        ==========
        s: Serial object
            gives the connection
        Hz: float
            frequency values -- give a Hz as a floating point number
        """
        setting = int(Hz/1e3+0.5)
        self.write('freq %d\r'%(setting))
        if self.freq_int() != setting:
            for j in range(10):
                result = self.freq_int()
                if result == setting:
                    return
            raise RuntimeError("After checking status 10 times, I can't get the "
                           "frequency to change -- result is %d setting is %d"%(result,setting))
    def freq_int(self):
        "return the frequency, in kHz (since it's set as an integer kHz)"
        self.write('freq?\r')
        return int(self.readline())
    def __enter__(self):
        self.bridge12_wait()
        return self
    def __exit__(self, exception_type, exception_value, traceback):
        try:
            self.set_power(0)
            self.set_rf(False)
            self.set_wg(False)
        except:
            print "error on standard shutdown -- running fallback shutdown"
            self.write('power %d\r'%0)
            self.write('rfstatus %d\r'%0)
            self.write('wgstatus %d\r'%0)
        self.close()
        return


# 


with Bridge12() as b:
    b.write('freq 9500101\r')
    time.sleep(1)
    b.write('freq?\r')
    print b.readline()


# 


with Bridge12() as b:
    b.set_freq(9.500401e9)


# Print out the com ports, so we know what we're looking for

# 


[(j.device, j.hwid, j.vid, j.description, j.manufacturer) for j in comports()] #list comprehension


# ## Code for MW Power Test

# check that all the ``set_`` functions work correctly:

# 


with Bridge12() as b:
    print "initial wg status:", b.wgstatus_int()
    b.set_wg(True)
    print "initial amp status:", b.ampstatus_int()
    b.set_amp(True)
    print "initial rf status:", b.rfstatus_int()
    b.set_rf(True)
    print "initial power:",b.power_int()
    b.set_power(10)
    print "up power:",b.power_int()
    time.sleep(10)


# #### Stop here -- need to read, understand, and use the previous before proceeding

# ## Tuning Curve

# a. Set Frequency and Define Frequency Sweep

# 


def freq_sweep(b,freq, old_code=False):
    """sweep over an array of frequencies

    Parameters
    ==========
    b: Bridge12 object
        gives the connection
    freq: array of floats
        frequencies in Hz
        
    Returns
    =======
    rxvalues: array
        An array of floats, same length as freq, containing the receiver (reflected) power in dBm at each frequency.
    txvalues: array
        An array of floats, same length as freq, containing the transmitted power in dBm at each frequency.
    
    """    
    rxvalues = zeros(len(freq))
    txvalues = zeros(len(freq))
    #FREQUENCY AND RXPOWER SWEEP
    for j,f in enumerate(freq):
            time.sleep(0.5)
            generate_beep(500, 300)
            b.write('freq %.1f\r'%(f/1e3))
            time.sleep(0.1)
            if old_code:
                b.write('txpowermv?\r')
                retval = b.readline()
                txvalues[j] = float(retval)/10
                b.write('rxpowermv?\r')
                retval = b.readline()
                rxvalues[j] = float(retval)/10
            else:
                txvalues[j] = b.txpowermv_float()
                rxvalues[j] = b.rxpowermv_float()
            
    return rxvalues, txvalues


# 


#edited to use set_freq function

def freq_sweep(b,freq, old_code=False):
    """sweep over an array of frequencies

    Parameters
    ==========
    b: Bridge12 object
        gives the connection
    freq: array of floats
        frequencies in Hz
        
    Returns
    =======
    rxvalues: array
        An array of floats, same length as freq, containing the receiver (reflected) power in dBm at each frequency.
    txvalues: array
        An array of floats, same length as freq, containing the transmitted power in dBm at each frequency.
    
    """    
    rxvalues = zeros(len(freq))
    txvalues = zeros(len(freq))
    #FREQUENCY AND RXPOWER SWEEP
    for j,f in enumerate(freq):
            generate_beep(500, 300)
            b.set_freq(f)  #is this what I would put here (the 'f')?
            txvalues[j] = b.txpowermv_float()
            rxvalues[j] = b.rxpowermv_float()     
    return rxvalues, txvalues


# b. Run Tuning Curve

# 


x = 'tuning_curve_181126'
freq = linspace(9.83e9,9.86e9, 100)

with Bridge12() as b:
    b.set_wg(True)
    b.set_amp(True)
    b.set_rf(True)
    b.set_power(10)
    rxvalues, txvalues = freq_sweep(b, freq)
    #rxvalues_old, txvalues_old = freq_sweep(b, freq, old_code=True)


# 


show_old = False
plot(freq/1e9, rxvalues, 'o-', alpha=0.5, markersize=3, label='rx - new') #tuning curve
plot(freq/1e9, txvalues, alpha=0.5, label='tx - new') #tuning curve
if show_old:
    plot(freq/1e9, rxvalues_old, 'o-', alpha=0.5, markersize=3, label='rx - old') #tuning curve
    plot(freq/1e9, txvalues_old, alpha=0.5, label='tx - old') #tuning curve
xlabel('frequency / GHz')
title('tuning curve')
#ylim(-0.5,3)
minorticks_on()
grid(True, which='both', alpha=0.1, linestyle='-')
legend(**dict(bbox_to_anchor=(1.05,1),loc=2,borderaxespad=0.))


# 



data = loadmat('TC2_10dBm_181127.mat')rx = data['rx'].flatten() #flatten the data
freq = data['freq'].flatten()
rx1 = rx[1:] #removes the faulty first data point at 6.8 mV
freq1 = freq[1:] #remove first frequency to match
md = (max(rx1)+min(rx1))/2

plot(freq1, rx1)
xlabel('Freq (Hz)')
ylabel('Rx (mV)')
title('Tuning Curve for Bridge 12')
axhline(y=md) #plot a line to see the half-maximum of the tuning dip

#determining where the dip crosses the rx-value md
crossovers = diff(rx1<md) 
halfway_idx = argwhere(diff(rx1<md))

#finding the frequency values at which this occurs
x_crossings = freq1[halfway_idx].flatten()
plot(x_crossings,r_[md,md],'o')

#printing out those values
print x_crossings
freq=linspace(x_crossings[0],x_crossings[1],100)


# 


with Bridge12() as b:
    print "test"


# with serial.Serial(thisport, timeout=3, baudrate=115200) as s:
#     bridge12_wait(s)
#     #Turn Components On and Power to 10dBm
#     set_wg(s,True)
#     set_amp(s, True)
#     set_rf(s, True)
#     set_power(s,5.0)
#     for j in range(1):
#         rxvalues = freq_sweep(s,freq)
#         plot(freq, rxvalues, alpha=0.5) #tuning curve
#     #Turn Components Off and Power to 0dBm
#     set_power(s,0)
#     set_rf(s,False)
#     set_wg(s,False)

# 


x += '_oldvnew'


# 


savemat(x+'.mat',{'freq':freq,
                  'tx':txvalues,'rx':rxvalues,
                  'tx_old':txvalues_old,'rx_old':rxvalues_old
                 })


# c. Load and Save the Image

# 


a= loadmat(x+'.mat')


# 


a = loadmat(x+'.mat')
x_axis = a.pop('freq').flatten()
for yname in a.keys():
    if not yname[0] == '_':
        plt.plot(x_axis,a[yname].flatten(), label=yname)
legend(**dict(bbox_to_anchor=(1.05,1),loc=2,borderaxespad=0.))
title(x)
savefig(x+'.png')


# 


#How do I add a title and Axis Labels to this Plot???
plt.plot(a['freq'].flatten(),a['rx'].flatten(), label='Rx')
plt.plot(a['freq'].flatten(), a['tx'].flatten(), label='Tx')
legend(**dict(bbox_to_anchor=(1.05,1),loc=2,borderaxespad=0.))
savefig(x+'.png')

