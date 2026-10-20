CXX ?= g++
CXXFLAGS ?= -O3 -std=c++17 -Wall -Wextra -Wpedantic
# Optional on a homogeneous cluster only: make CXXFLAGS='-O3 -std=c++17 -march=native'
.PHONY: all test clean
all: bin/lri_mc
bin/lri_mc: src/lri_mc.cpp
	mkdir -p bin
	$(CXX) $(CXXFLAGS) $< -o $@
test: all
	python3 tests/test_runner.py
	OPENBLAS_NUM_THREADS=1 python3 tests/test_analysis.py
	OPENBLAS_NUM_THREADS=1 python3 tests/test_fit_v2.py
clean:
	rm -rf bin

# 1D-specialised engine (lri_1d_precision, 2026-09-18 delivery; src_1d/ = upstream code/src with the status/DONE record extended by N, L, engine)
bin/lri_mc_1d: src_1d/lri_mc.cpp src_1d/alias.hpp src_1d/xoshiro.hpp src_1d/lattice.hpp src_1d/line_sampler.hpp
	mkdir -p bin
	$(CXX) $(CXXFLAGS) -DLRI_ONE_DIM src_1d/lri_mc.cpp -o $@
all: bin/lri_mc_1d
