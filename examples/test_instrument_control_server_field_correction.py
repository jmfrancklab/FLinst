"""Start the instrument-control log for ten minutes, then stop it."""

import logging
import time

from Instruments import instrument_control

LOG_DURATION_S = 10 * 60

logging.basicConfig(level=logging.INFO)
with instrument_control() as ic:
    logging.info("Starting instrument-control log")
    ic.start_log()
    for minutes_left in range(LOG_DURATION_S // 60, 0, -1):
        print(f"({minutes_left}) minutes left")
        time.sleep(60)
    logging.info("Stopping instrument-control log")
    ic.stop_log()
