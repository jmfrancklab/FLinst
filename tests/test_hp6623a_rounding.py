import importlib.util
import os
import pathlib
import sys
import types
import unittest


# Create a minimal Instruments package so we can load only the needed modules.
instruments_pkg = types.ModuleType("Instruments")
instruments_pkg.__path__ = []
sys.modules["Instruments"] = instruments_pkg

# Load channel_property from disk for HP6623A dependency.
channel_property_path = (
    pathlib.Path(__file__).resolve().parents[1]
    / "Instruments"
    / "channel_property.py"
)
channel_property_spec = importlib.util.spec_from_file_location(
    "Instruments.channel_property", channel_property_path
)
channel_property_module = importlib.util.module_from_spec(
    channel_property_spec
)
channel_property_spec.loader.exec_module(channel_property_module)
sys.modules["Instruments.channel_property"] = channel_property_module

# Load gpib_eth from disk so we can use the real Prologix connection code.
gpib_eth_path = (
    pathlib.Path(__file__).resolve().parents[1] / "Instruments" / "gpib_eth.py"
)
gpib_eth_spec = importlib.util.spec_from_file_location(
    "Instruments.gpib_eth", gpib_eth_path
)
gpib_eth_module = importlib.util.module_from_spec(gpib_eth_spec)
gpib_eth_spec.loader.exec_module(gpib_eth_module)
sys.modules["Instruments.gpib_eth"] = gpib_eth_module

# Load log_inst so HP6623A can access its logger dependency.
log_inst_path = (
    pathlib.Path(__file__).resolve().parents[1] / "Instruments" / "log_inst.py"
)
log_inst_spec = importlib.util.spec_from_file_location(
    "Instruments.log_inst", log_inst_path
)
log_inst_module = importlib.util.module_from_spec(log_inst_spec)
log_inst_spec.loader.exec_module(log_inst_module)
sys.modules["Instruments.log_inst"] = log_inst_module

# Load HP6623A using the package context above to keep imports localized.
hp6623a_path = (
    pathlib.Path(__file__).resolve().parents[1] / "Instruments" / "HP6623A.py"
)
hp6623a_spec = importlib.util.spec_from_file_location(
    "Instruments.HP6623A", hp6623a_path
)
hp6623a_module = importlib.util.module_from_spec(hp6623a_spec)
hp6623a_spec.loader.exec_module(hp6623a_module)

HP6623A = hp6623a_module.HP6623A
prologix_connection = gpib_eth_module.prologix_connection


class TestHP6623ARounding(unittest.TestCase):
    """Verify rounding helpers for voltage/current settings."""

    @classmethod
    def setUpClass(cls):
        """Connect to the instrument, or skip the suite if it is
        unavailable."""
        # Require an explicit address so the test never hits the wrong device.
        if "HP6623A_ADDRESS" not in os.environ:
            os.environ["HP6623A_ADDRESS"] = "3"
        address = int(os.environ["HP6623A_ADDRESS"])
        # Allow optional overrides for the Prologix connection settings.
        if "PROLOGIX_IP" not in os.environ:
            os.environ["PROLOGIX_IP"] = "192.168.0.162"
        ip = os.environ["PROLOGIX_IP"]
        if "PROLOGIX_PORT" not in os.environ:
            os.environ["PROLOGIX_PORT"] = "1234"
        port = int(os.environ["PROLOGIX_PORT"])

        # Connect to the Prologix adapter and the HP6623A itself.
        try:
            cls.prologix = prologix_connection(ip=ip, port=port)
        except Exception as exc:
            raise unittest.SkipTest(
                "prologix not available -- orig error:\n%s" % exc
            )
        try:
            cls.hp = HP6623A(prologix_instance=cls.prologix, address=address)
        except Exception as exc:
            raise unittest.SkipTest(
                "HP6623A not available -- orig error:\n%s" % exc
            )
        cls.hp.safe_current_on_enable = 1.8

    @classmethod
    def tearDownClass(cls):
        """Close the instrument connection after the test suite completes."""
        if hasattr(cls, "hp"):
            cls.hp.close()
        if hasattr(cls, "prologix"):
            cls.prologix.close()

    def test_v_round_to_allowed(self):
        """Verify V rounding snaps to nearest allowed step."""
        ch = 0
        res = self.hp.res_V[ch]
        base = self.hp.min_V[ch]
        value = base + res * 2.4
        expected = base + round((value - base) / res) * res
        self.assertAlmostEqual(
            self.hp._V_round_to_allowed(ch, value), expected, places=6
        )

    def test_v_round_to_allowed_above_max(self):
        """Verify V rounding rejects values above max."""
        ch = 0
        with self.assertRaises(AssertionError):
            self.hp._V_round_to_allowed(ch, self.hp.max_V[ch] + 0.1)

    def test_i_round_to_allowed(self):
        """Verify I rounding snaps to nearest allowed step."""
        ch = 1
        res = self.hp.res_I[ch]
        base = self.hp.min_I[ch]
        value = base + res * 3.6
        expected = base + round((value - base) / res) * res
        self.assertAlmostEqual(
            self.hp._I_round_to_allowed(ch, value), expected, places=6
        )

    def test_i_round_to_allowed_above_max(self):
        """Verify I rounding rejects values above max."""
        ch = 1
        with self.assertRaises(AssertionError):
            self.hp._I_round_to_allowed(ch, self.hp.max_I[ch] + 0.1)

    def test_v_limit_rounds_and_reads_back(self):
        """Set V_limit and verify readback matches rounded value."""
        ch = 0
        res = self.hp.res_V[ch]
        base = self.hp.min_V[ch]
        value = base + res * 2.4
        expected = base + round((value - base) / res) * res
        self.hp.V_limit[ch] = value
        self.assertAlmostEqual(self.hp.V_limit[ch], expected, places=3)
        self.hp.V_limit[ch] = 0.0

    def test_i_limit_rounds_and_reads_back(self):
        """Set I_limit and verify readback matches rounded value."""
        ch = 1
        res = self.hp.res_I[ch]
        base = self.hp.min_I[ch]
        value = base + res * 3.6
        expected = base + round((value - base) / res) * res
        self.hp.I_limit[ch] = value
        self.assertAlmostEqual(self.hp.I_limit[ch], expected, places=3)
        self.hp.I_limit[ch] = 0.0


if __name__ == "__main__":
    unittest.main()
