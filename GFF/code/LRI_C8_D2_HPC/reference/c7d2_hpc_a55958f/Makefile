CXX ?= g++
# User-adjustable hooks. OPTFLAGS keeps -O3 when CXXFLAGS or CPPFLAGS add include paths; the numerical flags in
# C7_REQUIRED are always appended and, like the compile commands below, cannot be overridden from the command line.
# Default settings give exactly the delivered commands
# (g++ -O3 -std=c++17 -fopenmp -ffp-contract=off -fno-fast-math src/c7d2_integrate.cpp -lquadmath [-lgmp] -o ...).
OPTFLAGS ?= -O3
CPPFLAGS ?=
CXXFLAGS ?=
LDFLAGS ?=
LDLIBS ?=
override C7_REQUIRED = -std=c++17 -fopenmp -ffp-contract=off -fno-fast-math
# LDFLAGS and LDLIBS follow the required flags in the compile-and-link command, so they may hold link-only words;
# a compiler option there (e.g. -O0 or -ffast-math) would override the required flags.
override C7_LINK_ONLY = -L% -l% -Wl,% -pthread -static% -rdynamic -fuse-ld=% %.a %.so %.o
override C7_BAD_LINK = $(strip $(filter-out $(C7_LINK_ONLY),$(LDFLAGS) $(LDLIBS)))
ifneq ($(C7_BAD_LINK),)
$(error LDFLAGS/LDLIBS may hold only link options (-L* -l* -Wl,* -pthread -static* -rdynamic -fuse-ld=* *.a *.so *.o), not: $(C7_BAD_LINK). Put compiler options in CPPFLAGS, OPTFLAGS or CXXFLAGS)
endif
PYTHON ?= python3
override COMPILE = $(strip $(CXX) $(CPPFLAGS) $(OPTFLAGS) $(CXXFLAGS) $(C7_REQUIRED))
override DECIMAL_CMD = $(COMPILE) $< $(strip $(LDFLAGS) -lquadmath $(LDLIBS)) -o $@
override GMP_CMD = $(COMPILE) -DC7_USE_GMP $< $(strip $(LDFLAGS) -lquadmath -lgmp $(LDLIBS)) -o $@
# tools/build_record.py receives the exact compile command as arguments; the make variables are recorded as well.
override C7B_CXX = $(CXX)
override C7B_CPPFLAGS = $(CPPFLAGS)
override C7B_OPTFLAGS = $(OPTFLAGS)
override C7B_CXXFLAGS = $(CXXFLAGS)
override C7B_REQUIRED = $(C7_REQUIRED)
override C7B_LDFLAGS = $(LDFLAGS)
override C7B_LDLIBS = $(LDLIBS)
export C7B_CXX C7B_CPPFLAGS C7B_OPTFLAGS C7B_CXXFLAGS C7B_REQUIRED C7B_LDFLAGS C7B_LDLIBS
# A failed build-record step removes the executable, so the next make rebuilds both.
.DELETE_ON_ERROR:
.PHONY: all decimal gmp inputs test test-python test-full clean
all: decimal inputs
# Distinct filenames make changing the arithmetic backend explicit and auditable.
decimal: bin/c7d2_decimal
gmp: bin/c7d2_gmp inputs
bin/c7d2_decimal: src/c7d2_integrate.cpp src/kernel.hpp Makefile
	@mkdir -p bin
	$(DECIMAL_CMD)
	$(PYTHON) -B tools/build_record.py $@ decimal -- $(DECIMAL_CMD)
bin/c7d2_gmp: src/c7d2_integrate.cpp src/kernel.hpp Makefile
	@mkdir -p bin
	$(GMP_CMD)
	$(PYTHON) -B tools/build_record.py $@ gmp -- $(GMP_CMD)
inputs:
	$(PYTHON) -B tools/prepare_inputs.py
# Pure Python, no native binary (also run on the packaging host).
test-python: inputs
	OPENBLAS_NUM_THREADS=1 $(PYTHON) -B tests/unit_orchestration.py
	OPENBLAS_NUM_THREADS=1 $(PYTHON) -B tests/check_inputs.py
test: all
	OPENBLAS_NUM_THREADS=1 $(PYTHON) -B tests/validate.py
	OPENBLAS_NUM_THREADS=1 $(PYTHON) -B tests/unit_orchestration.py
	OPENBLAS_NUM_THREADS=1 $(PYTHON) -B tests/check_inputs.py
	OPENBLAS_NUM_THREADS=1 $(PYTHON) -B tests/workflow.py
	OPENBLAS_NUM_THREADS=1 $(PYTHON) -B tests/staging.py
test-full: all gmp
	OPENBLAS_NUM_THREADS=1 $(PYTHON) -B tests/validate.py --full
	OPENBLAS_NUM_THREADS=1 $(PYTHON) -B tests/check_points.py
	OPENBLAS_NUM_THREADS=1 $(PYTHON) -B tools/reassemble_reference.py
clean:
	rm -f bin/c7d2_decimal bin/c7d2_gmp bin/c7d2_decimal.build.json bin/c7d2_gmp.build.json
