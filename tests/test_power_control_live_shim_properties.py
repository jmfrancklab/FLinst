import os
import unittest

import numpy as np

from Instruments.power_control import power_control


@unittest.skipUnless(
    os.environ.get("FLINST_RUN_LIVE_TESTS") == "1",
    "live power-control test requires FLINST_RUN_LIVE_TESTS=1",
)
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
        with power_control() as p:
            shim_names, initial_voltages, initial_currents = (
                self.read_initial_state(p)
            )
            z0_voltage_V = 1.5

            try:
                p.shim_voltage[:] = 0.0
                p.shim_current[:] = 1.5
                p.shim_voltage["Z0"] = z0_voltage_V
                voltage_readback = p.get_shims()
                self.assertTrue(np.isclose(p.shim_voltage["Z0"], z0_voltage_V))
                self.assertTrue(
                    np.isclose(p.shim_voltage["Z0"], voltage_readback["Z0"][0])
                )
            finally:
                self.restore_initial_state(
                    p, shim_names, initial_voltages, initial_currents
                )

    def test_slice_voltage_getter_matches_live_readback(self):
        with power_control() as p:
            shim_names, initial_voltages, initial_currents = (
                self.read_initial_state(p)
            )
            requested_voltage_V = [2.0] * len(shim_names)

            try:
                p.shim_voltage[:] = requested_voltage_V
                voltage_readback = p.get_shims()
                np.testing.assert_allclose(
                    p.shim_voltage[:],
                    [
                        voltage_readback[shim_name][0]
                        for shim_name in shim_names
                    ],
                )
            finally:
                self.restore_initial_state(
                    p, shim_names, initial_voltages, initial_currents
                )

    def test_named_current_getter_matches_live_readback(self):
        with power_control() as p:
            shim_names, initial_voltages, initial_currents = (
                self.read_initial_state(p)
            )
            z0_current_A = 0.5

            try:
                p.shim_current[:] = 0.0
                p.shim_voltage[:] = 15.0
                p.shim_current["Z0"] = z0_current_A
                current_readback = p.get_shims()
                self.assertTrue(np.isclose(p.shim_current["Z0"], z0_current_A))
                self.assertTrue(
                    np.isclose(p.shim_current["Z0"], current_readback["Z0"][1])
                )
            finally:
                self.restore_initial_state(
                    p, shim_names, initial_voltages, initial_currents
                )

    def test_slice_current_getter_matches_live_readback(self):
        with power_control() as p:
            shim_names, initial_voltages, initial_currents = (
                self.read_initial_state(p)
            )
            requested_current_A = [0.7] * len(shim_names)

            try:
                p.shim_current[:] = requested_current_A
                current_readback = p.get_shims()
                np.testing.assert_allclose(
                    p.shim_current[:],
                    [
                        current_readback[shim_name][1]
                        for shim_name in shim_names
                    ],
                )
            finally:
                self.restore_initial_state(
                    p, shim_names, initial_voltages, initial_currents
                )

    def test_round_shim_voltage_accepts_list_and_array(self):
        with power_control() as p:
            rounded_from_list = p.round_shim_voltage("Z0", [0.0, 0.5, 1.0])
            rounded_from_array = p.round_shim_voltage(
                "Z0", np.array([0.0, 0.5, 1.0])
            )
            self.assertEqual(len(rounded_from_list), 3)
            self.assertEqual(len(rounded_from_array), 3)


if __name__ == "__main__":
    unittest.main()
