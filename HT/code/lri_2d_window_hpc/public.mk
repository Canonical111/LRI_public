# Public targets for lri_2d_window_hpc (d = 2 finite-coupling HT). The package's own files are verbatim at 889a968.
# Usage: make -f public.mk <target>   (run from HT/code/lri_2d_window_hpc; relative paths only)
PYTHON ?= python3
THREADS ?= 4
ENV = OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 OMP_NUM_THREADS=1 BLIS_NUM_THREADS=1 NUMBA_NUM_THREADS=$(THREADS)
WORK = .work
DATA = ../../data/HT_2d/prod1
.PHONY: help test verify-manifest smoke smoke-point smoke-valley replay fetch-data clean

help:
	@echo "test            manifest check + the package's pytest suite on a scratch copy (~5 min, $(THREADS) Numba threads)"
	@echo "smoke           rerun the prod1 point Delta_sigma=0.25, N=8 and an N=8 valley scan point (~2 min)"
	@echo "replay          recompute every quoted d=2 number from the shipped records (public/replay_d2.py, ~1 min)"
	@echo "fetch-data      nothing is hosted for this package"

verify-manifest:
	$(PYTHON) public/verify_manifest.py

# The suite rewrites validation/independent_metrics.json, so it runs on a copy of the tree.
test: verify-manifest
	rm -rf $(WORK)/tree && mkdir -p $(WORK)/tree
	rsync -a --exclude .work --exclude .public_out --exclude public ./ $(WORK)/tree/
	cd $(WORK)/tree && $(ENV) NUMBA_CACHE_DIR=$(CURDIR)/$(WORK)/numba $(PYTHON) -m pytest -q -p no:cacheprovider \
	    tests/test_port.py tests/test_optimized.py tests/test_hpc.py tests/test_expanse.py

smoke: smoke-point smoke-valley

smoke-point:
	rm -rf $(WORK)/smoke && mkdir -p $(WORK)/smoke
	$(ENV) NUMBA_CACHE_DIR=$(CURDIR)/$(WORK)/numba $(PYTHON) code/hpc_run.py --L 8 --x 0.25 --nz 16 --osc 192 \
	    --backend tensor --window vacuum --window-mode consistent \
	    --basis reference/results/teacher_L6_x0.250.json --seed reference/results/window_L8_z16_x0.250.json \
	    --diagnostics all --ncv 40 --eig-tol 1e-12 --residual-tol 1e-8 --tuning-tol 3e-11 --maxiter 50 \
	    --threads $(THREADS) --memory-limit-gib 8 --output $(WORK)/smoke/L8_z16.json
	$(PYTHON) public/smoke_check.py $(WORK)/smoke/L8_z16.json $(DATA)/chains/x0.250/L8_z16.json

# N = 8 valley point at Delta_sigma = 0.126: theta1 is moved off the production root; the secant on f2 = 0 must find
# the root again, with f1 = 0 there (the N = 24 scan ran the same script; public/scan_valley.py is verbatim).
smoke-valley:
	mkdir -p $(WORK)/smoke
	$(ENV) NUMBA_CACHE_DIR=$(CURDIR)/$(WORK)/numba $(PYTHON) -E -s public/scan_valley.py code \
	    reference/results/teacher_L6_x0.126.json 0.126 8 $(THREADS) $(WORK)/smoke/valley_L8.json \
	    $$($(PYTHON) public/smoke_check.py --valley-seed $(DATA)/chains/x0.126/L8_z16.json)
	$(PYTHON) public/smoke_check.py --valley $(WORK)/smoke/valley_L8.json $(DATA)/chains/x0.126/L8_z16.json

replay:
	$(PYTHON) public/replay_d2.py

fetch-data:
	@echo "Nothing to fetch: the prod1 records (HT/data/HT_2d/prod1) and all results are in git."

clean:
	rm -rf $(WORK) .public_out
