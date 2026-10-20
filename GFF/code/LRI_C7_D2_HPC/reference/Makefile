CXX ?= g++
CXXFLAGS = -O3 -std=c++17 -fopenmp -ffp-contract=off -fno-fast-math
LDLIBS = -lquadmath
P = power_mass/code
all: $(P)/integrate $(P)/build_power_mass $(P)/check_edge_forests $(P)/check_fallback
$(P)/integrate: $(P)/integrate.cpp $(P)/kernel.hpp
	$(CXX) $(CXXFLAGS) $< -o $@ $(LDLIBS)
$(P)/build_power_mass: $(P)/build_power_mass.cpp
	$(CXX) $(CXXFLAGS) $< -o $@
$(P)/check_edge_forests: $(P)/check_edge_forests.cpp
	$(CXX) $(CXXFLAGS) $< -o $@
$(P)/check_fallback: $(P)/check_fallback.cpp $(P)/kernel.hpp
	$(CXX) $(CXXFLAGS) $< -o $@ $(LDLIBS)
checks: all
	python3 code/recheck.py
note:
	cd notes && pdflatex -interaction=nonstopmode -halt-on-error C7_d2_complete.tex && pdflatex -interaction=nonstopmode -halt-on-error C7_d2_complete.tex
clean:
	rm -f $(P)/integrate $(P)/build_power_mass $(P)/check_edge_forests $(P)/check_fallback
.PHONY: all checks note clean
