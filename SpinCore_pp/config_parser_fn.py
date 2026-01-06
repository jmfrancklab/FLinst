import configparser
import importlib.resources as resources

import yaml


class configuration(object):
    # this registers the type, the pretty case we want, the section, and
    # whether or not we can assume a default value; the definitions live in a
    # yaml file so wheels and zips can read the data reliably.
    yaml_path = resources.files(__package__).joinpath("config_params.yaml")
    with resources.as_file(yaml_path) as registered_params_source:
        type_lookup = {"float": float, "int": int, "str": str}
        with open(
            registered_params_source, "r", encoding="utf-8"
        ) as param_file:
            loaded_params = yaml.safe_load(param_file)
    registered_params = {}
    for paramname in loaded_params.keys():
        registered_params[paramname] = (
            type_lookup[loaded_params[paramname]["type"]],
            loaded_params[paramname]["section"],
            loaded_params[paramname]["default"],
            loaded_params[paramname]["description"],
        )

    def __init__(self, filename):
        self.filename = filename
        self.configobj = configparser.ConfigParser()
        self.configobj.read(self.filename)
        self._params = {}
        for j in ["acq_params", "odnp_params", "file_names"]:
            if j not in self.configobj.sections():
                self.configobj.add_section(j)
        for (
            paramname,
            (converter, section, default, _),
        ) in self.registered_params.items():
            try:
                temp = self.configobj.get(section, paramname.lower())
            except Exception:
                continue
            self._params[paramname] = converter(temp)
        # {{{ auto-register all counters
        if "file_names" in self.configobj.keys():
            for paramname in [
                j
                for j in self.configobj["file_names"].keys()
                if j.lower().endswith("_counter")
            ]:
                self.registered_params[paramname] = (
                    int,
                    "file_names",
                    0,
                    "a counter",
                )
                self._params[paramname] = int(
                    self.configobj["file_names"][paramname]
                )
        # }}}
        self._case_insensitive_keys = {
            j.lower(): j for j in self.registered_params.keys()
        }

    def __getitem__(self, key):
        # {{{ auto-register counters
        if key.lower().endswith("_counter"):
            if key.lower() not in self._case_insensitive_keys.keys():
                self._case_insensitive_keys[key.lower()] = key
                self.registered_params[key] = (
                    int,
                    "file_names",
                    0,
                    "a counter",
                )
        # }}}
        key = self._case_insensitive_keys[key.lower()]
        if key not in self._params.keys():
            converter, section, default, _ = self.registered_params[key]
            if default is None:
                raise KeyError(
                    f"You're asking for the '{key}' parameter, and it's not"
                    " set in the .ini file!\nFirst, ask yourself if you"
                    " should have run some type of set-up program (tuning,"
                    " adc offset, resonance finder, etc.) that would set this"
                    " parameter.\nThen, try setting the parameter in the"
                    " appropriate section of your .ini file by editing the"
                    " file with gvim or notepad++!"
                )
            else:
                return default
        return self._params[key]

    def __setitem__(self, key, value):
        if key.lower() not in self._case_insensitive_keys.keys():
            raise ValueError(
                f"I don't know what section to put the {key} setting in, or"
                " what type it's supposed to be!!  You should register it's"
                " existence in the config_parser_fn subpackage before trying"
                " to use it!! (Also -- do you really need another setting??)"
            )
        else:
            key = self._case_insensitive_keys[key.lower()]
            converter, section, default, _ = self.registered_params[key]
            self._params[key] = converter(
                value
            )  # check that it's the right type
            self.configobj.set(section, key.lower(), str(self._params[key]))

    def __str__(self):
        retval = ["-" * 50]
        allkeys = [j for j in self._params.keys()]
        idx = sorted(
            range(len(allkeys)), key=lambda x: allkeys.__getitem__(x).lower()
        )
        allkeys_sorted = [allkeys[j] for j in idx]
        for key in allkeys_sorted:
            converter, section, default, description = self.registered_params[
                key
            ]
            description = description.split("\n")
            description = ["\t" + j for j in description]
            description = "\n".join(description)
            value = self.__getitem__(key)
            retval.append(f"{key} {value} (in [{section}])\n{description}")
        retval.append("-" * 50)
        return "\n".join(retval)

    def keys(self):
        return self._params.keys()

    def write(self):
        for (
            paramname,
            (converter, section, default, _),
        ) in self.registered_params.items():
            if paramname in self._params.keys():
                self.configobj.set(
                    section, paramname.lower(), str(self._params[paramname])
                )
            self.configobj.write(open(self.filename, "w"))

    def asdict(self):
        return self._params
