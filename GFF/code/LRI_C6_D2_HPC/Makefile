CXX ?= g++
CPPFLAGS ?=
# User-adjustable. The numerical flags in C6_REQUIRED are always appended and cannot be dropped by the environment.
CXXFLAGS ?= -O3 -std=c++17
override C6_REQUIRED = -fopenmp -ffp-contract=off -fno-fast-math
LDLIBS = -lquadmath
PYTHON ?= python3
.PHONY: all test test-python test-workflow test-points test-levels test-e2e prepare clean
all: bin/c6_integrate
bin/c6_integrate: src/c6_integrate.cpp src/kernel.hpp Makefile
	@mkdir -p bin
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) $(C6_REQUIRED) $< $(LDLIBS) -o $@
prepare:
	$(PYTHON) -B tools/prepare_inputs.py
# Pure Python (no native binary): archived assembly, input regeneration, archived seed replay, orchestration.
test-python: prepare
	$(PYTHON) -B tests/archived_assembly.py
	$(PYTHON) -B tests/check_inputs.py
	$(PYTHON) -B tests/archived_replay.py
	$(PYTHON) -B tests/unit_orchestration.py
test: all test-python
	$(PYTHON) -B tests/validate.py
test-workflow: all prepare
	$(PYTHON) -B tests/workflow.py
test-points: all prepare
	$(PYTHON) -B tests/check_points.py
test-levels: all prepare
	$(PYTHON) -B tests/force_levels.py
test-e2e: all prepare
	$(PYTHON) -B tests/e2e_reference.py
clean:
	rm -f bin/c6_integrate
