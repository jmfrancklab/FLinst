"""
Shared helpers for SpinCore/GDS tuning workflows.

This module centralizes the instrument configuration, acquisition, and
post-processing routines that were previously embedded inside the
``examples/gds_for_tune.py`` script.  The GUI and CLI entry points both import
from here so that the low-level waveform handling only needs to be maintained in
one place.
"""

from numpy import r_
import numpy as np
from pyspecdata import concat
from Instruments import GDS_scope, SerialInstrument
import SpinCore_pp

try:
    import _SpinCore_pp as _spin_core_backend
except ImportError:
    _spin_core_backend = None

_gui_pause_enable_func = getattr(SpinCore_pp, "set_gui_pause_enabled", None)
_gui_pause_ready_func = getattr(SpinCore_pp, "set_gui_pause_ready", None)
if _gui_pause_enable_func is None and _spin_core_backend is not None:
    if hasattr(_spin_core_backend, "set_gui_pause_enabled"):
        _gui_pause_enable_func = _spin_core_backend.set_gui_pause_enabled
if _gui_pause_ready_func is None and _spin_core_backend is not None:
    if hasattr(_spin_core_backend, "set_gui_pause_ready"):
        _gui_pause_ready_func = _spin_core_backend.set_gui_pause_ready

gui_pause_supported = (
    _gui_pause_enable_func is not None and _gui_pause_ready_func is not None
)


def set_gui_pause_enabled(enabled):
    """Proxy to the C extension so callers need not import _SpinCore_pp."""
    if not gui_pause_supported:
        raise RuntimeError("SpinCore pause override is unavailable on this build.")
    _gui_pause_enable_func(enabled)


def set_gui_pause_ready(ready):
    """Update the extension's READY latch from Qt without touching stdin."""
    if not gui_pause_supported:
        raise RuntimeError("SpinCore pause override is unavailable on this build.")
    _gui_pause_ready_func(ready)

jump_series_default = r_[-1, -0.5, 0, 0.5, 1]


def channel_label(channel_index):
    """Return the Tektronix-style ``CHn`` label for a zero-based channel index."""
    return "CH%d" % (channel_index + 1)


def load_active_config():
    """Return the SpinCore configuration that all tuning paths use."""
    return SpinCore_pp.configuration("active.ini")


def list_serial_instruments():
    """Trigger the serial enumeration routine so the operator can verify I/O."""
    SerialInstrument(None)


def grab_waveforms(scope, control_channel=1, reflection_channel=2):
    """Capture a control/reflection waveform pair from the supplied scope."""
    # ``waveform`` already expects the zero-based index that the GUI passes
    # around, so hand the arguments straight through without any translation.
    control_trace = scope.waveform(ch=control_channel)
    reflection_trace = scope.waveform(ch=reflection_channel)
    success = False
    for _ in range(10):
        if control_trace.data.max() < 50e-3:
            # Keep retrying with the same zero-based indices until the scope
            # reports a signal large enough for the GUI workflow.
            control_trace = scope.waveform(ch=control_channel)
            reflection_trace = scope.waveform(ch=reflection_channel)
        else:
            success = True
    if not success:
        raise ValueError("can't seem to get a waveform that's large enough!")
    waveforms = concat([control_trace, reflection_trace], "ch")
    waveforms.reorder("ch")
    return waveforms


def configure_scope(scope, control_channel=1, reflection_channel=2):
    """Reset the scope using zero-based channel indices for control/reflection."""
    scope.reset()
    for channel_index in range(4):
        # Mirror the original ``gds_for_tune`` script by blanking all four
        # displays via SCPI so we never touch a non-existent ``CH4`` attribute.
        # ``channel_index`` stays zero-based, hence the ``+ 1`` when issuing
        # Tektronix commands.
        scope.write(":CHAN%d:DISP OFF" % (channel_index + 1))
    for channel_index, scale in [
        (control_channel, 100e-3),
        (reflection_channel, 50e-3),
    ]:
        channel_name = channel_label(channel_index)
        getattr(scope, channel_name).disp = True
        scope.write(":CHAN%d:DISP ON" % (channel_index + 1))
        getattr(scope, channel_name).voltscal = scale
    scope.timscal(500e-9, pos=2.325e-6)
    for channel_index in (control_channel, reflection_channel):
        scope.write(":CHAN%d:IMP 5.0E+1" % (channel_index + 1))
    scope.write(":TRIG:SOUR %s" % channel_label(control_channel))
    scope.write(":TRIG:MOD NORMAL")
    scope.write(":TRIG:HLEV 7.5E-2")


def run_frequency_sweep(
    parser_dict,
    jump_series=None,
    waveform_callback=None,
    status_callback=None,
    stop_requested=None,
    control_channel=1,
    reflection_channel=2,
    ready_callback=None,
    ready_clear_callback=None,
):
    """Acquire waveforms and optionally notify GUIs before tune() pauses."""
    if jump_series is None:
        jump_series = jump_series_default
    d_all = None
    with GDS_scope() as scope:
        configure_scope(scope, control_channel, reflection_channel)
        for idx, carrier in enumerate(
            parser_dict["carrierFreq_MHz"]
            + parser_dict["tuning_offset_jump_MHz"] * jump_series
        ):
            if stop_requested is not None and stop_requested():
                raise RuntimeError("Sweep cancelled")
            if status_callback is not None:
                status_callback("about to change frequency to %s" % carrier)
            if ready_callback is not None:
                # Tell the GUI to show the READY button before tune() pauses.
                if gui_pause_supported:
                    set_gui_pause_ready(0)
                ready_callback()
            try:
                SpinCore_pp.tune(carrier)
            finally:
                if ready_clear_callback is not None:
                    # Hide the READY button once tune() returns or raises.
                    ready_clear_callback()
            if status_callback is not None:
                status_callback("changed frequency to %s" % carrier)
            waveforms = grab_waveforms(scope, control_channel, reflection_channel)
            SpinCore_pp.stopBoard()
            if d_all is None:
                d_all = (
                    waveforms.shape
                    + ("offset", len(jump_series))
                ).alloc(dtype="float")
                d_all["offset", idx] = waveforms
                d_all["t"] = waveforms["t"]
                d_all["ch"] = waveforms["ch"]
                d_all.setaxis(
                    "offset",
                    parser_dict["tuning_offset_jump_MHz"] * jump_series,
                ).set_units("offset", "MHz")
            else:
                d_all["offset", idx] = waveforms
            if waveform_callback is not None:
                waveform_callback(d_all.C, idx)
    analytic_data = analytic_signal(d_all, parser_dict)
    flat_slice = analytic_data["offset":0]["t":(3.7e-6, 6.5e-6)]
    return analytic_data, flat_slice


def analytic_signal(dataset, parser_dict):
    """Apply the analytic-signal conversion used by the legacy CLI script."""
    dataset.ft("t", shift=True)
    dataset["t" : (parser_dict["carrierFreq_MHz"] * 2.3e6, None)] = 0
    dataset["t":(None, 0)] = 0
    dataset *= 2
    dataset.ift("t")
    return dataset


def reflection_metrics(flat_slice):
    """Return the ratio and tuning dB that summarize the reflection quality."""
    ratio = abs(flat_slice["ch", 1] / flat_slice["ch", 0]).item()
    tuning_dB = np.log10(ratio) * 20
    return ratio, tuning_dB
