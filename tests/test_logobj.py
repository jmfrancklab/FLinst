import multiprocessing
import pickle
import socket
import tempfile
import unittest

import h5py
import numpy as np
import pyspecdata
from Instruments.logobj import logobj
from Instruments.power_control import power_control
from pyspecdata.file_saving.hdf_save_dict_to_group import (
    hdf_save_dict_to_group,
)


def socket_log_server(port_queue):
    """Serve a minimal subset of the power control protocol for log transfer."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("127.0.0.1", 0))
    sock.listen(1)
    port_queue.put(sock.getsockname()[1])
    this_logobj = logobj(array_len=8)
    sample_time = 1.0
    try:
        conn, _ = sock.accept()
        with conn:
            leave_open = True
            while leave_open:
                data = conn.recv(1024)
                if len(data) == 0:
                    break
                for cmd in data.strip().split(b"\n"):
                    cmd = cmd.strip()
                    if len(cmd) == 0:
                        continue
                    if this_logobj.currently_logging:
                        this_logobj.add(
                            time=sample_time,
                            Rx=sample_time + 1.0,
                            power=sample_time + 2.0,
                            cmd=cmd,
                        )
                        sample_time += 1.0
                    if cmd == b"START_LOG":
                        this_logobj.currently_logging = True
                    elif cmd == b"STOP_LOG":
                        this_logobj.currently_logging = False
                        conn.sendall(
                            pickle.dumps(this_logobj) + b"ENDTCPIPBLOCK"
                        )
                        this_logobj.reset()
                    elif cmd.startswith(b"SET_POWER "):
                        continue
                    elif cmd == b"CLOSE":
                        leave_open = False
                        break
                    else:
                        raise ValueError(
                            "unexpected command in test server: " + repr(cmd)
                        )
    finally:
        sock.close()


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

    def test_power_control_stop_log_unwraps_pickled_state_dict(self):
        """Socket log transfer should rebuild the pickled logobj correctly."""
        context = multiprocessing.get_context("fork")
        port_queue = context.Queue()
        server = context.Process(target=socket_log_server, args=(port_queue,))
        server.start()
        try:
            port = port_queue.get(timeout=5)
            with power_control(ip="127.0.0.1", port=port) as controller:
                controller.start_log()
                controller.set_power(10)
                recovered = controller.stop_log()
            server.join(timeout=5)
            self.assertFalse(server.is_alive())
            self.assertEqual(server.exitcode, 0)
        finally:
            if server.is_alive():
                server.terminate()
                server.join(timeout=5)
        self.assertIsInstance(recovered, logobj)
        self.assertIsInstance(recovered.total_log, np.ndarray)
        self.assertEqual(len(recovered.total_log), 2)
        self.assertEqual(
            recovered.log_dict[recovered.total_log[0]["cmd"]],
            b"SET_POWER 10.00",
        )
        self.assertEqual(
            recovered.log_dict[recovered.total_log[1]["cmd"]],
            b"STOP_LOG",
        )


if __name__ == "__main__":
    unittest.main()
