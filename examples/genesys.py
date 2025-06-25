from Instruments import genesys
import time

with genesys("192.168.0.199") as g:
    g.V_over = 30.0  # overvoltage protection
    print("V_over", g.V_over)
    g.V_max = 25.0  # set the voltage limit to the voltage we think we will need at *max* field
    print("V_max", g.V_max)
    g.A_max = 0.01  # start with a low current
    print("A_max", g.A_max)
    print("about to turn on output")
    g.output = True
    print("Is output on?", g.output)
    time.sleep(10)
    print("Is output on?", g.output)
    # no need to turn off -- the context block does that for us!!
