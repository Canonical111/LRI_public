# Public targets for HT_Pert/code/lri_1d_c5_exact: exact finite-cutoff C5(Λ) of the d = 1 frozen-cutoff HT (production
# Λmax = 500 on symmetry), the blind-fit records and the analysis fits. Shipped at its production code (later commits add
# only fit records and analysis scripts); public/ is added. Needs ../lri_1d_c4_exact (regression test) and
# ../../data/HT_1d/exact_c4 (reference of the A6e gate and of the constrained fit).
# Run from this folder:  make -f public.mk test | replay | replay-quick | smoke | fetch-data | clean
#
#   test          public/run_tests_c5.py = validate/test_core.py (run-time copy pointing at ../lri_1d_c4_exact)
#                 and validate/test_kernel5.py (fast tests: jets vs mpmath, densities vs the dense
#                 reference, five-vertex kernel, orders 2-4 against lri_1d_c4_exact), validate/v1_exact.py (A1, A2),
#                 validate/v3_brute.py --cut4max 32 (A3), validate/v7_closed.py --Lmax 400 (window closed forms).
#                 About 2 min on 4 cores.
#   replay        public/replay_c5.py: records and code binding, quoted values, overlaps, blind-check and intercept
#                 reruns, refits, fixed-intercept tail fits, constrained fit (rows x5.*). About 5 min on a 64-core node.
#   replay-quick  the same without the mpmath refits (seconds).
#   smoke         public/smoke_c5.py: production path at Λmax = 24 (16 workers, about 10 min), compared with the shipped
#                 L80 result to 1e-11.
#   fetch-data    public/fetch_hosted.py: downloads the raw per-fit results of the cited blind re-implementation
#                 (results_574286/574292/574295.jsonl, 71 MB, one archive from the Zenodo data record, unpacked into
#                 fits/explore/constrained_L500/xchk/cfit_blind/, where final_table.py reads them), checks size and
#                 sha256 of the archive and of every member, and skips files already in place. Not needed by test or
#                 replay. DATA_URL = the record's file URL (Zenodo record 23466766, DOI 10.5281/zenodo.23466766).
PY    ?= python3
WORK  ?= .work
DATA  ?= ../../data/HT_1d
DATA_URL ?= https://zenodo.org/records/23466766/files
PROCS ?= $(shell $(PY) -c 'import os; print(os.cpu_count())')
export PYTHONDONTWRITEBYTECODE = 1
export NUMBA_CACHE_DIR ?= $(WORK)/numba_cache

.PHONY: test replay replay-quick smoke fetch-data clean
test:
	$(PY) public/run_tests_c5.py --work $(WORK)
	$(PY) validate/v1_exact.py
	$(PY) validate/v3_brute.py --cut4max 32
	$(PY) validate/v7_closed.py --Lmax 400

replay:
	$(PY) public/replay_c5.py --data $(DATA) --work $(WORK) --procs $(PROCS)

replay-quick:
	$(PY) public/replay_c5.py --data $(DATA) --work $(WORK) --quick

smoke:
	$(PY) public/smoke_c5.py --data $(DATA) --work $(WORK)

fetch-data:
	$(PY) public/fetch_hosted.py --url $(DATA_URL) --cache $(WORK)/fetch

clean:
	rm -rf $(WORK)
