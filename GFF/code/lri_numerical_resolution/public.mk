# Public targets of lri_numerical_resolution (added for the public edition; the package has no Makefile).
# Run from GFF/: make -C code/lri_numerical_resolution -f public.mk test|replay
# One core, no compiler needed. Needs Python >= 3.10 with mpmath, sympy, numpy (public/requirements.txt).
# Every original script runs unchanged in a fresh copy under .work/pkg (they write their records in place);
# the package tree is never written. The PASS/FAIL table is printed and written to .work/VERIFY_<target>.md.
# Runtimes: one core of an Apple M1 Max, Python 3.10, mpmath 1.3.0 (also passed with mpmath 1.2.1, sympy 1.11).
#   test    ~1 s   exact certificate algebra, rational propagation identity, saved-data reassembly of the
#                  raw graph amplitudes, graph-control table and README values, checksum manifest
#   replay  ~25 s  test + fresh 80-digit reference (K, L, P4, P5, closed-form C5(1)), lower-loop controls,
#                  graph regeneration against the executed-input hashes, sector/group audit,
#                  unlabelled class audit (129 = 92 + 6 + 3 + 28), and the external lattice comparison of
#                  Section 14 of the note (public/lattice_comparison.py, seconds)
# The production rerun of the raw graph integrals (hours, AVX-512 node) is documented in public/README.md.

PY     ?= python3
WORK   ?= .work
QUOTED ?= ../../results/closed_forms_1/C5_1_quoted.json

.PHONY: test replay clean
test:
	$(PY) public/replay.py --mode test --work $(WORK) --quoted $(QUOTED)

replay:
	$(PY) public/replay.py --mode replay --work $(WORK) --quoted $(QUOTED)
	$(PY) -I public/lattice_comparison.py

clean:
	rm -rf $(WORK)
