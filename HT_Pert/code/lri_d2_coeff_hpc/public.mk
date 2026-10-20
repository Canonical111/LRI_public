# Public targets for lri_d2_coeff_hpc (d = 2 eighth-order coefficient solver). The package's own files are verbatim
# at f847d38. Usage: make -f public.mk <target>   (run from HT_Pert/code/lri_d2_coeff_hpc; relative paths only)
# The native backend needs x86-64 with 80-bit long double and a C++17 compiler with OpenMP (Linux; not arm64 macOS).
PYTHON ?= python3
THREADS ?= 4
ENV = OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 OMP_NUM_THREADS=$(THREADS) NUMBA_NUM_THREADS=$(THREADS) OMP_WAIT_POLICY=PASSIVE
WORK = .work
PROD = ../../data/HT_2d/prod
.PHONY: help verify-manifest test smoke replay fetch-data clean

help:
	@echo "verify-manifest  the three MANIFEST.sha256 lists (scrubbed files listed in public/SCRUBBED.txt: presence only)"
	@echo "test             verify-manifest + the package's suite (tests/run_all.py: native/JIT warmup + 61 pytest tests) on a scratch copy (~2 min)"
	@echo "smoke            rerun L = 6 (consistent and raw, eighth order) and compare with the shipped records (~1 min)"
	@echo "replay           integrity of the 41 production records and the cited tables (public/replay_prod.py, seconds)"
	@echo "fetch-data       nothing is hosted for this package"

verify-manifest:
	$(PYTHON) public/verify_manifest.py

# run_all.py writes results/validation.json, so the suite runs on a copy of the tree.
test: verify-manifest
	rm -rf $(WORK)/tree && mkdir -p $(WORK)/tree
	rsync -a --exclude .work --exclude public ./ $(WORK)/tree/
	cd $(WORK)/tree && $(ENV) NUMBA_CACHE_DIR=$(CURDIR)/$(WORK)/numba LRI_COEFF_NATIVE_CACHE=$(CURDIR)/$(WORK)/native \
	    $(PYTHON) tests/run_all.py

smoke:
	rm -rf $(WORK)/smoke && mkdir -p $(WORK)/smoke
	for s in consistent raw; do \
	  $(ENV) PYTHONPATH=src NUMBA_CACHE_DIR=$(CURDIR)/$(WORK)/numba LRI_COEFF_NATIVE_CACHE=$(CURDIR)/$(WORK)/native \
	    $(PYTHON) -m lri_coeff run --cutoff 6 --degree 8 --scheme $$s --threads $(THREADS) --memory-gib 2 \
	    --output $(WORK)/smoke/$${s}_L6.json || exit 1; done
	$(PYTHON) public/smoke_check.py $(WORK)/smoke/consistent_L6.json $(PROD)/check_small_symmetry/d8/consistent_L6.json
	$(PYTHON) public/smoke_check.py $(WORK)/smoke/raw_L6.json $(PROD)/check_small_symmetry/d8/raw_L6.json

replay:
	$(PYTHON) public/replay_prod.py

fetch-data:
	@echo "Nothing to fetch: the production records (data/HT_2d/prod) are in git."

clean:
	rm -rf $(WORK)
