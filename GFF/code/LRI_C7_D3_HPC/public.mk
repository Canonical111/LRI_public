# Public targets of LRI_C7_D3_HPC, the C7(3) package (production commit 4de9412). GFF/Makefile calls
#     make -C code/LRI_C7_D3_HPC -f public.mk <target>
# The package's own Makefile (verbatim) is called for builds and its own tests. Paths are relative to this folder.
#
# Tiers and where to run them:
#   replay           any machine, Python >= 3.10 + numpy; about 10 s on one core; no compiler, no hosted data.
#   test             x86-64 Linux node with GCC (C++17, OpenMP, libquadmath), GMP and Boost 1.77 headers; the delivered
#                    tests took 18 s (validate) + 12 s (workflow) after the build on a 64-core AMD EPYC 7532 node; allow
#                    10 min including the two builds. Needs no hosted data (setup unpacks the kernels shipped in git).
#   test-full, archived-replay, indep-rows   need the hosted records of the previous calculation (fetch-data, records).
#   fetch-data       downloads the two hosted files from the project's Zenodo data record (ZENODO = base URL of its files) into
#                    ../../data/C7_3 and checks them against public/hosted.sha256; 147 MB.
#   reverify         needs the hosted run directory run1-20260930-m4096_full.tgz (fetch-data); about 1 min, 0.6 GB disk.
#   smoke            needs the same tarball, the test toolchain and SciPy 1.17.1 (the Sobol nets of run1); re-plans run1
#                    (about 20 s, 0.1 GB) and reruns three of its 1,280 job indices (about 2 min on 64 cores).
#
# Boost: src/kernel.hpp does not compile with Boost >= 1.86. If the headers are not on the compiler's default path, pass
# BOOST_INC=<directory that contains boost/> (e.g. BOOST_INC=$BOOST_ROOT/include on Spack-module sites). GMP and
# libquadmath must be found by the linker (LIBRARY_PATH). The package Makefile builds with -O3 -std=c++17 -fopenmp
# -ffp-contract=off -fno-fast-math; never add fast-math flags.

PY      ?= python3
RES     ?= ../../results/C7_3
DATA    ?= ../../data/C7_3
WORK    ?= .work
THREADS ?= 64
ROWS    ?= [["production_a","power",3,0,0],["production_b","free",4,0,5],["production_a","free",3,0,1]]
RUN1     = run1-20260930-m4096
# Base URL of the files of the project's Zenodo data record (https://doi.org/10.5281/zenodo.23466766). A file's name there is its
# repository path with / replaced by __ (GFF__data__C7_3__<file>).
ZENODO  ?= https://zenodo.org/records/23466766/files
SHA256  ?= $(shell command -v sha256sum >/dev/null 2>&1 && echo sha256sum || echo "shasum -a 256")
# run1's plan (CAMPAIGN.md, "Campaign run1"); the cost model is byte-identical to run1's (sha256 f815b1fa..., pinned by
# the run1 manifest) and only places tasks on shards.
RUN1_PLAN = --seed 4805754955154533039 --backend gmp --replicates 64 --multiplier 4096 --primitive-mode recompute \
            --primitive-points 1024 --shards 64 --threads 64 --checkpoint-tasks 1024 --chunk-points 1048576 \
            --cost-model reverify_a6ce987/cost_models/gmp_symmetry_epyc7532.json
# job indices: 0 = a_free_L3 shard 0, 320 = a_power_L3 shard 0, 192 = a_free_L6 shard 0 (binary128 and GMP promotions)
SMOKE_INDICES ?= 0 320 192
export PYTHONDONTWRITEBYTECODE := 1
export OPENBLAS_NUM_THREADS := 1
export MKL_NUM_THREADS := 1
ifdef BOOST_INC
export CPLUS_INCLUDE_PATH := $(BOOST_INC)$(if $(CPLUS_INCLUDE_PATH),:$(CPLUS_INCLUDE_PATH))
endif

.PHONY: help test replay smoke setup boost-check checksums fetch-data records run1-dir test-full archived-replay indep-rows reverify clean distclean

help:            ## list the targets
	@grep -E '^[a-z0-9-]+:.*##' public.mk | sed 's/:.*##/:/'

replay:          ## recompute every quoted C7(3) number from results/C7_3 and compare (PASS/FAIL table; exit 1 on FAIL)
	$(PY) -B public/replay_C7_3.py --results $(RES) --out $(WORK)/replay

setup:           ## unpack inputs/packs from public/kernels/inputs_packs.tar.gz and cut out reference/inputs payloads (verified)
	$(PY) -B public/setup_kernels.py

boost-check:     ## refuse Boost >= 1.86 or missing Boost headers before compiling
	@v=$$(printf '#include <boost/version.hpp>\nBOOST_VERSION\n' | $${CXX:-g++} -x c++ -E -P - 2>/dev/null | tail -n 1 | tr -d ' '); \
	case "$$v" in ''|*[!0-9]*) echo "C7: Boost headers not found; pass BOOST_INC=<dir containing boost/> (Boost 1.77 tested)" >&2; exit 2;; esac; \
	if [ "$$v" -ge 108600 ]; then echo "C7: Boost $$v is not supported (src/kernel.hpp fails with >= 1.86); use 1.77" >&2; exit 2; fi; \
	echo "C7: Boost $$v (tested: 107700)"

