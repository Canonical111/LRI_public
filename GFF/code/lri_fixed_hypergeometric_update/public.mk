# Public targets of lri_fixed_hypergeometric_update (added for the public edition; the package has no Makefile).
# Run from GFF/: make -C code/lri_fixed_hypergeometric_update -f public.mk test|replay
# One core. Needs Python >= 3.10 with mpmath and sympy (public/requirements.txt).
# The original verifier runs unchanged in a fresh copy under .work/pkg; the package tree is never written.
# The PASS/FAIL table is printed and written to .work/VERIFY_<target>.md.
# Runtimes: one core of an Apple M1 Max, Python 3.10, mpmath 1.3.0 (also passed with mpmath 1.2.1, sympy 1.11).
#   test    ~3 s   checksum manifest; exact Barnes-kernel identity (note Sec. 10); the d = 1 closed forms of
#                  note Sec. 1.1 at 70 digits (C2..C5, K, L, P4, P5); original verifier at 40 digits
#   replay  ~6 s   test + original verifier at the recorded 100 digits with its 125-digit control

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
