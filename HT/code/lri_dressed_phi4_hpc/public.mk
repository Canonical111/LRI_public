# Public targets for HT/code/lri_dressed_phi4_hpc: the d = 1 dressed zero-mode phi^4 HT solver at commit 33998bb (the
# code of the dens_v1 production; HT note, sections on the d = 1 model, zero-mode basis and window correction).
# Run from this folder:  make -f public.mk test | replay | smoke | clean
# The package's own files (README.md, INTEGRATION.md, docs/, scripts/, cluster/symmetry/) ship verbatim.
#
#   test     the package's staged release validation, scripts/validate_release.py: pytest (104 tests), saved-seed
#            regression, --window none bit-equality with the frozen baseline reference/production_e637dfd, a
#            calibration smoke run, window baseline equality and the density-basis validation. About 2-3 min on one
#            node with THREADS=4 (receipt 570965 took 128 s on symmetry), < 2 GB. Python 3.11 with numpy 2.3.5,
#            scipy 1.17.0, numba 0.65.1, pytest (requirements-tested.txt). The equality stages compare two runs in the
#            same environment, so they are bitwise on any CPU vendor.
#   replay   public/replay_solver.py: binds the shipped tree to the records (source and release fingerprints) and runs
#            the package's own validator on all 881 shipped results. About 1 min, one core. The quoted numbers are
#            replayed by ../lri_dressed_phi4_hpc_analysis.
#   smoke    public/smoke.py: reruns the dens_v1 item N = 12, Ds = 0.2 and compares with its record (tol 1e-8).
#            On the production runtime (Python 3.11.4, numpy 2.3.5, scipy 1.17.0, numba 0.65.1) it uses the shipped
#            basis artifact (about 1 min). On any other runtime the package refuses that artifact by design, so smoke
#            first retrains the Ds = 0.2 basis with the production settings (train-basis; about 3-6 min, THREADS=4).

PY      ?= python3
WORK    ?= .work
DATA    ?= ../../data/HT_1d
THREADS ?= 4
export PYTHONDONTWRITEBYTECODE = 1
export OPENBLAS_NUM_THREADS = 1
export MKL_NUM_THREADS = 1
export OMP_NUM_THREADS = 1
export NUMBA_CACHE_DIR = $(abspath $(WORK))/numba_cache

.PHONY: test replay smoke clean
test:
	@mkdir -p $(WORK)
	NUMBA_NUM_THREADS=$(THREADS) PYTHONPATH=src $(PY) scripts/validate_release.py --threads $(THREADS) \
	  --output $(WORK)/validation/receipt.json --baseline reference/production_e637dfd

replay:
	DATA=$(DATA) WORK=$(WORK) $(PY) public/replay_solver.py

smoke:
	DATA=$(DATA) WORK=$(WORK) THREADS=$(THREADS) $(PY) public/smoke.py

clean:
	rm -rf $(WORK)
