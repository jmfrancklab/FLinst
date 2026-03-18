"""Scan the Y shim current and score the NMR signal.

The Y coil acts like a Z1 shim in this setup, so the goal is to maximize a
single scalar derived from the acquired transient.  This script reuses the
existing SpinCore spin-echo acquisition path and reduces each scan to either:

- integrated ``abs(signal)``
- integrated ``|signal|^2`` ("energy")
- peak ``abs(signal)``

It then plots a line scan versus Y current and leaves the supply at the best
current unless told otherwise.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pyspecdata as psp
from numpy import r_

import SpinCore_pp
from Instruments import HP6623A, power_control, prologix_connection
from SpinCore_pp.ppg import run_spin_echo


logger = logging.getLogger(__name__)
DEFAULT_SERVER_IP = "127.0.0.1"


@dataclass
class Settings:
    config: str | None = None
    metric: str = "energy"
    currents: list[float] | None = None
    center: float | None = None
    span: float = 0.6
    start: float | None = None
    stop: float | None = None
    points: int = 11
    y_channel: int = 1
    hp_address: int | None = None
    v_limit: float = 15.0
    settle_s: float = 2.0
    apo_ms: float | None = 10.0
    t_start_us: float | None = None
    t_stop_us: float | None = None
    server_ip: str = DEFAULT_SERVER_IP
    skip_field: bool = False
    auto_adc: bool = False
    restore_initial: bool = False
    save_prefix: str | None = None
    log_level: str = "INFO"


# Edit these values directly before running the script.
SETTINGS = Settings(
    metric="energy",
    center=None,
    span=0.6,
    start=None,
    stop=None,
    points=11,
    currents=None,
    y_channel=1,
    hp_address=None,
    v_limit=15.0,
    settle_s=2.0,
    apo_ms=10.0,
    t_start_us=None,
    t_stop_us=None,
    server_ip=DEFAULT_SERVER_IP,
    skip_field=False,
    auto_adc=False,
    restore_initial=False,
    save_prefix=None,
    log_level="INFO",
)


def resolve_config_path(config_path: str | None) -> Path:
    """Locate the active config file."""
    candidates = []
    if config_path is not None:
        candidates.append(Path(config_path).expanduser())
    candidates += [
        Path("active.ini"),
        Path("examples/active.ini"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate.resolve()
    raise FileNotFoundError(
        "Could not find a config file. Use --config to point at active.ini."
    )


def stabilize_adc_offset(max_tries: int = 20) -> int:
    """Repeat the ADC offset measurement until it stops moving."""
    counter = 0
    first = True
    result1 = result2 = result3 = None
    while first or not (result1 == result2 == result3):
        first = False
        result1 = SpinCore_pp.adc_offset()
        time.sleep(0.1)
        result2 = SpinCore_pp.adc_offset()
        time.sleep(0.1)
        result3 = SpinCore_pp.adc_offset()
        counter += 1
        if counter > max_tries:
            raise RuntimeError("Could not stabilize ADC offset")
    return result3


def acquire_echo(config_dict, n_points, sw_khz, adc_offset):
    """Acquire one spin-echo transient using the existing pulse program."""
    echo_data = run_spin_echo(
        nScans=config_dict["nScans"],
        indirect_idx=0,
        indirect_len=1,
        deblank_us=config_dict["deblank_us"],
        adcOffset=adc_offset,
        carrierFreq_MHz=config_dict["carrierFreq_MHz"],
        nPoints=n_points,
        nEchoes=1,
        plen=config_dict["beta_90_s_sqrtW"],
        repetition_us=config_dict["repetition_us"],
        amplitude=config_dict["amplitude"],
        tau_us=config_dict["tau_us"],
        SW_kHz=sw_khz,
        ret_data=None,
        deadtime_us=config_dict["deadtime_us"],
    )
    echo_data.chunk("t", ["ph1", "t2"], [4, -1])
    echo_data.setaxis("ph1", r_[0.0, 1.0, 2.0, 3.0] / 4)
    if "nScans" in echo_data.dimlabels:
        echo_data.setaxis("nScans", r_[0 : config_dict["nScans"]])
    echo_data.reorder(["ph1", "nScans", "t2"])
    echo_data.squeeze()
    echo_data.set_units("t2", "s")
    return echo_data


def scalar_from_trace(trace, metric: str) -> float:
    """Convert a 1D nddata trace into a scalar score."""
    time_axis = trace.getaxis("t2")
    if len(time_axis) > 1:
        dt = float(np.diff(time_axis).mean())
    else:
        dt = 1.0
    trace_data = np.asarray(trace.data, dtype=np.float64)
    if metric == "energy":
        return float(np.sum(trace_data**2) * dt)
    if metric == "absint":
        return float(np.sum(np.abs(trace_data)) * dt)
    if metric == "peak":
        return float(np.max(np.abs(trace_data)))
    raise ValueError(f"Unknown metric {metric!r}")


def process_echo(
    echo_data,
    tau_us: float,
    metric: str,
    apo_s: float | None,
    t_start_us: float | None,
    t_stop_us: float | None,
):
    """Reduce raw echo data to a single scalar and a plotted trace."""
    data = echo_data.C
    data.ft("ph1", unitary=True)
    if "nScans" in data.dimlabels and int(psp.ndshape(data)["nScans"]) > 1:
        data.mean("nScans")
    data.ft("t2", shift=True)
    analytic = data["t2" : (0, None)] * 2
    analytic.ift("t2")
    if apo_s is not None and apo_s > 0:
        analytic *= np.exp(
            -abs(analytic.fromaxis("t2") - tau_us * 1e-6) / apo_s
        )
    signal_trace = abs(analytic["ph1", 1])
    noise_trace = analytic["ph1", r_[0, 2, 3]].run(np.std, "ph1")
    signal_trace -= noise_trace
    signal_trace.data = np.maximum(
        np.real(np.asarray(signal_trace.data, dtype=np.float64)),
        0.0,
    )
    if t_start_us is not None or t_stop_us is not None:
        start_s = None if t_start_us is None else t_start_us * 1e-6
        stop_s = None if t_stop_us is None else t_stop_us * 1e-6
        signal_trace = signal_trace["t2" : (start_s, stop_s)]
        noise_trace = noise_trace["t2" : (start_s, stop_s)]
    score = scalar_from_trace(signal_trace, metric)
    return score, signal_trace, noise_trace


def build_current_array(hp_supply, channel, settings):
    """Generate and instrument-round the list of requested shim currents."""
    if settings.currents is not None:
        requested = np.array(settings.currents, dtype=float)
    else:
        start = settings.start
        stop = settings.stop
        if start is None or stop is None:
            current_center = hp_supply.I_limit[channel]
            if settings.center is not None:
                current_center = settings.center
            span = settings.span
            start = current_center - span / 2.0
            stop = current_center + span / 2.0
        requested = np.linspace(start, stop, settings.points)
    if np.any(requested < 0):
        raise ValueError("This shim script only supports non-negative current")
    rounded = []
    for value in requested:
        if np.isclose(value, 0.0):
            new_value = 0.0
        else:
            new_value = hp_supply.round_to_allowed("I", channel, value)
        if not rounded or not np.isclose(rounded[-1], new_value):
            rounded.append(float(new_value))
    return np.array(rounded, dtype=float)


def set_y_current(hp_supply, channel, current_amps, v_limit):
    """Apply the Y current to the chosen supply channel."""
    if np.isclose(current_amps, 0.0):
        hp_supply.I_limit[channel] = 0.0
        hp_supply.V_limit[channel] = 0.0
        hp_supply.output[channel] = 0
        return
    hp_supply.V_limit[channel] = v_limit
    hp_supply.I_limit[channel] = current_amps
    hp_supply.output[channel] = 1


def plot_results(
    current_axis,
    score_axis,
    trace_matrix,
    best_index,
    metric,
    save_prefix: str | None,
):
    """Plot the line scan and the signal traces."""
    fig, axes = plt.subplots(
        3,
        1,
        figsize=(9, 10),
        constrained_layout=True,
    )
    axes[0].plot(current_axis, score_axis.data, "o-", lw=1.5)
    axes[0].axvline(current_axis[best_index], color="r", ls=":")
    axes[0].set_ylabel(metric)
    axes[0].set_xlabel("Y current / A")
    axes[0].set_title("Y shim line scan")

    mesh = axes[1].pcolormesh(
        trace_matrix.getaxis("t2") * 1e6,
        trace_matrix.getaxis("y_current"),
        trace_matrix.data,
        shading="auto",
    )
    axes[1].set_xlabel("t2 / us")
    axes[1].set_ylabel("Y current / A")
    axes[1].set_title("Processed signal trace")
    fig.colorbar(mesh, ax=axes[1], label="abs(signal) - noise")

    best_trace = trace_matrix["y_current", best_index]
    axes[2].plot(best_trace.getaxis("t2") * 1e6, best_trace.data)
    axes[2].set_xlabel("t2 / us")
    axes[2].set_ylabel("signal")
    axes[2].set_title(f"Best trace at {current_axis[best_index]:0.3f} A")

    if save_prefix is not None:
        figure_path = Path(f"{save_prefix}.png")
        csv_path = Path(f"{save_prefix}.csv")
        fig.savefig(figure_path, dpi=150)
        np.savetxt(
            csv_path,
            np.column_stack([current_axis, score_axis.data]),
            delimiter=",",
            header=f"y_current_A,{metric}",
            comments="",
        )
    plt.show()


def main():
    settings = SETTINGS
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(levelname)s:%(name)s:%(message)s",
    )
    config_path = resolve_config_path(settings.config)
    config_dict = SpinCore_pp.configuration(str(config_path))
    hp_address = (
        config_dict["HP1_address"]
        if settings.hp_address is None
        else settings.hp_address
    )
    n_points, sw_khz, acq_time_ms = SpinCore_pp.get_integer_sampling_intervals(
        SW_kHz=config_dict["SW_kHz"],
        time_per_segment_ms=config_dict["acq_time_ms"],
    )
    logger.info(
        "Using %d points, actual SW %.6f kHz, actual acq %.6f ms",
        n_points,
        sw_khz,
        acq_time_ms,
    )
    adc_offset = config_dict["adc_offset"]
    if settings.auto_adc:
        adc_offset = stabilize_adc_offset()
        config_dict["adc_offset"] = adc_offset
        config_dict.write()
        logger.info("ADC offset updated to %d", adc_offset)
    if not settings.skip_field:
        target_field = (
            config_dict["carrierFreq_MHz"] / config_dict["gamma_eff_MHz_G"]
        )
        with power_control(ip=settings.server_ip) as field_control:
            true_field = field_control.set_field(target_field)
        logger.info(
            "Field requested at %.6f G and measured at %.6f G",
            target_field,
            true_field,
        )
    with prologix_connection(
        ip=config_dict["prologix_ip"],
        port=config_dict["prologix_port"],
    ) as prologix:
        with HP6623A(
            prologix_instance=prologix,
            address=hp_address,
        ) as hp_supply:
            hp_supply.safe_current = 1.8
            y_channel = settings.y_channel
            initial_current = hp_supply.I_limit[y_channel]
            current_axis = build_current_array(hp_supply, y_channel, settings)
            logger.info(
                "Scanning Y current values: %s",
                ", ".join(f"{j:0.3f}" for j in current_axis),
            )
            score_axis = psp.nddata(np.zeros(len(current_axis)), ["y_current"])
            score_axis.setaxis("y_current", current_axis)
            trace_matrix = None
            best_index = None
            try:
                for j, current_amps in enumerate(current_axis):
                    set_y_current(
                        hp_supply,
                        y_channel,
                        current_amps,
                        settings.v_limit,
                    )
                    logger.info(
                        "Acquiring at Y current %.6f A (%d/%d)",
                        current_amps,
                        j + 1,
                        len(current_axis),
                    )
                    time.sleep(settings.settle_s)
                    echo_data = acquire_echo(
                        config_dict,
                        n_points,
                        sw_khz,
                        adc_offset,
                    )
                    score, signal_trace, _ = process_echo(
                        echo_data,
                        tau_us=config_dict["tau_us"],
                        metric=settings.metric,
                        apo_s=(
                            settings.apo_ms * 1e-3
                            if settings.apo_ms is not None
                            else None
                        ),
                        t_start_us=settings.t_start_us,
                        t_stop_us=settings.t_stop_us,
                    )
                    if trace_matrix is None:
                        trace_matrix = psp.ndshape(
                            [
                                len(current_axis),
                                len(signal_trace.getaxis("t2")),
                            ],
                            ["y_current", "t2"],
                        ).alloc(dtype=float)
                        trace_matrix.setaxis("y_current", current_axis)
                        trace_matrix.setaxis("t2", signal_trace.getaxis("t2"))
                        trace_matrix.set_units("t2", "s")
                    score_axis["y_current", j] = score
                    trace_matrix["y_current", j] = signal_trace.data
                    logger.info(
                        "Score at %.6f A is %.6g",
                        current_amps,
                        score,
                    )
                best_index = int(np.argmax(score_axis.data))
                best_current = float(current_axis[best_index])
                logger.info(
                    "Best Y current is %.6f A with %s score %.6g",
                    best_current,
                    settings.metric,
                    float(score_axis.data[best_index]),
                )
                if settings.restore_initial:
                    set_y_current(
                        hp_supply,
                        y_channel,
                        initial_current,
                        settings.v_limit,
                    )
                    logger.info(
                        "Restored initial Y current %.6f A",
                        initial_current,
                    )
                else:
                    set_y_current(
                        hp_supply,
                        y_channel,
                        best_current,
                        settings.v_limit,
                    )
                    logger.info("Left Y shim at %.6f A", best_current)
            except Exception:
                set_y_current(
                    hp_supply,
                    y_channel,
                    initial_current,
                    settings.v_limit,
                )
                logger.exception(
                    "Aborting the scan and restoring the initial Y current"
                )
                raise
    print(
        "Best Y current: "
        f"{current_axis[best_index]:0.6f} A "
        f"({settings.metric}={float(score_axis.data[best_index]):0.6g})"
    )
    plot_results(
        current_axis,
        score_axis,
        trace_matrix,
        best_index,
        settings.metric,
        settings.save_prefix,
    )


if __name__ == "__main__":
    main()
