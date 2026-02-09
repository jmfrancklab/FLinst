import importlib.util
import pathlib
import sys
import types
import unittest

import numpy as np
# {{{ Provide minimal stub modules to satisfy relative imports in HP6623A.
#     The test uses these shims to load the descriptor without importing
#     optional dependencies from the Instruments package.
instruments_pkg = types.ModuleType("Instruments")
instruments_pkg.__path__ = []
sys.modules["Instruments"] = instruments_pkg

gpib_eth_module = types.ModuleType("Instruments.gpib_eth")
gpib_eth_module.gpib_eth = object
sys.modules["Instruments.gpib_eth"] = gpib_eth_module

log_inst_module = types.ModuleType("Instruments.log_inst")
log_inst_module.logger = types.SimpleNamespace(debug=lambda *args, **kwargs: None)
sys.modules["Instruments.log_inst"] = log_inst_module
# }}}

# {{{ Load the channel_property descriptor directly to avoid package import side effects.
#     This isolates the descriptor implementation so the tests can run in
#     environments without hardware driver dependencies.
module_path = pathlib.Path(__file__).resolve().parents[1] / "Instruments" / "HP6623A.py"
spec = importlib.util.spec_from_file_location("Instruments.HP6623A", module_path)
HP6623A_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(HP6623A_module)
channel_property = HP6623A_module.channel_property
# }}}


class DemoInstrument:
    """Simple fixture class to demonstrate channel_property get/set behavior."""
    def __init__(self, channel_count):
        """Store channel values and known output states for proxy sizing."""
        self.values = list(range(channel_count))
        self._known_output_state = [0 for _ in self.values]

    @channel_property
    def voltage(self, channel):
        """Return the stored value for the requested channel."""
        return self.values[channel]

    @voltage.setter
    def voltage(self, channel, value):
        """Update the stored value for the requested channel."""
        self.values[channel] = value
        return


class TestChannelProperty(unittest.TestCase):
    """Verify channel_property indexing, assignment, and error behavior."""
    def test_scalar_get_set(self):
        """Exercise scalar indexing and assignment."""
        inst = DemoInstrument(3)
        self.assertEqual(inst.voltage[1], 1)
        inst.voltage[2] = 4.5
        self.assertEqual(inst.voltage[2], 4.5)

    def test_slice_get_set(self):
        """Exercise slice indexing and scalar broadcasting."""
        inst = DemoInstrument(4)
        self.assertEqual(inst.voltage[1:3], [1, 2])
        inst.voltage[0:2] = 7.0
        self.assertEqual(inst.voltage[0:3], [7.0, 7.0, 2])

    def test_list_get_set(self):
        """Exercise list indexing and list assignment."""
        inst = DemoInstrument(4)
        self.assertEqual(inst.voltage[[0, 2]], [0, 2])
        inst.voltage[[1, 3]] = [8.0, 9.0]
        self.assertEqual(inst.voltage[0:4], [0, 8.0, 2, 9.0])

    def test_numpy_vector_set(self):
        """Exercise numpy vector assignment for channel values."""
        inst = DemoInstrument(3)
        inst.voltage[0:3] = np.array([1.0, 2.0, 3.0])
        self.assertEqual(inst.voltage[0:3], [1.0, 2.0, 3.0])

    def test_direct_numpy_vector_set(self):
        """Exercise direct vector assignment across all channels."""
        inst = DemoInstrument(3)
        inst.voltage = np.array([3.0, 3.0, 3.0])
        self.assertEqual(inst.voltage[0:3], [3.0, 3.0, 3.0])

    def test_len_and_iter(self):
        """Exercise len() and iteration of the proxy."""
        inst = DemoInstrument(3)
        self.assertEqual(len(inst.voltage), 3)
        self.assertEqual(list(inst.voltage), [0, 1, 2])

    def test_invalid_index_and_direct_set(self):
        """Exercise error paths for invalid index and direct attribute set."""
        inst = DemoInstrument(2)
        with self.assertRaises(IndexError):
            _ = inst.voltage[5]
        with self.assertRaises(AttributeError):
            # Assignment to a scalar without indexing is not allowed.
            inst.voltage = 3


if __name__ == "__main__":
    # {{{ Allow running this module directly for demonstration.
    #     This keeps the module usable as a simple, executable example.
    unittest.main()
    # }}}
