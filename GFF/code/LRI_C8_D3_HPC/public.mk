# Public targets of LRI_C8_D3_HPC, the C8(3) package. GFF/Makefile runs: make -C code/LRI_C8_D3_HPC -f public.mk <target>
# The package's own Makefile ships verbatim (production commit 4fbd1bae); this file only adds the public tiers and calls it.
# Paths are relative to this folder. Outputs go to .public_out/ (git-ignored); nothing under results/ or data/ is written,
# except that fetch-data places the hosted files (data/C8_3/HOSTED.json says where).
#
#   make -f public.mk replay        recompute every quoted C8(3) number from results/C8_3 (no hosted data needed; the
#                                   optional steps H use data/C8_3/results when fetched). 1 core, 2 GB, about 20 s
#                                   (40 s with the hosted tables). Writes .public_out/replay/REPLAY.md; exit 1 on a FAIL row.
#   make -f public.mk test          pure-Python regression tests that need no hosted data and no compiler: assembly and
#                                   statistics, result verifier, design, pilot report, orchestration on the fake worker.
#                                   1 core, 4 GB; measured 7 min on an Apple M-series core, allow 15-20 min on a cluster core.
#   make -f public.mk fetch-data [TIER=replay|test|rerun|optional|all] [ZENODO=<base URL of the record's files>]
#                                   the hosted files, from the Zenodo record (see data/C8_3/DATA.md): replay 0.33 GB,
#                                   test +0.69 GB, rerun +8.80 GB, optional +2.15 GB (unpacked sizes)
#   make -f public.mk test-native   the package's make test-native (native build, validate.py, class_b.py), check_build.py
#                                   --selftest and the gen3 tests.
#                                   Needs GCC >= 11 (C++17, OpenMP), Boost 1.77 headers, GMP 6.2, libquadmath and
#                                   fetch-data TIER=rerun (L7 and L8 packs). One 64-core node, 32 GB: build 3 min, gates
#                                   1-2 min (val1 571477 on symmetry: make_native 178 s, validate 26 s, class_b 12 s).
#   make -f public.mk test-replay   the archived C7(3) production (168,528 rows) replayed with the C8 worker in order-7 mode
#                                   and C7(3) rebuilt (cited in note Sec 32.2). Needs the toolchain and fetch-data TIER=test.
#                                   One 64-core node: build 3 min + 1 min (J-RUN1 570390: 56 s at 64 threads). The verbatim
#                                   test's row tolerance 1e-10 holds on AMD CPUs; when only it fails (Intel: 1.4e-10), the
#                                   target reruns the same test with a portable row tolerance and says so
#                                   (public/test_replay_portable.py).
#   make -f public.mk test-full     the package's own `make test` (every pure-Python test, the native gates, workflow and
#                                   staging with the real workers). Needs the toolchain and fetch-data TIER=rerun. One
#                                   64-core node, about 45 min (check_inputs alone took 28 min in val1 571477). On Expanse
#                                   and symmetry the fake-Slurm tests refuse by design (exit 64, "SITE_REFUSED" in the
#                                   package's val1 records); run them on another host or read REPRODUCE.md section 2.

PY      ?= python3
RESULTS ?= ../../results/C8_3
DATA    ?= ../../data/C8_3
OUT     ?= .public_out
TIER    ?= replay
# Base URL of the files of a mirror of the project's Zenodo data record (https://doi.org/10.5281/zenodo.23466766);
# empty = HOSTED.json base_url, https://zenodo.org/records/23466766/files
ZENODO  ?=
export OPENBLAS_NUM_THREADS := 1
export OMP_NUM_THREADS ?= 1

# the pure-Python tests that pass without the hosted packs and on a real Slurm site (val1 PASS rows of the production
# export); the fake-Slurm tests that refuse on a real site are in test-full
# (tests/thru_report_test.py runs through public/thru_report_test_portable.py: verbatim first; with Python >= 3.12, whose
# sum() of floats rounds differently, three floats of the committed re-derivation move by one ulp and the same test is
# rerun with float equality to relative 1e-12, and says so)
TESTS_PY := tests/ast_scan.py tests/blocks_test.py tests/compat_run1.py "tests/assembly_checks.py --exact" \
            tests/verify_result_tamper.py tests/design_fallback_test.py tests/drill_select_test.py tests/native_static.py \
            tests/test_delivery_verifier.py "tests/check_build.py --selftest" "tests/forced_tiers.py --selftest" \
            tests/pack_reads_test.py tests/integration_3a.py tests/test_pilot_report.py public/thru_report_test_portable.py \
            tests/margin_probe8_test.py "tests/workflow.py --fake" "tests/staging.py --fake" tests/cost_refresh_test.py \
            "tests/unit_orchestration.py --only atomic_and_guards,chunking_synthetic,lanes,merge_and_safety,per_index_and_spies,plan_staging,zero_task_groups"

.PHONY: help replay test fetch-data test-native test-replay test-full clean

help:          ## list the targets
	@grep -E '^[a-z-]+:.*##' public.mk | sed 's/:.*##/:/'

replay:        ## recompute and verify every quoted number (PASS/FAIL table in $(OUT)/replay/REPLAY.md)
	OPENBLAS_CORETYPE=$${OPENBLAS_CORETYPE:-Zen} $(PY) -B public/replay_c8_3.py --results $(RESULTS) --data $(DATA) --out $(OUT)/replay

test:          ## pure-Python tests, no hosted data, no compiler (7-20 min, 1 core)
	@mkdir -p $(OUT)/test; s=0; for t in $(TESTS_PY); do \
	  printf '%-60s ' "$$t"; \
	  if C8_ALLOW_NO_L8=1 env -u C8_SITE $(PY) -B $$t > $(OUT)/test/$$(echo $$t | tr ' /,' '___').log 2>&1; then echo PASS; else echo FAIL; s=1; fi; \
	done; echo "logs in $(OUT)/test"; exit $$s

fetch-data:    ## fetch and place the hosted files of TIER (replay < test < rerun < optional)
	$(PY) -B public/fetch_data.py --tier $(TIER) --data $(DATA) $(if $(ZENODO),--url $(ZENODO))

test-native:   ## native build and gates (needs the toolchain and fetch-data TIER=rerun)
	$(MAKE) test-native
	$(PY) -B tests/check_build.py --selftest
	$(PY) -B gen3/test_gen3.py

test-replay:   ## archived C7(3) production replay with the C8 worker (needs the toolchain and fetch-data TIER=test)
	@mkdir -p $(OUT); \
	 if $(MAKE) test-replay > $(OUT)/test-replay.log 2>&1; then cat $(OUT)/test-replay.log; exit 0; fi; \
	 cat $(OUT)/test-replay.log; \
	 if grep -q 'AssertionError: replayed rows differ from the archive by' $(OUT)/test-replay.log; then \
	   echo "test-replay: the verbatim row tolerance 1e-10 is exceeded. This is expected off the AMD CPU class (x87"; \
	   echo "expl/logl rounding; see public/test_replay_portable.py). Rerunning the same test with the portable tolerance."; \
	   OPENBLAS_NUM_THREADS=1 $(PY) -B public/test_replay_portable.py; \
	 else exit 1; fi

test-full:     ## the package's own make test (needs the toolchain and fetch-data TIER=rerun)
	$(MAKE) test
	$(PY) -B tests/check_vendored.py --no-review-record

clean:         ## remove $(OUT)
	rm -rf $(OUT)
