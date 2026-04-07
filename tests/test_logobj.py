import tempfile
import unittest

import h5py
import numpy as np
import pyspecdata
from Instruments.logobj import logobj
from pyspecdata.file_saving.hdf_save_dict_to_group import (
    hdf_save_dict_to_group,
)


class TestLogobjSerialization(unittest.TestCase):
    """Verify that logobj survives the HDF state round-trip it uses in practice."""

    def build_log(self):
        """Create a small log with both blank and non-blank commands."""
        result = logobj(array_len=4)
        result.add(time=1.0, Rx=2.0, power=3.0, cmd=None)
        result.add(time=4.0, Rx=5.0, power=6.0, cmd="set power")
        result.add(time=7.0, Rx=8.0, power=9.0, cmd="set freq")
        return result

    def test_hdf_helper_roundtrip_restores_logobj_from_hdf_group(self):
        """Round-trip through the helper and restore directly from the HDF group."""
        self.assertTrue(hasattr(pyspecdata, "__file__"))
        original = self.build_log()
        state = original.__getstate__()
        self.assertEqual(
            set(state["array"].keys()),
            {"NUMPY_DATA", "dictkeys", "dictvalues"},
        )
        recovered = logobj()
        with tempfile.NamedTemporaryFile(suffix=".h5") as tmpfile:
            with h5py.File(tmpfile.name, "w") as h5file:
                log_group = h5file.create_group("log")
                hdf_save_dict_to_group(log_group, state)
            with h5py.File(tmpfile.name, "r") as h5file:
                log_group = h5file["log"]
                self.assertEqual(list(log_group.keys()), ["array"])
                self.assertIn("dictkeys", log_group["array"].attrs)
                self.assertIn("dictvalues", log_group["array"].attrs)
                recovered.__setstate__(log_group)
        self.assertEqual(recovered.log_dict, original.log_dict)
        np.testing.assert_array_equal(recovered.total_log, original.total_log)

    def test_legacy_hdf_layout_still_loads(self):
        """Legacy files with dict metadata on the group should still load."""
        original = self.build_log()
        recovered = logobj()
        with tempfile.NamedTemporaryFile(suffix=".h5") as tmpfile:
            with h5py.File(tmpfile.name, "w") as h5file:
                log_group = h5file.create_group("log")
                log_group.attrs["dictkeys"] = list(original.log_dict.keys())
                log_group.attrs["dictvalues"] = [
                    thisval.encode("utf-8")
                    if isinstance(thisval, str)
                    else thisval
                    for thisval in original.log_dict.values()
                ]
                log_group.create_dataset(
                    "array",
                    data=original.total_log,
                    dtype=original.total_log.dtype,
                )
            with h5py.File(tmpfile.name, "r") as h5file:
                recovered.__setstate__(h5file["log"])
        self.assertEqual(recovered.log_dict, original.log_dict)
        np.testing.assert_array_equal(recovered.total_log, original.total_log)


if __name__ == "__main__":
    unittest.main()
