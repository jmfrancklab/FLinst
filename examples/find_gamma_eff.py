"""
This is a simple script used with run_hahn_echo.py for getting on NMR
resonance.
After seeing your signal with a ppg scripts, run 'py find_gamma_eff.py
####' where the value indicated if the frequency offset of you're signal
from the carrier frequency.
This script then adjusts the gamma effective in your active.ini, for
getting on resonance.
Then rerun the ppg script to see that you are now on resonance and the
location of your signal is adjusted.
"""
# PR this needs a docstring, which should make it clear why we are doing this
import SpinCore_pp
import sys

config_dict = SpinCore_pp.configuration("active.ini")
print("Your original gamma effective was:", config_dict["gamma_eff_MHz_G"])
Delta_nu = float(sys.argv[1]) / 1e6
new_gamma = config_dict["gamma_eff_MHz_G"] * (
    1 - (Delta_nu / config_dict["carrierFreq_MHz"])
)
print("based on your offset of %d" % Delta_nu)
print("your new gamma_eff should be %.8f" % new_gamma)
config_dict["gamma_eff_MHz_G"] = new_gamma
config_dict.write()
