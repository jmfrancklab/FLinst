"""Manual integration tests for the live FLInst field-control server.

These tests move the real magnet and Z0 shim. They are skipped unless
``FLINST_RUN_INSTRUMENT_TESTS=1`` is set. Run them only while the spectrometer
is supervised and no acquisition is active.

The instrument-control server must already be running with the modified
``field_feedback.py`` and ``instrument_control_server.py``.

Example
-------

From the client/NMR computer::

    FLINST_RUN_INSTRUMENT_TESTS=1 \
    FLINST_ACTIVE_INI=active.ini \
    pytest -s tests/test_field_feedback_instrument.py

The suite restores the starting field in a ``finally`` block. It deliberately
leaves the final Z0 voltage chosen by ``SET_FIELD``, because restoring an old
Z0 voltage independently would move the total field away from the restored
value.
"""

import configparser
import os
from pathlib import Path
import time

import pytest


RUN_LIVE_TESTS = os.environ.get("FLINST_RUN_INSTRUMENT_TESTS") == "1"
pytestmark = pytest.mark.skipif(
    not RUN_LIVE_TESTS,
    reason="set FLINST_RUN_INSTRUMENT_TESTS=1 to move the real magnet",
)


@pytest.fixture(scope="module")
def live_setup():
    """Connect to the live server and restore the starting field afterward."""
    # Import only after the opt-in check, so ordinary unit-test collection does
    # not initialize the instrument package on machines without FLInst drivers.
    from Instruments import instrument_control

    ini_path = Path(os.environ.get("FLINST_ACTIVE_INI", "active.ini"))
    parser = configparser.ConfigParser()
    if not parser.read(ini_path):
        pytest.fail(f"Could not read active.ini at {ini_path.resolve()}")

    gamma_MHz_G = parser.getfloat("acq_params", "gamma_eff_mhz_g")
    tolerance_Hz = parser.getfloat("acq_params", "tolerance_hz")
    z0_G_V = parser.getfloat("acq_params", "z0_field_v_voltage_g_v")
    tolerance_G = tolerance_Hz * 1e-6 / gamma_MHz_G

    ip = os.environ.get("FLINST_SERVER_IP", "127.0.0.1")
    port = int(os.environ.get("FLINST_SERVER_PORT", "6002"))
    controller = instrument_control(ip=ip, port=port)
    starting_field_G = controller.get_field()
    logging_active = False

    setup = {
        "controller": controller,
        "starting_field_G": starting_field_G,
        "tolerance_G": tolerance_G,
        "z0_G_V": z0_G_V,
        "logging_active": lambda: logging_active,
        "set_logging_active": lambda value: None,
    }

    # A mutable one-item list keeps cleanup state simple without introducing a
    # test-only controller class.
    logging_state = [False]
    setup["logging_active"] = lambda: logging_state[0]
    setup["set_logging_active"] = lambda value: logging_state.__setitem__(
        0, value
    )

    print(f"Starting field: {starting_field_G:.2f} G")
    print(f"Configured field tolerance: {tolerance_G:.4f} G")
    print(f"Configured Z0 sensitivity: {z0_G_V:.6f} G/V")

    try:
        yield setup
    finally:
        if logging_state[0]:
            try:
                controller.stop_log()
            except Exception as error:
                print(f"WARNING: could not stop logging during cleanup: {error}")
        try:
            restored_field_G = controller.set_field(starting_field_G)
            print(
                "Restored starting field: "
                f"{restored_field_G:.2f} G "
                f"(requested {starting_field_G:.2f} G)"
            )
        finally:
            # CLOSE keeps the server alive. The server performs its normal
            # microwave soft shutdown; magnet state is managed by SET_FIELD.
            controller.send("CLOSE")
            controller.sock.close()


def _assert_safe_field(target_G):
    minimum_G = float(os.environ.get("FLINST_TEST_MIN_FIELD_G", "3300"))
    maximum_G = float(os.environ.get("FLINST_TEST_MAX_FIELD_G", "3700"))
    assert minimum_G <= target_G <= maximum_G, (
        f"Test target {target_G:.3f} G is outside the configured safe window "
        f"{minimum_G:.1f}–{maximum_G:.1f} G"
    )


