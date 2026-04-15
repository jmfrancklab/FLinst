import importlib
import pathlib
import sys
import types
import unittest
import numpy as np
from collections import OrderedDict

# {{{ Provide a minimal Instruments package so the descriptor and shim mapping
#     can be loaded in isolation from optional runtime dependencies.
instruments_dir = pathlib.Path(__file__).resolve().parents[1] / "Instruments"
instruments_pkg = types.ModuleType("Instruments")
instruments_pkg.__path__ = [str(instruments_dir)]
sys.modules["Instruments"] = instruments_pkg
hp_module = types.ModuleType("Instruments.HP6623A")

class StubHP6623A:
    pass

hp_module.HP6623A = StubHP6623A
sys.modules["Instruments.HP6623A"] = hp_module
# }}}

# {{{ Load the inst_dict_property descriptor directly from disk.
inst_dict_property_module = importlib.import_module(
    "Instruments.inst_dict_property"
)
# }}}

# {{{ Load ShimDictMapping using the lightweight package context above.
shim_mapping_module = importlib.import_module(
    "Instruments.shim_current_mapping"
)
ShimDictMapping = shim_mapping_module.ShimDictMapping
# }}}


class FakeHP(StubHP6623A):
    def __init__(self):
        self.I_limit = [0.0, 0.0, 0.0]
        self.V_limit = [0.0, 0.0, 0.0]
        self.I_read = [0.1, 0.2, 0.3]
        self.V_read = [1.1, 1.2, 1.3]
        self.output = [0, 0, 0]
        self.overvoltage = [0.0, 0.0, 0.0]
        self.safe_current = None

    def round_to_allowed(self, which_limit, channel, value):
        return value


class FakePowerControl:
    def __init__(self):
        self._shim_voltage_cache = OrderedDict([("Y", 0.0), ("Z0", 0.0)])
        self._shim_current_cache = OrderedDict([("Y", 0.0), ("Z0", 0.0)])

    @inst_dict_property_module.inst_dict_property
    def shim_voltage(self, shim_name):
        return self._shim_voltage_cache[shim_name]

    @shim_voltage.setter
    def shim_voltage(self, shim_name, voltage_V):
        self._shim_voltage_cache[shim_name] = voltage_V
        return voltage_V


class TestInstDictProperty(unittest.TestCase):
    def test_constructor_sorts_keys_alphabetically(self):
        shims = ShimDictMapping(
            {
                "Z0": (FakeHP(), 0),
                "Z2": (FakeHP(), 3),
                "A": (FakeHP(), 1),
                "Y": (FakeHP(), 2),
            }
        )
        self.assertEqual(list(shims.keys()), ["A", "Y", "Z0", "Z2"])

    def test_named_access_reads_and_writes_underlying_instrument_values(self):
        hp = FakeHP()
        shims = ShimDictMapping({"Y": (hp, 1), "Z0": (hp, 0)})
        # set the owning dict mapping in a dict-like way
        shims.V_limit["Y"] = 7.5
        # make sure the voltage of the owned instrument instance is set
        self.assertEqual(hp.V_limit[1], 7.5)
        self.assertEqual(shims.V_limit["Y"], 7.5)

    def test_slice_access_returns_values_in_sorted_key_order(self):
        hp = FakeHP()
        # manipulate the owned instrument instance
        hp.V_limit[0] = 4.0
        hp.V_limit[1] = 8.0
        shims = ShimDictMapping({"Z0": (hp, 0), "Y": (hp, 1)})
        assert type(shims.V_limit[:]) is np.ndarray
        np.testing.assert_array_equal(shims.V_limit[:], np.array([8.0, 4.0]))

    def test_integer_indexing_reads_and_writes_by_sorted_position(self):
        hp = FakeHP()
        shims = ShimDictMapping({"Z0": (hp, 0), "Y": (hp, 1)})
        self.assertEqual(shims.V_limit[0], 0.0)
        shims.V_limit[0] = 3.25
        self.assertEqual(shims.V_limit["Y"], 3.25)
        shims.V_limit[1] = 3.75
        self.assertEqual(shims.V_limit["Y"], 3.25)
        self.assertEqual(shims.V_limit["Z0"], 3.75)
        self.assertEqual(hp.V_limit[1], 3.25)

    def test_slice_assignment_broadcasts_scalar_to_all_shims(self):
        hp = FakeHP()
        shims = ShimDictMapping({"Z0": (hp, 0), "Y": (hp, 1)})
        shims.V_limit[:] = 3.25
        assert type(shims.V_limit[:]) is np.ndarray
        np.testing.assert_array_equal(shims.V_limit[:], np.array([3.25, 3.25]))

    def test_direct_vector_assignment_updates_all_shims_and_validates_length(
        self,
    ):
        hp = FakeHP()
        shims = ShimDictMapping({"Z0": (hp, 0), "Y": (hp, 1)})
        shims.V_limit = np.array([5.0, 6.0])
        assert type(shims.V_limit[:]) is np.ndarray
        np.testing.assert_array_equal(shims.V_limit[:], np.array([5.0, 6.0]))
        self.assertEqual(shims.V_limit["Y"], 5.0)
        self.assertEqual(shims.V_limit["Z0"], 6.0)
        # {{{ if we try to assign to the wrong length of array, that should
        #     cause an error
        with self.assertRaises(ValueError):
            shims.V_limit = np.array([5.0])
        with self.assertRaises(ValueError):
            shims.V_limit = np.array([5.0, 5.0, 5.0])
        # }}}

    def test_cache_backed_owner_supports_named_and_slice_assignment(self):
        p = FakePowerControl()
        p.shim_voltage["Y"] = 1.5
        self.assertEqual(p.shim_voltage["Y"], 1.5)
        p.shim_voltage[:] = [2.0, 3.0]
        assert type(p.shim_voltage[:]) is np.ndarray
        np.testing.assert_array_equal(p.shim_voltage[:], np.array([2.0, 3.0]))
        self.assertEqual(p._shim_voltage_cache, {"Y": 2.0, "Z0": 3.0})

    def test_limited_slice_assignment(self):
        hp = FakeHP()
        shims = ShimDictMapping({"Z0": (hp, 0), "Y": (hp, 1), "A": (hp, 2)})
        print("length is", len(shims.V_limit))
        print("length is", len(shims.V_limit[0:2]))
        shims.V_limit[0:2] = [1, 2]
        shims.V_limit[2] = 3
        np.testing.assert_array_equal(
            shims.V_limit[:], np.array([1.0, 2.0, 3.0])
        )


if __name__ == "__main__":
    unittest.main()
