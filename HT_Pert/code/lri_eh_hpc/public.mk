# Public targets for HT_Pert/code/lri_eh_hpc: lri_eh 0.2.0 (2026-10-02), the isolated g(eps)^2 D(eps) vacuum-window
# add-on of the d = 1 frozen-cutoff HT. Not a git repository: shipped whole and verbatim (MANIFEST_SHA256.json, source
# fingerprint 2e2e8ca8..., supplied receipt 648fa9fb...); public.mk and public/ are added. Its exact.py gives K and the
# exact Delta C4(g^2 D); its solver made the g^2 D tables d5_all.json, d7_all.json that ship in
# ../lri_hpc_Hamitonian/analysis/eh_review/physics-impact (cross-folder input of replay, smoke and replay-full).
# Run from this folder:  make -f public.mk test | replay | smoke | replay-full | fetch-data | clean
#
#   test         public/run_tests_eh.py: manifest (102 files, public/SCRUBBED.txt honoured), the verbatim
#                scripts/verify_package.py, and the package's scripts/validate_release.py --threads 4 on a copy in
#                $(WORK)/pkg (pytest, 32 tests, then a gated degree-7 smoke at cutoff 20 and a sealed receipt).
#                Needs >= 4 CPUs. About 35 s on symmetry (Xeon Gold 6148, 4 threads), < 1 GB.
#   replay       public/replay_eh.py: rows a1.eh.* (results_map.md): integrity, K, exact Delta C4 vs the shipped
#                g^2 D tables, supplier benchmark. Standard library + mpmath, 3 s.
#   smoke        public/g2d_rerun.py --smoke: g^2 D tables regenerated at Lambda 4..20 (degree 5) and 4..12
#                (degree 7) with gen_deltas.py, compared with the shipped tables. About 16 s with JIT.
#   replay-full  public/g2d_rerun.py --full: the whole tables, degree 5 at Lambda 4..118 and degree 7 at 4..90.
#                Solver memory guard MEMLIM = 64 GiB (degree 7 above Lambda ~ 78 needs more than 12).
#                About 700 s on 8 threads (degree 5 24 s, degree 7 673 s on symmetry).
#   fetch-data   nothing is hosted: every record of this package is in git.
PY      ?= python3
WORK    ?= .work
DATA    ?= ../../data/HT_1d
HPCHAM  ?= ../lri_hpc_Hamitonian
THREADS ?= 4
MEMLIM  ?= 64
export PYTHONDONTWRITEBYTECODE = 1
export OPENBLAS_NUM_THREADS = 1
export MKL_NUM_THREADS = 1
export OMP_NUM_THREADS = 1
export NUMBA_CACHE_DIR ?= $(abspath $(WORK))/numba_cache

.PHONY: help test replay smoke replay-full fetch-data clean
help:
	@sed -n '1,19p' public.mk

test:
	$(PY) public/run_tests_eh.py --work $(WORK) --threads $(THREADS)

replay:
	$(PY) public/replay_eh.py --hpcham $(HPCHAM) --work $(WORK)

smoke:
	$(PY) public/g2d_rerun.py --smoke --hpcham $(HPCHAM) --work $(WORK) --threads $(THREADS)

replay-full:
	$(PY) public/g2d_rerun.py --full --hpcham $(HPCHAM) --work $(WORK) --threads $(THREADS) --memlim $(MEMLIM)

fetch-data:
	@echo "lri_eh_hpc: nothing hosted yet, and nothing needed: the package and its g^2 D tables are in git"

clean:
	rm -rf $(WORK)
