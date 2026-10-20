# Public targets of lri_psi_complete_update (added for the public edition; the package has no Makefile).
# Run from GFF/: make -C code/lri_psi_complete_update -f public.mk test|replay
# One core. Needs Python >= 3.10 with mpmath and sympy (public/requirements.txt).
# Every original script runs unchanged in a fresh copy under .work/pkg (they write their records in place);
# the package tree is never written. The PASS/FAIL table is printed and written to .work/VERIFY_<target>.md.
# Runtimes: one core of an Apple M1 Max, Python 3.10, mpmath 1.3.0 (also passed with mpmath 1.2.1, sympy 1.11).
#   test    ~2 s   exact SymPy certificate of the K proof and of all C0..C5 rewritings; 70-digit values of
#                  C2..C5(1), K, P4, P5; 130-digit complex bilinear test
#   replay  ~15 s  test + 110-digit endpoint-subtracted original master for K and 75-digit
#                  finite-parameter tests of the six-3F2 master and the bilinear identity

PY     ?= python3
WORK   ?= .work
QUOTED ?= ../../results/closed_forms_1/C5_1_quoted.json

.PHONY: test replay clean
test:
	$(PY) public/replay.py --mode test --work $(WORK) --quoted $(QUOTED)

replay:
	$(PY) public/replay.py --mode replay --work $(WORK) --quoted $(QUOTED)

clean:
	rm -rf $(WORK)
