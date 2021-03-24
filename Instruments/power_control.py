import socket
import sys
import time
import pickle

IP = "127.0.0.1"
#IP = "jmfrancklab-bruker.syr.edu"
#IP = "128.230.29.95"
if len(sys.argv) > 1:
    IP = sys.argv[1]
PORT = 6002

class power_control(object):
    """wraps the ethernet connection to the XEPR server and allows you to send commands (provides a with block)"""
    def __init__(self, ip=IP, port=PORT):
        print("target IP:", IP)
        print("target port:", PORT)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((IP, PORT))
    def __enter__(self):
        return self
    def __exit__(self, exception_type, exception_value, traceback):
        self.send('CLOSE')
        self.sock.close()
        return 
    def get(self):
        data = self.sock.recv(1024).decode('ASCII').strip()
        success = False
        for j in range(30):
            if len(data) == 0:
                data = self.sock.recv(1024).decode('ASCII').strip()
                time.sleep(0.01)
            else:
                success = True
                break
        if not success: raise ValueError("no response after 30 tries!!")
        return data
    def get_bytes(self,ending):
        data = self.sock.recv(1024)
        success = False
        for j in range(300):
            if len(data) == 0:
                time.sleep(0.01)
                data += self.sock.recv(1024)
            else:
                if data.endswith(ending):
                    success = True
                    break
                else:
                    data += self.sock.recv(1024)
        if not success: raise ValueError("no success after 300 tries!!")
        return data
    def send(self,msg):
        self.sock.send(msg.encode('ASCII'))
        return
    def set_power(self,dBm):
        "Sets the current field with high accuracy"
        self.send('SET_POWER %0.2f'%dBm)
        return float(self.get())
    def start_log(self):
        self.send('START_LOG')
        return
    def stop_log(self):
        self.send('STOP_LOG')
        retval = self.get_bytes(b'ENDARRAY')
        dict_idx = reval.find('ENDDICT')
        array_idx = reval.find('ENDARRAY')
        thedict = pickle.loads(retval[:dict_idx])
        thearray = pickle.loads(retval[dict_idx+6:array_idx])
        return thearray, thedict
