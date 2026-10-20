CXX ?= g++
PYTHON ?= python3
OPTFLAGS ?= -O3
CPPFLAGS ?=
CXXFLAGS ?=
LDFLAGS ?=
LDLIBS ?=
override STRICT = -std=c++17 -fopenmp -ffp-contract=off -fno-fast-math
FLAG_CHECK = $(PYTHON) -B tools/native_buildinfo.py check $(CPPFLAGS) $(OPTFLAGS) $(CXXFLAGS) $(LDFLAGS) $(LDLIBS)
GMP_CMD = $(CXX) $(CPPFLAGS) $(OPTFLAGS) $(CXXFLAGS) $(STRICT) -DC8_USE_GMP src/c8d3_integrate.cpp $(LDFLAGS) -lquadmath -lgmp $(LDLIBS) -o bin/c8d3_gmp
DECIMAL_CMD = $(CXX) $(CPPFLAGS) $(OPTFLAGS) $(CXXFLAGS) $(STRICT) src/c8d3_integrate.cpp $(LDFLAGS) -lquadmath $(LDLIBS) -o bin/c8d3_decimal
REFERENCE_CMD = $(CXX) $(CPPFLAGS) $(OPTFLAGS) $(CXXFLAGS) $(STRICT) -DC7_USE_GMP reference_c7/src/c7d3_integrate.cpp $(LDFLAGS) -lquadmath -lgmp $(LDLIBS) -o bin/c7d3_reference
.PHONY: all gmp decimal points reference test-native test-points requirements hpc check-flags clean
.DELETE_ON_ERROR:
all: gmp
gmp: bin/c8d3_gmp
decimal: bin/c8d3_decimal
points: bin/point_checks_gmp
reference: bin/c7d3_reference
test-native: all points reference
	OPENBLAS_NUM_THREADS=1 $(PYTHON) -B tests/test_native.py
test-points: points
	$(PYTHON) -B tests/check_c8_points.py
# Optional convenience targets. Neither target submits jobs to a cluster.
requirements:
	$(PYTHON) -m pip install -r requirements.txt
hpc: all
	@$(PYTHON) -c "print('Native worker ready. See README.md and slurm/ for cluster commands.')"
check-flags:
	@$(FLAG_CHECK)
bin/c8d3_gmp: src/kernel.hpp src/positive_quad.hpp src/c8d3_integrate.cpp Makefile tools/native_buildinfo.py
	@mkdir -p bin
	@$(FLAG_CHECK)
	$(GMP_CMD)
	@$(PYTHON) -B tools/native_buildinfo.py write bin/c8d3_gmp '$(CXX)' '$(CPPFLAGS)' -- $(GMP_CMD)
bin/c8d3_decimal: src/kernel.hpp src/positive_quad.hpp src/c8d3_integrate.cpp Makefile tools/native_buildinfo.py
	@mkdir -p bin
	@$(FLAG_CHECK)
	$(DECIMAL_CMD)
	@$(PYTHON) -B tools/native_buildinfo.py write bin/c8d3_decimal '$(CXX)' '$(CPPFLAGS)' -- $(DECIMAL_CMD)
bin/point_checks_gmp: src/kernel.hpp src/positive_quad.hpp tests/point_checks.cpp Makefile
	@mkdir -p bin
	@$(FLAG_CHECK)
	$(CXX) $(CPPFLAGS) $(OPTFLAGS) $(CXXFLAGS) $(STRICT) -DC8_USE_GMP tests/point_checks.cpp $(LDFLAGS) -lquadmath -lgmp $(LDLIBS) -o $@
bin/c7d3_reference: reference_c7/src/kernel.hpp reference_c7/src/c7d3_integrate.cpp Makefile
	@mkdir -p bin
	@$(FLAG_CHECK)
	$(REFERENCE_CMD)
clean:
	rm -f bin/c8d3_gmp bin/c8d3_decimal bin/c7d3_reference bin/point_checks_gmp bin/c8d3_gmp.buildinfo.json bin/c8d3_decimal.buildinfo.json

.PHONY: baseline test-optimization
baseline: bin/c8d3_baseline
bin/c8d3_baseline: baseline/src/kernel.hpp baseline/src/c8d3_integrate.cpp
	@mkdir -p bin
	@$(FLAG_CHECK)
	$(CXX) $(CPPFLAGS) $(OPTFLAGS) $(CXXFLAGS) $(STRICT) -DC8_USE_GMP baseline/src/c8d3_integrate.cpp $(LDFLAGS) -lquadmath -lgmp $(LDLIBS) -o $@
bin/test_positive_quad: tests/test_positive_quad.cpp src/positive_quad.hpp
	@mkdir -p bin
	@$(FLAG_CHECK)
	$(CXX) $(CPPFLAGS) $(OPTFLAGS) $(CXXFLAGS) $(STRICT) tests/test_positive_quad.cpp $(LDFLAGS) -lquadmath $(LDLIBS) -o $@
test-optimization: optimized baseline bin/test_positive_quad
	bin/test_positive_quad
	OPENBLAS_NUM_THREADS=1 $(PYTHON) -B tests/test_optimization.py
	OPENBLAS_NUM_THREADS=1 $(PYTHON) -B tests/test_hpc_dispatch.py
	OPENBLAS_NUM_THREADS=1 $(PYTHON) -B tests/test_streaming_assembly.py

.PHONY: optimized profile
optimized: bin/c8d3_optimized
bin/c8d3_optimized: src/kernel.hpp src/positive_quad.hpp src/c8d3_integrate.cpp Makefile tools/native_buildinfo.py
	@mkdir -p bin
	@$(FLAG_CHECK)
	$(CXX) $(CPPFLAGS) $(OPTFLAGS) $(CXXFLAGS) $(STRICT) -DC8_USE_GMP src/c8d3_integrate.cpp $(LDFLAGS) -lquadmath -lgmp $(LDLIBS) -o $@
	@$(PYTHON) -B tools/native_buildinfo.py write $@ '$(CXX)' '$(CPPFLAGS)' -- $(CXX) $(CPPFLAGS) $(OPTFLAGS) $(CXXFLAGS) $(STRICT) -DC8_USE_GMP src/c8d3_integrate.cpp $(LDFLAGS) -lquadmath -lgmp $(LDLIBS) -o $@
profile: bin/c8d3_profile
bin/c8d3_profile: baseline/src/kernel_profile.hpp baseline/src/profiling.hpp baseline/src/c8d3_profile.cpp
	@mkdir -p bin
	@$(FLAG_CHECK)
	$(CXX) $(CPPFLAGS) $(OPTFLAGS) $(CXXFLAGS) $(STRICT) -DC8_USE_GMP baseline/src/c8d3_profile.cpp $(LDFLAGS) -lquadmath -lgmp $(LDLIBS) -o $@
