// Copyright (c) 2016 CEF Python, see the Authors file.
// All rights reserved. Licensed under BSD 3-clause license.
// Project website: https://github.com/cztomczak/cefpython

// NOTE: This file is also used by "subprocess" and "libcefpythonapp"
//       targets during build.

#include "x11.h"
#include "include/base/cef_logging.h"
#include "include/base/cef_callback.h"
#include "include/cef_task.h"
#include "include/wrapper/cef_closure_task.h"

#include <string.h>
#include <unistd.h>

#include <X11/Xatom.h>

int XErrorHandlerImpl(Display *display, XErrorEvent *event) {
    LOG(INFO) << "[Browser process] "
        << "X error received: "
        << "type " << event->type << ", "
        << "serial " << event->serial << ", "
        << "error_code " << static_cast<int>(event->error_code) << ", "
        << "request_code " << static_cast<int>(event->request_code) << ", "
        << "minor_code " << static_cast<int>(event->minor_code);
    return 0;
}

int XIOErrorHandlerImpl(Display *display) {
    return 0;
}

void InstallX11ErrorHandlers() {
    // Copied from upstream cefclient.
    // Install xlib error handlers so that the application won't be terminated
    // on non-fatal errors. Must be done after initializing GTK.
    LOG(INFO) << "[Browser process] Install X11 error handlers";
    XSetErrorHandler(XErrorHandlerImpl);
    XSetIOErrorHandler(XIOErrorHandlerImpl);
}

// Since Chromium 128 the browser window is created with the default
// visual and a colormap inherited from the parent window. Creating it
// fails with a MatchError when the parent window uses a different
// visual, which is the case with GTK 3 (also wxPython). In such case
// a wrapper window with the default visual is created between the
// parent window and the browser window.
static const char kWrapperProperty[] = "_CEFPYTHON_BROWSER_WRAPPER";

static bool IsX11WrapperWindow(::Display* xdisplay, ::Window xwindow) {
    Atom property = XInternAtom(xdisplay, kWrapperProperty, True);
    if (property == None)
        return false;
    Atom type = None;
    int format = 0;
    unsigned long nitems = 0, bytes_after = 0;
    unsigned char* data = NULL;
    bool ret = false;
    if (XGetWindowProperty(xdisplay, xwindow, property, 0, 1, False,
                           XA_CARDINAL, &type, &format, &nitems,
                           &bytes_after, &data) == 0) {
        ret = (type == XA_CARDINAL);
        if (data)
            XFree(data);
    }
    return ret;
}

// Returns the wrapper window that is the parent of the browser
// window, or 0 when there is no wrapper window.
static ::Window GetX11WrapperWindow(::Display* xdisplay, ::Window xwindow) {
    ::Window root = 0, parent = 0;
    ::Window* children = NULL;
    unsigned int nchildren = 0;
    if (!XQueryTree(xdisplay, xwindow, &root, &parent, &children,
                    &nchildren))
        return 0;
    if (children)
        XFree(children);
    if (parent && parent != root && IsX11WrapperWindow(xdisplay, parent))
        return parent;
    return 0;
}

