# Public targets for GFF/code/LRI_C7_HPC (full C7(1), note Section "Full seventh order in one dimension").
# Run from this folder:  make -f public.mk test | replay | fetch-data | replay-full | clean
# The package's own Makefile (production build and `make test`) ships verbatim and is called, never replaced.
#
#   test         package's own tests: builds bin/c7_integrate (GCC >= 9 with __float128/quadmath, OpenMP, Boost
#                multiprecision headers; x86-64 Linux), then tests/validate.py, tests/test_pipeline.py and
#                tests/check_inventory.py. About 10-20 min on a 16-core node (a personal desktop or an Expanse shared/debug job);
#                it does not build on Apple silicon (no __float128).
#   replay       Tier 1, git only: recomputes every quoted C7(1) number from results/C7_1 and reference/ (214 checks,
#                PASS/FAIL table in $(WORK)/replay7_tier1.txt). About 5 s and < 1 GB on one core; Python >= 3.8, numpy.
#   fetch-data   downloads the merged records from the Zenodo data record (doi:10.5281/zenodo.23466766) and unpacks
#                them into $(DATA) (a copy of the tarball already in $(DATA) is used if its sha256 matches
#                public/data_C7_1.json).
#   replay-full  Tier 2: reruns tools/combine.py on the hosted records and compares with results/C7_1 byte for byte
#                (byte-identical on Expanse and symmetry Intel; to 1e-12 on symmetry AMD, which differs in the last bits).
#                About 7 min on 1 core, < 2 GB RAM, 2 GB disk under $(WORK) (Expanse job 54901438, 2026-10-13: 409 s,
#                peak 1.7 GB, 14 checks PASS).

PY      ?= python3
WORK    ?= .work
RESULTS ?= ../../results/C7_1
DATA    ?= ../../data/C7_1
JOBS    ?= 1
export PYTHONDONTWRITEBYTECODE = 1
export OPENBLAS_NUM_THREADS = 1

.PHONY: test replay fetch-data replay-full clean

# tests/validate.py requires the reassembled archive to equal reference/verification/C7_assembled_result.json bit for
# bit, which depends on the platform's numpy/BLAS (it fails by one bit on symmetry, numpy 1.24.3). If validate.py stops
# at exactly that assertion, public/check_reassembly_portable.py repeats its remaining checks at 1e-13 relative and the
# rest of the package test (test_pipeline.py, check_inventory.py) runs as in the Makefile. test_pipeline.py has one
# exact comparison with a committed fixture (tests/fixtures/assemble_original_0227dc5.json) that is platform dependent in
# the same way; if it stops exactly there, public/run_pipeline_portable.py reruns the whole test with only that
# comparison made at 1e-12 relative. Any other failure fails.
test:
	rm -rf build/validation $(WORK)/validate.log
	@mkdir -p $(WORK)
	$(MAKE) -f Makefile all
	@if OPENBLAS_NUM_THREADS=1 $(PY) tests/validate.py > $(WORK)/validate.log 2>&1; then tail -1 $(WORK)/validate.log; \
	elif tail -3 $(WORK)/validate.log | grep -q "assert now\['C7_full'\]==old\['C7_full'\] and now\['sampling_se'\]==old\['sampling_se'\]" && \
	     tail -1 $(WORK)/validate.log | grep -qx AssertionError; then \
	  echo "tests/validate.py: every check passed except the bitwise reassembly comparison (platform floating point); portable check:"; \
	  $(PY) public/check_reassembly_portable.py; \
	else tail -30 $(WORK)/validate.log; exit 1; fi
	@if $(PY) tests/test_pipeline.py > $(WORK)/test_pipeline.log 2>&1; then tail -1 $(WORK)/test_pipeline.log; \
	elif tail -3 $(WORK)/test_pipeline.log | grep -q "o1\['primitive_guard'\].pop('primitive_classes')==44 and o0==o1" && \
	     tail -1 $(WORK)/test_pipeline.log | grep -qx AssertionError; then \
	  echo "tests/test_pipeline.py: stopped only at the exact comparison with the archived baseline fixture (platform floating point)"; \
	  $(PY) public/run_pipeline_portable.py; \
	else tail -30 $(WORK)/test_pipeline.log; exit 1; fi
	$(PY) tests/check_inventory.py build/validation/full_inventory.json

replay:
	$(PY) public/replay7.py --results $(RESULTS) --work $(WORK)

fetch-data:
	$(PY) public/fetch_data.py --data $(DATA)

replay-full:
	$(PY) public/replay7_full.py --data $(DATA) --results $(RESULTS) --work $(WORK) --jobs $(JOBS)

clean:
	rm -rf $(WORK) build/validation
