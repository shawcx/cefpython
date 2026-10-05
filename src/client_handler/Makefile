# -g - extra debug information
# -O1 - more precise backtraces
# -fPIC - required when using -shared option, required for use with Cython
# -Wall - show important warnings
# -Werror - treat warnings as errors

# Cython compiler options on Linux:
# -fPIC -shared -Wl,-O1 -Wl,-Bsymbolic-functions -Wl,-Bsymbolic-functions \
# -Wl,-z,relro

UNAME_S = $(shell uname -s)
CCFLAGS = -fPIC $(CEF_CCFLAGS)

ifeq ($(UNAME_S), Linux)
	SRC_MORE = x11.cpp dialog_handler_gtk.cpp
else ifeq ($(UNAME_S), Darwin)
	SRC_MORE = util_mac.mm
endif

SRC = client_handler.cpp cookie_visitor.cpp resource_handler.cpp \
	web_request_client.cpp string_visitor.cpp \
	task.cpp context_menu_handler.cpp display_handler.cpp \
	download_handler.cpp focus_handler.cpp js_dialog_handler.cpp \
	keyboard_handler.cpp lifespan_handler.cpp load_handler.cpp \
	render_handler.cpp request_handler.cpp dialog_handler.cpp \
	cef_log.cpp accessibility_handler.cpp cookie_access_filter.cpp \
	$(SRC_MORE)

OBJ = $(filter %.o, $(SRC:.cpp=.o) $(SRC:.mm=.o))
.SUFFIXES: .cpp .mm .o

OUT = libclient_handler.a

INC = -I./../ -I./../common/ -I$(PYTHON_INCLUDE)
ifeq ($(UNAME_S), Linux)
	INC += $(shell pkg-config --cflags gtk+-3.0 gtk+-unix-print-3.0 x11)
endif


$(OUT): $(OBJ)
	@echo [CLIENT HANDLER] Creating library $(OUT) from $(OBJ)...
	ar rcs $(OUT) $(OBJ)

.cpp.o:
	@echo [CLIENT HANDLER] Building $@ from $<...
	$(CXX) $(CCFLAGS) $(INC) -c $< -o $@ -MMD -MP

.mm.o:
	@echo [CLIENT HANDLER] Building $@ from $<...
	$(CXX) $(CCFLAGS) $(INC) -c $< -o $@ -MMD -MP


clean:
	@echo [CLIENT HANDLER] Cleaning...
	rm *.o *.a

# Rebuild objects when included headers change
-include $(OBJ:.o=.d)
