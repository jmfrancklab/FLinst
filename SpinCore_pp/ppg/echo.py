from .. import (
    configureTX,
    configureRX,
    init_ppg,
    stop_ppg,
    runBoard,
    getData,
    stopBoard,
)
from .. import load as spincore_load
from .. import prog_plen
import pyspecdata as psp
import numpy as np
from numpy import r_
from pyspecdata import strm
import time
import logging


# {{{spin echo ppg
def run_spin_echo(
    settings,
    indirect_idx,
    indirect_len,
    nPoints,
    plen,
    indirect_fields=None,
    ph1_cyc=r_[0, 1, 2, 3],
    ph2_cyc=r_[0],
    ret_data=None,
    plen_as_beta=True,
):
    """
    run nScans and slot them into the indirect_idx index of ret_data -- assume
    that the first time this is run, it will be run with ret_data=None and that
    after that, you will pass in ret_data this generates an "indirect" axis.

    Parameters
    ==========
    settings: configuration
        contains the following keys.

        :nScans: int
        :nEchoes: int
        :amplitude: float
        :adc_offset: int
        :carrierFreq_MHz: float
        :repetition_us: float
        :tau_us: float
        :SW_kHz: float
        :deadtime_us: float
        :deblank_us: float
        :acq_time_ms: float

    indirect_idx: int
        index along the 'indirect' dimension
    indirect_len: int
        size of indirect axis.
        Used to allocate space for the data once the first scan is run.
    nPoints: int
        number of points for the data
    plen: float
        desired length of the pulse -- either μs or s√W
        (see plen_as_beta)
    indirect_fields: tuple (pair) of str or (default) None
        Name for the first field of the structured array
        that stores the indirect dimension coordinates.
        We use a structured array, e.g., to store both start and
        stop times for the experiment.

        If you want the indirect dimension coordinates
        to be a normal array, set this to None

        This parameter is only used when `ret_data` is set to `None`.
    ph1_cyc: array
        phase steps for the first pulse
    ph2_cyc: array
        phase steps for the second pulse
    ret_data: nddata (default None)
        returned data from previous run or `None` for the first run.
    plen_as_beta: boolean
        Is plen supplied as a β value [s√W] or directly as programmed length [μs]
    """
    assert settings["nEchoes"] == 1, "you must only choose nEchoes=1"
    # take the desired p90 and p180
    # (2*desired_p90) and convert to what needs to
    # be programmed in order to get the desired
    # times
    prog_p90_us = prog_plen(plen, settings=settings) if plen_as_beta else plen
    prog_p180_us = (
        prog_plen(2 * plen, settings=settings) if plen_as_beta else (2 * plen)
    )
    tx_phases = r_[0.0, 90.0, 180.0, 270.0]
    RX_nScans = 1
    nPhaseSteps = len(ph1_cyc) * len(ph2_cyc)
    data_length = 2 * nPoints * settings["nEchoes"] * nPhaseSteps
    for nScans_idx in range(settings["nScans"]):
        run_scans_time_list = [time.time()]
        run_scans_names = ["configure"]
        configureTX(settings["adc_offset"], settings["carrierFreq_MHz"], tx_phases, settings["amplitude"], nPoints)
        run_scans_time_list.append(time.time())
        run_scans_names.append("configure Rx")
        acq_time_ms = configureRX(
            settings["SW_kHz"], nPoints, RX_nScans, settings["nEchoes"], nPhaseSteps
        )
        run_scans_time_list.append(time.time())
        run_scans_names.append("init")
        init_ppg()
        run_scans_time_list.append(time.time())
        run_scans_names.append("prog")
        spincore_load(
            [
                ("phase_reset", 1),
                ("delay_TTL", settings["deblank_us"]),
                ("pulse_TTL", prog_p90_us, "ph1", ph1_cyc),
                ("delay", settings["tau_us"]),
                ("delay_TTL", settings["deblank_us"]),
                ("pulse_TTL", prog_p180_us, "ph2", ph2_cyc),
                ("delay", settings["deadtime_us"]),
                ("acquire", settings["acq_time_ms"]),
                ("delay", settings["repetition_us"]),
            ]
        )
        run_scans_time_list.append(time.time())
        run_scans_names.append("stop ppg")
        stop_ppg()
        run_scans_time_list.append(time.time())
        run_scans_names.append("run")
        runBoard()
        run_scans_time_list.append(time.time())
        run_scans_names.append("get data")
        raw_data = getData(data_length, nPoints, settings["nEchoes"], nPhaseSteps)
        run_scans_time_list.append(time.time())
        run_scans_names.append("shape data")
        data_array = []
        data_array[::] = np.complex128(raw_data[0::2] + 1j * raw_data[1::2])
        dataPoints = float(np.shape(data_array)[0])
        if ret_data is None:
            if indirect_fields is None:
                times_dtype = np.double
            else:
                # {{{ dtype for structured array
                times_dtype = np.dtype(
                    [
                        (indirect_fields[0], np.double),
                        (indirect_fields[1], np.double),
                    ]
                )
                # }}}
            mytimes = np.zeros(indirect_len, dtype=times_dtype)
            time_axis = r_[0:dataPoints] / (settings["SW_kHz"] * 1e3)
            ret_data = psp.ndshape(
                [indirect_len, settings["nScans"], len(time_axis)],
                ["indirect", "nScans", "t"],
            ).alloc(dtype=np.complex128)
            ret_data.setaxis("indirect", mytimes)
            ret_data.setaxis("t", time_axis).set_units("t", "s")
            ret_data.setaxis("nScans", r_[0:settings["nScans"]])
        elif indirect_idx == 0 and nScans_idx == 0:
            raise ValueError(
                "you seem to be on the first scan, but ret_data is not None -- it is "
                + str(ret_data)
                + " and we're not currently running ppgs where this makes sense"
            )
        ret_data["indirect", indirect_idx]["nScans", nScans_idx] = data_array
        stopBoard()
        run_scans_time_list.append(time.time())
        this_array = np.array(run_scans_time_list)
        logging.debug(
            strm("stored scan", nScans_idx, "for indirect_idx", indirect_idx)
        )
        logging.debug(strm("checkpoints:", this_array - this_array[0]))
        logging.debug(
            strm(
                "time for each chunk",
                [
                    "%s %0.1f" % (run_scans_names[j], v)
                    for j, v in enumerate(np.diff(this_array))
                ],
            )
        )
    return ret_data
