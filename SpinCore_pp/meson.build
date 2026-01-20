# Set NumPy include directory (NumPy 2.x-safe)
numpy_inc = get_option('numpy')
if not fs.is_dir(numpy_inc)
  numpy_inc = run_command(
    py, ['-c', 'import numpy; print(numpy.get_include())'],
    check: true
  ).stdout().strip()
endif

# Define include directories using relative paths
inc_dirs = include_directories('.')

# Ensure C++ flags are correctly applied
env = environment()
env.set('CXXFLAGS', '-shared -DMS_WIN64')

swig = find_program('swig')
spincore_swig = custom_target(
    'SpinCore_pp_wrap',
    output: ['SpinCore_pp_wrap.c', 'SpinCore_pp.py'],
    input: 'SpinCore_pp.i',
    command: [swig, '-python', '-o', '@OUTPUT0@',
      '-outdir','@OUTDIR@',
      '@INPUT@'],
    build_by_default: true,
    install: true,
    install_dir: py.get_install_dir(subdir: 'SpinCore_pp'),
)
spincore_extension = py.extension_module(
    '_SpinCore_pp',
    sources: [spincore_swig[0], 'SpinCore_pp.c'],
    include_directories: [get_option('conda_headers'), inc_dirs, numpy_inc],
    install: true,
    install_dir: py.get_install_dir(subdir: 'SpinCore_pp'),
    dependencies: [declare_dependency(link_args: [
        '-L' + get_option('conda_libs'),
        '-L' + join_paths(meson.project_source_root(),'SpinCore_pp'),
        '-lmrispinapi64',
    ])]
)
