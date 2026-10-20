# Public targets of LRI_C7_D2_HPC: the full seventh-order coefficient C7(2) (note Section 28), exported at git commit
# fb64c47, the code that ran the 2026 production. Run from this folder: make -f public.mk <target>.
# Paths are relative. Shipped files are never modified; new files go to inputs/packs/ (setup), bin/ (builds) and
# public/out/. The package's own Makefile is unchanged; its `test` writes benchmarks/validation.json, so the `test` target
# below runs the same steps with that record written to public/out/ instead.
#
#   setup        rebuild the ten graph packs inputs/packs/*.pack (266 MiB, not in git) from the shipped reference kernels
#                and verify them against inputs/manifest.json (about 2 s; Python only)
#   test-python  the platform-independent part of `test`: setup, the delivery manifest and SHA256SUMS of all 4,405
#                files through public/verify_delivery_public.py (the delivered tools/verify_delivery.py, unchanged; the
#                five merged TeX notes of reference/ are the only files it accepts as absent), and the delivery-verifier
#                tests (about 10 s; Python 3.9+ only; runs on macOS)
#   test         the package's `make test` (decimal build, graph-kernel replay against the original executable on a
#                subset, plan/run/merge/assemble workflow) plus test-python (about 3-5 min on one Linux x86-64 node with
#                4-8 cores: g++ >= 11 with OpenMP and libquadmath, Boost headers >= 1.77; Python >= 3.10, numpy, scipy)
#   test-full    the package's `make test-full`: both backends (needs GMP), all 3,511 graph kernels against the original
#                executable, 450-digit point checks, previous-result reassembly, staging (about 5-8 min, same node)
#   replay       every number the note quotes for C7(2), recomputed from the shipped merged records with the production's
#                own assembly, and the previous calculation re-assembled by tools/reassemble_reference.py (about 10 s;
#                Python 3.9+ and numpy only; no compiler, no hosted data)
#   fetch-data   the hosted full run directory (640 MiB: checkpoints, tasks.sqlite, nets, graph tables); not needed by any
#                target above
#
# Boost: if the headers are not on the default include path, pass them as make -f public.mk test CPATH=<boost>/include
# (exported to every compiler call). CXXFLAGS would not do: tests/validate.py and tests/check_points.py call g++ themselves
# (the original executable and the point checks) and see only the environment.

PY      ?= python3
DATA    ?= ../../data/C7_2
RESULTS ?= ../../results/C7_2
C6      ?= ../../results/C6_2/C6_result.json
OUT     ?= public/out
export OPENBLAS_NUM_THREADS := 1
export PYTHONDONTWRITEBYTECODE := 1

.PHONY: help setup test-python test test-full replay fetch-data clean

help:            ## list the targets
	@grep -E '^[a-z-]+:.*##' public.mk | sed 's/:.*##/:/'

setup:           ## rebuild inputs/packs/ from reference/ and verify every pack sha256
	$(PY) -B public/regen_packs.py

test-python: setup  ## delivery manifest + SHA256SUMS of the shipped tree, delivery-verifier tests (no compiler)
	@mkdir -p $(OUT)
	$(PY) -B public/verify_delivery_public.py > $(OUT)/verify_delivery.json || { cat $(OUT)/verify_delivery.json; exit 1; }
	@$(PY) -c "import json; r=json.load(open('$(OUT)/verify_delivery.json')); print('verify_delivery:', r['status'], r['payload_files_checked'], 'files,', r['extra_files_count'], 'extra (public/ and builds are allowed);', 'INFO', len(r['merged_notes_not_shipped']), 'merged notes not shipped (one TeX note per direction)')"
	$(PY) -B tests/test_delivery_verifier.py > $(OUT)/delivery_verifier.json
	@echo "test_delivery_verifier: passed"

test: test-python  ## the package's make test (Linux x86-64): build, kernel replay on a graph subset, workflow
	$(MAKE) all
	$(PY) -B tests/validate.py --output $(OUT)/validation.json
	$(PY) -B tests/workflow.py > $(OUT)/workflow.json
	@echo "test: PASS (records in $(OUT)/)"

test-full: test  ## the package's make test-full: gmp backend, all 3,511 kernels, point checks, reassembly, staging
	$(MAKE) gmp
	$(PY) -B tests/validate.py --full --output $(OUT)/full_validation.json
	$(PY) -B tests/check_points.py > $(OUT)/point_checks.json
	$(PY) -B tools/reassemble_reference.py > $(OUT)/reassembled.json
	$(PY) -B tests/staging.py > $(OUT)/staging.json
	@echo "test-full: PASS (records in $(OUT)/)"

replay:          ## recompute every quoted number from the merged records and compare (PASS/FAIL table, public/out/replay.json)
	$(PY) -B public/replay_c7d2.py --data $(DATA)/run1-20260930-m4096 --results $(RESULTS) --c6 $(C6) --out $(OUT)

fetch-data:      ## no target needs hosted data; the full run directory (640 MiB, a re-merge audit only) is available on request
	@echo "No target of this package needs hosted data. The full run directory (640 MiB) is kept in the authors' archive and is"
	@echo "available on request; it is not in the paper's Zenodo data record. See $(DATA)/DATA.md, part (b)."; exit 2

clean:
	rm -rf $(OUT)
	$(MAKE) clean
