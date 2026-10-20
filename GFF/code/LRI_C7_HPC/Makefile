CXX ?= g++
# Default is portable within x86-64; set ARCH=-march=native only on compatible compute CPUs.
ARCH ?=
# CXXFLAGS may be overridden; C7_REQUIRED is always appended after it. CPPFLAGS holds include paths (e.g. -I$BOOST_ROOT/include).
CXXFLAGS ?= -O3 -g
C7_REQUIRED = -std=c++17 -fopenmp -fno-fast-math -ffp-contract=off
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
all: bin/c7_integrate
bin/c7_integrate: src/c7_integrate.cpp src/common.hpp src/point.hpp src/power.hpp
	mkdir -p bin
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) $(C7_REQUIRED) $(ARCH) $< -o $@ $(LDFLAGS) $(LDLIBS) $(RPATH_FLAGS)
inputs:
	python3 tools/prepare_inputs.py reference/inputs
# Tests add oracle and malformed-input checks and use small, actual C7 graph subsets.
test: all
	OPENBLAS_NUM_THREADS=1 python3 tests/validate.py
	python3 tests/test_pipeline.py
	python3 tests/check_inventory.py build/validation/full_inventory.json
clean:
	rm -f bin/c7_integrate bin/test_points
