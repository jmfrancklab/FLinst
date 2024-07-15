"""
In the scenario where running run_Hahn_echo.py is required,
(usually for a new probe or diagnostic purposes) this function
allows to user to manually determine the appropriate gamma_eff_MHz_G
parameter. To do so the user types 'py find_gamma_eff.py XX'
where XX is the offset of the signal (being careful to note positive
or negative offsets!). The function then takes this offset and the current
gamma_eff_MHz_G as well as the carrierFreq_MHz in the users active.ini to 
determine the appropriate gamma_eff_MHz_G.
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
