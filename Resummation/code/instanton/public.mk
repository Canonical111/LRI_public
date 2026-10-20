# Public targets for Resummation/code/instanton: the critical bubble, the one-loop amplitude K_I of the d = 1 epsilon
# series and its benchmarks (phi^4 in d = 4 - eps, McKane's phi^6 formula in d = 3), with the independent re-derivation.
# The scripts and results.json ship verbatim from the production folder; public/ is added.
# Run from this folder:  make -f public.mk test | replay | clean
#
#   test     public/selftest_instanton.py: the zero-dimensional sign check and the d = 4 benchmark (ratio 1). Seconds.
#   replay   public/replay_instanton.py: reruns every script in a copy (results.json regenerated and compared; the two
#            benchmarks reproduce McKane's constants with ratio 1; his simplified Eq. (A10) is off by 64/pi), the
#            independent re-derivation, and recomputes \RSKI, \RSKIalt, \RSfracLow, \RSfracEight, \RSratioExcess and
#            A_eps(1,2,3). Reads the d = 1 chain record in ../resum_d1 and the 2d/3d ratio tables in ../resum_d23.
#            About 1 min on one core; Python >= 3.10, mpmath, numpy, scipy, sympy.

PY      ?= python3
WORK    ?= .work
export PYTHONDONTWRITEBYTECODE = 1
export OPENBLAS_NUM_THREADS = 1

.PHONY: help test replay clean
help:
	@sed -n '1,13p' public.mk

test:
	$(PY) public/selftest_instanton.py

replay:
	$(PY) public/replay_instanton.py --work $(WORK)

clean:
	rm -rf $(WORK)
