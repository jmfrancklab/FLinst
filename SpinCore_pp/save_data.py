import h5py
import os
import pyspecdata as psd
import pyspecProcScripts
import subprocess


def save_data(dataset, my_exp_type, config_dict, counter_type=None, proc=True):
    """save data to an h5 file with appropriately labeled nodename and performs
    rough processing

    Parameters
    ==========
    dataset : nddata
        Acquired data in nddata format.
    my_exp_type : str
        Directory on the share drive you want to save to.
    config_dict : dict
        Config_dict pulled from the active.ini file.
    counter_type : str, default None
        Type of counter you are incrementing.
        Default of `None` sets to `config_dict['type']`
    proc : boolean
        Dictates whether the processing script, proc_raw is ran on the
        acquired data.

    Returns
    =======
    config_dict : dict
        The updated config dict after appropriately incrementing the
        counter.
    """
    # {{{ if we didn't explicitly pass a counter type, go ahead and use the
    #     "type" of the experiment
    if counter_type is None:
        counter_type = config_dict["type"]
    # }}}
    target_directory = psd.getDATADIR(exp_type=my_exp_type)
    # {{{ create filename
    filename_out = (
        f"{config_dict['date']}_{config_dict['chemical']}_{config_dict['type']}"
        + ".h5"
    )
    # }}}
    nodename = (
        config_dict["type"]
        + "_"
        + str(config_dict["%s_counter" % counter_type])
    )
    dataset.name(nodename)
    if os.path.exists(f"{target_directory}{filename_out}"):
        print("this file already exists so we will add a node to it!")
        with h5py.File(
            os.path.normpath(os.path.join(target_directory, f"{filename_out}"))
        ) as fp:
            while nodename in fp.keys():
                config_dict["%s_counter" % counter_type] += 1
                nodename = (
                    config_dict["type"]
                    + "_"
                    + str(config_dict["%s_counter" % counter_type])
                )
            dataset.name(nodename)
    dataset.hdf5_write(f"{filename_out}", directory=target_directory)
    print("\n** FILE SAVED IN TARGET DIRECTORY ***\n")
    print(
        "saved data to (node, file, exp_type):",
        dataset.name(),
        filename_out,
        my_exp_type,
    )
    if proc:
        env = os.environ
        subprocess.call(
            (
                " ".join(
                    [
                        "python",
                        os.path.join(
                            os.path.split(
                                os.path.split(pyspecProcScripts.__file__)[0]
                            )[0],
                            "examples",
                            "proc_raw.py",
                        ),
                        dataset.name(),
                        filename_out,
                        my_exp_type,
                    ]
                )
            ),
            env=env,
        )
    return config_dict
