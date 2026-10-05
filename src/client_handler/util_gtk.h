// Copyright (c) 2026 CEF Python, see the Authors file.
// All rights reserved. Licensed under BSD 3-clause license.
// Project website: https://github.com/cztomczak/cefpython

// Replacements for the upstream "cef/tests/cefclient/browser/util_gtk.h",
// "cef/tests/shared/browser/main_message_loop.h" and
// "cef/tests/shared/common/string_util.h" helpers that are
// used by dialog_handler_gtk.cpp and print_handler_gtk.cpp. In CEF Python
// the GTK main thread is the CEF UI thread.

// NOTE: This file is also used by "libcefpythonapp" target during build.

#pragma once

#include <gtk/gtk.h>

#include <sstream>
#include <string>
#include <vector>

#include "include/base/cef_bind.h"
#include "include/base/cef_callback.h"
#include "include/base/cef_platform_thread.h"
#include "include/cef_task.h"
#include "include/wrapper/cef_closure_task.h"
#include "include/wrapper/cef_helpers.h"

#define CURRENTLY_ON_MAIN_THREAD() CefCurrentlyOn(TID_UI)
#define REQUIRE_MAIN_THREAD() CEF_REQUIRE_UI_THREAD()
#define MAIN_POST_CLOSURE(closure) CefPostTask(TID_UI, closure)

// Scoped helper that manages the global GDK lock by calling
// gdk_threads_enter() and gdk_threads_leave(). The lock is not
// reentrant so it is taken only when not already held by the
// current thread.
class ScopedGdkThreadsEnter {
 public:
  ScopedGdkThreadsEnter() {
    base::PlatformThreadId current_thread = base::PlatformThread::CurrentId();
    take_lock_ = current_thread != locked_thread_;
    if (take_lock_) {
      gdk_threads_enter();
      locked_thread_ = current_thread;
    }
  }
  ~ScopedGdkThreadsEnter() {
    if (take_lock_) {
      locked_thread_ = kInvalidPlatformThreadId;
      gdk_threads_leave();
    }
  }
  ScopedGdkThreadsEnter(const ScopedGdkThreadsEnter&) = delete;
  ScopedGdkThreadsEnter& operator=(const ScopedGdkThreadsEnter&) = delete;

 private:
  bool take_lock_;
  static inline base::PlatformThreadId locked_thread_ =
      kInvalidPlatformThreadId;
};

// Split |str| at each instance of |delim|.
inline std::vector<std::string> AsciiStrSplit(const std::string& str,
                                              char delim) {
  std::vector<std::string> result;
  std::stringstream ss(str);
  std::string item;
  while (getline(ss, item, delim)) {
    result.push_back(item);
  }
  return result;
}
