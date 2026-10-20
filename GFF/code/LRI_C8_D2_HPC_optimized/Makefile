CXX ?= g++
PYTHON ?= python3
OPTFLAGS ?= -O3
CPPFLAGS ?=
CXXFLAGS ?=
LDFLAGS ?=
LDLIBS ?=
override C8_REQUIRED = -std=c++17 -fopenmp -ffp-contract=off -fno-fast-math
override C8_LINK_ONLY = -L% -l% -Wl,% -pthread -static% -rdynamic -fuse-ld=% %.a %.so %.o
override C8_BAD_LINK = $(strip $(filter-out $(C8_LINK_ONLY),$(LDFLAGS) $(LDLIBS)))
ifneq ($(C8_BAD_LINK),)
$(error LDFLAGS/LDLIBS accept only link options; compiler options belong in CPPFLAGS, OPTFLAGS or CXXFLAGS)
endif
override COMPILE = $(strip $(CXX) $(CPPFLAGS) $(OPTFLAGS) $(CXXFLAGS) $(C8_REQUIRED))
override DECIMAL_CMD = $(COMPILE) $< $(strip $(LDFLAGS) -lquadmath $(LDLIBS)) -o $@
override GMP_CMD = $(COMPILE) -DC8_USE_GMP $< $(strip $(LDFLAGS) -lquadmath -lgmp $(LDLIBS)) -o $@
override C8B_CXX = $(CXX)
override C8B_CPPFLAGS = $(CPPFLAGS)
override C8B_OPTFLAGS = $(OPTFLAGS)
override C8B_CXXFLAGS = $(CXXFLAGS)
override C8B_REQUIRED = $(C8_REQUIRED)
override C8B_LDFLAGS = $(LDFLAGS)
override C8B_LDLIBS = $(LDLIBS)
export C8B_CXX C8B_CPPFLAGS C8B_OPTFLAGS C8B_CXXFLAGS C8B_REQUIRED C8B_LDFLAGS C8B_LDLIBS
.DELETE_ON_ERROR:
.PHONY: all decimal gmp test test-kernel test-workflow clean
all: decimal
decimal: bin/c8d2_decimal
gmp: bin/c8d2_gmp
bin/c8d2_decimal: src/c8d2_integrate.cpp src/kernel.hpp src/positive_qadd.hpp src/build_record.py Makefile
	@mkdir -p bin
	$(DECIMAL_CMD)
	$(PYTHON) -B src/build_record.py $@ decimal -- $(DECIMAL_CMD)
bin/c8d2_gmp: src/c8d2_integrate.cpp src/kernel.hpp src/positive_qadd.hpp src/build_record.py Makefile
	@mkdir -p bin
	$(GMP_CMD)
	$(PYTHON) -B src/build_record.py $@ gmp -- $(GMP_CMD)
test-kernel: decimal
	OPENBLAS_NUM_THREADS=1 $(PYTHON) -B tests/kernel_checks.py
test: test-kernel
	OPENBLAS_NUM_THREADS=1 $(PYTHON) -B tests/assembly_formula.py --production-module tools/assemble.py
test-workflow: gmp
	OPENBLAS_NUM_THREADS=1 $(PYTHON) -B tests/workflow.py
clean:
	rm -f bin/c8d2_decimal bin/c8d2_gmp bin/c8d2_decimal.build.json bin/c8d2_gmp.build.json