::Window GetX11BrowserParentWindow(::Window parent, int x, int y,
                                   int width, int height) {
    ::Display* xdisplay = cef_get_xdisplay();
    if (!xdisplay || !parent)
        return parent;
    XWindowAttributes attrs;
    if (!XGetWindowAttributes(xdisplay, parent, &attrs))
        return parent;
    int screen = DefaultScreen(xdisplay);
    Visual* visual = DefaultVisual(xdisplay, screen);
    if (XVisualIDFromVisual(attrs.visual) == XVisualIDFromVisual(visual))
        return parent;
    if (width <= 0 || height <= 0) {
        width = attrs.width;
        height = attrs.height;
    }
    XSetWindowAttributes wrapper_attrs = {};
    wrapper_attrs.colormap = DefaultColormap(xdisplay, screen);
    wrapper_attrs.border_pixel = 0;
    wrapper_attrs.background_pixel = WhitePixel(xdisplay, screen);
    ::Window wrapper = XCreateWindow(
            xdisplay, parent, x, y, width > 0 ? width : 1,
            height > 0 ? height : 1, 0, DefaultDepth(xdisplay, screen),
            InputOutput, visual, CWColormap | CWBorderPixel | CWBackPixel,
            &wrapper_attrs);
    if (!wrapper)
        return parent;
    unsigned long value = 1;
    XChangeProperty(xdisplay, wrapper,
                    XInternAtom(xdisplay, kWrapperProperty, False),
                    XA_CARDINAL, 32, PropModeReplace,
                    reinterpret_cast<unsigned char*>(&value), 1);
    XMapWindow(xdisplay, wrapper);
    // The browser window is created using another X connection
    XSync(xdisplay, False);
    LOG(INFO) << "[Browser process] Created X11 wrapper window for"
                 " parent window with non-default visual";
    return wrapper;
}

static void DestroyX11WindowTask(::Window xwindow) {
    ::Display* xdisplay = cef_get_xdisplay();
    if (xdisplay) {
        XDestroyWindow(xdisplay, xwindow);
        XFlush(xdisplay);
    }
}

void DestroyX11WrapperWindow(CefRefPtr<CefBrowser> browser) {
    ::Display* xdisplay = cef_get_xdisplay();
    if (!xdisplay)
        return;
    ::Window wrapper = GetX11WrapperWindow(
            xdisplay, browser->GetHost()->GetWindowHandle());
    if (!wrapper)
        return;
    // Hide it now and destroy it after the browser window was
    // destroyed by CEF.
    XUnmapWindow(xdisplay, wrapper);
    XFlush(xdisplay);
    CefPostDelayedTask(TID_UI, base::BindOnce(&DestroyX11WindowTask,
                                              wrapper), 2000);
}

void SetX11WindowBounds(CefRefPtr<CefBrowser> browser,
                        int x, int y, int width, int height) {
    ::Window xwindow = browser->GetHost()->GetWindowHandle();
    ::Display* xdisplay = cef_get_xdisplay();
    XWindowChanges changes = {0};
    changes.x = x;
    changes.y = y;
    changes.width = static_cast<int>(width);
    changes.height = static_cast<int>(height);
    ::Window wrapper = GetX11WrapperWindow(xdisplay, xwindow);
    if (wrapper) {
        XConfigureWindow(xdisplay, wrapper,
                         CWX | CWY | CWHeight | CWWidth, &changes);
        changes.x = 0;
        changes.y = 0;
    }
    XConfigureWindow(xdisplay, xwindow,
                     CWX | CWY | CWHeight | CWWidth, &changes);
}

// Returns the _NET_WM_PID property of a window or 0 when not set.
static unsigned long GetX11WindowPid(::Display* xdisplay, ::Window xwindow) {
    Atom net_wm_pid = XInternAtom(xdisplay, "_NET_WM_PID", True);
    if (net_wm_pid == None)
        return 0;
    Atom type = None;
    int format = 0;
    unsigned long nitems = 0, bytes_after = 0;
    unsigned char* data = NULL;
    unsigned long pid = 0;
    if (XGetWindowProperty(xdisplay, xwindow, net_wm_pid, 0, 1, False,
                           XA_CARDINAL, &type, &format, &nitems,
                           &bytes_after, &data) == 0) {
        if (data && type == XA_CARDINAL && format == 32 && nitems == 1)
            pid = *reinterpret_cast<unsigned long*>(data);
        if (data)
            XFree(data);
    }
    return pid;
}

