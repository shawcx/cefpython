# Copyright (c) 2013 CEF Python, see the Authors file.
# All rights reserved. Licensed under BSD 3-clause license.
# Project website: https://github.com/cztomczak/cefpython

# NOTE: Template variables like {{VERSION}} are replaced with actual
#       values when make_installer.py tool generates this package
#       installer.

import os
import sys
import ctypes
import importlib
import platform

__all__ = ["cefpython"]
__version__ = "{{VERSION}}"
__author__ = "The CEF Python authors"

package_dir = os.path.dirname(os.path.abspath(__file__))

# This loads the libcef.so library for the subprocess executable on Linux.
# TODO: Use -Wl,-rpath=\$$ORIGIN in Makefile.
ld_library_path = os.environ.get("LD_LIBRARY_PATH")
if ld_library_path and ld_library_path.strip():
    os.environ["LD_LIBRARY_PATH"] = package_dir + os.pathsep + ld_library_path
else:
    os.environ["LD_LIBRARY_PATH"] = package_dir

# This env variable will be returned by cefpython.GetModuleDirectory().
os.environ["CEFPYTHON3_PATH"] = package_dir

# This loads the libcef library for the main python executable.
# Loading library dynamically using ctypes.CDLL is required on Linux.
# TODO: Check if on Linux libcef.so can be linked like on Mac.
# On Mac the CEF framework dependency information is added to
# the cefpython*.so module by linking to CEF framework.
# The libffmpegsumo.so library does not need to be loaded here,
# it may cause issues to load it here in the browser process.
if platform.system() == "Linux":
    libcef = os.path.join(package_dir, "libcef.so")
    ctypes.CDLL(libcef, ctypes.RTLD_GLOBAL)

# Load the cefpython module for given Python version
if sys.version_info[:2] < (3, 12):
    raise Exception("Python version not supported: " + sys.version)
cefpython = importlib.import_module(
    ".cefpython_py{0}{1}".format(*sys.version_info[:2]), __name__)
