# Public targets for SRI/code/integ_d1: C^SR_8 from the integrable point (s = 1), in the magnetization scheme, from
# Bethe-ansatz data and kink clusters continued in v; no nine-kink integral, no input shared with dual_d1 or indep_d1.
# The project files (code/, results/) ship verbatim at commit 8bd5a22 (public/SNAPSHOT.sha256); public/ is added.
# Run from this folder:
#   make -f public.mk test | replay | replay-full | fetch-data | clean
#
#   test        public/selftest_integ.py: the snapshot, the git stand-in table, the record hashes; the engine and checker
#               built from source (production build ids reproduced), test_cluster.py, test_gates.py, test_two_bubble.py;
#               sectors of four production chunks rerun and compared with the shipped outputs (about 4 min on 8 cores).
#   replay      public/replay_integ.py: the verbatim gates in a work copy (git stand-in on PATH): every record from M2
#               to C8 rebuilt from the shipped engine outputs and compared byte for byte; the comparison stage; every
#               number of the note's App. I; \SRCeightMag against ../../results/quoted_numbers.json (about a minute,
#               one core).
#   replay-full prints the documented production rerun (about 2.7e4 core-hours on symmetry; public/REPLAY_FULL.md).
#   fetch-data  nothing is hosted elsewhere: every input of test and replay ships here.
# Python >= 3.10 with mpmath, sympy, numpy (requirements_integ_d1.txt); test also needs g++ with OpenMP (x86-64-v3) and bash.

PY      ?= python3
WORK    ?= .work
THREADS ?=
export PYTHONDONTWRITEBYTECODE = 1
export OPENBLAS_NUM_THREADS = 1

.PHONY: help test replay replay-full fetch-data clean
help:
	@sed -n '1,20p' public.mk

test:
	$(PY) public/selftest_integ.py --work $(WORK)/test $(if $(THREADS),--threads $(THREADS))

replay:
	$(PY) public/replay_integ.py --work $(WORK)/replay

replay-full:
	@sed -n '/^## Production rerun/,/^## End of production rerun/p' public/REPLAY_FULL.md

fetch-data:
	@sed -n '/^## Hosted data/,/^## End of hosted data/p' public/REPLAY_FULL.md

clean:
	rm -rf $(WORK)
