import importlib.util
import pathlib
import sys
import types
import unittest
import numpy as np

# {{{ Provide a minimal Instruments package so the descriptor and shim mapping
#     can be loaded in isolation from optional runtime dependencies.
instruments_pkg = types.ModuleType("Instruments")
instruments_pkg.__path__ = []
sys.modules["Instruments"] = instruments_pkg
hp_module = types.ModuleType("Instruments.HP6623A")
class StubHP6623A:
    pass
hp_module.HP6623A = StubHP6623A
sys.modules["Instruments.HP6623A"] = hp_module
# }}}

# {{{ Load the inst_dict_property descriptor directly from disk.
# TODO ☐: this seems very convoluted.  I would ask GPT why you can't just load
#         in a more normal way.  Even if you're going for a more minimal load,
#         why not uses resources or a similar library to help you do that in a
#         less convoluted way.
inst_dict_property_path = (
    pathlib.Path(__file__).resolve().parents[1]
    / "Instruments"
    / "inst_dict_property.py"
)
# TODO ☐: here it spend 3 lines (not counting wrapping) just loading a single module -- WHY??
inst_dict_property_spec = importlib.util.spec_from_file_location(
    "Instruments.inst_dict_property", inst_dict_property_path
)
inst_dict_property_module = importlib.util.module_from_spec(
    inst_dict_property_spec
)
inst_dict_property_spec.loader.exec_module(inst_dict_property_module)
sys.modules["Instruments.inst_dict_property"] = inst_dict_property_module
# }}}

# {{{ Load ShimDictMapping using the lightweight package context above.
# TODO ☐: same insanity
shim_mapping_path = (
    pathlib.Path(__file__).resolve().parents[1]
    / "Instruments"
    / "shim_current_mapping.py"
)
shim_mapping_spec = importlib.util.spec_from_file_location(
    "Instruments.shim_current_mapping", shim_mapping_path
)
shim_mapping_module = importlib.util.module_from_spec(shim_mapping_spec)
shim_mapping_spec.loader.exec_module(shim_mapping_module)
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
        self._shim_voltage_cache = {"Y": 0.0, "Z0": 0.0}
        self._shim_current_cache = {"Y": 0.0, "Z0": 0.0}

    @inst_dict_property_module.inst_dict_property
    def shim_voltage(self, shim_name):
        return self._shim_voltage_cache[shim_name]

    @shim_voltage.setter
    def shim_voltage(self, shim_name, voltage_V):
        self._shim_voltage_cache[shim_name] = voltage_V
        return voltage_V


class TestInstDictProperty(unittest.TestCase):
    def test_init_sorts_keys_alphabetically(self):
        shims = ShimDictMapping(
            {
                "Z0": (FakeHP(), 0),
                "Z2": (FakeHP(), 3),
                "A": (FakeHP(), 1),
                "Y": (FakeHP(), 2),
            }
        )
        self.assertEqual(list(shims._shim_dict), ["A", "Y", "Z0", "Z2"])

    def test_scalar_get_set_by_shim_name(self):
        hp = FakeHP()
        shims = ShimDictMapping({"Y": (hp, 1), "Z0": (hp, 0)})
        # set the owning dict mapping in a dict-like way
        shims.V_limit["Y"] = 7.5
        # make sure the voltage of the owned instrument instance is set
        self.assertEqual(hp.V_limit[1], 7.5)
        self.assertEqual(shims.V_limit["Y"], 7.5)

    def test_slice_get_returns_vector_in_sorted_key_order(self):
        # TODO ☐: ask GPT to read and preserve the explanatory comments that
        #         have been added and rename the test functions in a better
        #         way.
        hp = FakeHP()
        # manipulate the owned instrument instance 
        hp.V_limit[0] = 4.0
        hp.V_limit[1] = 8.0
        shims = ShimDictMapping({"Z0": (hp, 0), "Y": (hp, 1)})
        self.assertEqual(shims.V_limit[:], [8.0, 4.0])

    def test_integer_indexing_is_not_supported(self):
        hp = FakeHP()
        shims = ShimDictMapping({"Z0": (hp, 0), "Y": (hp, 1)})
        with self.assertRaises(TypeError):
            _ = shims.V_limit[0]
        with self.assertRaises(TypeError):
            shims.V_limit[0] = 3.25

    def test_slice_set_broadcasts_scalar(self):
        hp = FakeHP()
        shims = ShimDictMapping({"Z0": (hp, 0), "Y": (hp, 1)})
        shims.V_limit[:] = 3.25
        # TODO ☐: I realize that we need to modify both the source and the
        #         tests so that the things like shims.V_limit[:] return a numpy
        #         array, not a list.  The reason is that you will want to do
        #         vector math with them. (Assignment with rhs equal to either a
        #         list or a numpy array should be fine)
        self.assertEqual(shims.V_limit[:], [3.25, 3.25])

    def test_direct_vector_set_across_all_shims(self):
        hp = FakeHP()
        shims = ShimDictMapping({"Z0": (hp, 0), "Y": (hp, 1)})
        shims.V_limit = np.array([5.0, 6.0])
        self.assertEqual(shims.V_limit[:], [5.0, 6.0])
        self.assertEqual(shims.V_limit["Y"], 5.0)
        self.assertEqual(shims.V_limit["Z0"], 6.0)
        # {{{ if we try to assign to the wrong length of array, that should cause an error
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
        self.assertEqual(p.shim_voltage[:], [2.0, 3.0])
        self.assertEqual(p._shim_voltage_cache, {"Y": 2.0, "Z0": 3.0})

    def test_limited_slice_assignment(self):
        hp = FakeHP()
        shims = ShimDictMapping({"Z0": (hp, 0), "Y": (hp, 1), "A": (hp,3)})
        shims.shim_voltage[0:2] = [1,2]
        shims.shim_voltage[2] = 3
        self.assertEqual(p.shim_voltage[:], np.array([1.0, 2.0, 3.0]))


if __name__ == "__main__":
    unittest.main()
