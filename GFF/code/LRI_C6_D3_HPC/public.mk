# Public targets of LRI_C6_D3_HPC (C6(3), d = 3). Run from this folder: make -f public.mk <target>
# (GFF/Makefile runs make -C code/LRI_C6_D3_HPC -f public.mk <target>). The package's own Makefile ships unchanged.
#
# Needs ../LRI_C6_D2_HPC (its reference/ tree is shared: setup links reference -> ../LRI_C6_D2_HPC/reference).
# Python >= 3.10 with numpy, scipy, mpmath (+ sympy, networkx for test-all); see requirements.txt.
# Compiled targets (test, test-all, smoke) need GNU/Linux, GCC with OpenMP and libquadmath, and Boost headers
# (Expanse: module load cpu/0.21.2a gcc/13.3.0 boost/1.86.0). They do not build on macOS/clang.
#
#   target       what                                                        measured runtime and node
#   setup        link reference/ to ../LRI_C6_D2_HPC/reference               instant
#   test         shipped-file check + the package's `make test` (build,      ~70 s on 16 cores (Expanse shared, 32 GB)
#                inputs regeneration, archived assembly, seeds, dimension
#                checks, orchestration with a fake worker, validate.py)
#   test-python  the same without the C++ build (any OS)                     ~70 s (Apple M-series, 1 core)
#   test-all     test + workflow, point checks, forced precision tiers,      ~6 min on 16 cores, 32 GB (Expanse job
#                end-to-end vs original code, archived-stream replay          54510646: build 7 s, test 62 s, workflow 35 s,
#                (385,744,896 samples)                                       points 18 s, levels 37 s, e2e 23 s, replay 143 s)
#   smoke        tiny campaigns through plan/run/merge/assemble with the     ~35 s on 16 cores
#                real worker, restart and tampering (tests/workflow.py)
#   replay       recompute every quoted C6(3) number from results/C6_3       ~1-2 s, 1 core, any OS (no compiler)
#   fetch-data   download the hosted full run directory (74 MB) from the     network
#                Zenodo record (ZENODO = base URL of its files)
#   replay-full  rebuild the merged records from the 1060 checkpoints,       53 s, 1 core (symmetry Intel, 2026-10-19:
#                then replay (needs fetch-data)                              60 PASS); about 1 GB in .work/
PY        ?= python3
WORK      ?= .work
RESULTS   ?= ../../results/C6_3/results_run-20260929-m8192
C7_RESULT ?= ../../results/C7_3/run1-20260930-m4096/C7_result.json
DATA      ?= ../../data/C6_3
TGZ        = run-20260929-m8192_full.tgz
# Base URL of the files of the project's Zenodo data record (https://doi.org/10.5281/zenodo.23466766). The file's name there is its
# repository path with / replaced by __.
ZENODO    ?= https://zenodo.org/records/23466766/files
DATA_URL  ?= $(ZENODO)/GFF__data__C6_3__$(TGZ)
export OPENBLAS_NUM_THREADS := 1
export MKL_NUM_THREADS := 1

.PHONY: help setup test test-python test-all smoke replay fetch-data replay-full clean

help:            ## list the targets
	@grep -E '^[a-z-]+:.*##' public.mk | sed 's/:.*##/:/'

setup:           ## link reference/ to the shared copy in ../LRI_C6_D2_HPC (byte-identical tree)
	@if [ -e reference ]; then :; \
	 elif [ -d ../LRI_C6_D2_HPC/reference ]; then ln -s ../LRI_C6_D2_HPC/reference reference && echo "reference -> ../LRI_C6_D2_HPC/reference"; \
	 else echo "setup: ../LRI_C6_D2_HPC/reference is missing; this package shares that tree (see public/README.md)"; exit 2; fi
	@test -f reference/verification/method_precision_results.json || { echo "setup: reference/ is incomplete"; exit 2; }

test: setup      ## shipped files vs SHA256SUMS_HPC.json, then the package's make test (C++ build)
	$(PY) -B public/verify_shipped.py
	$(MAKE) -f Makefile test PYTHON=$(PY)

test-python: setup  ## the same without the C++ build (runs on any OS)
	$(PY) -B public/verify_shipped.py
	$(MAKE) -f Makefile test-python PYTHON=$(PY)

test-all: setup  ## every package test target, including the archived-stream replay (C++ build)
	$(PY) -B public/verify_shipped.py
	$(MAKE) -f Makefile test-all PYTHON=$(PY)

smoke: setup     ## tiny campaigns with the real worker through the full pipeline (C++ build)
	$(MAKE) -f Makefile test-workflow PYTHON=$(PY)

replay: setup    ## recompute every quoted C6(3) number from the merged records; PASS/FAIL table in .work/replay/
	$(PY) -B public/replay_c6_3.py --results $(RESULTS) --c7-result $(C7_RESULT) --out $(WORK)/replay

fetch-data:      ## download the full run directory from the Zenodo record to ../../data/C6_3 and check its sha256
	@mkdir -p $(DATA)
	@if [ ! -f $(DATA)/$(TGZ) ]; then \
	   curl -fL -o $(DATA)/$(TGZ).part "$(DATA_URL)" && mv $(DATA)/$(TGZ).part $(DATA)/$(TGZ) \
	   || { echo "fetch-data: download of $(DATA_URL) failed; pass ZENODO=<base URL of a mirror> or place the file (74,439,565 bytes) in $(DATA)/" >&2; exit 1; }; fi
	@cd $(DATA) && $(PY) -c "import hashlib,sys;h=hashlib.sha256(open('$(TGZ)','rb').read()).hexdigest();e=open('$(abspath $(RESULTS))/../$(TGZ).sha256').read().split()[0];print('sha256',h,'OK' if h==e else 'MISMATCH');sys.exit(h!=e)"

replay-full: setup fetch-data  ## rebuild merged records from the checkpoints (tools/production.py merge), then replay
	rm -rf $(WORK)/full && mkdir -p $(WORK)/full
	tar -xzf $(DATA)/$(TGZ) -C $(WORK)/full
	$(PY) -B public/replay_c6_3.py --results $(WORK)/full/run-20260929-m8192 --remerge --c7-result $(C7_RESULT) --out $(WORK)/replay_full

clean:           ## remove .work/ and the built worker (the reference link stays)
	rm -rf $(WORK)
	$(MAKE) -f Makefile clean
