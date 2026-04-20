import unittest
import numpy as np
from Instruments.instrument_control import instrument_control


class TestPowerControlLiveShimProperties(unittest.TestCase):
    def read_initial_state(self, controller):
        readback = controller.get_shims()
        shim_names = sorted(readback)
        self.assertIn("Z0", readback)
        initial_voltages = {
            shim_name: readback[shim_name][0] for shim_name in shim_names
        }
        initial_currents = {
            shim_name: readback[shim_name][1] for shim_name in shim_names
        }
        return shim_names, initial_voltages, initial_currents

    def restore_initial_state(
        self, controller, shim_names, initial_voltages, initial_currents
    ):
        controller.shim_current[:] = [
            initial_currents[shim_name] for shim_name in shim_names
        ]
        controller.shim_voltage[:] = [
            initial_voltages[shim_name] for shim_name in shim_names
        ]

    def test_named_voltage_getter_matches_live_readback(self):
        with instrument_control() as ic:
            z0_voltage_V = ic.round_shim_voltage("Z0", 1.501)
            ic.shim_voltage[:] = 0.0
            ic.shim_current[:] = 1.5
            ic.shim_voltage["Z0"] = z0_voltage_V
            self.assertTrue(np.isclose(ic.shim_voltage["Z0"], z0_voltage_V))

    def test_slice_voltage_getter_matches_live_readback(self):
        with instrument_control() as ic:
            shim_names = sorted(ic.get_shims())
            requested_voltage_V = [2.0] * len(shim_names)
            ic.shim_voltage[:] = requested_voltage_V
            shim_readback = ic.get_shims()
            np.testing.assert_allclose(
                ic.shim_voltage[:],
                # the voltage is given by the second element of the tuple
                [shim_readback[shim_name][0] for shim_name in shim_names],
            )

    def test_named_current_getter_matches_live_readback(self):
        with instrument_control() as ic:
            z0_current_A = ic.round_shim_current("Z0", 0.508)
            ic.shim_current[:] = 0.0
            ic.shim_voltage[:] = 15.0
            ic.shim_current["Z0"] = z0_current_A
            print("current set to:", ic.shim_current["Z0"])
            self.assertTrue(np.isclose(ic.shim_current["Z0"], z0_current_A))

    def test_slice_current_getter_matches_live_readback(self):
        with instrument_control() as ic:
            shim_names = sorted(ic.get_shims())
            requested_current_A = [0.508] * len(shim_names)
            ic.shim_current[:] = requested_current_A
            shim_readback = ic.get_shims()
            np.testing.assert_allclose(
                ic.shim_current[:],
                # the current is given by the second element of the tuple
                [shim_readback[shim_name][1] for shim_name in shim_names],
            )

    def test_round_shim_voltage_accepts_list_and_array(self):
        with instrument_control() as ic:
            rounded_from_list = ic.round_shim_voltage("Z0", [0.0, 0.5, 1.0])
            rounded_from_array = ic.round_shim_voltage(
                "Z0", np.array([0.0, 0.5, 1.0])
            )
            self.assertEqual(len(rounded_from_list), 3)
            self.assertEqual(len(rounded_from_array), 3)


if __name__ == "__main__":
    unittest.main()
