# C8(2) d=2 payload generator (PLAN.md component A). `make -C gen` builds into ../bin/gen, which git and
# tools/verify_delivery.py ignore (bin/). Generation runs on x86-64 Linux only (long double printing).
#
# The required flags are those of the frozen C7(2) kernels (reference/LRI_C7_d2_progress/verification/build.log:
# g++ -O3 -std=c++17 -fopenmp -fno-fast-math -ffp-contract=off) and cannot be dropped from the command line.
# Each binary gets <name>.build.txt with the exact compile command and the compiler version.
CXX ?= g++
OPTFLAGS ?= -O3
CXXFLAGS ?=
override GEN_REQUIRED = -std=c++17 -fopenmp -fno-fast-math -ffp-contract=off
BIN ?= ../bin/gen
PROGS = build_free build_power check_edge_forests test_keys
override GEN_CMD = $(strip $(CXX) $(OPTFLAGS) $(CXXFLAGS) $(GEN_REQUIRED))

.DELETE_ON_ERROR:
.PHONY: all clean
all: $(addprefix $(BIN)/,$(PROGS))

$(BIN)/%: %.cpp c8gen.hpp Makefile
	@mkdir -p $(BIN)
	$(GEN_CMD) $< -o $@
	@{ echo "command: $(GEN_CMD) $< -o $@"; echo "compiler: $$($(CXX) --version | head -1)"; } > $@.build.txt

clean:
	rm -f $(addprefix $(BIN)/,$(PROGS)) $(addsuffix .build.txt,$(addprefix $(BIN)/,$(PROGS)))
