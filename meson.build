project('FLinst', 'cpp', version: '0.1.0')

py = import('python').find_installation()
swig = find_program('swig')

# Set environment variables correctly
environment = environment()

# Properly formatted PATH string
path_entries = [
    'C:/ProgramData/Anaconda3/MinGW/bin',
    'C:/ProgramData/Anaconda3/',
    'C:/ProgramData/Anaconda3/scripts/',
    'C:/ProgramData/Anaconda3/Library/bin',
    'C:/ProgramData/Anaconda3/MinGW/bin'
]
environment.set('PATH', ';'.join(path_entries))

# Set necessary environment variables
environment.set('conda_headers', 'C:/ProgramData/Anaconda3/include')
environment.set('conda_libs', 'C:/ProgramData/Anaconda3/libs')
environment.set('numpy', 'C:/ProgramData/Anaconda3/lib/site-packages/numpy/core/include')

# Ensure C++ flags are correctly applied
env = environment()
env.set('CXXFLAGS', '-shared -DMS_WIN64')

# Define include directories using relative paths
inc_dirs = include_directories('.')

# Define the SWIG-based extension for SpinCore_pp
spincore_extension = py.extension_module(
    '_SpinCore_pp',
    sources: ['SpinCore_pp/SpinCore_pp.i', 'SpinCore_pp/SpinCore_pp.c'],
    include_directories: [get_option('conda_headers'), inc_dirs, get_option('numpy')],
    override_options: ['cpp_std=c++11'],
    install: true,
    dependencies: [declare_dependency(link_args: ['-L' + get_option('conda_libs')])]
)

# Install the pure Python packages
py.install_sources('SpinCore_pp', subdir: 'FLinst/SpinCore_pp')
py.install_sources('Instruments', subdir: 'FLinst/Instruments')