test: setup boost-check  ## the production commit's own `make test`: build bin/c7d3_gmp, tests/validate.py, tests/workflow.py
	$(MAKE) -f Makefile test

checksums:       ## verify every present file against the delivered SHA256SUMS and reference/DELIVERY_MANIFEST.json
	$(PY) -B public/check_tree.py

fetch-data:      ## download the two hosted files from the Zenodo record into $(DATA) and check their sha256
	@mkdir -p $(DATA); for f in reference_records.tar.gz $(RUN1)_full.tgz; do \
	  test -f $(DATA)/$$f && continue; \
	  curl -fL -o $(DATA)/$$f.part "$(ZENODO)/GFF__data__C7_3__$$f" && mv $(DATA)/$$f.part $(DATA)/$$f \
	  || { echo "fetch-data: download of $$f failed; pass ZENODO=<base URL of a mirror> or place the file in $(DATA)/ (sha256 in public/hosted.sha256)" >&2; exit 1; }; done
	cd $(DATA) && $(SHA256) -c "$(CURDIR)/public/hosted.sha256"

records:         ## unpack the hosted records of the previous calculation into reference/records and verify them
	@test -f $(DATA)/reference_records.tar.gz || { echo "records: $(DATA)/reference_records.tar.gz missing; see make -f public.mk fetch-data" >&2; exit 2; }
	@if tar -tzf $(DATA)/reference_records.tar.gz | grep -v -E '^reference/?$$|^reference/records(/.*)?$$' | grep -q . \
	   || tar -tzf $(DATA)/reference_records.tar.gz | grep -q -F '..'; then \
	   echo "records: unexpected members in reference_records.tar.gz" >&2; exit 1; fi
	test -d reference/records || tar -xzf $(DATA)/reference_records.tar.gz
	$(PY) -B public/check_tree.py --require-hosted

test-full: setup boost-check records  ## the production commit's `make test-full`: every graph, point checks, archived reassembly
	$(MAKE) -f Makefile test-full

archived-replay: setup boost-check records  ## the cited check: rerun the worker on the 168,528 archived rows, rebuild the previous C7(3)
	$(MAKE) -f Makefile gmp
	rm -rf $(WORK)/archived_replay
	$(PY) -B public/replay_archived.py . $(WORK)/archived_replay --threads $(THREADS)
	$(PY) -B public/compare_archived_replay.py $(WORK)/archived_replay/replay_report.json $(RES)/evidence/replay_report.json

indep-rows: setup records  ## independent mpmath re-implementation on archived rows (no C++): make -f public.mk indep-rows ROWS='[...]'
	$(PY) -B public/indep_rows.py '$(ROWS)'

run1-dir:        ## verify the hosted run1 tarball against results/C7_3 and unpack it into .work/
	@test -f $(DATA)/$(RUN1)_full.tgz || { echo "run1-dir: $(DATA)/$(RUN1)_full.tgz missing; see make -f public.mk fetch-data" >&2; exit 2; }
	@h=$$($(PY) -c "import hashlib,sys;h=hashlib.sha256();f=open(sys.argv[1],'rb');[h.update(b) for b in iter(lambda:f.read(1<<20),b'')];print(h.hexdigest())" $(DATA)/$(RUN1)_full.tgz); \
	 test "$$h" = "$$(cut -d' ' -f1 $(RES)/$(RUN1)_full.tgz.sha256)" || { echo "run1-dir: sha256 of $(RUN1)_full.tgz differs from $(RES)/$(RUN1)_full.tgz.sha256" >&2; exit 1; }
	@mkdir -p $(WORK)
	test -d $(WORK)/$(RUN1) || tar -xzf $(DATA)/$(RUN1)_full.tgz -C $(WORK)

reverify: run1-dir  ## run reverify_a6ce987/tools/report.py on the hosted full run directory and compare with the shipped report
	rm -rf $(WORK)/reverify && mkdir -p $(WORK)/reverify
	$(PY) -B reverify_a6ce987/tools/report.py $(WORK)/$(RUN1) --output $(WORK)/reverify/run1_report.json
	$(PY) -B public/compare_report.py $(WORK)/reverify/run1_report.json $(RES)/run1_report_bb9d2ca.json
	$(PY) -B public/replay_C7_3.py --results $(RES) --out $(WORK)/reverify/replay --full-run $(WORK)/$(RUN1)

smoke: setup boost-check run1-dir  ## re-plan run1 with its seed and flags, rerun SMOKE_INDICES, compare with run1's checkpoints
	$(MAKE) -f Makefile gmp
	rm -rf $(WORK)/smoke && mkdir -p $(WORK)/smoke/tmp
	$(PY) -B tools/production.py plan $(WORK)/smoke/run $(RUN1_PLAN)
	for i in $(SMOKE_INDICES); do $(PY) -B tools/production.py run $(WORK)/smoke/run --index $$i --threads $(THREADS) --scratch $(WORK)/smoke/tmp || exit 1; done
	$(PY) -B public/compare_smoke.py $(WORK)/smoke/run $(WORK)/$(RUN1) $(SMOKE_INDICES)

clean:           ## remove the work area and build products (bin/; benchmarks/validation.json written by make test)
	rm -rf $(WORK) bin
	rm -f benchmarks/validation.json

distclean: clean ## also remove what setup and records restored
	rm -rf inputs/packs reference/records
	find reference/inputs/free reference/inputs/power -name 'G*.txt' ! -path '*/L2/*' -delete
