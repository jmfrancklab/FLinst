import datetime
import numpy as np
import RPi.GPIO as g
import time
import gpiozero
from w1thermsensor import W1ThermSensor

g.setmode(g.BCM) 
g.setwarnings(False)

sensor1 = W1ThermSensor(W1ThermSensor.THERM_SENSOR_DS18B20, "00000976a304") #reservoir
sensor2 = W1ThermSensor(W1ThermSensor.THERM_SENSOR_DS18B20, "00000b2fa615") # waterbath
threshold_temp = 40.00
min_temp = 20.00

#pump stuff
pump_pin = 18
freq = 100
g.setup(pump_pin, g.OUT)
p = g.PWM(pump_pin, freq)

#heater stuff
heater_pin = 27
g.setup(heater_pin, g.OUT)
heater = g.PWM(heater_pin, True)
heater_on = False
   
#arrays for time/temp recording
nowtime = datetime.datetime.now()
temp1_array = []
temp2_array = []
time_array = []
NaN = float('nan')

#actual code
try:
    while True: 
        messages = []
        maxr = 3
        retries = 0
        while retries<maxr: 
            try: 
                p.start(100) # starting the motor at 100 dutycycle
                temp1 = sensor1.get_temperature()
                temp2 = sensor2.get_temperature()
                temp1_array.append(temp1) #Assign either bath/reservoir
                temp2_array.append(temp2)
                time_array.append(nowtime)
                # in here insert code for motor to run as well
               
                if temp1 == 85.00:
                    print "Ignoring temperature"
                    temp1_array.append(NaN)
                else: 
                    print "Reservoir is %0.2F"%temp1
                    print "Water Bath is %0.2F"%temp2
                    temp1_array.append(temp1)
                if (temp2 < threshold_temp): 
                    print "Heater On" 
                    g.output(heater_pin, True)
                    heater_on = True
                    time.sleep(1)
                    if heater_on is True: 
                        print "..."
                    else: 
                        print "Restarting Heater"
                        g.output(heater_pin, True)
                        heater_on = True        
                else: 
                    print "Temp Exceeded"
                    if heater_on is True: 
                        print "Turning Heater Off"
                        g.output(heater_pin, False) 
                        heater_on = False
                    else:
                        print "Heater Off"
                        heater_on = False 
                np.savez("190723Heater1.npz", temp1 = temp1_array, temp2 = temp2_array, nowtime = time_array)
            except Exception as e: 
                messages.append(e)
                print "Encountered error..."
                time.sleep(1)
            retries += 1

except KeyboardInterrupt:
    p.stop()
    heater_on = False
    g.output(heater_pin, False)
    g.cleanup()
