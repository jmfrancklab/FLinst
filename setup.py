#from setuptools import setup
import setuptools # I think this is needed for the following
from numpy.distutils.core import Extension,setup
from distutils.spawn import find_executable
import os

ext_modules = []
exec(compile(open('Instruments/version.py', "rb").read(), 'Instruments/version.py', 'exec'))

# {{{ to compile spincore, we need the following set by environment.sh
#     if we don't set that, it skips the spincore package
compile_spincore = False
arg_list = []
if "conda_headers" in os.environ.keys():
    compile_spincore = True
    for j in ["conda_headers","spincore","numpy"]:
        arg_list.append('-I'+os.environ[j])
    for j in ["conda_libs","spincore"]:
        arg_list.append('-L'+os.environ[j])
# }}}
if compile_spincore:
    ext_modules.append(Extension(name='SpinCore_pp._SpinCore_pp',
        sources = ["SpinCore_pp/SpinCore_pp.i", "SpinCore_pp/SpinCore_pp.c"],
        define_macros = [('ADD_UNDERSCORE',None)],
        #  flags from compile_SpinCore_pp.sh
        extra_compile_args = [
            "-shared",
            "-DMS_WIN64",
            ] + arg_list,# debug flags
        library_dirs = ['.'],
        libraries = ['mrispinapi64'],
        swig_opts=['-threads'],
        ))

    setup(
        name='SpinCore_pp',
        author='Beaton,Franck,Guinness',
        version=__version__,
        packages=setuptools.find_packages(),
        license='LICENSE.md',
        author_email='jmfranck@notgiven.com',
        url='http://github.com/jmfrancklab/spincore_apps',
        description='custom pulse programming language',
        long_description="Pulse programming language for SpinCore RadioProcessor G",
        install_requires=[
            "numpy",
            "h5py",
            "pyserial>=3.0",
            ],
        ext_modules = ext_modules,
        entry_points=dict(console_scripts=
                ['calc_tempol_vd=SpinCore_pp.calc_vdlist:print_tempo_vdlist'],)
    )

setup(
        name='francklab_instruments',
        author='Beaton,Betts,Franck',
        version=__version__,
        packages=setuptools.find_packages(),
        license='LICENSE.md',
        author_email='jmfranck@notgiven.com',
        url='http://github.com/jmfrancklab/inst_notebooks',
        description='object-oriented control of various instruments',
        long_description="Bridge12 amplifier, GwInstek AFG and oscilloscope",
        install_requires=[
            "numpy",
            "h5py",
            "pyserial>=3.0",
            ],
        ext_modules = ext_modules,
        entry_points=dict(console_scripts=
            [
                'power_control_server=Instruments.power_control_server:main',
                'quit_power_control=Instruments.just_quit:main',
                'FLInst=Instruments.cmd:cmd'
                ]
            )
        )