def _wait_for_field(controller, target_G, tolerance_G, timeout_s):
    """Poll the server until its Hall readback reaches the target."""
    deadline = time.monotonic() + timeout_s
    history = []
    while time.monotonic() < deadline:
        measured_G = controller.get_field()
        history.append(measured_G)
        print(
            f"target={target_G:.3f} G, measured={measured_G:.3f} G, "
            f"error={measured_G - target_G:+.3f} G"
        )
        if abs(measured_G - target_G) <= tolerance_G:
            return measured_G, history
        time.sleep(0.5)
    pytest.fail(
        f"Field did not reach {target_G:.3f} ± {tolerance_G:.3f} G; "
        f"readbacks were {history}"
    )


def test_repeated_half_gauss_steps_and_direction_reversal(live_setup):
    """Exercise the former zero-ramp-step failure with adjacent sweep moves."""
    controller = live_setup["controller"]
    start_G = live_setup["starting_field_G"]
    step_G = float(os.environ.get("FLINST_TEST_STEP_G", "0.5"))
    acceptance_G = max(live_setup["tolerance_G"], 0.11) + 0.02

    # Two consecutive upward points exercise accumulated fine correction; the
    # return sequence also checks that a direction reversal does not leave a
    # stale Z0 request or fail to command a small main-current change.
    targets_G = [
        start_G + step_G,
        start_G + 2 * step_G,
        start_G + step_G,
        start_G,
    ]

    for target_G in targets_G:
        _assert_safe_field(target_G)
        returned_G = controller.set_field(target_G)
        measured_G = controller.get_field()
        print(
            f"SET_FIELD returned {returned_G:.3f} G; "
            f"fresh readback {measured_G:.3f} G"
        )
        assert abs(returned_G - target_G) <= acceptance_G
        assert abs(measured_G - target_G) <= acceptance_G


def test_live_z0_feedback_corrects_artificial_drift(live_setup):
    """Perturb Z0 and verify that the logging feedback returns to target."""
    controller = live_setup["controller"]
    target_G = live_setup["starting_field_G"]
    tolerance_G = max(live_setup["tolerance_G"], 0.11) + 0.02
    perturb_G = float(os.environ.get("FLINST_TEST_PERTURB_G", "0.25"))
    timeout_s = float(os.environ.get("FLINST_TEST_TIMEOUT_S", "45"))
    z0_delta_V = perturb_G / live_setup["z0_G_V"]

    _assert_safe_field(target_G)
    controller.set_field(target_G)
    initial_shims = controller.get_shims()
    initial_z0_V = float(initial_shims["Z0"][0])
    z0_min_V = 0.0
    z0_max_V = float(os.environ.get("FLINST_TEST_Z0_MAX_V", "6.0"))

    directions = []
    if initial_z0_V - z0_delta_V >= z0_min_V:
        directions.append(-1.0)
    if initial_z0_V + z0_delta_V <= z0_max_V:
        directions.append(1.0)
    if not directions:
        pytest.fail(
            f"Z0={initial_z0_V:.3f} V has insufficient headroom for a "
            f"{perturb_G:.3f} G perturbation in either direction"
        )

    controller.start_log()
    live_setup["set_logging_active"](True)
    try:
        for direction in directions:
            controller.set_field(target_G)
            controller.get_shims()
            baseline_z0_V = float(controller.shim_voltage["Z0"])
            perturbed_z0_V = baseline_z0_V + direction * z0_delta_V
            perturbed_z0_V = controller.round_shim_voltage(
                "Z0", perturbed_z0_V
            )

            print(
                f"Perturbing Z0 from {baseline_z0_V:.3f} V to "
                f"{perturbed_z0_V:.3f} V"
            )
            controller.shim_voltage["Z0"] = perturbed_z0_V

            # GET_FIELD commands pass through get_field_for_logging(), so the
            # first poll can perform the one-step maintain_field correction.
            _, history = _wait_for_field(
                controller,
                target_G,
                tolerance_G,
                timeout_s,
            )
            final_z0_V = float(controller.get_shims()["Z0"][0])
            print(
                f"Feedback finished at Z0={final_z0_V:.3f} V; "
                f"field history={history}"
            )

            if direction > 0:
                assert final_z0_V < perturbed_z0_V
            else:
                assert final_z0_V > perturbed_z0_V
    finally:
        controller.stop_log()
        live_setup["set_logging_active"](False)
