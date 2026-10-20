# Public targets for GFF/code/LRI_C6_1D_HPC: C6(1) of the 1D long-range Ising model from exact all-graph sums.
# Run from this folder:  make -f public.mk test | replay | smoke | rerun-lower | compare-rerun RERUN=<file> | clean
# The package's own Makefile (engine build) ships verbatim and is not used by test or replay.
# Inputs (relative paths): ../../results/C6_1 (final records), ../../data/C6_1 (levels/, runs/, analysis/),
# and, for the RR-002 C7 cross-check, C7_final.json of LRI_C7_HPC (searched at ../../results/C7_1/ and
# ../LRI_C7_HPC/results/2026-09_expanse_v2/; override with C7_FINAL=<path>; absent = SKIP rows, not FAIL).
# Outputs go to $(WORK) only; tables in $(WORK)/<target>_table.txt. Python 3.10+, mpmath, numpy, sympy.
#
# Runtimes (one core; measured on a Mac arm64, Python 3.10.11; memory < 1 GB):
#   test         about 10 s   the package's tests/test_tools.py (72 checks) + every hash binding between the
#                             shipped records, level files and run files (public/replay_c6.py test)
#   replay       about 40 s   test + bitwise regeneration of assembled.json, rounding.json, C6_final.json and the
#                             four stopping decisions, re-merge of all 62 levels from the run files, the 21 weight
#                             tables, RR-001 and RR-002 records, the RG-algebra check, and every quoted number
#   smoke        1-3 min      x86-64 Linux, g++ >= 11 with OpenMP: builds the engines and reruns the five-loop
#                             degree-12 levels; compares with the production levels (passed on symmetry AMD: 7 PASS, 36 s)
#   rerun-lower  about 30 s   RR-001 rerun of the L2-L4 amplitudes at degree 28 in long double and float64
#                             (x86-64 for the 80-bit long double; elsewhere the long-double half is SKIP)
#   compare-rerun  seconds    a production rerun's C6_N22.json (cluster/analyze_stage.sh) against C6_final.json

PY      ?= python3
WORK    ?= .work
RESULTS ?= ../../results/C6_1
DATA    ?= ../../data/C6_1
C7_FINAL ?=
THREADS ?= 0
RERUN   ?=

export PYTHONDONTWRITEBYTECODE = 1
REPLAY = $(PY) public/replay_c6.py --results $(RESULTS) --data $(DATA) --work $(WORK) $(if $(C7_FINAL),--c7-final $(C7_FINAL))

.PHONY: test replay smoke rerun-lower compare-rerun clean

test:
	$(PY) tests/test_tools.py
	$(REPLAY) test

replay:
	$(REPLAY) replay

smoke:
	$(REPLAY) --threads $(THREADS) smoke

rerun-lower:
	$(REPLAY) rerun-lower

compare-rerun:
	$(REPLAY) --rerun $(RERUN) compare-rerun

clean:
	rm -rf $(WORK)
