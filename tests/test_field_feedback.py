"""Focused, hardware-free regression tests for Z0 field feedback behavior."""

import importlib.util
import pathlib
import sys
import types
import pytest
from types import SimpleNamespace

# Load field_feedback without importing the Instruments package, whose
# __init__ imports optional hardware drivers that are not available in CI.
module_path = (
    pathlib.Path(__file__).resolve().parents[1]
    / "Instruments"
    / "field_feedback.py"
)
spec = importlib.util.spec_from_file_location(
    "field_feedback_under_test",
    module_path,
)
field_feedback = importlib.util.module_from_spec(spec)
pyspecdata_module = types.ModuleType("pyspecdata")
pyspecdata_module.strm = lambda *args: " ".join(map(str, args))
previous_pyspecdata = sys.modules.get("pyspecdata")
sys.modules["pyspecdata"] = pyspecdata_module
try:
    spec.loader.exec_module(field_feedback)
finally:
    if previous_pyspecdata is None:
        del sys.modules["pyspecdata"]
    else:
        sys.modules["pyspecdata"] = previous_pyspecdata


class FakeHall:
    def __init__(self, fields):
        self.fields = iter(fields)
        self.last_field = fields[-1]

    @property
    def field_in_G(self):
        self.last_field = next(self.fields, self.last_field)
        return self.last_field


class FakeGenesys:
    def __init__(self, measured_current_A=1.0):
        self.output = True
        self.V_limit = 25.0
        self.I_meas = measured_current_A
        self.current_settings_A = []

    @property
    def I_limit(self):
        return self.current_settings_A[-1]

    @I_limit.setter
    def I_limit(self, value):
        self.current_settings_A.append(value)


class TrackingLimit(dict):
    def __init__(self, readback, *args, **kwargs):
        self.readback = readback
        super().__init__(*args, **kwargs)

    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        self.readback[key] = value


class CountingRead(dict):
    def __init__(self, *args, **kwargs):
        self.read_count = 0
        super().__init__(*args, **kwargs)

    def __getitem__(self, key):
        self.read_count += 1
        return super().__getitem__(key)


class FakeShims:
    def __init__(
        self,
        voltage_V=1.0,
        current_A=0.1,
        current_limit_A=1.0,
        hardware_max_voltage_V=15.0,
    ):
        self.V_read = {"Z0": voltage_V}
        self.V_limit = TrackingLimit(self.V_read, Z0=voltage_V)
        self.I_read = CountingRead(Z0=current_A)
        self.I_limit = CountingRead(Z0=current_limit_A)
        self.output = {"Z0": 1}
        self.z0_instrument = SimpleNamespace(max_V={0: hardware_max_voltage_V})

    def instrument(self, name):
        assert name == "Z0"
        return self.z0_instrument

    def channel(self, name):
        assert name == "Z0"
        return 0

    def round_to_allowed(self, kind, name, value):
        assert (kind, name) == ("V", "Z0")
        return value


def feedback_config(**overrides):
    values = {
        "current_v_field_A_G": 0.1,
        "gamma_eff_mhz_g": 1.0,
        "magnet_settle_long": 0.0,
        "magnet_settle_medium": 0.0,
        "magnet_settle_short": 0.0,
        "tolerance_Hz": 10000.0,
        "z0_midpoint_setting_G": 1.0,
        "z0_field_v_voltage_G_V": 1.0,
        "main_field_resolution_G": 0.4,
        "z0_max_voltage_V": 5.71,
    }
    values.update(overrides)
    return values


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    monkeypatch.setattr(field_feedback.time, "sleep", lambda _: None)


def record_main_field_adjustments(
    monkeypatch,
    fields,
    shims,
):
    # {{{ set it up to capture info in adjusted_fields_G rather than actually
    #     run the field sweep
    adjusted_fields_G = []

    def record_adjustment(B0_des_G, config_dict, h, gen):
        adjusted_fields_G.append(B0_des_G)

    monkeypatch.setattr(
        field_feedback,
        "adjust_main_field",
        record_adjustment,
    )
    # }}}
    result = field_feedback.ramp_field(
        10.0,
        feedback_config(),
        FakeHall(fields),
        FakeGenesys(),
        shims,
        settling_attempts=10,
    )
    return result, adjusted_fields_G


def test_usable_z0_request_does_not_adjust_main_field(monkeypatch):
    adjusted_fields_G = []
    monkeypatch.setattr(
        field_feedback,
        "adjust_main_field",
        lambda B0_des_G, config_dict, h, gen: adjusted_fields_G.append(
            B0_des_G
        ),
    )
    shims = FakeShims(voltage_V=1.0)
    result = field_feedback.ramp_field(
        10.0,
        feedback_config(),
        FakeHall([9.5, 9.5, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0]),
        FakeGenesys(),
        shims,
        settling_attempts=10,
    )
    assert result == 10.0
    assert adjusted_fields_G == []
    assert shims.V_limit["Z0"] == 1.5


# TODO ☐:  explain why 15.1 is supposed to raise an error? And why is this the place to test for it
@pytest.mark.parametrize("maximum_voltage_V", [0.0, 15.1])
def test_invalid_z0_maximum_is_rejected(maximum_voltage_V):
    with pytest.raises(ValueError, match="z0_max_voltage_V"):
        field_feedback.ramp_field(
            10.0,
            feedback_config(z0_max_voltage_V=maximum_voltage_V),
            FakeHall([10.0]),
            FakeGenesys(),
            FakeShims(),
        )
