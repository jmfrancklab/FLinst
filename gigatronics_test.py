from Instruments import prologix_connection,gigatronics

with prologix_connection() as p:
    with gigatronics(prologix_instance=p, address=7) as g:
        meter_power = g.read_power()
        print("POWER READING",meter_power)
print("Done.")
quit()
