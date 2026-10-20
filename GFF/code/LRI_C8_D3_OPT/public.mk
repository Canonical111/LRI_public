# Public targets of the independent C8(3) package (GFF/code/LRI_C8_D3_OPT). The package's own Makefile ships
# verbatim; this file only adds the public targets. Run from this folder:
#     make -f public.mk help
# GFF/Makefile calls `make -C code/LRI_C8_D3_OPT -f public.mk <target>`.
#
#   replay       recompute every quoted number of the check from ../../results/C8_3_check (no native outputs needed);
#                about 3 s, 1 core, < 1 GB, any OS (tested on macOS arm64 and Linux); Python 3.10+, numpy, scipy.
#   replay-full  replay plus the allocation replay (R7); needs `make -f public.mk fetch-data` (pilot bundle).
#   test         build the native workers and run the package's own tests in a copy under .work/test:
#                Linux x86-64 only (__float128, libquadmath), GNU C++17 with OpenMP, GMP, Boost multiprecision headers
#                (tested: GCC 13.3.0 + Boost 1.77 + GMP 6.2.1 on AMD EPYC 7742; GCC 11.4.0 on EPYC 7543 and Xeon 6148).
#                About 2-3 min on a 32-core node with 64 GB (build 5-10 s with -j32; slowest step test_points, ~40 s).
#                Set CPPFLAGS/LDFLAGS for Boost and GMP if they are not on the default paths.
#   test-py      the Python-only tests (rg, campaign, allocate, streaming assembly): seconds, any OS.
#   test-cluster tests/test_cluster.py (cluster admission layer with fake Slurm); needs the pilot bundle (fetch-data).
#   fetch-data   download the hosted bundles from the project's Zenodo data record (ZENODO = base URL of its files) into
#                ../../data/C8_3_check and unpack them here (graph payloads, pilot, regeneration inputs); needed only
#                for a production rerun, graph regeneration, replay-full, test-cluster.
#   verify-data  check the tree against the package's SHA256SUMS (public/verify_data.py): every present file matches,
#                only hosted files (before fetch-data) and the merged notes of public/dropped_paths.txt may be absent.
#   clean        remove .work/
#
# The package's own tests rewrite verification/*.json, so `test` runs in a copy (.work/test) whose large data
# (inputs/free, inputs/power, results) are symlinks, as the production build script slurm/build.sh does.

PYTHON   ?= python3
NPROC    ?= $(shell nproc 2>/dev/null || sysctl -n hw.ncpu 2>/dev/null || echo 4)
SHA256   ?= $(shell command -v sha256sum >/dev/null 2>&1 && echo sha256sum || echo "shasum -a 256")
RESULTS  ?= ../../results/C8_3_check
DATA     ?= ../../data/C8_3_check
# Set to the main C8(3) record (LRI_C8_D3_HPC prod1 C8_result.json) if it is not at one of replay_check.py's defaults.
MAIN_RESULT ?=
WORK     := .work
TESTDIR  := $(WORK)/test
export OPENBLAS_NUM_THREADS := 1
export PYTHONDONTWRITEBYTECODE := 1

MAIN_ARG = $(if $(MAIN_RESULT),--main-result $(MAIN_RESULT),)

.PHONY: help replay replay-full test test-py test-cluster test-copy fetch-data verify-data clean

help:
	@sed -n '1,/^$$/p' public.mk

replay:
	$(PYTHON) -B public/replay_check.py --results $(RESULTS) --out $(WORK)/replay $(MAIN_ARG)

replay-full:
	$(PYTHON) -B public/replay_check.py --results $(RESULTS) --out $(WORK)/replay --full $(MAIN_ARG)

# A fresh copy of the package without .work, bin and the large data; the data are linked back.
test-copy:
	rm -rf $(TESTDIR)
	mkdir -p $(TESTDIR)
	tar --exclude=./.work --exclude=./bin --exclude=./inputs/free --exclude=./inputs/power --exclude=./results \
	    -cf - . | tar -xf - -C $(TESTDIR)
	ln -s "$(CURDIR)/inputs/free" $(TESTDIR)/inputs/free
	ln -s "$(CURDIR)/inputs/power" $(TESTDIR)/inputs/power
	if [ -d results ]; then ln -s "$(CURDIR)/results" $(TESTDIR)/results; fi

# The steps of slurm/build.sh after its delivery check, in the same order (test_cluster is test-cluster here).
test: test-copy
	cd $(TESTDIR) && $(MAKE) -f Makefile -j$(NPROC) PYTHON=$(PYTHON) gmp optimized baseline points reference bin/test_positive_quad
	cd $(TESTDIR) && bin/test_positive_quad
	cd $(TESTDIR) && $(MAKE) -f Makefile PYTHON=$(PYTHON) test-native
	cd $(TESTDIR) && $(MAKE) -f Makefile PYTHON=$(PYTHON) test-points
	cd $(TESTDIR) && for t in test_optimization test_hpc_dispatch test_streaming_assembly test_rg test_campaign test_allocate; do \
	    echo "== tests/$$t.py"; $(PYTHON) -B tests/$$t.py || exit 1; done
	@echo "test: PASS (native build, arithmetic, native regression, points, optimization, dispatch, assembly, RG, campaign, allocation)"

test-py: test-copy
	cd $(TESTDIR) && for t in test_rg test_campaign test_allocate test_streaming_assembly; do \
	    echo "== tests/$$t.py"; $(PYTHON) -B tests/$$t.py || exit 1; done
	@echo "test-py: PASS"

test-cluster: test-copy
	@test -f results/pilot_20261008/manifest.json || { echo "test-cluster needs the pilot bundle: make -f public.mk fetch-data"; exit 1; }
	cd $(TESTDIR) && $(PYTHON) -B tests/test_cluster.py

# Hosting is not decided yet (see ../../data/C8_3_check/DATA.md). Set DATA_URL to the base URL of the bundles.
# Base URL of the files of the project's Zenodo data record (https://doi.org/10.5281/zenodo.23466766). A bundle's name there is its
# repository path with / replaced by __ (GFF__data__C8_3_check__<b>).
ZENODO   ?= https://zenodo.org/records/23466766/files
BUNDLES  := c8opt_inputs_free.tar.xz c8opt_inputs_power.tar.xz c8opt_pilot_20261008.tar.xz c8opt_regeneration.tar.xz
fetch-data:
	mkdir -p $(DATA)
	@cd $(DATA) && for b in $(BUNDLES); do [ -f $$b ] && continue; \
	  curl -fL -o $$b.part "$(ZENODO)/GFF__data__C8_3_check__$$b" && mv $$b.part $$b \
	  || { echo "fetch-data: download of $$b failed; pass ZENODO=<base URL of a mirror> or place the bundles in $(DATA) (see ../../data/C8_3_check/DATA.md)" >&2; exit 1; }; done
	cd $(DATA) && $(SHA256) -c "$(CURDIR)/public/data_bundles.sha256"
	for b in $(BUNDLES); do tar -xJf $(DATA)/$$b -C . || exit 1; done
	$(PYTHON) -B public/verify_data.py --require-hosted

verify-data:
	$(PYTHON) -B public/verify_data.py

clean:
	rm -rf $(WORK)
