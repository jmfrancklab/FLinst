project('FLinst', 'cpp', version: '0.1.0')

py = import('python').find_installation()
swig = find_program('swig')

# Set environment variables within Meson
environment = environment()
environment.set('PATH', 'C:/ProgramData/Anaconda3/MinGW/bin', prepend: true)
environment.set('PATH', 'C:/ProgramData/Anaconda3/', append: true)
environment.set('PATH', 'C:/ProgramData/Anaconda3/scripts/', append: true)
environment.set('PATH', 'C:/ProgramData/Anaconda3/Library/bin', append: true)
environment.set('PATH', 'C:/ProgramData/Anaconda3/MinGW/bin', append: true)

environment.set('conda_headers', 'C:/ProgramData/Anaconda3/include')
environment.set('conda_libs', 'C:/ProgramData/Anaconda3/libs')
environment.set('numpy', 'C:/ProgramData/Anaconda3/lib/site-packages/numpy/core/include')

# Check for required environment variables
env = environment()
env.set('CXXFLAGS', '-shared -DMS_WIN64')

# Define the SWIG-based extension for SpinCore_pp
spincore_extension = py.extension_module(
    '_SpinCore_pp',
    sources: ['SpinCore_pp/SpinCore_pp.i', 'SpinCore_pp/SpinCore_pp.c'],
    include_directories: [
        get_option('conda_headers'),
        os.path.dirname(os.path.abspath(__file__)),
        get_option('numpy')
    ],
    override_options: ['cpp_std=c++11'],
    install: true,
    env: env,
    kwargs: {
        'swig_args': ['-threads'],
        'link_with': [declare_dependency(link_args: ['-L' + get_option('conda_libs'), '-L' + os.path.dirname(os.path.abspath(__file__))])]
    }
)

# Install the pure Python packages
py.install_sources('SpinCore_pp', subdir: 'FLinst/SpinCore_pp')
py.install_sources('Instruments', subdir: 'FLinst/Instruments')
