# Copyright (c) 2015 CEF Python, see the Authors file.
# All rights reserved. Licensed under BSD 3-clause license.
# Project website: https://github.com/cztomczak/cefpython

include "compile_time_constants.pxi"

from libcpp cimport bool as cpp_bool
from cef_types cimport CefRect, cef_runtime_style_t

cdef extern from "include/internal/cef_mac.h":

    ctypedef void* CefWindowHandle
    ctypedef void* CefCursorHandle

    cdef cppclass CefWindowInfo:
        void SetAsChild(CefWindowHandle parent,
                        const CefRect& windowRect)
        void SetAsWindowless(CefWindowHandle parent)
        cef_runtime_style_t runtime_style

    cdef cppclass CefMainArgs:
        CefMainArgs()
        CefMainArgs(int argc_arg, char** argv_arg)

cdef extern from "include/wrapper/cef_library_loader.h":
    # Since CEF 75 the CEF framework on Mac is not linked, it must
    # be loaded at runtime before calling any CEF function.
    int cef_load_library(const char* path)
