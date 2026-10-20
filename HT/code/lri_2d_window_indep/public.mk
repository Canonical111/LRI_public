# Public targets for lri_2d_window_indep (independent d = 2 finite-coupling solver). The package files are verbatim.
# Usage: make -f public.mk <target>   (run from HT/code/lri_2d_window_indep; relative paths only)
PYTHON ?= python3
ENV = OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 OMP_NUM_THREADS=1
WORK = .work
RECORDS = ../../data/HT_2d/prod1/chains
OUT = ../../results/HT_2d/independent_check/out_sym
.PHONY: help test smoke replay fetch-data clean

help:
	@echo "test        self-tests of indep_ht2d.py (vertices by brute force, two-point weights, projector, Lanczos; ~1 min)"
	@echo "smoke       recompute two shipped comparisons (Delta_sigma=0.25 and 0.125, N=8, K=24) and compare (~2 min)"
	@echo "replay      recompute the agreement figures from the shipped outputs (public/replay_indep.py, seconds)"
	@echo "fetch-data  nothing is hosted for this package"

test:
	$(ENV) $(PYTHON) test_indep.py

# run_check.py skips tasks whose output exists, so the smoke run writes into its own folder.
smoke:
	rm -rf $(WORK)/smoke && mkdir -p $(WORK)/smoke
	$(ENV) $(PYTHON) run_check.py $(RECORDS) $(WORK)/smoke 1 --only fixed_x0.250_L8_K24-24_M400_J
	$(ENV) $(PYTHON) run_check.py $(RECORDS) $(WORK)/smoke 1 --only fixed_x0.125_L8_K24-24_M400_J
	$(PYTHON) public/smoke_compare.py $(WORK)/smoke $(OUT) fixed_x0.250_L8_K24-24_M400_J fixed_x0.125_L8_K24-24_M400_J

replay:
	$(PYTHON) public/replay_indep.py

fetch-data:
	@echo "Nothing to fetch: the outputs (HT/results/HT_2d/independent_check) and the records they bind to are in git."

clean:
	rm -rf $(WORK)
