# try:
from .serial_instrument import SerialInstrument
from .gds import GDS_scope
from .afg import AFG
from .bridge12 import Bridge12
from .power_control import power_control

__all__ = ["SerialInstrument", "GDS_scope", "AFG", "Bridge12"]
# except:
#    print "warning! serial (USB) instruments not available!"
#    __all__ = []
from .HP8672A import HP8672A
from .HP6623A import HP6623A
from .gigatronics import gigatronics
from .gpib_eth import prologix_connection
from .logobj import logobj
from .hall_probe import LakeShore475
from .genesys import genesys

__all__ += [
    "HP8672A",
    "HP6623A",
    "gigatronics",
    "prologix_connection",
    "power_control",
    "LakeShore475",
    "genesys",
]
