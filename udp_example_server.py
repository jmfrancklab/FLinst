import socket

#IP = "jmfrancklab-bruker.syr.edu"
#IP = "128.230.29.95"
#IP = "192.168.1.1"
IP = "0.0.0.0"
PORT = 5005

use_udp = False

if use_udp:
    sock = socket.socket(socket.AF_INET, # Internet
                         socket.SOCK_DGRAM) # UDP
    sock.bind((IP, PORT))
    while True:
        data, addr = sock.recvfrom(1024) # buffer size is 1024 bytes
        print("received message:", data)
else:
    sock = socket.socket(socket.AF_INET, # Internet
                         socket.SOCK_STREAM) # TCP
    sock.bind((IP, PORT))
    while True:
        sock.listen(1)
        conn, addr = sock.accept()
        data = conn.recv(1024) # buffer size is 1024 bytes
        conn.close()
        if len(data) > 0:
            print(data.strip())
