import sys
from Instruments import power_control_server, just_quit, cmd
from SpinCore_pp import calc_vdlist

def main():
    script_name = sys.argv[0]
    if "power_control_server" in script_name:
        power_control_server.main()
    elif "quit_power_control" in script_name:
        just_quit.main()
    elif "FLInst" in script_name:
        cmd.cmd()
    elif "calc_tempol_vd" in script_name:
        calc_vdlist.print_tempo_vdlist()
    else:
        print(f"Unknown command: {script_name}")

if __name__ == "__main__":
    main()
