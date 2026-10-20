# Public targets for HT_Pert/code/lri_1d_c4_exact: exact finite-cutoff C4(Λ) of the d = 1 frozen-cutoff HT by exact
# sums over intermediate-state patterns (production Λmax = 2000 on symmetry). Shipped at its production code; public/ is added.
# Run from this folder:  make -f public.mk test | replay | replay-quick | smoke | clean
#
#   test          validate/test_kernels.py (fast tests: series, zero-mode paths, densities, shells), validate/v1_exact.py
#                 (A1, A2: exact rationals at small cutoffs), validate/v3_brute.py --cut4max 48 (A3: brute-force RS).
#                 About 10 s, numpy, scipy, numba, mpmath.
#   replay        public/replay_c4.py: records and code binding, quoted values, overlap, blind check rerun, frozen
#                 intercepts, refit to Λ = 2000 (rows x4.*). A few minutes (mpmath refit).
#   replay-quick  the same without the refit (seconds).
#   smoke         public/smoke_c4.py: production path at Λmax = 40, compared with the shipped L200 result to 1e-12.
PY    ?= python3
WORK  ?= .work
DATA  ?= ../../data/HT_1d
export PYTHONDONTWRITEBYTECODE = 1
export NUMBA_CACHE_DIR ?= $(WORK)/numba_cache

.PHONY: test replay replay-quick smoke clean
test:
	$(PY) -m pytest -q -p no:cacheprovider validate/test_kernels.py
	$(PY) validate/v1_exact.py
	$(PY) validate/v3_brute.py --cut4max 48

replay:
	$(PY) public/replay_c4.py --data $(DATA)

replay-quick:
	$(PY) public/replay_c4.py --data $(DATA) --quick

smoke:
	$(PY) public/smoke_c4.py --data $(DATA) --work $(WORK)

clean:
	rm -rf $(WORK)
