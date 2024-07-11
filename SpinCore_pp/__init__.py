from Instruments.environment import compile_spincore
if compile_spincore:
    from .SpinCore_pp import (
        pause,
        configureRX,
        configureTX,
        init_ppg,
        stop_ppg,
        ppg_element,
        runBoard,
        load,
        getData,
        stopBoard,
        tune,
        adc_offset,
    )
from .pulse_length_conv import prog_plen
from .config_parser_fn import configuration
from .calc_vdlist import vdlist_from_relaxivities, return_vdlist
from .process_first_arg import process_args
from .simple_fns import get_integer_sampling_intervals
from .save_data import save_data

__all__ = [
    "adc_offset",
    "configuration",
    "configureRX",
    "configureTX",
    "getData",
    "get_integer_sampling_intervals",
    "init_ppg",
    "load",
    "pause",
    "ppg_element",
    "process_args",
    "prog_plen",
    "return_vdlist",
    "runBoard",
    "save_data",
    "stopBoard",
    "stop_ppg",
    "tune",
    "vdlist_from_relaxivities",
]
if compile_spincore:
    __all__ += ["SpinCore_pp"]
