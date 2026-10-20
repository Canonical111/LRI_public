CXX ?= g++
CXXFLAGS ?= -O3 -std=c++17 -fopenmp
LDLIBS = -lgmpxx -lgmp
PROGRAMS = stage_fast check_apply apply_poly_stage convert_poly normalize_products build_low_basis test_poly
all: $(PROGRAMS)
stage_fast: stage_sparse.cpp word_core.hpp
	$(CXX) $(CXXFLAGS) $< -o $@ $(LDLIBS)
%: %.cpp word_core.hpp low_basis.hpp
	$(CXX) $(CXXFLAGS) $< -o $@ $(LDLIBS)
clean:
	rm -f $(PROGRAMS)
.PHONY: all clean
