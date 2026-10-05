// Copyright (c) 2012 CEF Python, see the Authors file.
// All rights reserved. Licensed under BSD 3-clause license.
// Project website: https://github.com/cztomczak/cefpython

/* This is a wrapper around including cefpython_fixed.h that is generated
   by Cython. Functions marked with the 'public' keyword are exposed
   to C through that header file. */

#ifndef CEFPYTHON_PUBLIC_API_H
#define CEFPYTHON_PUBLIC_API_H

#if defined(OS_WIN)
#pragma warning(disable:4190)  // cefpython API extern C-linkage warnings
#endif

// Python.h must be included first otherwise error on Linux:
// >> error: "_POSIX_C_SOURCE" redefined
#include "Python.h"


// Includes required by "cefpython_fixed.h".
#include "include/cef_client.h"
#include "include/cef_urlrequest.h"
#include "include/cef_command_line.h"
#include "util.h"

// cefpython_fixed.h declares public functions using DL_IMPORT and these
// macros are not available in Python 3.
#ifndef DL_IMPORT
#define DL_IMPORT(RTYPE) RTYPE
#endif
#ifndef DL_EXPORT
#define DL_EXPORT(RTYPE) RTYPE
#endif

#if PY_MAJOR_VERSION != 3 || PY_MINOR_VERSION < 12
#error "CEF Python requires Python 3.12 or later"
#elif PY_MINOR_VERSION == 12
#include "../../build/build_cefpython/cefpython_py312_fixed.h"
#elif PY_MINOR_VERSION == 13
#include "../../build/build_cefpython/cefpython_py313_fixed.h"
#elif PY_MINOR_VERSION == 14
#include "../../build/build_cefpython/cefpython_py314_fixed.h"
#else
#error "Unsupported Python version, add it to cefpython_public_api.h"
#endif

#endif // CEFPYTHON_PUBLIC_API_H
