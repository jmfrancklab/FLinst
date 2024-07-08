#!/usr/bin/python
# use https://github.com/OE-FET/customxepr/blob/fc3ff0407d89f955a106056112e50b71a3ae8756/customxepr/main.py as a reference
import numpy as np
import matplotlib.pyplot as plt
import sys
import os
import time
sys.path.append('/opt/Bruker/xepr/sharedProDeL/Standard/XeprAPI/')
import XeprAPI
from datetime import datetime
#from pyspecdata import * 
date = datetime.now().strftime('%y%m%d')
output_name = '211116_120mM_TEMPOL' #USE THE SAME NAME AS YOUR QEPR DATASET
user = 'alex' #your user in xeprFiles
x = XeprAPI.Xepr()
x.XeprOpen()
h = x.XeprExperiment('AcqHidden')
freq = h["FrequencyMon"].value  # get current frequency
h["OpMode"].value = "Tune"
time.sleep(2.0)
print("the mode zoom is",h["ModeZoom"].value,"and the attenuation is",h["PowerAtten"].value,
    "the display is initially logarithmic",h["LogScaleEnab"].value)
print("setting to linear scale and 33 dB atten")
h["LogScaleEnab"].value = False
h["PowerAtten"].value = 33
tune_data = {}
h["RefArm"].value = "On"
def return_curve(h,n_points):
    n_curves = 5
    y_data = np.empty((n_curves,n_points))
    for j in range(n_curves):
        for i in range(0, n_points):
            y_data[j,i] = h["Data"][i]
    return y_data
def consistent_curve(h,n_points):
    keepgoing = True
    while keepgoing:
        y_data = return_curve(h, n_points)
        thisstd = np.sqrt(np.var(y_data,axis=0).mean())
        keepgoing = thisstd < 1e-7 or thisstd > 2e-3*y_data.max()
        if keepgoing:
            print("std",thisstd,"max",y_data.max(),
                    "capturing again")
    print("max",y_data.max(),"std %e"%thisstd)
    return y_data.mean(axis=0)

for mode_zoom in [1,2,4,8]:
    h['ModeZoom'].value = mode_zoom
    n_points = int(h["DataRange"][1])
    x_data = np.linspace(-0.5/mode_zoom,0.5/mode_zoom,n_points)
    y_data = consistent_curve(h, n_points)
    tune_data['y%d'%mode_zoom] = y_data
    tune_data['x%d'%mode_zoom] = x_data

tune_data_hpnoref = {}
h["RefArm"].value = "Off"
h["PowerAtten"].value = 20
time.sleep(2.0) # takes longer to turn up power
for mode_zoom in [1,2,4,8]:
    h['ModeZoom'].value = mode_zoom
    n_points = int(h["DataRange"][1])
    x_data = np.linspace(-0.5/mode_zoom,0.5/mode_zoom,n_points)
    y_data = consistent_curve(h, n_points)
    tune_data_hpnoref['y%d'%mode_zoom] = y_data
    tune_data_hpnoref['x%d'%mode_zoom] = x_data
h["RefArm"].value = "On"

for thistitle,thisdata in (('33 dB, arm on',tune_data),
    ('20 dB arm off',tune_data_hpnoref)):
    plt.figure()
    plt.title(thistitle)
    mydata = {}
    for mode_zoom in [1,2,4,8]:
        node_name = 'zoom%d'%mode_zoom
        y_data = thisdata['y%d'%mode_zoom]
        x_data = thisdata['x%d'%mode_zoom]
        plt.plot(x_data,y_data,'o', alpha=0.5, label='zoom level %d'%mode_zoom)
        thatdata = [[y_data],[x_data]]
        nd_thatdata = np.array(thatdata)
        mydata['zoom%d'%mode_zoom] = nd_thatdata
    plt.legend()
BASE_PATH = "../xeprFiles/Data/"+"%s"%user
filename = date+'_'+output_name
np.savez(os.path.join(BASE_PATH,filename),
        **mydata)
plt.show()
