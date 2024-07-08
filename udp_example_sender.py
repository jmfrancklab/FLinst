import socket
import sys

#IP = "127.0.0.1"
IP = "jmfrancklab-bruker.syr.edu"
#IP = "128.230.29.95"
if len(sys.argv) > 1:
    IP = sys.argv[1]
PORT = 6001
MESSAGE = "Hello, World!"

use_udp = False

print("target IP:", IP)
print("target port:", PORT)
print("Using UDP (vs. TCP)",use_udp)
print("message:", MESSAGE)

if use_udp:
    sock = socket.socket(socket.AF_INET, # Internet
            socket.SOCK_DGRAM) # UDP
    sock.sendto(MESSAGE, (IP, PORT))
else:
    sock = socket.socket(socket.AF_INET, # Internet
            socket.SOCK_STREAM) # TCP
    sock.connect((IP, PORT))
    sock.send(MESSAGE)
    sock.close()
