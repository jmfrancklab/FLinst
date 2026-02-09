import importlib.util
import os
import pathlib
import sys
import types
import unittest

import numpy as np

# Create a minimal Instruments package so we can load only the needed modules.
instruments_pkg = types.ModuleType("Instruments")
instruments_pkg.__path__ = []
sys.modules["Instruments"] = instruments_pkg

# Load gpib_eth from disk so we can use the real Prologix connection code.
gpib_eth_path = pathlib.Path(__file__).resolve().parents[1] / "Instruments" / "gpib_eth.py"
gpib_eth_spec = importlib.util.spec_from_file_location("Instruments.gpib_eth", gpib_eth_path)
gpib_eth_module = importlib.util.module_from_spec(gpib_eth_spec)
gpib_eth_spec.loader.exec_module(gpib_eth_module)
sys.modules["Instruments.gpib_eth"] = gpib_eth_module

# Load log_inst so HP6623A can access its logger dependency.
log_inst_path = pathlib.Path(__file__).resolve().parents[1] / "Instruments" / "log_inst.py"
log_inst_spec = importlib.util.spec_from_file_location("Instruments.log_inst", log_inst_path)
log_inst_module = importlib.util.module_from_spec(log_inst_spec)
log_inst_spec.loader.exec_module(log_inst_module)
sys.modules["Instruments.log_inst"] = log_inst_module

# Load HP6623A using the package context above to keep imports localized.
hp6623a_path = pathlib.Path(__file__).resolve().parents[1] / "Instruments" / "HP6623A.py"
hp6623a_spec = importlib.util.spec_from_file_location("Instruments.HP6623A", hp6623a_path)
hp6623a_module = importlib.util.module_from_spec(hp6623a_spec)
hp6623a_spec.loader.exec_module(hp6623a_module)

HP6623A = hp6623a_module.HP6623A
prologix_connection = gpib_eth_module.prologix_connection


class TestHP6623AChannelProperty(unittest.TestCase):
    """Verify channel-aware property behavior on the actual HP6623A hardware."""
    @classmethod
    def setUpClass(cls):
        """Connect to the instrument, or skip the suite if it is unavailable."""
        # Require an explicit address so the test never hits the wrong device.
        if "HP6623A_ADDRESS" not in os.environ:
            raise unittest.SkipTest("HP6623A_ADDRESS not set; skipping hardware test.")
        address = int(os.environ["HP6623A_ADDRESS"])

        # Allow optional overrides for the Prologix connection settings.
        if "PROLOGIX_IP" in os.environ:
            ip = os.environ["PROLOGIX_IP"]
        else:
            ip = "192.168.0.162"
        if "PROLOGIX_PORT" in os.environ:
            port = int(os.environ["PROLOGIX_PORT"])
        else:
            port = 1234

        # Connect to the Prologix adapter and the HP6623A itself.
        try:
            cls.prologix = prologix_connection(ip=ip, port=port)
            cls.hp = HP6623A(prologix_instance=cls.prologix, address=address)
        except Exception as exc:
            # Clean up any partial connection before skipping.
            if hasattr(cls, "hp"):
                try:
                    cls.hp.close()
                except Exception:
                    pass
            if hasattr(cls, "prologix"):
                try:
                    cls.prologix.close()
                except Exception:
                    pass
            raise unittest.SkipTest("HP6623A not available: %s" % exc)

    @classmethod
    def tearDownClass(cls):
        """Close the instrument connection after the test suite completes."""
        if hasattr(cls, "hp"):
            cls.hp.close()
        if hasattr(cls, "prologix"):
            cls.prologix.close()

    def require_channels(self, count):
        """Skip a test when the connected instrument has too few channels."""
        if len(self.hp._known_output_state) < count:
            self.skipTest("Not enough channels available for this test.")

    def setUp(self):
        """Reset all channels to zero to keep the hardware in a safe state."""
        for ch in range(len(self.hp._known_output_state)):
            self.hp.voltage[ch] = 0

    def tearDown(self):
        """Return all channels to zero after each test."""
        for ch in range(len(self.hp._known_output_state)):
            self.hp.voltage[ch] = 0

    def test_scalar_get_set(self):
        """Exercise scalar indexing and assignment on the instrument."""
        self.require_channels(1)
        self.hp.voltage[0] = 0.1
        self.assertAlmostEqual(self.hp.voltage[0], 0.1, places=2)

    def test_slice_get_set(self):
        """Exercise slice indexing and scalar broadcasting."""
        self.require_channels(3)
        self.hp.voltage[0:2] = 0.05
        self.assertEqual(self.hp.voltage[0:3], [0.05, 0.05, 0.0])

    def test_list_get_set(self):
        """Exercise list indexing and list assignment."""
        self.require_channels(3)
        self.hp.voltage[[0, 2]] = [0.1, 0.2]
        self.assertEqual(self.hp.voltage[0:3], [0.1, 0.0, 0.2])

    def test_numpy_vector_set(self):
        """Exercise numpy vector assignment for channel values."""
        self.require_channels(3)
        self.hp.voltage[0:3] = np.array([0.2, 0.3, 0.4])
        self.assertEqual(self.hp.voltage[0:3], [0.2, 0.3, 0.4])

    def test_direct_numpy_vector_set(self):
        """Exercise direct vector assignment across all channels."""
        self.require_channels(3)
        self.hp.voltage = np.array([0.3, 0.3, 0.3])
        self.assertEqual(self.hp.voltage, [0.3, 0.3, 0.3])

    def test_len_and_iter(self):
        """Exercise len() and iteration of the proxy."""
        self.require_channels(3)
        self.hp.voltage[0:3] = [0.0, 0.1, 0.2]
        self.assertEqual(len(self.hp.voltage), len(self.hp._known_output_state))
        self.assertEqual(list(self.hp.voltage)[0:3], [0.0, 0.1, 0.2])

    def test_invalid_index_and_direct_set(self):
        """Exercise error paths for invalid index and direct attribute set."""
        self.require_channels(1)
        with self.assertRaises(IndexError):
            _ = self.hp.voltage[len(self.hp._known_output_state) + 1]
        with self.assertRaises(AttributeError):
            # Assignment to a scalar without indexing is not allowed.
            self.hp.voltage = 3


if __name__ == "__main__":
    unittest.main()
