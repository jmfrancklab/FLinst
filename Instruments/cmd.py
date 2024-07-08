import Instruments
import Instruments.power_control_server
import Instruments.microwave_tuning_gui
import Instruments.nmr_signal_gui
from Instruments.XEPR_eth import xepr
import sys

def set_field(arg):
    with xepr() as x:
        field = float(arg)
        print("About to set field to %f"%field)
        assert field < 3700, "are you crazy??? field is too high!"
        assert field > 3300, "are you crazy?? field is too low!"
        field = x.set_field(field)
        print("field set to ",field)
def cmd():
    cmds = {
            "NMRsignal":Instruments.nmr_signal_gui.main,
            "MWtune":Instruments.microwave_tuning_gui.main,
            "server":Instruments.power_control_server.main,
            "quitServer":Instruments.power_control_server.main,
            "setField":set_field,
            }
    if len(sys.argv) < 2 or sys.argv[1] not in cmds.keys():
        raise ValueError("I don't know what you're talking about, the sub-commands are:\n\n\t"+'\n\t'.join(cmds.keys()))
    elif len(sys.argv) == 2:
        cmds[sys.argv[1]]()
    elif len(sys.argv) > 2:
        cmds[sys.argv[1]](*sys.argv[2:])
