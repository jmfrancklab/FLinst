import usb.core

import usb.util

dev = usb.core.find(idVendor=8580, idProduct=28)
if dev is None:
    raise ValueError('Device not found')
    
dev.reset()
dev.set_configuration()
cfg = dev.get_active_configuration()
#help(dev.ctrl_transfer)
intf = cfg[(0,0)]
#print intf
for j in intf.endpoints():
    #j.write('*idn?\n',timeout=1000)
    print("result for",j)
    thisdir = usb.util.endpoint_direction(j.bEndpointAddress)
    if thisdir == usb.util.ENDPOINT_IN:
        print("direction IN")
    elif thisdir == usb.util.ENDPOINT_OUT:
        print("direction OUT")
    #print j.read(100)
    #print help(usb.util.ctrl_direction)
    
