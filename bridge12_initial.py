
# coding: utf-8

# initialization

# In[17]:


get_ipython().magic(u'pylab inline')
from serial.tools.list_ports import comports, grep
import serial
import time
#import winsound
print serial.VERSION

def generate_beep(freq,duration):
    "Generates a beep -- used winsound.Beep under windows -- use pygame under linux"
    return
def bridge12_wait(s):
    #time.sleep(5)
    def look_for(this_str):
        for j in range(1000):
            a = s.read_until(this_str+'\r\n')
            time.sleep(0.1)
            #print "a is",repr(a)
            print "look for",this_str,"try",j+1
            if this_str in a:
                print "found: ",this_str
                break
    look_for('MPS Started')
    look_for('System Ready')
    return


# print out the com ports, so we know what we're looking for

# In[14]:


[(j.device, j.hwid, j.vid, j.description, j.manufacturer) for j in comports()] #list comprehension


# Grab the port labeled as Arduino (since the Bridge12 microcontroller is an Arduino)

# In[15]:


portlist = [j.device for j in comports() if u'Arduino Due' in j.description]
assert len(portlist)==1
thisport = portlist[0]


# try the help command -- start with the simplest way possible, which uses very long wait times:

# In[8]:


with serial.Serial(thisport, timeout=1, baudrate=115200) as s:
    time.sleep(20)
    print "done"
    print "initial:",repr(s.read_all()) #Bridge 12 MPS Started
    s.write("help\r") #command for "help"
    time.sleep(10)
    print "after help:",repr(s.read_all()) #read help 


# Here, I play with minimal wait times.  Note the timeout=3, which causes readline and read_until to wait longer.  Though there are many lines of code to grab the help response, this should work for any multiline response.
# 
# Note that the read_all only reads what's in the buffer *right now* -- with the laptop we were able to call this once, because the bufer fills up so fast.  The USB on the pi seems to be slower.

# In[23]:


with serial.Serial(thisport, timeout=3, baudrate=115200) as s:
    bridge12_wait(s) #give it time to start
    s.write("help\r") #command for "help"
    print "after help:"
    entire_response = ''
    start = time.time()
    entire_response += s.readline()
    time_to_read_a_line = time.time()-start
    grab_more_lines = True
    while grab_more_lines:
        time.sleep(3*time_to_read_a_line)
        more = s.read_all()
        entire_response += more
        if len(more) == 0:
            grab_more_lines = False
    print repr(entire_response)


# freq query test

# In[24]:


with serial.Serial(thisport, timeout=3, baudrate=115200) as s:
    bridge12_wait(s)
    print "done"
    generate_beep(1000,300)
    s.write('freq?\r')
    print float(s.readline())
print "final"


# frequency test

# In[25]:


with serial.Serial(thisport, timeout=3, baudrate=115200) as s:
    bridge12_wait(s)
    #time.sleep(10)
    tmp = s.read_all()
    print repr(tmp)
    print "done"
    generate_beep(1000,300)
    for freq in linspace(9.45e9,9.51e9,11):
        time.sleep(0.5)
        generate_beep(500,300)
        s.write('freq %.1f\r'%(freq/1e3))
    generate_beep(1000,300)
    time.sleep(5)
    print "final:", s.read_all()


# preliminary code for ampstatus and freq (no need to run):

# In[ ]:


with serial.Serial(thisport, timeout=3, baudrate=115200) as s:
    bridge12_wait(s)
    print "done"
    print "initial:",s.readline()
    s.write('ampstatus 0\r') #command amp to be OFF
    s.write('ampstatus?\r') #command to check amp status (ON/OFF)
    amp_status = int(s.readline()) #read amp status as an integer
    print "amp status:",amp_status #print amp status 
    generate_beep(1000, 300) #signal to begin running through frequencies
    for mw_freq in linspace(9.45e9,9.51e9,11): #frequencies being ran through 
        time.sleep(0.5) #time between frequencies
        generate_beep(500, 300) #signal frequency change
        s.write('freq %.1f\r'%(mw_freq/1e3)) #changing frequency values to a string for Bridge12 to read
    generate_beep(1000, 300) #signal when finished running through frequencies
    time.sleep(5) #time to process
    print "final:",s.read_all() #print any values coming out from "with" loop


