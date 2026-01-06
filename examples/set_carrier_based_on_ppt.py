import SpinCore_pp

print("(hit enter for OK, ctrl-c if not!)\n\n")
myconfig = SpinCore_pp.configuration("active.ini")
input(
    "your ppt value is set to %0.6f" % (myconfig["guessed_MHz_to_GHz"])
    + " does that look right?"
)
new_carrier = myconfig["guessed_MHz_to_GHz"] * myconfig["uw_dip_center_GHz"]
input(
    f"Your NMR frequency was {myconfig['carrierFreq_MHz']:0.6f} and I'm going"
    f" to change it to {new_carrier:0.6f}, which is a difference of"
    f" {(new_carrier-myconfig['carrierFreq_MHz'])*1e3:0.6f} kHz.  Does that"
    " sound OK?"
)
myconfig["carrierFreq_MHz"] = new_carrier
myconfig.write()
