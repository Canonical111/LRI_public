CXX ?= g++
CXXFLAGS ?= -O3 -std=c++17 -fopenmp -fno-fast-math -ffp-contract=off
.PHONY: all test reproduce clean
all: code/c7d2_integrate code/build_schwinger code/check_fallback
code/c7d2_integrate: code/c7d2_integrate.cpp code/kernel.hpp
	$(CXX) $(CXXFLAGS) $< -lquadmath -o $@
code/build_schwinger: code/build_schwinger.cpp
	$(CXX) $(CXXFLAGS) $< -o $@
code/check_fallback: code/check_fallback.cpp code/kernel.hpp
	$(CXX) $(CXXFLAGS) $< -lquadmath -o $@
test:
	python3 code/check_assembly.py
	python3 code/validate_kernels.py
reproduce:
	python3 code/reproduce.py
clean:
	rm -f code/c7d2_integrate code/build_schwinger code/check_fallback