// Returns the top-level window for a CEF browser window that was
// created without a parent window. This is the topmost ancestor that
// belongs to the current process (Chromium sets _NET_WM_PID on its
// top-level windows). Never returns a window manager's frame window.
static ::Window GetX11TopLevelWindow(::Display* xdisplay, ::Window xwindow) {
    const unsigned long pid = static_cast<unsigned long>(getpid());
    ::Window toplevel = xwindow;
    ::Window current = xwindow;
    while (current) {
        if (GetX11WindowPid(xdisplay, current) == pid)
            toplevel = current;
        ::Window root = 0, parent = 0;
        ::Window* children = NULL;
        unsigned int nchildren = 0;
        if (!XQueryTree(xdisplay, current, &root, &parent, &children,
                        &nchildren))
            break;
        if (children)
            XFree(children);
        if (!parent || parent == root)
            break;
        current = parent;
    }
    return toplevel;
}

void SetX11WindowTitle(CefRefPtr<CefBrowser> browser, char* title) {
    ::Display* xdisplay = cef_get_xdisplay();
    ::Window xwindow = GetX11TopLevelWindow(
            xdisplay, browser->GetHost()->GetWindowHandle());
    XStoreName(xdisplay, xwindow, title);
    // Modern window managers read the UTF-8 _NET_WM_NAME property.
    XChangeProperty(xdisplay, xwindow,
                    XInternAtom(xdisplay, "_NET_WM_NAME", False),
                    XInternAtom(xdisplay, "UTF8_STRING", False), 8,
                    PropModeReplace,
                    reinterpret_cast<unsigned char*>(title),
                    static_cast<int>(strlen(title)));
}

GtkWindow* CefBrowser_GetGtkWindow(CefRefPtr<CefBrowser> browser) {
  // TODO: Should return NULL when using the Views framework
  // -- REWRITTEN FOR CEF PYTHON USE CASE --
  // X11 window handle
  ::Window xwindow = browser->GetHost()->GetWindowHandle();
  // X11 display
  ::Display* xdisplay = cef_get_xdisplay();
  // GDK display
  GdkDisplay* gdk_display = NULL;
  if (xdisplay) {
    // See if we can find GDK display using X11 display
    gdk_display = gdk_x11_lookup_xdisplay(xdisplay);
  }
  if (!gdk_display) {
    // If not then get the default display
    gdk_display = gdk_display_get_default();
  }
  if (!gdk_display) {
    // The tkinter_.py and hello_world.py examples do not use GTK
    // internally, so GTK wasn't yet initialized and must do it
    // now, so that display is available. Also must install X11
    // error handlers to avoid 'BadWindow' errors.
    // --
    // A similar code is in cefpython_app.cpp and it might already
    // been executed. If making changes here, make changes there
    // as well.
    LOG(INFO) << "[Browser process] Initialize GTK";
    gtk_init(0, NULL);
    InstallX11ErrorHandlers();
    // Now the display is available
    gdk_display = gdk_display_get_default();
  }
  // In kivy_.py example getting error message:
  // > Can't create GtkPlug as child of non-GtkSocket
  // However dialog handler works just fine.
  GtkWidget* widget = gtk_plug_new_for_display(gdk_display, xwindow);
  // Getting top level widget doesn't seem to be required.
  // OFF: GtkWidget* toplevel = gtk_widget_get_toplevel(widget);
  GtkWindow* window = GTK_WINDOW(widget);
  if (!window) {
    LOG(ERROR) << "No GtkWindow for browser";
  }
  return window;
}

XImage* CefBrowser_GetImage(CefRefPtr<CefBrowser> browser) {
    ::Display* display = cef_get_xdisplay();
    if (!display) {
        LOG(ERROR) << "XOpenDisplay failed in CefBrowser_GetImage";
        return NULL;
    }
    ::Window browser_window = browser->GetHost()->GetWindowHandle();
    XWindowAttributes attrs;
    if (!XGetWindowAttributes(display, browser_window, &attrs)) {
        LOG(ERROR) << "XGetWindowAttributes failed in CefBrowser_GetImage";
        return NULL;
    }
    XImage* image = XGetImage(display, browser_window,
                              0, 0, attrs.width, attrs.height,
                              AllPlanes, ZPixmap);
    if (!image) {
        LOG(ERROR) << "XGetImage failed in CefBrowser_GetImage";
        return NULL;
    }
    return image;
}
