"""
Testing the output of the Genesys power supply
============================
Identification, checking and setting the current.
"""


from Instruments import genesys
import time

with genesys("192.168.0.199") as g:
    print("IDN again!", g.ask("*IDN?"))
    print("output?", g.output)
    print("current limit?", g.I_limit)
    g.I_limit = 0.01
    print("current limit?", g.I_limit)
    g.output = True
    time.sleep(10)
