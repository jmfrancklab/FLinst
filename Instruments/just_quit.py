"""just quit the server"""
from pyspecdata import init_logging
from Instruments import power_control

def main():
    with power_control() as p:
        p.arrange_quit()
