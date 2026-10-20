CXX ?= g++
# Default is portable within x86-64; set ARCH=-march=native only on compatible compute CPUs.
ARCH ?=
# CXXFLAGS may be overridden; C8_REQUIRED is always appended after it. CPPFLAGS holds include paths (e.g. -I$BOOST_ROOT/include).
CXXFLAGS ?= -O3 -g
C8_REQUIRED = -std=c++17 -fopenmp -fno-fast-math -ffp-contract=off
CPPFLAGS ?=
LDFLAGS ?=
LDLIBS = -lquadmath
# GCC 8 keeps std::filesystem in libstdc++fs. Empty (clang, no compiler) or non-numeric majors add nothing.
GCC_MAJOR := $(shell $(CXX) --version 2>/dev/null | grep -qi clang || $(CXX) -dumpversion 2>/dev/null | cut -d. -f1)
ifneq ($(filter 1 2 3 4 5 6 7 8,$(GCC_MAJOR)),)
LDLIBS += -lstdc++fs
endif
# RPATH=1 embeds the compiler's runtime-library directory, so a module-GCC binary runs without the module loaded.
RPATH ?=
RPATH_FLAGS =
ifeq ($(RPATH),1)
GOMP_SO := $(shell $(CXX) -print-file-name=libgomp.so)
ifeq ($(filter /%,$(GOMP_SO)),)
$(error RPATH=1: $(CXX) -print-file-name=libgomp.so gave no absolute path)
endif
RPATH_FLAGS = -Wl,-rpath,$(patsubst %/,%,$(dir $(GOMP_SO)))
endif
.PHONY: all test clean inputs
all: bin/c8_integrate
bin/c8_integrate: src/c8_integrate.cpp src/common.hpp src/point.hpp src/power.hpp
	mkdir -p bin
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) $(C8_REQUIRED) $(ARCH) $< -o $@ $(LDFLAGS) $(LDLIBS) $(RPATH_FLAGS)
inputs:
	python3 gen/index_coord.py inputs8/L*_coord.txt
# Local, fast checks of the Python tooling; kernel regressions run on x86-64 Linux (tests/c8_vs_c7.py, tests/bench8.py).
test:
	python3 tests/test_c8_tools.py
	python3 tests/test_pipeline8.py
clean:
	rm -f bin/c8_integrate
