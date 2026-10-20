CXX ?= g++
CPPFLAGS ?=
# User-adjustable. The numerical flags in C6_REQUIRED are always appended and cannot be dropped by the environment.
CXXFLAGS ?= -O3 -std=c++17
override C6_REQUIRED = -fopenmp -ffp-contract=off -fno-fast-math
LDLIBS = -lquadmath
PYTHON ?= python3
.PHONY: all test test-python test-workflow test-points test-levels test-e2e test-replay test-all check-delivery prepare clean
all: bin/c6_integrate
bin/c6_integrate: src/c6_integrate.cpp src/kernel.hpp Makefile
	@mkdir -p bin
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) $(C6_REQUIRED) $< $(LDLIBS) -o $@
prepare:
	$(PYTHON) -B tools/prepare_inputs.py
# Pure Python (no native binary): archived assembly, input regeneration, archived seed replay, conventions, orchestration.
test-python: prepare
	$(PYTHON) -B tests/archived_assembly.py
	$(PYTHON) -B tests/check_inputs.py
	$(PYTHON) -B tests/archived_replay.py
	$(PYTHON) -B tests/dimension_checks.py
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
# Replays the eight archived fresh d=3 production streams (385,744,896 samples; about 2 min at 16 threads).
test-replay: all prepare
	$(PYTHON) -B tests/archived_stream_replay.py
test-all: test test-workflow test-points test-levels test-e2e test-replay
# Package integrity: every listed file unchanged and every package file listed (after `checksums.py write`).
check-delivery:
	$(PYTHON) -B tools/checksums.py verify --strict
clean:
	rm -f bin/c6_integrate
