from Instruments import Bridge12
import time
with Bridge12() as b:
    b.set_wg(True)
    time.sleep(10)
    b.set_wg(False)
