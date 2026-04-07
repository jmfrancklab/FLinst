"""just quit the server"""
from pyspecdata import init_logging
from Instruments import instrument_control

def main():
    with instrument_control() as p:
        p.arrange_quit()
