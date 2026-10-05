UNAME_S = $(shell uname -s)
CCFLAGS = -fPIC $(CEF_CCFLAGS)

SRC = PaintBuffer.cpp
OBJ = $(SRC:.cpp=.o)
OUT = libcpp_utils.a

INC = -I./../

.cpp.o:
	$(CXX) $(INC) $(CCFLAGS) -c $< -o $@ -MMD -MP

$(OUT): $(OBJ)
	ar rcs $(OUT) $(OBJ)

# Rebuild objects when included headers change
-include $(OBJ:.o=.d)
