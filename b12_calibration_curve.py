from pyspecdata import *
from Instruments import Bridge12, prologix_connection, gigatronics
import time

id_string = '191030_b12_calib_2'

start_power = 0.0
stop_power = 30.0 # Actually -5
power_points = 25 
b12_powers = linspace(start_power,stop_power,power_points)

raw_points = 250
raw_powers = zeros(raw_points*power_points)

count = 0
with prologix_connection() as p:
    with Bridge12() as b:
        with gigatronics(prologix_instance=p, address=7) as g:
            print("BEGINNING...")
            b.set_wg(True)
            print("Switched waveguide")
            b.set_rf(True)
            print("Turned microwaves on")
            b.set_amp(True)
            b.calib_set_freq(9.85e9)
            print("Set frequency")
            for b12_setting in b12_powers:
                print("*** *** ***")
                print("SETTING POWER",b12_setting)
                print("*** *** ***")
                b.calib_set_power(b12_setting)
                time.sleep(2)
                for x in range(raw_points):
                    raw_powers[count] = g.read_power()
                    count += 1

avg_powers = zeros(power_points)
for x in range(power_points):
    avg_powers[x] = raw_powers[raw_points*x:raw_points*(x+1)].mean()
savez(id_string,prog_powers=b12_powers,read_powers=avg_powers)
