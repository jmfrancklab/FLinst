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

jump_series_default = r_[-1, -0.5, 0, 0.5, 1]


def load_active_config():
    """Return the SpinCore configuration that all tuning paths use."""
    return SpinCore_pp.configuration("active.ini")


def list_serial_instruments():
    """Trigger the serial enumeration routine so the operator can verify I/O."""
    SerialInstrument(None)


def grab_waveforms(scope):
    """Capture a control/reflection waveform pair from the supplied scope."""
    ch1 = scope.waveform(ch=2)
    ch2 = scope.waveform(ch=3)
    success = False
    for _ in range(10):
        if ch1.data.max() < 50e-3:
            ch1 = scope.waveform(ch=2)
            ch2 = scope.waveform(ch=3)
        else:
            success = True
    if not success:
        raise ValueError("can't seem to get a waveform that's large enough!")
    waveforms = concat([ch1, ch2], "ch")
    waveforms.reorder("ch")
    return waveforms


def configure_scope(scope):
    """Reset and configure the Tektronix scope to the expected settings."""
    scope.reset()
    scope.CH2.disp = True
    scope.CH3.disp = True
    scope.write(":CHAN1:DISP OFF")
    scope.write(":CHAN2:DISP ON")
    scope.write(":CHAN3:DISP ON")
    scope.write(":CHAN4:DISP OFF")
    scope.CH2.voltscal = 100e-3
    scope.CH3.voltscal = 50e-3
    scope.timscal(500e-9, pos=2.325e-6)
    scope.write(":CHAN2:IMP 5.0E+1")
    scope.write(":CHAN3:IMP 5.0E+1")
    scope.write(":TRIG:SOUR CH2")
    scope.write(":TRIG:MOD NORMAL")
    scope.write(":TRIG:HLEV 7.5E-2")


def run_frequency_sweep(
    parser_dict,
    jump_series=None,
    waveform_callback=None,
    status_callback=None,
    stop_requested=None,
):
    """Acquire waveforms for each frequency offset and return nddata containers."""
    if jump_series is None:
        jump_series = jump_series_default
    d_all = None
    with GDS_scope() as scope:
        configure_scope(scope)
        for idx, carrier in enumerate(
            parser_dict["carrierFreq_MHz"]
            + parser_dict["tuning_offset_jump_MHz"] * jump_series
        ):
            if stop_requested is not None and stop_requested():
                raise RuntimeError("Sweep cancelled")
            if status_callback is not None:
                status_callback("about to change frequency to %s" % carrier)
            SpinCore_pp.tune(carrier)
            if status_callback is not None:
                status_callback("changed frequency to %s" % carrier)
            waveforms = grab_waveforms(scope)
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
