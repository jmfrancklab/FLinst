# This file was automatically generated by SWIG (http://www.swig.org).
# Version 3.0.12
#
# Do not make changes to this file unless you know what you are doing--modify
# the SWIG interface file instead.

from sys import version_info as _swig_python_version_info
if _swig_python_version_info >= (2, 7, 0):
    def swig_import_helper():
        import importlib
        pkg = __name__.rpartition('.')[0]
        mname = '.'.join((pkg, '_ppg_lang')).lstrip('.')
        try:
            return importlib.import_module(mname)
        except ImportError:
            return importlib.import_module('_ppg_lang')
    _ppg_lang = swig_import_helper()
    del swig_import_helper
elif _swig_python_version_info >= (2, 6, 0):
    def swig_import_helper():
        from os.path import dirname
        import imp
        fp = None
        try:
            fp, pathname, description = imp.find_module('_ppg_lang', [dirname(__file__)])
        except ImportError:
            import _ppg_lang
            return _ppg_lang
        try:
            _mod = imp.load_module('_ppg_lang', fp, pathname, description)
        finally:
            if fp is not None:
                fp.close()
        return _mod
    _ppg_lang = swig_import_helper()
    del swig_import_helper
else:
    import _ppg_lang
del _swig_python_version_info

try:
    _swig_property = property
except NameError:
    pass  # Python < 2.2 doesn't have 'property'.

try:
    import builtins as __builtin__
except ImportError:
    import __builtin__

def _swig_setattr_nondynamic(self, class_type, name, value, static=1):
    if (name == "thisown"):
        return self.this.own(value)
    if (name == "this"):
        if type(value).__name__ == 'SwigPyObject':
            self.__dict__[name] = value
            return
    method = class_type.__swig_setmethods__.get(name, None)
    if method:
        return method(self, value)
    if (not static):
        if _newclass:
            object.__setattr__(self, name, value)
        else:
            self.__dict__[name] = value
    else:
        raise AttributeError("You cannot add attributes to %s" % self)


def _swig_setattr(self, class_type, name, value):
    return _swig_setattr_nondynamic(self, class_type, name, value, 0)


def _swig_getattr(self, class_type, name):
    if (name == "thisown"):
        return self.this.own()
    method = class_type.__swig_getmethods__.get(name, None)
    if method:
        return method(self)
    raise AttributeError("'%s' object has no attribute '%s'" % (class_type.__name__, name))


def _swig_repr(self):
    try:
        strthis = "proxy of " + self.this.__repr__()
    except __builtin__.Exception:
        strthis = ""
    return "<%s.%s; %s >" % (self.__class__.__module__, self.__class__.__name__, strthis,)

try:
    _object = object
    _newclass = 1
except __builtin__.Exception:
    class _object:
        pass
    _newclass = 0


def ppg_element(str_label, firstarg, secondarg=0):
    return _ppg_lang.ppg_element(str_label, firstarg, secondarg)
ppg_element = _ppg_lang.ppg_element

marker_names = {}
def load(args):
    for a_tuple in args:
        if a_tuple[0] == 'marker':
            a_tuple = list(a_tuple)
            marker_names[a_tuple[1]] = len(marker_names)
            a_tuple[1] = len(marker_names)-1
        elif a_tuple[0] == 'jumpto':
            a_tuple = list(a_tuple)
            a_tuple[1] = marker_names[a_tuple[1]]
        ppg_element(*a_tuple)

# This file is compatible with both classic and new-style classes.


