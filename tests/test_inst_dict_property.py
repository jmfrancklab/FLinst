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
inst_dict_property_path = (
    pathlib.Path(__file__).resolve().parents[1]
    / "Instruments"
    / "inst_dict_property.py"
)
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


class TestInstDictProperty(unittest.TestCase):
    def test_init_sorts_keys_alphabetically(self):
        shims = ShimDictMapping(
            {
                "Z0": (FakeHP(), 0),
                "A": (FakeHP(), 1),
                "Y": (FakeHP(), 2),
            }
        )
        self.assertEqual(list(shims._shim_dict), ["A", "Y", "Z0"])

    def test_scalar_get_set_by_shim_name(self):
        hp = FakeHP()
        shims = ShimDictMapping({"Y": (hp, 1), "Z0": (hp, 0)})
        shims.V_limit["Y"] = 7.5
        self.assertEqual(hp.V_limit[1], 7.5)
        self.assertEqual(shims.V_limit["Y"], 7.5)

    def test_slice_get_returns_vector_in_sorted_key_order(self):
        # TODO: We don't want this capability. We don't want to
        # refer them as an index number. Always a string key of a dict
        hp = FakeHP()
        hp.V_limit[0] = 4.0
        hp.V_limit[1] = 8.0
        shims = ShimDictMapping({"Z0": (hp, 0), "Y": (hp, 1)})
        self.assertEqual(shims.V_limit[:], [8.0, 4.0])

    def test_slice_set_broadcasts_scalar(self):
        hp = FakeHP()
        shims = ShimDictMapping({"Z0": (hp, 0), "Y": (hp, 1)})
        shims.V_limit[:] = 3.25
        self.assertEqual(shims.V_limit[:], [3.25, 3.25])

    def test_direct_vector_set_across_all_shims(self):
        hp = FakeHP()
        shims = ShimDictMapping({"Z0": (hp, 0), "Y": (hp, 1)})
        shims.V_limit = np.array([5.0, 6.0])
        self.assertEqual(shims.V_limit[:], [5.0, 6.0])

        # Also here, test that Y is 5 and Z0 is 6 (sorted key order).
        self.assertEqual(shims.V_limit["Y"], 5.0)
        self.assertEqual(shims.V_limit["Z0"], 6.0)
        # TODO: The previous should work but the codex may need to change the
        # project code to make it work.


if __name__ == "__main__":
    unittest.main()
