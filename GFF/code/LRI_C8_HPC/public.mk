# Public targets of GFF/code/LRI_C8_HPC: make -C code/LRI_C8_HPC -f public.mk <target>
# The package's own Makefile (build of bin/c8_integrate, `make test`) ships verbatim and is only called from here.
# Outputs go to .work/ (git-ignored); nothing under code/, data/ or results/ is written.
PY      ?= python3
DATA    ?= ../../data/C8_1
RESULTS ?= ../../results/C8_1
C7FINAL ?= ../../results/C7_1/C7_final.json
WORK    ?= .work
export OMP_NUM_THREADS := 1
export OPENBLAS_NUM_THREADS := 1
export MKL_NUM_THREADS := 1

.PHONY: help setup test replay verify clean

help:    ## list the targets
	@grep -E '^[a-z-]+:.*##' public.mk | sed 's/:.*##/:/'

setup:   ## link reference -> ../LRI_C7_HPC/reference (the identical archive of the C7 package; no symlink is committed)
	@if [ ! -e reference ]; then ln -sfn ../LRI_C7_HPC/reference reference; fi
	@test -f reference/verification/full_affine_assembly.json || { echo "reference/: ../LRI_C7_HPC/reference is missing" >&2; exit 1; }

# tests/test_pipeline8.py exercises the lane runner with claims of a worker called 'local', the identity tools/lane8.py
# uses outside Slurm; inside a Slurm job (SLURM_JOB_ID set) those claims belong to another job and the test waits for
# their 30-minute staleness. It therefore runs with the Slurm job variables removed.
test: setup  ## tests of the Python tooling (affine map, channel rule, tree counts; pipeline and lane runner with a fake integrator); about 10 min, 2 cores
	@$(PY) tests/test_c8_tools.py || echo "tests/test_c8_tools.py (bitwise Jacobian) failed: expected on some platforms (1 ulp, numpy/BLAS/CPU dependent); the portable form follows"
	$(PY) public/test_tools_portable.py
	env -u SLURM_JOB_ID -u SLURM_RESTART_COUNT -u SLURM_ARRAY_JOB_ID -u SLURM_ARRAY_TASK_ID $(PY) tests/test_pipeline8.py

replay: setup  ## rerun the K=4, A1 and K=14 combinations from data/C8_1 and check every quoted number; about 5 min, 1 core, 4 GB
	$(PY) public/replay8.py --data $(DATA) --work $(WORK)
	$(MAKE) -f public.mk verify

verify: setup  ## the PASS/FAIL table of the last replay (writes $(WORK)/verify_c8.tsv; exit 1 on any FAIL)
	$(PY) public/verify8.py --work $(WORK) --data $(DATA) --results $(RESULTS) --c7-final $(C7FINAL)

clean:   ## remove the work tree
	rm -rf $(WORK)
