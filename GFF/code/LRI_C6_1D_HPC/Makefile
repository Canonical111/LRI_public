# Build the c6sum engines (Linux, GCC 11+). bin/c6sum: 8-lane double as two AVX2 halves; bin/c6sum_ld: long double.
GIT := $(shell cat GIT_SHA 2>/dev/null || git rev-parse --short HEAD 2>/dev/null || echo unknown)
CXX ?= g++
SRCSHA := $(shell (sha256sum src/c6sum.cpp 2>/dev/null || shasum -a 256 src/c6sum.cpp) | cut -c1-64)
# Portable target: x86-64-v3 (AVX2 + FMA) runs on symmetry's AMD (amdq) and Intel nodes with one executable.
ARCH ?= -march=x86-64-v3
CXXFLAGS := -O3 -std=c++17 $(ARCH) -fopenmp -DC6_GIT_SHA=\"$(GIT)\" -DC6_SRC_SHA=\"$(SRCSHA)\"

all: bin/c6sum bin/c6sum_ld bin/enumerate

bin/c6sum: src/c6sum.cpp
	mkdir -p bin && $(CXX) $(CXXFLAGS) $< -o $@

bin/c6sum_ld: src/c6sum.cpp
	mkdir -p bin && $(CXX) $(CXXFLAGS) -DC6_REFERENCE $< -o $@

bin/enumerate: reference/enumerate.cpp
	mkdir -p bin && $(CXX) -O3 -std=c++17 $< -o $@

test-local:
	python tests/test_tools.py

clean:
	rm -rf bin

.PHONY: all test-local clean
