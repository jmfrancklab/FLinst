# Franck Lab Instrumentation (FLinst)

This repository provides a package (Instruments) that represents USB and GPIB-connected instruments as file-like objects and allows the collection of data in [pyspecdata](http://jmfrancklab.github.io/pyspecdata) nddata format.  Additionally, some code for jupyter-format notebooks using these classes is included.

The documentation is not extensive, but feel free to contact us jmfranck [at] syr.edu.  A manuscript describing the implementation of this package in the context of Overhauser DNP (enhanced Nuclear Magnetic Resonance) is forthcoming.

Currently supported instruments include:

* Instek oscilloscope
* Instek frequency generator
* HP Microwave Frequency source
* Gigatronics power meter
* SpinCore pulse programming board

## Note on installation

We assume you've followed the development install of pySpecData (which is required).  This gives most of the installation packages you need.

You will **also** need: ``conda install -y -c conda-forge gxx_win-64 swig`` to provide the mingw c++ compiler.

## note on SpinCore package:

This package contains a very convenient extension that wraps the SpinCore API for collecting NMR data.  Data is collected and saved using [pyspecdata](https://jmfrancklab.github.io/pyspecdata) for convenience and extensibility, and a very simple and flexible pulse programming language (based on [doi:10.1016/j.jmr.2013.07.015](http://doi.org/10.1016/j.jmr.2013.07.015) with some upgrades)

The documentation is not extensive, and unrelated files freely available from SpinCore are currently included, but feel free to contact us jmfranck [at] syr.edu

This code was primarily developed by A Beaton in the Franck lab at Syracuse University.

A manuscript describing implementation of this library in the context of Overhauser DNP is forthcoming.
