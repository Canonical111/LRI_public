# Public targets for HT_Pert/code/lri_c8_hpc: eighth-order coefficients C0..C8 of the d = 1 frozen-cutoff HT, raw and
# isolated g^2D (vacuum_only), even Lambda = 52..92 (symmetry defq, validation job 569659, production array 569698,
# campaign 654fb90d19a573c1). Shipped verbatim at its production commit 529f208 (source digest dd811aca...); public.mk
# and public/ are added. Records: ../../data/HT_1d/c8. The data.json rebuild also reads the thermal records shipped in
# ../lri_hpc_Hamitonian/analysis/extended (row c8.datajson is SKIP without them).
# Run from this folder:  make -f public.mk test | replay | smoke | replay-full | fetch-data | clean
# Costs below: default THREADS=4, one Xeon Gold 6148 node of symmetry defq (job 575032).
#   test         public/verify_manifest_public.py (MANIFEST_SHA256.json, 164 files, public/SCRUBBED.txt honoured), then
#                public/run_tests_c8.py on a copy in $(WORK)/tree: pytest tests/ (74 tests) with a fresh Numba cache and
#                the Numba threading layer pinned (as in production; see the script), and the 38-point saved-grid
#                replay (scripts/regression_saved_grid.py --compare). 6 min (Python 3.12.9, numpy 2.3.5, numba 0.68.0),
#                4 min (production stack), 1.3 GiB.
#   replay       public/replay_c8.py: every quoted number of the package from the shipped records (rows c8.*;
#                results_map.md), table also in $(WORK)/replay_lri_c8_hpc.txt. Standard library only; about 1 s.
#   smoke        public/smoke_c8.py: production item Lambda = 52, raw and vacuum_only, rerun and compared with the
#                shipped outputs (bitwise on the production stack, else 1e-7 + 2e-11 |ref|; bitwise on both tested
#                stacks). About 1.2 min, 1.7 GiB.
#   replay-full  public/replay_full_c8.py: `python -m lri_c8 export` of the shipped outputs (byte-identical exports
#                and sidecars) and scripts/compare_original.py at Lambda = 60 (rows c8.validation, c8.original
#                recomputed). 13 min, 9 GiB.
#   fetch-data   nothing is hosted: every record of this package is in git (data/HT_1d/c8, 92 files, 1.2 MB).
# A production rerun needs a working copy with a rehashed manifest: public/rehash_manifest.py (REPRODUCE, section 5).
PY      ?= python3
WORK    ?= .work
DATA    ?= ../../data/HT_1d
THERMAL ?= ../lri_hpc_Hamitonian/analysis/extended
THREADS ?= 4
export PYTHONDONTWRITEBYTECODE = 1
export OPENBLAS_NUM_THREADS = 1
export MKL_NUM_THREADS = 1
export OMP_NUM_THREADS = 1
export NUMBA_CACHE_DIR ?= $(abspath $(WORK))/numba_cache

.PHONY: help test replay smoke replay-full fetch-data clean
help:
	@sed -n '1,22p' public.mk

test:
	$(PY) public/verify_manifest_public.py
	$(PY) public/run_tests_c8.py --work $(WORK) --threads $(THREADS)

replay:
	$(PY) public/replay_c8.py --data $(DATA) --thermal $(THERMAL) --work $(WORK)

smoke:
	$(PY) public/smoke_c8.py --data $(DATA) --work $(WORK) --threads $(THREADS)

replay-full:
	$(PY) public/replay_full_c8.py --data $(DATA) --work $(WORK) --threads $(THREADS)

fetch-data:
	@echo "lri_c8_hpc: nothing hosted yet, and nothing needed: all records are in git under $(DATA)/c8"

clean:
	rm -rf $(WORK)
