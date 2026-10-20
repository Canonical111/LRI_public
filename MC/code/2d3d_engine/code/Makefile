CXX ?= g++
CXXFLAGS ?= -O3 -std=c++17 -Wall -Wextra -Wpedantic
.PHONY: all test clean
all: bin/lri_mc bin/lri_reference bin/lri_mt
bin/lri_mc: src/lri_mc.cpp src/alias.hpp src/xoshiro.hpp src/lattice.hpp
	mkdir -p bin
	$(CXX) $(CXXFLAGS) src/lri_mc.cpp -o $@
bin/lri_mt: src/lri_mc.cpp src/alias.hpp src/xoshiro.hpp src/lattice.hpp
	mkdir -p bin
	$(CXX) $(CXXFLAGS) -DLRI_MT src/lri_mc.cpp -o $@
bin/lri_reference: ../reference/lri_mc_v1.cpp
	mkdir -p bin
	$(CXX) $(CXXFLAGS) $< -o $@
test: all
	OPENBLAS_NUM_THREADS=1 python3 test_v2.py
	OPENBLAS_NUM_THREADS=1 python3 test_analysis_v2.py
clean:
	rm -f bin/lri_mc bin/lri_mt bin/lri_reference
