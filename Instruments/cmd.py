import Instruments
import Instruments.power_control_server
import Instruments.microwave_tuning_gui
import Instruments.nmr_signal_gui
import Instruments.gds_tune_gui
from Instruments.XEPR_eth import xepr
import sys
import os


def ensure_active_ini():
    """Guard GUI subcommands by requiring an active.ini in the current folder."""
    if not os.path.isfile("active.ini"):
        raise RuntimeError(
            "active.ini must be present in %s before launching this GUI"
            % os.getcwd()
        )

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
            "GDStune":Instruments.gds_tune_gui.main,
            "server":Instruments.power_control_server.main,
            "quitServer":Instruments.power_control_server.main,
            "setField":set_field,
            }
    if len(sys.argv) < 2 or sys.argv[1] not in cmds.keys():
        raise ValueError("I don't know what you're talking about, the sub-commands are:\n\n\t"+'\n\t'.join(cmds.keys()))
    command = sys.argv[1]
    if command in ("NMRsignal", "MWtune", "GDStune"):
        ensure_active_ini()
    if len(sys.argv) == 2:
        cmds[command]()
    elif len(sys.argv) > 2:
        cmds[command](*sys.argv[2:])
