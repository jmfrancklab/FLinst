import importlib.util
import pathlib
import sys
import types
import unittest

# Provide minimal stub modules to satisfy relative imports in HP6623A.
instruments_pkg = types.ModuleType("Instruments")
instruments_pkg.__path__ = []
sys.modules["Instruments"] = instruments_pkg

gpib_eth_module = types.ModuleType("Instruments.gpib_eth")
gpib_eth_module.gpib_eth = object
sys.modules["Instruments.gpib_eth"] = gpib_eth_module

log_inst_module = types.ModuleType("Instruments.log_inst")
log_inst_module.logger = types.SimpleNamespace(debug=lambda *args, **kwargs: None)
sys.modules["Instruments.log_inst"] = log_inst_module

# Load the channel_property descriptor directly to avoid package import side effects.
module_path = pathlib.Path(__file__).resolve().parents[1] / "Instruments" / "HP6623A.py"
spec = importlib.util.spec_from_file_location("Instruments.HP6623A", module_path)
HP6623A_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(HP6623A_module)
channel_property = HP6623A_module.channel_property


class DemoInstrument:
    # Simple fixture class to demonstrate channel_property get/set behavior.
    def __init__(self, values):
        # Store channel values and known output states for proxy sizing.
        self.values = list(values)
        self._known_output_state = [0 for _ in self.values]

    @channel_property
    def voltage(self, channel):
        # Return the stored value for the requested channel.
        return self.values[channel]

    @voltage.setter
    def voltage(self, channel, value):
        # Update the stored value for the requested channel.
        self.values[channel] = value
        return


class TestChannelProperty(unittest.TestCase):
    # Verify scalar indexing and assignment for the channel-aware property.
    def test_scalar_get_set(self):
        inst = DemoInstrument([0.0, 1.0, 2.0])
        self.assertEqual(inst.voltage[1], 1.0)
        inst.voltage[2] = 4.5
        self.assertEqual(inst.voltage[2], 4.5)

    # Verify slice indexing and broadcasting assignment.
    def test_slice_get_set(self):
        inst = DemoInstrument([0.0, 1.0, 2.0, 3.0])
        self.assertEqual(inst.voltage[1:3], [1.0, 2.0])
        inst.voltage[0:2] = 7.0
        self.assertEqual(inst.voltage[0:3], [7.0, 7.0, 2.0])

    # Verify list indexing and list assignment behavior.
    def test_list_get_set(self):
        inst = DemoInstrument([0.0, 1.0, 2.0, 3.0])
        self.assertEqual(inst.voltage[[0, 2]], [0.0, 2.0])
        inst.voltage[[1, 3]] = [8.0, 9.0]
        self.assertEqual(inst.voltage[0:4], [0.0, 8.0, 2.0, 9.0])

    # Verify that iteration and length reflect the channel count.
    def test_len_and_iter(self):
        inst = DemoInstrument([1.0, 2.0, 3.0])
        self.assertEqual(len(inst.voltage), 3)
        self.assertEqual(list(inst.voltage), [1.0, 2.0, 3.0])

    # Verify error behavior for invalid index and direct attribute set.
    def test_invalid_index_and_direct_set(self):
        inst = DemoInstrument([1.0, 2.0])
        with self.assertRaises(IndexError):
            _ = inst.voltage[5]
        with self.assertRaises(AttributeError):
            inst.voltage = 3.0


if __name__ == "__main__":
    # Allow running this module directly for demonstration.
    unittest.main()