# playing with loops

# In[ ]:


for mw_freq in linspace(9.5e9,9.51e9,11):
    print 'freq %.1f\r'%(mw_freq/1e3) #printing


# just checking to see if sounds work

# In[ ]:


import winsound
duration = 1000  # millisecond
freq = 440  # Hz
generate_beep(880, 300)


# use this block for the tuning curve:

# In[ ]:


freq = linspace(9.4e9,9.9e9, 50)
rxvalues = zeros(len(freq))
with serial.Serial(thisport, timeout=3, baudrate=115200) as s:
    time.sleep(10)
    print "initial:",s.readline()
    #ampstatus commands
    s.write('ampstatus 0\r')
    time.sleep(0.5)
    s.write('ampstatus?\r')
    amp_status = int(s.readline())
    print "amp status:",amp_status
    time.sleep(5)
    generate_beep(1000,300)
    #frequency and rxpower
    for j,f in enumerate(freq):
        time.sleep(0.5)
        generate_beep(500, 300)
        s.write('freq %.1f\r'%(f/1e3)) #frequencies are now defined as f, NOT mw_freq
        s.write('rxpowerdbm?\r') 
        rx =s.readline()
        rxvalues[j] = float(rx)/10 #converting string to float point values
    generate_beep(1000, 300)
    time.sleep(5)
    print "final:",s.read_all()
print "j",j, "freq",f, "rxpower", rxvalues #'table' of values
plot(freq, rxvalues) #tuning curve


# another option for tuning curve (with sound):

# In[ ]:


freq = linspace(9.4e9,9.9e9, 50)
rxvalues = zeros(len(freq))
txvalues = zeros(len(freq))
with serial.Serial(thisport, timeout=3, baudrate=115200) as s:
    time.sleep(10) 
    print "done."
    print "initial:",s.readline()
    s.write('power?\r')
    check_set_power = float(s.readline())/10.
    print "power is set to",check_set_power
    s.write('ampstatus 0\r') #command amp to be OFF
    s.write('ampstatus?\r') #command to check amp status (ON/OFF)
    amp_status = int(s.readline()) #read amp status as an integer
    print "amp status:",amp_status #print amp status 
    s.write('rfstatus?\r') #command to check rf status (ON/OFF)
    rf_status = int(s.readline()) #read rf status as an integer
    print "rf status:",rf_status #print amp status 
    s.write('wgstatus 1\r') #switch to DNP mode
    s.read_all()
    #s.write('wgstatus?\r') #check wg status
    #wg_status1= int(s.readline()) #read wg status as an integer
    #print "wg status1:", wg_status1 #print wg status
    generate_beep(1000,300)
    set_power = 10.0
    s.write('power %d\r'%(round(set_power*10)))
    s.write('power?\r')
    check_set_power = float(s.readline())/10.
    print "power is set to",check_set_power
    generate_beep(1000, 300) #signal to begin running through frequencies
    for j,f in enumerate(freq):
        time.sleep(0.5) #time between frequencies
        generate_beep(500, 300) #signal frequency change
        s.write('freq %.1f\r'%(mw_freq/1e3)) #changing frequency values to a string for Bridge12 to read
        s.write('rxpowerdbm?\r')
        rxvalues[j]=float(s.readline())
        s.write('txpowerdbm?\r')
        txvalues[j]=float(s.readline())
    generate_beep(1000, 300) #signal when finished running through frequencies
    time.sleep(5) #time to process
    s.write('wgstatus 0\r')
    #s.write('wgstatus?\r')
    #wg_status0 = int(s.readline())
    print "wg status0:", wg_status0
    print "final:",s.read_all() #print any values coming out from "with" loop
plot(freq, rxvalues, alpha=0.5, label='Rx')
plot(freq, txvalues, alpha=0.5, label='Tx')
legend()


# testing the power

# In[ ]:


with serial.Serial(thisport, timeout=3, baudrate=115200) as s:
    s.read_until('Started\r\n') #read this instead of time sleep
    s.write('power 0\r')
    time.sleep(10)


