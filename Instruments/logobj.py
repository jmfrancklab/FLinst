from numpy import dtype, empty, concatenate, generic
import time as timemodule


class logobj(object):
    def __init__(self, array_len=1000):  # just the size of the buffer
        self.log_list = []
        # {{{ this is a structured array
        self.log_dtype = dtype(
            [
                ("time", "f8"),
                ("Rx", "f8"),
                ("power", "f8"),
                ("field", "f8"),
                ("cmd", "i8"),
            ]
        )
        self.log_array = empty(array_len, dtype=self.log_dtype)
        self.log_dict = {
            0: ""
        }  # use hash to convert commands to a number, and this to look up the
        #    meaning of the hashes
        # }}}
        self.currently_logging = False
        self.log_pos = 0
        self.array_len = array_len
        self.wg_has_been_flipped = False
        return

    @classmethod
    def from_group(cls, h5group):
        """initialize a new log object with data loaded from the h5py group
        h5group (factory method"""
        thislog = cls()
        thislog.__setstate__(h5group)
        return thislog

    def reset(self):
        "wipe the log and start over, set to not currently logging"
        self.log_array = empty(self.array_len, dtype=self.log_dtype)
        self.log_dict = {
            0: ""
        }  # use hash to convert commands to a number, and this to look up the
        #    meaning of the hashes
        self.currently_logging = False
        self.log_pos = 0
        self.log_list = []
        if hasattr(self, "_totallog"):
            del self._totallog
        return

    def add(self, time=None, Rx=None, power=None, field=None, cmd=None):
        if time is None:
            time = timemodule.time()
        self.log_array[self.log_pos]["time"] = time
        if cmd is None:
            self.log_array[self.log_pos]["cmd"] = 0
        else:
            thehash = hash(cmd)
            self.log_dict[thehash] = cmd
            self.log_array[self.log_pos]["cmd"] = thehash
        assert Rx is not None
        self.log_array[self.log_pos]["Rx"] = Rx
        assert power is not None
        self.log_array[self.log_pos]["power"] = power
        assert field is not None
        self.log_array[self.log_pos]["field"] = field
        # {{{ done for all additions
        self.log_pos += 1
        if self.log_pos == self.array_len:
            self.log_pos = 0
            self.log_list.append(self.log_array)
            self.log_array = empty(self.array_len, dtype=self.log_dtype)
        # }}}
        return self

    @property
    def total_log(self):
        """the log is stored internally as a list of arrays -- here return a
        single array for the whole log"""
        if hasattr(self, "_totallog"):
            return self._totallog
        else:
            return concatenate(
                self.log_list + [self.log_array[: self.log_pos]]
            )

    @total_log.setter
    def total_log(self, result):
        self._totallog = result

    def __getstate__(self):
        """return a picklable object -- I go with a dictionary that contains
        the message dict and the total array"""
        return {
            "NUMPY_DATA": self.total_log,
            "dictkeys": list(self.log_dict.keys()),
            "dictvalues": list(self.log_dict.values()),
        }

    def __setstate__(self, inputdict):
        if hasattr(inputdict, "keys") and "array" in inputdict.keys():
            # legacy format
            if "dictkeys" in inputdict.keys():
                # {{{ legacy plain-dict state: older code stored both
                #     metadata lists and the array directly at the top level
                dictkeys = inputdict["dictkeys"]
                dictvalues = inputdict["dictvalues"]
                total_log = inputdict["array"]
                # }}}
            elif (
                hasattr(inputdict, "attrs")
                and "dictkeys" in inputdict.attrs.keys()
            ):
                # {{{ legacy HDF layout: the group carries the metadata as
                #     attrs and the actual structured array lives in the
                #     "array" dataset below it
                dictkeys = inputdict.attrs["dictkeys"]
                dictvalues = inputdict.attrs["dictvalues"]
                total_log = inputdict["array"][
                    :
                ]  # force the dataset into memory before the file is closed
                dictkeys = [
                    (
                        thisitem.decode("utf-8")
                        if isinstance(thisitem, bytes)
                        else thisitem
                    )
                    for thisitem in dictkeys
                ]
                dictvalues = [
                    (
                        thisitem.decode("utf-8")
                        if isinstance(thisitem, bytes)
                        else thisitem
                    )
                    for thisitem in dictvalues
                ]
                # }}}
        else:
            # new format -- three keys for numpy data, dict keys, and
            # dict values
            if isinstance(inputdict, dict):
                # {{{ pickle over the socket carries the raw __getstate__
                #     dictionary, so the NUMPY_DATA key is still present
                #     here, as opposed to when we use hdf_save_dict_to_group
                #     to write to disk, and it consumes that wrapper when
                #     writing HDF5, so only the raw dict path should still
                #     see it.
                dictkeys = inputdict["dictkeys"]
                dictvalues = inputdict["dictvalues"]
                total_log = inputdict["NUMPY_DATA"]
                # }}}
            elif hasattr(inputdict, "attrs"):
                # {{{ current HDF layout: hdf_save_dict_to_group has already
                #     consumed the NUMPY_DATA wrapper and written the array
                #     as the "array" dataset.  The remaining metadata is
                #     stored as dataset attrs, and HDF gives string attrs
                #     back as bytes that need decoding here.
                dictkeys = inputdict.attrs["dictkeys"]
                dictvalues = inputdict.attrs["dictvalues"]
                total_log = inputdict[
                    :
                ]  # force the dataset into memory before the file is closed
                dictkeys = [
                    (
                        thisitem.decode("utf-8")
                        if isinstance(thisitem, bytes)
                        else thisitem
                    )
                    for thisitem in dictkeys
                ]
                dictvalues = [
                    (
                        thisitem.decode("utf-8")
                        if isinstance(thisitem, bytes)
                        else thisitem
                    )
                    for thisitem in dictvalues
                ]
            else:
                raise IOError(
                    "You fed me a state dictionary without a key called"
                    " 'array', so it seemed new-style, but the keys were"
                    f" {list(inputdict.keys())}, which don't seem  to represent"
                    " a properly structured data node"
                )
        dictkeys = [
            thisitem.item() if isinstance(thisitem, generic) else thisitem
            for thisitem in dictkeys
        ]
        dictvalues = [
            thisitem.item() if isinstance(thisitem, generic) else thisitem
            for thisitem in dictvalues
        ]
        self.log_dict = dict(zip(dictkeys, dictvalues))
        self.total_log = total_log
