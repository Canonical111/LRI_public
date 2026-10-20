# Public targets of lri_3d_window_hpc (d = 3 finite-coupling Hamiltonian truncation with the vacuum window).
# Run from this folder: make -f public.mk <target>   (HT/Makefile runs make -C code/lri_3d_window_hpc -f public.mk <target>).
# The package's own files ship unchanged at git ref b330ee7; everything public-specific is in public/.
#
# Python >= 3.10 with numpy, scipy, numba, threadpoolctl, sympy, pytest (requirements.txt; production used
# Python 3.11.9, numpy 2.3.5, scipy 1.17.0, numba 0.65.1). Any OS for replay; test and smoke need numba.
#
#   target      what                                                          measured runtime and node
#   test        MANIFEST.sha256 check, then pytest (158 tests) and the five   3.5 min (symmetry, AMD EPYC 8534P) and 4.3 min
#               validators in a scratch copy (public/run_tests.py)            (symmetry, Intel Xeon 6148), 8 cores, 4 numba
#                                                                             threads, 32 GB (jobs 574386, 574390, 2026-10-13)
#   replay      every quoted d = 3 number from the shipped records in         ~5 s, 1 core, any OS (numpy + scipy);
#               ../../data/HT_3d (public/replay_ht3d.py); PASS/FAIL table     20/20 on symmetry Intel 6148 and AMD 8534P
#                                                                             (jobs 574437, 574420); 21/21 with
#                                                                             row NUM3 (added 2026-10-16)
#   smoke       re-solve L = 8, 10 at x = 0.7 and 0.518149 from the shipped   17-23 s, 4 numba threads (symmetry Intel 6148,
#                                                                             job 574437; AMD 8534P, job 574420): max diff
#                                                                             1.5e-12 on both
#               continuation inputs; Delta_E, r, g must match the records
#               to 1e-9 (public/smoke_points.py)
#   fetch-data  nothing is hosted: prints how the L20 static cache is rebuilt  instant
#   clean       remove .work/
PY      ?= python3
WORK    ?= .work
DATA    ?= ../../data/HT_3d
RESULTS ?= ../../results/HT_3d
# the HT_Pert record with C4(L=20) for the C4-RATIO check (SKIP if absent)
PERT_SUMMARY ?= ../../../HT_Pert/results/HT_3d/SUMMARY.md

.PHONY: help test replay smoke fetch-data clean

help:        ## list the targets
	@grep -E '^[a-z-]+:.*##' public.mk | sed 's/:.*##/:/'

test:        ## manifest check + pytest + validators (the Expanse receipt without its release-tarball stage)
	$(PY) -B public/run_tests.py

replay:      ## recompute every quoted d = 3 number from the shipped records; PASS/FAIL table in .work/replay/
	$(PY) -B public/replay_ht3d.py --campaigns $(DATA)/campaigns --manifest $(DATA)/MANIFEST.sha256 \
	  --expected-table $(RESULTS)/finite_L_table.csv --out $(WORK)/replay --pert-summary $(PERT_SUMMARY)

smoke:       ## re-solve four low-cutoff production points and compare with their records
	$(PY) -B public/smoke_points.py --campaigns $(DATA)/campaigns

fetch-data:  ## nothing to fetch; see DATA.md for the static cache of the L20 runs
	@echo "fetch-data: every record the replay reads is in git ($(DATA)). The L20 static cache (graph, scalar projector,"
	@echo "x-dependent vertices) is not hosted: a production rerun rebuilds it (scripts/probe_large_setup.py --cache-dir,"
	@echo "run by cluster/expanse/setup_probe.sbatch: 9.0 h and 92 GiB peak for spin 0 on one 192G node); see"
	@echo "public/REPRODUCE.md and ../../data/HT_3d/DATA.md."

clean:       ## remove .work/
	rm -rf $(WORK)
