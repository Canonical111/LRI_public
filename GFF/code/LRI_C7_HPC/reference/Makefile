CXX ?= g++
CXXFLAGS ?= -O3 -std=c++17 -fopenmp
LDLIBS ?= -lquadmath
PROGRAMS = enumerate_classes build_coordinate_forests forest_audit coordinate_integrate coordinate_tree_qmc coordinate_tree_integrate_safe coordinate_tree_integrate_allocated check_tree_points
.PHONY: all reproduce clean
all: $(addprefix code/,$(PROGRAMS))
code/%: code/%.cpp code/tree_common.hpp code/coordinate_point_common.hpp code/coordinate_integrate.cpp
	$(CXX) $(CXXFLAGS) $< -o $@ $(LDLIBS)
reproduce:
	OPENBLAS_NUM_THREADS=1 python code/reproduce.py
clean:
	rm -f $(addprefix code/,$(PROGRAMS))
