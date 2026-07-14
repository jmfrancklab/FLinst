"""Focused tests for the main-field and Z0 feedback logic."""

import importlib.util
from pathlib import Path
import sys
import types

import numpy as np
import pytest


# Load field_feedback.py directly so these unit tests do not initialize the
# complete Instruments package or require a connected instrument stack.
MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "Instruments"
    / "field_feedback.py"
)

pyspecdata_stub = types.ModuleType("pyspecdata")
pyspecdata_stub.strm = lambda *args: " ".join(str(x) for x in args)
sys.modules.setdefault("pyspecdata", pyspecdata_stub)

spec = importlib.util.spec_from_file_location("field_feedback", MODULE_PATH)
field_feedback = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(field_feedback)


class FakeHall:
    """Return a prescribed sequence, then repeat the last field value."""

    def __init__(self, values):
        self.values = list(values)
        self.read_count = 0

    @property
    def field_in_G(self):
        self.read_count += 1
        if len(self.values) > 1:
            return self.values.pop(0)
        return self.values[0]

    def zero_probe(self):
        pass


class FakeGenesys:
    def __init__(self, measured_current=0.0, output=True):
        self.output = output
        self.V_limit = 0.0
        self._I_meas = measured_current
        self._I_limit = measured_current
        self.current_commands = []

    @property
    def I_meas(self):
        return self._I_meas

    @property
    def I_limit(self):
        return self._I_limit

    @I_limit.setter
    def I_limit(self, value):
        self._I_limit = float(value)
        self._I_meas = float(value)
        self.current_commands.append(float(value))


class NamedProperty:
    """Minimal dictionary-like property used by ShimDictMapping."""

    def __init__(self, initial):
        self.values = dict(initial)
        self.commands = []

    def __getitem__(self, key):
        return self.values[key]

    def __setitem__(self, key, value):
        self.values[key] = float(value)
        self.commands.append((key, float(value)))


class FakeZ0Instrument:
    max_V = [6.0]


class FakeShims:
    def __init__(self, voltage=0.0):
        self.V_read = NamedProperty({"Z0": voltage})
        self.V_limit = NamedProperty({"Z0": voltage})
        self.output = NamedProperty({"Z0": 1.0})

    def round_to_allowed(self, which, name, value):
        assert which == "V"
        assert name == "Z0"
        return float(np.round(value, 3))

    def instrument(self, name):
        assert name == "Z0"
        return FakeZ0Instrument()

    def channel(self, name):
        assert name == "Z0"
        return 0


@pytest.fixture
def config():
    return {
        "current_v_field_A_G": 0.00620515974113444,
        "z0_field_v_voltage_G_V": 0.434244,
        "magnet_settle_short": 0.0,
        "magnet_settle_medium": 0.0,
        "magnet_settle_long": 0.0,
        "tolerance_Hz": 440.0,
        "gamma_eff_mhz_g": 0.00431224267380725,
    }


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    monkeypatch.setattr(field_feedback.time, "sleep", lambda _seconds: None)


def test_adjust_main_field_uses_incremental_error_without_mutating_config(config):
    hall = FakeHall([100.5])
    gen = FakeGenesys(measured_current=0.620)
    original_ratio = config["current_v_field_A_G"]

    field_feedback.adjust_main_field(100.0, config, hall, gen)

    expected = 0.620 + (100.0 - 100.5) * original_ratio
    assert gen.I_limit == pytest.approx(expected)
    assert config["current_v_field_A_G"] == original_ratio


def test_maintain_field_applies_single_z0_correction(config):
    hall = FakeHall([100.0])
    gen = FakeGenesys(measured_current=0.620)
    shims = FakeShims(voltage=1.0)

    result = field_feedback.maintain_field(
        100.2,
        100.0,
        config,
        hall,
        gen,
        shims,
    )

    expected_voltage = 1.0 + 0.2 / config["z0_field_v_voltage_G_V"]
    assert shims.V_limit.commands == [
        ("Z0", pytest.approx(np.round(expected_voltage, 3)))
    ]
    assert result == pytest.approx(100.0)
    assert gen.current_commands == []


def test_maintain_field_falls_back_when_z0_cannot_reach_target(
    config, monkeypatch
):
    hall = FakeHall([100.0])
    gen = FakeGenesys(measured_current=0.620)
    shims = FakeShims(voltage=5.9)
    calls = []

    def fake_ramp(target, passed_config, passed_hall, passed_gen, passed_shims):
        calls.append(
            (target, passed_config, passed_hall, passed_gen, passed_shims)
        )
        return 100.25

    monkeypatch.setattr(field_feedback, "ramp_field", fake_ramp)

    result = field_feedback.maintain_field(
        100.5,
        100.0,
        config,
        hall,
        gen,
        shims,
    )

    assert result == pytest.approx(100.25)
    assert len(calls) == 1
    assert shims.V_limit.commands == []


def test_small_main_current_move_still_sends_target_command(config):
    target_G = 100.0
    target_A = target_G * config["current_v_field_A_G"]
    gen = FakeGenesys(measured_current=target_A - 0.001)
    hall = FakeHall([target_G])
    shims = FakeShims(voltage=0.5)

    result = field_feedback.ramp_field(
        target_G,
        config,
        hall,
        gen,
        shims,
        settling_attempts=3,
    )

    assert gen.current_commands[0] == pytest.approx(target_A)
    assert result == pytest.approx(target_G)


def test_negative_z0_request_restarts_loop_without_sending_stale_voltage(
    config, monkeypatch
):
    target_G = 100.0
    target_A = target_G * config["current_v_field_A_G"]
    gen = FakeGenesys(measured_current=target_A)
    # First outer-loop reading is 0.2 G above target, so Z0 would need a
    # negative voltage. Subsequent readings are on target and converge.
    hall = FakeHall([100.2, 100.0, 100.0, 100.0, 100.0])
    shims = FakeShims(voltage=0.0)
    adjusted_targets = []

    def fake_adjust(target, passed_config, passed_hall, passed_gen):
        adjusted_targets.append(target)

    monkeypatch.setattr(field_feedback, "adjust_main_field", fake_adjust)

    result = field_feedback.ramp_field(
        target_G,
        config,
        hall,
        gen,
        shims,
        settling_attempts=6,
    )

    assert adjusted_targets == [pytest.approx(target_G - 1.0)]
    assert shims.V_limit.commands == []
    assert result == pytest.approx(target_G)
