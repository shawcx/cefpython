// Copyright (c) 2016 CEF Python, see the Authors file.
// All rights reserved. Licensed under BSD 3-clause license.
// Project website: https://github.com/cztomczak/cefpython

#pragma once

#include <X11/Xlib.h>
#include <gtk/gtk.h>
#include <gtk/gtkx.h>
#include <gdk/gdkx.h>

// Xlib.h defines macros that conflict with names in CEF headers,
// eg. "typedef cef_urlrequest_status_t Status" in cef_urlrequest.h.
#undef Status

#include "include/cef_browser.h"

void InstallX11ErrorHandlers();
::Window GetX11BrowserParentWindow(::Window parent, int x, int y,
                                   int width, int height);
void DestroyX11WrapperWindow(CefRefPtr<CefBrowser> browser);
void SetX11WindowBounds(CefRefPtr<CefBrowser> browser,
                        int x, int y, int width, int height);
void SetX11WindowTitle(CefRefPtr<CefBrowser> browser, char* title);

GtkWindow* CefBrowser_GetGtkWindow(CefRefPtr<CefBrowser> browser);
XImage* CefBrowser_GetImage(CefRefPtr<CefBrowser> browser);
