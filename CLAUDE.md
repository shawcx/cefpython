# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

CEF Python (`cefpython3`): Cython bindings for the Chromium Embedded Framework. This branch targets CEF 154 / Chromium 154 (see `src/version/cef_version_*.h`) and Python 3.12+ only. Cython is pinned to an exact version in `tools/requirements.txt` (`build.py` checks it) and compiles with `language_level=3`.

Only Linux x64 has been ported and tested on CEF 154. The Windows and Mac code paths still need work: `src/include/` has Windows/Mac-only headers left over from CEF 123, and the Mac helper bundles are not done.

## Build

Builds run from a `build/` directory at the repo root (it's gitignored and you create it yourself). Extract the CEF binary distribution from https://cef-builds.spotifycdn.com/index.html into `build/`; its version must match `CEF_VERSION` in `src/version/cef_version_<os>.h` exactly. Then run `automate.py --prebuilt-cef`, which builds `libcef_dll_wrapper` and creates `build/cefNNN_<version>_<os>/`. Use a venv (`venv/` at the repo root is gitignored); `build.py` installs the package with `pip`.

```sh
python3.12 -m venv venv && venv/bin/pip install -r tools/requirements.txt
cd build
../venv/bin/python ../tools/automate.py --prebuilt-cef
../venv/bin/python ../tools/build.py 154.0                # build, install, run unit tests, then run examples
../venv/bin/python ../tools/build.py 154.0 --unittests    # skip the interactive examples
../venv/bin/python ../tools/build.py 154.0 --clean        # also rebuild all C++ objects (Linux/Mac)
```

On Linux, `build.py` needs `cmake g++ ninja-build pkg-config libgtk-3-dev`. The C++ code is compiled as C++20 with `-Werror`.

The first run after a clean build always fails once on purpose. The C++ code needs the `cefpython_pyXY.h` header that Cython generates, so `build.py` re-runs itself. Run it with `</dev/null`, because otherwise a failed `make` prompts for input.

What `build.py` does:
1. Compiles the C++ static libs (`client_handler`, `cpp_utils`, `subprocess`/`libcefpythonapp`) with `make` on Linux/Mac, or `build_cpp_projects.py` on Windows.
2. Copies `src/*.pyx` into `build/build_cefpython/` and rewrites them. It strips the duplicate `include` statements from every file except `cefpython.pyx`, and it checks that `cdef` functions returning C types have `except *`.
3. Cythonizes the result into `cefpython_pyXY`.
4. Patches the generated `cefpython_pyXY.h` public API header.
5. Builds a wheel with `make_installer.py --wheel` and installs it with `pip`.
6. Runs `unittests/_test_runner.py`, then the examples (`tools/run_examples.py`).

Packaging: `tools/make_deb.py VERSION` builds `build/python3-cefpython3_VERSION-1_amd64.deb` (Linux; runs make_installer.py, strips binaries, gets dependencies from dpkg-shlibdeps). `tools/make_installer.py VERSION [--wheel --python-tag py3]`. The wheel contains a `cefpython_pyXY` module for every Python version you've built with. Its `manylinux_2_X` tag comes from the highest `GLIBC_` symbol version used by the packaged binaries, so build in an older environment for broader compatibility. `tools/build_distrib.py VERSION` builds packages for every Python version and architecture.

## Tests

The tests need an installed `cefpython3` built by the step above.

```sh
python unittests/_test_runner.py                 # all tests
python unittests/_test_runner.py main_test.py    # one file
```

CEF constraints shape the tests:
- CEF can be initialized only once per process. So each test class has a single `test_main()` that runs its subtests (reported with `subtest_message()`).
- A class whose name contains `IsolatedTest` runs in its own Python interpreter. It must call `cef.Initialize` and `cef.Shutdown` itself.
- Files starting with `_` are not collected as tests.
- In `main_test.py`, attributes on handler or external objects ending in `_True` or `_False` are asserted automatically before shutdown. Set them before any normal asserts.
- Tests depend on timing, so run the suite several times after a change. Recent Chromium versions changed several behaviours the tests depended on, and the comments in `main_test.py` and `osr_test.py` explain them:
  - V8 contexts are no longer created for the initial empty document.
  - `layoutComplete` accessibility events are no longer sent.
  - Input events sent right at load end are dropped.
- Minimum manual check before a PR: unit tests plus `examples/hello_world.py`, `tutorial.py` and `screenshot.py`.

## Architecture

- **`src/cefpython.pyx`** is the single Cython compilation unit. It `include`s every other `src/*.pyx` and `src/handlers/*.pyx`. The other `.pyx` files also contain `include`s, but only so IDEs resolve symbols, and `build.py` strips them. A new `.pyx` must be added to the include list in `cefpython.pyx`.
- **`src/extern/*.pxd`** declares the C++ APIs (CEF headers in `src/extern/cef/`, plus this project's C++ classes). Declare CEF calls `nogil` in the `.pxd` and call them inside `with nogil:` in the `.pyx`, to avoid deadlocks.
- **C++ → Python callbacks:**
  - `src/client_handler/` implements CEF's `CefClient` handler interfaces in C++.
  - Those handlers call `cdef public ... with gil` functions defined in `src/handlers/*.pyx` (and in `cefpython.pyx`).
  - Cython exports those functions in the generated `cefpython_pyXY.h`, which the C++ code includes through `src/common/cefpython_public_api.h`.
  - Python users register handler objects with `browser.SetClientHandler()`.
- **Renderer process:**
  - `src/subprocess/` builds the separate `subprocess` executable (`main.cpp`, `CefPythonApp`). It runs CEF's renderer and other child processes.
  - It has no Python in it. JavaScript bindings and V8 callbacks talk to the browser process through CEF process messages: C++ `v8function_handler`/`javascript_callback` on the subprocess side, and `process_message_utils.pyx`/`javascript_bindings.pyx` on the Python side.
  - `libcefpythonapp` is the same app code built as a library for the browser process.
- **Platform code:**
  - Platform-specific `.pyx` files are `window_utils_{win,linux,mac}.pyx`, `string_utils_win.pyx` and `dpi_aware_win.pyx`.
  - Platform C++ code is `x11.cpp`, `util_mac.mm` and the `*_gtk.cpp` dialog and print handlers.
  - The GTK handlers and `main_message_loop_external_pump_linux.cpp` are copies of upstream cefclient files. The `.patch` file next to each one records our changes, and `util_gtk.h` replaces the cefclient helpers they use. When updating CEF, regenerate them from the new `tests/cefclient` sources rather than editing them by hand.
  - `src/include/cef_config.h` is shared by all platforms and defines `CEF_X11` on Linux.
  - Compile-time constants come from `compile_time_constants.pxi`, which `build.py` generates.
- **`patches/`** holds patches applied to upstream CEF when building it from source.
- **`api/`** holds the Markdown API reference. When you add or change an API, update the doc, then run `tools/toc.py` (TOC) and `tools/apidocs.py` (API index).
- **`examples/`** has GUI framework integrations (Qt, wx, GTK, Tk, PySDL2, ...); supported ones are listed in `examples/README-examples.md`.
- **X11 embedding:** GTK 3 and wxPython parent windows use a non-default X visual, and CEF can't create its child window directly under them (`MatchError`). `GetX11BrowserParentWindow` in `x11.cpp` inserts a wrapper window when needed, and `SetX11WindowBounds` resizes both windows.
- **Runtime style:** `window_info.pyx` forces `CEF_RUNTIME_STYLE_ALLOY` for every browser. CEF's default Chrome style does not support all the client callbacks that cefpython implements.
- **JavaScript bindings** passed to `CreateBrowserSync(javascript_bindings=...)` travel in CEF's `extra_info` and are applied in the renderer's `OnBrowserCreated`, so page scripts see them from the start. Popups get them the same way in `LifespanHandler_OnBeforePopup` when the bindings have `bindToPopups=True`. Bindings set later with `SetJavascriptBindings()` arrive by process message and can lose the race with `window.onload`.

## Conventions

- PEP 8 with 79-char lines; keep comments to about 60–65 chars. Use 4-space indents and Unix newlines.
- Send PRs to `master`, one feature per PR. Contributors add themselves to `Authors`.
- When updating the CEF version, follow issue #264. Diffs between CEF versions are in `src/cef_v*_changes.txt`.
- When CEF removes a setting or constant, keep the Python name. Removed settings log `Debug("DEPRECATED: ...")` and do nothing; removed constants keep their old value. Then document the change in `docs/Migration-guide.md`.
