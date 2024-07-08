import numpy as np
import pandas as pd
import matplotlib as mp
import matplotlib.pyplot as plt

data = np.load('190723Heater1.npz')
temp = data['temp1']
temp2 = data['temp2']
temp1 = temp[::2]

print(len(temp1))
print(len(temp2))

time = []
for i in range(len(temp2)):
    time.append(i)

plt.plot(time, temp1, label = 'Reservoir')
plt.plot(time, temp2, label = 'Waterbath')
plt.xlabel('Seconds')
plt.ylabel('Temperature in Celcius')
plt.legend(loc='best')
plt.title('Dry Run #1')
plt.show()

plt.plot(time, temp1, label = 'Reservoir')
plt.xlabel('Seconds') 
plt.ylabel('Temperature in Celcius')
plt.legend(loc='best')
plt.title('Reservoir #1')
plt.show()

plt.plot(time, temp2, 'darkorange', label = 'Waterbath')
plt.xlabel('Seconds') 
plt.ylabel('Temperature in Celcius')
plt.legend(loc='best')
plt.title('Waterbath #1')
plt.show()

