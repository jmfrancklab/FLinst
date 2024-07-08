# To be run from the computer connected to the EPR spectrometer
import sys, os, time, socket
sys.path.append('/opt/Bruker/xepr/sharedProDeL/Standard/XeprAPI/')
import XEPR_eth
x = XeprAPI.Xepr()
cmd = x.XeprCmds
cmd.aqSetServer('localhost')

# {{{ commands that can be run
def wait_for_run(exp):
    start_time = time.time()
    while time.time() - start_time < 60:
        time.sleep(0.1)
        if exp.aqGetExpState() == 5:
            print("experiment is running!!!")
            return
        elif exp.aqGetExpState() == 4:
            print("experiment is not running")
        else:
            print("I don't know what Exp State code",exp.aqGetExpState(),"means!")
    raise ValueError("timed out")
def wait_for_stop(exp):
    start_time = time.time()
    while time.time() - start_time < 60:
        time.sleep(0.1)
        if exp.aqGetExpState() == 4:
            print("experiment has stopped!!!")
            return
        elif exp.aqGetExpState() == 5:
            print("experiment is still running")
        else:
            print("I don't know what Exp State code",exp.aqGetExpState(),"means!")
    raise ValueError("timed out")
def wait_for_field(exp, field):
    r"""assuming we are running a sweep, wait for the field to hit the right value, and then abort"""
    start_time = time.time()
    while time.time() - start_time < 60:
        time.sleep(0.1)
        print("the field is",exp['FieldPosition'].value)
        if exp['FieldPosition'].value >= field:
            exp.aqExpAbort()
            wait_for_stop(exp)
            print("after stopping, the field is",exp['FieldPosition'].value)
            return exp['FieldPosition'].value
    raise ValueError("timed out")
def set_coarse_field(desired_field):
    """just set the field to the nearest 0.1 G"""
    cmd.aqExpDel('set_field') # at least in IPython, this doesn't raise an error
    cmd.aqExpLoad(os.path.expanduser('~xuser/xeprFiles/Acquisition/set_field'))
    exp = x.XeprExperiment()
    print("trying to coarse set the field to",desired_field)
    exp["CenterField"].value = round(desired_field*10)/10.0 # nearest 0.1 beneath where I want to be
    print("about to set the field (coarse) to",exp["CenterField"].value)
    exp["SweepWidth"].value = 0.0
    exp["SweepTime"].value = 20
    exp.aqExpRun()
    wait_for_run(exp)
    return exp['FieldPosition'].value
def set_field(desired_field):
    """run a sweep to set the field with high resolution

    requires the existence of experiment `set_field` in
    the Acquisition folder"""
    cmd.aqExpDel('set_field') # at least in IPython, this doesn't raise an error
    cmd.aqExpLoad(os.path.expanduser('~xuser/xeprFiles/Acquisition/set_field'))
    exp = x.XeprExperiment()
    exp["CenterField"].value = int(desired_field*10)/10.0 # nearest 0.1 beneath where I want to be
    exp["SweepWidth"].value = 0.2
    exp["SweepTime"].value = 20
    exp.aqExpRun()
    wait_for_run(exp)
    field_result = wait_for_field(exp,desired_field)
    return field_result
# }}}

IP = "0.0.0.0"
PORT = 6001

sock = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
sock.bind((IP,PORT))
while True:
    sock.listen(1)
    print("I am listening")
    conn, addr = sock.accept()
    print("I have accepted from",addr)
    leave_open = True
    while leave_open:
        data = conn.recv(1024)
        if len(data) > 0:
            print("I received a command '",data,"'")
            args = data.split(' ')
            print("I split it to ",args)
            if len(args) == 2:
                if args[0] == 'SET_FIELD':
                    print("they want to get the field")
                    field = float(args[1])
                    field_result = set_field(field)
                    conn.send('%f'%field_result)
                elif args[0] == 'SET_COARSE_FIELD':
                    field = float(args[1])
                    field_result = set_coarse_field(field)
                    conn.send('%f'%field_result)
                else:
                    raise ValueError("I don't understand this 2 component command")
            elif len(args) == 1:
                if args[0] == 'GET_FIELD':
                    print("they want to get the field")
                    exp = x.XeprExperiment()
                    result = '%0.5f'%exp['FieldPosition'].value
                    print("about to reply",result)
                    conn.send(result)
                elif args[0] == 'CLOSE':
                    print("closing connection")
                    conn.close()
                    leave_open = False
                else:
                    raise ValueError("I don't understand this 1 component command")
        else:
            print("no data received")
