project('FLinst', ['c', 'cpp'], version: '0.1.0')

py = import('python').find_installation()
fs = import('fs')
message('Enable SpinCore_pp set to: ' + get_option('enable_spincore_pp').to_string())
if get_option('enable_spincore_pp')
  message('SpinCore_pp build enabled!')
  swig = find_program('swig')

  spincore_swig = custom_target(
      'SpinCore_pp_wrap',
      output: 'SpinCore_pp_wrap.c',
      input: 'SpinCore_pp/SpinCore_pp.i',
      command: [swig, '-python', '-o', '@OUTPUT@', '@INPUT@'],
      build_by_default: true
  )
endif

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
if get_option('enable_spincore_pp')
  spincore_extension = py.extension_module(
      '_SpinCore_pp',
      sources: [spincore_swig, 'SpinCore_pp/SpinCore_pp.c'],
      include_directories: [get_option('conda_headers'), inc_dirs, get_option('numpy')],
      install: true,
      dependencies: [declare_dependency(link_args: [
          '-L' + get_option('conda_libs'),
          '-L' + meson.project_source_root(),
          '-lmrispinapi64',
      ])]
  )
endif

# Install the pure Python packages
py.install_sources(files([
    'SpinCore_pp/calibrate_clock_offset.py',
    'SpinCore_pp/run_FID_mw.py',
    'SpinCore_pp/calc_vdlist.py',
    'SpinCore_pp/field_control.py',
    'SpinCore_pp/expt.py',
    'SpinCore_pp/simple_fns.py',
    'SpinCore_pp/thread_example.py',
    'SpinCore_pp/see_powers.py',
    'SpinCore_pp/spincore_capture.py',
    'SpinCore_pp/proc_IR.py',
    'SpinCore_pp/SpinCore_pp.py',
    'SpinCore_pp/save_data.py',
    'SpinCore_pp/bruker_sender.py',
    'SpinCore_pp/mplwidget.py',
    'SpinCore_pp/vary_amp_gds.py',
    'SpinCore_pp/run_varSTE.py',
    'SpinCore_pp/run_COSY.py',
    'SpinCore_pp/__init__.py',
    'SpinCore_pp/version.py',
    'SpinCore_pp/echo_experiment_ui.py',
    'SpinCore_pp/process_first_arg.py',
    'SpinCore_pp/run_IR_STE.py',
    'SpinCore_pp/verifyParams.py',
    'SpinCore_pp/run_nutation_CPMG.py',
    'SpinCore_pp/test_CPMG_params.py',
    'SpinCore_pp/run_STE.py',
    'SpinCore_pp/config_parser_fn.py',
    'SpinCore_pp/config_params.yaml',
    'SpinCore_pp/GDS.py',
    'SpinCore_pp/run_STE_mw.py',
    'SpinCore_pp/power_helper.py',
    'SpinCore_pp/ppg/echo.py',
    'SpinCore_pp/ppg/__init__.py',
    'SpinCore_pp/ppg/run_IR.py',
    'SpinCore_pp/ppg/generic.py',
    'SpinCore_pp/ppg/IR.py',
    'SpinCore_pp/run_FID.py',
    'SpinCore_pp/test_nutation.py',
    'SpinCore_pp/pulse_length_conv.py',
]), subdir: 'SpinCore_pp')
py.install_sources(files([
    'SpinCore_pp/ppg/echo.py',
    'SpinCore_pp/ppg/__init__.py',
    'SpinCore_pp/ppg/run_IR.py',
    'SpinCore_pp/ppg/generic.py',
    'SpinCore_pp/ppg/IR.py',
]), subdir: 'SpinCore_pp/ppg')
py.install_sources(files([
    'Instruments/XEPR_eth.py',
    'Instruments/afg.py',
    'Instruments/power_control_server.py',
    'Instruments/gigatronics.py',
    'Instruments/temp.py',
    'Instruments/serial_instrument.py',
    'Instruments/HP8672A.py',
    'Instruments/gds.py',
    'Instruments/logobj.py',
    'Instruments/nmr_signal_gui.py',
    'Instruments/__init__.py',
    'Instruments/bridge12.py',
    'Instruments/log_inst.py',
    'Instruments/version.py',
    'Instruments/cmd.py',
    'Instruments/HP6623A.py',
    'Instruments/gpib_eth.py',
    'Instruments/power_control_server_dummy.py',
    'Instruments/gpib_legacy.py',
    'Instruments/power_control.py',
    'Instruments/microwave_tuning_gui.py',
    'Instruments/gds_tune.py',
    'Instruments/gds_tune_gui.py',
    'Instruments/just_quit.py',
    'Instruments/hall_probe.py',
    'Instruments/genesys.py',
]), subdir: 'Instruments')

scripts = [['calc_tempol_vd', 'SpinCore_pp.calc_vdlist', 'print_tempo_vdlist'], 
        ['power_control_server', 'Instruments.power_control_server', 'main'], 
        ['quit_power_control', 'Instruments.just_quit', 'main'], 
        ['FLInst', 'Instruments.cmd', 'cmd']]

foreach script : scripts
    configure_file(
        output: script[0],
        input: 'entry_point.template',
        configuration: {
            'python_executable': py.path(),
            'module': script[1],
            'function': script[2],
        },
        install: true,
        install_dir: get_option('bindir'),
    )
endforeach
