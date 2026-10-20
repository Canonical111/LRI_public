# Public targets of LRI_C8_D2_HPC_optimized: the independent eighth-order code for d = 2 (note Section 31.7), exported at git
# commit a2a9a46, which is a791a1f (the commit that ran the pilot and the production) plus a791a1f's final Expanse gate
# record. Run from this folder: make -f public.mk <target>.
# Paths are relative. Shipped files are never modified; outputs go to bin/, build/ and public/out/.
#
#   test      package tests without graph packs (about 5 min on one cluster node; Linux, g++ >= 9 with OpenMP and
#             libquadmath, Boost headers, GMP; Python >= 3.10 with numpy, scipy, mpmath)
#   fixtures  the bitwise check cited in the note: the optimized GMP kernel against the unmodified reference kernel on the
#             52 frozen fixture cases at 1 and 2 threads (about 3 min; same requirements)
#   replay    every number the note quotes for this check, recomputed from the shipped merged records with the production's
#             own assembler (about 10 s; Python and numpy only; no compiler)
#   remerge   re-merge all 24 groups from their checkpoints and compare with the shipped merged records byte for byte
#             (needs `make -f public.mk fetch-data`, 1.7 GB; about 15 min on 8 cores)
#   fetch-data  download the hosted campaign directory from the paper's Zenodo record; ALL=1 adds the delivered package zip
#               with the original graph packs (public/fetch.py, public/hosted.json; ../../data/C8_2_check/DATA.md)

PY      ?= python3
DATA    ?= ../../data/C8_2_check
RESULTS ?= ../../results/C8_2_check
OURS8   ?= ../../results/C8_2/C8_final.json
OURS7   ?= ../../results/C7_2/C7_result.json
OUT     ?= public/out
ZENODO  ?= https://zenodo.org/records/23466766/files
J       ?= 4
export OPENBLAS_NUM_THREADS := 1
export OMP_NUM_THREADS ?= 2
# The site layer checks seeds against the main C8(2) calculation's seed registry with that package's own tools/seeds.py and
# tools/common.py (pinned by sha256 in tools/node_runner.py; byte-identical in GFF/code/LRI_C8_D2_HPC at 9df5b1c). Without
# them 18 site-layer tests skip and one fails.
export C8_SEEDS_TOOL_DIR ?= $(abspath ../LRI_C8_D2_HPC/tools)

.PHONY: help test test-here fixtures replay remerge fetch-data clean

help:            ## list the targets
	@grep -E '^[a-z-]+:.*##' public.mk | sed 's/:.*##/:/'

test:            ## the package tests, run in a copy under $TMPDIR (see test-here)
	@W=$$(mktemp -d "$${TMPDIR:-/tmp}/c8chk_test.XXXXXX") && cp -a . "$$W/pkg" && \
	  $(MAKE) -C "$$W/pkg" -f public.mk test-here PY=$(PY); rc=$$?; rm -rf "$$W"; exit $$rc

# The scheduler's cache test rewrites a file in place within one second and expects the stat-bound receipt to notice;
# file systems with one-second timestamps (Lustre) miss that, so `test` runs in a copy on node-local disk ($TMPDIR).
test-here:       ## decimal build, kernel point and Taylor checks, assembly formula, scheduler/allocation/site-layer tests
	$(MAKE) test PYTHON=$(PY)
	$(PY) -B tests/kernel_checks.py --graph-list tests/fixtures/graphs.txt
	for t in hpc_scheduler allocation refinement_allocation precision_delivery site_layer; do $(PY) -B tests/$$t.py || exit 1; done

fixtures:        ## the 52-case frozen replay: optimized kernel equals the reference kernel bit for bit
	$(MAKE) -j$(J) gmp PYTHON=$(PY)
	$(PY) -B tools/benchmark_native.py build-baseline --backend gmp --output $(OUT)/baseline_gmp
	$(PY) -B tools/benchmark_native.py compare --manifest optimization_work/baseline_profile/matrix/manifest.json \
	  --baseline $(OUT)/baseline_gmp --candidate bin/c8d2_gmp --output $(OUT)/exact_replay --threads 1 2 --repeats 1
	bash slurm/site_gate.sh --check-replay $(OUT)/exact_replay | tee $(OUT)/fixtures.json
	@$(PY) -c "import json,sys; r=json.load(open('$(OUT)/fixtures.json')); ok=r['passed'] and r['cases']==52 and r['equals_sandbox_digest']; print('fixtures:', 'PASS' if ok else 'FAIL', r['cases'], 'cases, science digest', r['science_digest'][:16]); sys.exit(0 if ok else 1)"

replay:          ## recompute every quoted number from the merged records and compare (PASS/FAIL table)
	$(PY) -B public/replay.py --data $(DATA) --results $(RESULTS) --ours8 $(OURS8) --ours7 $(OURS7) --out $(OUT)

remerge:         ## re-merge the 24 groups from the hosted checkpoints and compare byte for byte (after fetch-data)
	bash public/remerge.sh $(DATA)/hosted/prod1 $(DATA)/prod1 $(OUT)/remerge

fetch-data:      ## the production's campaign directory (1.7 GB unpacked) from the paper's Zenodo record, checked, into ../../data/C8_2_check/hosted/; ALL=1 adds the delivered package zip (production rerun only)
	$(PY) -B public/fetch.py --base $(ZENODO) $(if $(ALL),--all,)

clean:
	rm -rf $(OUT) build
	$(MAKE) clean
