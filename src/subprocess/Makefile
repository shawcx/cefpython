# -g - extra debug information
# -O1 - more precise backtraces
# -fPIC - required when using -shared option, required for use with Cython
# -Wall - show important warnings
# -Werror - treat warnings as errors

UNAME_S = $(shell uname -s)
INC = -I./../ -I./../common/ -I$(PYTHON_INCLUDE)
ifeq ($(UNAME_S), Linux)
	INC += $(shell pkg-config --cflags gtk+-3.0 gtk+-unix-print-3.0 x11)
endif

ifeq ($(UNAME_S), Linux)
	LIB_DIRS = -L$(CEF_BIN) \
							-L$(CEF_LIB)
else ifeq ($(UNAME_S), Darwin)
	LIB_DIRS = -F$(CEF_BIN) \
							-L$(CEF_LIB)
endif

ifeq ($(UNAME_S), Linux)
	CPP_FILES = print_handler_gtk.cpp ../client_handler/x11.cpp
	LIBS = -lcef $(shell pkg-config --libs gtk+-3.0 gtk+-unix-print-3.0 x11)
else ifeq ($(UNAME_S), Darwin)
	CPP_FILES =
	# Include framework before libcef_dll_wrapper
	LIBS = -framework "Chromium Embedded Framework"
endif

CCFLAGS = -DRENDERER_PROCESS $(CEF_CCFLAGS)

subprocess:
	# -fPIC is required only for libraries included by Cython.
	@echo [SUBPROCESS] Building the 'subprocess' executable
	$(CXX) $(CCFLAGS) $(INC) $(LIB_DIRS) main.cpp cefpython_app.cpp \
		v8function_handler.cpp v8utils.cpp javascript_callback.cpp \
		$(CPP_FILES) \
		$(CEF_LINK_FLAGS) \
		$(LIBS) -lcef_dll_wrapper \
		-o subprocess -Wl,-rpath,@loader_path/