# testing the waveguide switch

# In[ ]:


with serial.Serial(thisport, timeout=3, baudrate=115200) as s:
    s.read_until('Started\r\n')
    #s.write('power 100\r')
    for j in range(10):
        time.sleep(5)
        s.write('wgstatus?\r')
        print "wgstatus:",repr(s.readline())
    #print "power:", int(s.readline())


# testing frequency

# In[ ]:


with serial.Serial(thisport, timeout=3, baudrate=115200) as s:
    s.read_until('Started\r\n')
    time.sleep(10)
    generate_beep(700,300)
    s.write('freq 9505000.0/r')
    generate_beep(500,300)
print "done"


# testing both power and rfstatus

# In[ ]:


with serial.Serial(thisport, timeout=3, baudrate=115200) as s:
    s.read_until('Started\r\n')
    s.write('power 0\r')
    s.write('power?\r')
    print "power:", int(s.readline())
    generate_beep(1000,300)
    s.write('rfstatus 1\r')
    s.write('rfstatus?\r')
    print "rfstatus:", int(s.readline())
    generate_beep(1000,300)
    time.sleep(10)
print "done"


# messing with lots of on/off commands at once

# In[ ]:


with serial.Serial(thisport, timeout=3, baudrate=115200) as s:
    s.read_until('Started\r\n')
    s.write('power 0\r')
    s.write('power?\r')
    print "power:", int(s.readline())
    generate_beep(1000,300)
    time.sleep(5)
    s.write('wgstatus 1\r')
    s.write('wgstatus?\r')
    print "wgstatus:", int(s.readline())
    generate_beep(1000,300)
    time.sleep(5)
    s.write('ampstatus 1\r')
    s.write('ampstatus?\r')
    print "ampstatus:", int(s.readline())
    generate_beep(1000,300)
    time.sleep(5)
    s.write('rfstatus 1\r')
    s.write('rfstatus?\r')
    print "rfstatus:", int(s.readline())
    generate_beep(1000,300)
    time.sleep(10)
    s.write('rfstatus 0\r')
    s.write('rfstatus?\r')
    print "rfstatus:" int(s.readline)
    s.write('ampstatus 0\r')
    s.write('ampstatus?\r')
    print "ampstatus:" int(s.readline())
print "done"


# will be a fully operational tuning curve with power on/off

# In[ ]:


freq = linspace(9.845e9,9.855e9, 50)
rxvalues = zeros(len(freq))
with serial.Serial(thisport, timeout=3, baudrate=115200) as s:
    s.read_untill('Started\r\n')
    s.write('power 100\r')
    s.write('power?\r')
    print "power:", int(s.readline())
    generate_beep(1000,300)
    time.sleep(5)
    s.write('wgstatus 1\r')
    s.write('wgstatus?\r')
    print "wgstatus:", int(s.readline())
    generate_beep(1000,300)
    time.sleep(5)
    s.write('ampstatus 1\r')
    s.write('ampstatus?\r')
    print "ampstatus:", int(s.readline())
    generate_beep(1000,300)
    time.sleep(5)
    s.write('rfstatus 1\r')
    s.write('rfstatus?\r')
    print "rfstatus:", int(s.readline())
    generate_beep(1000,300)
    for j, f in enumerate(freq): 
        time.sleep(0.5) 
        generate_beep(500, 300) 
        s.write('freq %.3f\r'%(freq/1e3)) 
        s.write('rxpowerdbm?\r')
        rxvalues[j]=float(s.readline())
    generate_beep(1000,300)
    time.sleep(5)
    s.write('rfstatus 0\r')
    s.write('rfstatus?\r')
    print "rfstatus:", int(s.readline())
    generate_beep(1000,300)
    time.sleep(5)
    s.write('ampstatus 0\r')
    s.write('ampstatus?\r')
    print "ampstatus:", int(s.readline())
    generate_beep(1000,300)
    time.sleep(5)
    s.write('power 0\r')
    s.write('power?\r')
    print "power:", int(s.readline())
    generate_beep(1000,300)
    time.sleep(5)
plot(freq, rxvalues, alpha=1.0, label='Rx')
legend()

