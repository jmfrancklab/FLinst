# To be run from the computer connected to the EPR spectrometer
import sys, os, time, socket, pickle
from .logobj import logobj
from numpy.random import rand


IP = "0.0.0.0"
PORT = 6002

def main():
    print("once script works, move code into here")

if True:
    if True:
        if True:
            sock = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
            sock.bind((IP,PORT))
            this_logobj = logobj()
            def process_cmd(cmd,this_logobj):
                leave_open = True
                cmd = cmd.strip()
                print("I am processing",cmd)
                if this_logobj.currently_logging:
                    this_logobj.add(Rx = rand(),
                            power = rand(),
                            cmd = cmd)
                args = cmd.split(b' ')
                print("I split it to ",args)
                if len(args) == 3:
                    if args[0] == b'DIP_LOCK':
                        freq1 = float(args[1])
                        freq2 = float(args[2])
                        time.sleep(1)
                        min_f = 9.8
                        conn.send(('%0.6f'%min_f).encode('ASCII'))
                    else:
                        raise ValueError("I don't understand this 3 component command")
                if len(args) == 2:
                    if args[0] == b'SET_POWER':
                        dBm_setting = float(args[1])
                        last_power = dBm_setting
                        if dBm_setting > last_power + 3:
                            last_power += 3
                            print("SETTING TO...",last_power)
                            while dBm_setting > last_power+3:
                                last_power += 3
                                print("SETTING TO...",last_power)
                            print("FINALLY - SETTING TO DESIRED POWER")
                    else:
                        raise ValueError("I don't understand this 2 component command:"+str(args))
                elif len(args) == 1:
                    if args[0] == b'CLOSE':
                        print("closing connection")
                        leave_open = False
                        conn.close()
                    elif args[0] == b'GET_POWER':
                        result = rand()
                        conn.send(('%0.1f'%result).encode('ASCII'))
                    elif args[0] == b'QUIT':
                        print("closing connection")
                        conn.close()
                        leave_open = False
                        quit()
                    elif args[0] == b'START_LOG':
                        this_logobj.currently_logging = True
                    elif args[0] == b'STOP_LOG':
                        this_logobj.currently_logging = False
                        retval = pickle.dumps(this_logobj) +b'ENDTCPIPBLOCK'
                        conn.send(retval)
                        this_logobj.reset()
                    else:
                        raise ValueError("I don't understand this 1 component command"+str(args))
                return leave_open
            while True:
                sock.listen(1)
                print("I am listening")
                conn, addr = sock.accept()
                print("I have accepted from",addr)
                leave_open = True
                oldtimeout = conn.gettimeout()
                while leave_open:
                    conn.settimeout(0.001)
                    try:
                        data = conn.recv(1024)
                        conn.settimeout(oldtimeout)
                        if len(data) > 0:
                            print("I received a command '",data,"'")
                            for cmd in data.strip().split(b'\n'):
                                leave_open = process_cmd(cmd,this_logobj)
                        else:
                            print("no data received")
                    except socket.timeout as e:
                        if this_logobj.currently_logging:
                            this_logobj.add(Rx=rand(),
                                    power=rand())
