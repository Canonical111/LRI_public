CXX ?= g++
CXXFLAGS ?= -O3
STRICT = -std=c++17 -fopenmp -ffp-contract=off -fno-fast-math
.PHONY: all decimal gmp inputs test test-full clean
all: decimal inputs
# Distinct filenames make changing the arithmetic backend explicit and auditable.
decimal: bin/c7d2_decimal
gmp: bin/c7d2_gmp inputs
bin/c7d2_decimal: src/c7d2_integrate.cpp src/kernel.hpp
	@mkdir -p bin
	$(CXX) $(CXXFLAGS) $(STRICT) $< -lquadmath -o $@
bin/c7d2_gmp: src/c7d2_integrate.cpp src/kernel.hpp
	@mkdir -p bin
	$(CXX) $(CXXFLAGS) $(STRICT) -DC7_USE_GMP $< -lquadmath -lgmp -o $@
inputs:
	python3 tools/prepare_inputs.py
test: all
	OPENBLAS_NUM_THREADS=1 python3 tests/validate.py
	OPENBLAS_NUM_THREADS=1 python3 tests/workflow.py
test-full: all gmp
	OPENBLAS_NUM_THREADS=1 python3 tests/validate.py --full
	OPENBLAS_NUM_THREADS=1 python3 tests/check_points.py
	OPENBLAS_NUM_THREADS=1 python3 tools/reassemble_reference.py
clean:
	rm -f bin/c7d2_decimal bin/c7d2_gmp
