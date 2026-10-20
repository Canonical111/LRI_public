# Public targets of LRI_C8_D2_HPC: the full eighth-order coefficient C8(2) = 45990 +- 33 (note Section 31), exported at
# git commit 9df5b1c (its code is byte-identical to ba68f40, the export the production ran; 9df5b1c adds the
# production, tail-check and pilot evidence). Run from this folder: make -f public.mk <target>.
# Paths are relative. Shipped files are never modified; outputs go to public/out/, bin/ and build/.
#
#   setup        put the C7(2) reference trees in place (hard links to ../LRI_C7_D2_HPC/reference after checking every
#                file against this package's SHA256SUMS) and rebuild the two L7 graph packs (checked against
#                inputs/manifest.json); about 10 s, 0 extra disk with hard links
#   replay       every number the note quotes for C8(2), recomputed from the shipped merged records with the package's own
#                assembler and combiner (about 10 s; Python >= 3.10 and numpy; no compiler, no hosted data)
#   test         setup, then the package's pure-Python and host-compiler suite (make test-python with no L8 packs):
#                about 1 h on a Linux node or a macOS machine (needs a C++17 compiler with Boost and GMP headers)
#   retest-lane-sigterm  LOG=<log of a failed test>: only if that log shows the timing failure of lane_sigterm that the
#                README describes, rerun that case once, then the test-python steps make skipped; about 30 min
#   verify-lists the package's checksum lists SHA256SUMS and DELIVERY_MANIFEST.json, after setup (the files the release
#                scrubbed, public/SCRUBBED.txt, are checked for presence only); a few seconds
#   replay-tails the tail screen and the variance analysis from the full group tables (after fetch-data, 2.7 GB;
#                about 15 min, 8 GB)
#   jval1        the package's own cluster validation J-VAL-1 (`make test`): builds the kernels, needs the L8 packs
#                (setup-l8, after fetch-data of ../LRI_C8_shared payloads, 7.8 GB); about 40 min on a whole Linux node
#   fetch-data   download the production's group tables and the pilot's records from the paper's Zenodo record
#                (public/fetch.py, public/hosted.json; ../../data/C8_2/DATA.md)

PY      ?= python3
DATA    ?= ../../data/C8_2
RESULTS ?= ../../results/C8_2
SHARED  ?= ../LRI_C8_shared
OUT     ?= public/out
ZENODO  ?= https://zenodo.org/records/23466766/files
export OPENBLAS_NUM_THREADS := 1

# Every call into the package's own Makefile, and every package test that itself runs make, gets a clean make
# environment, as if started from a shell. Reason: when this file runs as a sub-make (GFF/Makefile calls
# `make -C code/<pkg> -f public.mk ...`, or a recipe calls $(MAKE)), GNU make turns on -w and passes `w` down in
# MAKEFLAGS; the package's tests run `make -s -n -C ROOT ...` and compare its output exactly (tests/test_gmp_prefix.py,
# tests/test_numerics_flags.py), and an inherited `w` adds "Entering directory" lines that -s does not remove (symmetry
# job 574317, GNU make 4.3). The package's own gates always ran make test-python as a top-level make.
PKGENV  := env -u MAKEFLAGS -u MFLAGS -u MAKELEVEL -u MAKEOVERRIDES -u GNUMAKEFLAGS
PKGMAKE := $(PKGENV) $(MAKE)

.PHONY: help setup setup-check setup-l8 replay replay-tails verify-lists test test-quick jval1 fetch-data clean retest-lane-sigterm

help:            ## list the targets
	@grep -E '^[a-z0-9-]+:.*##' public.mk | sed 's/:.*##/:/'

setup:           ## reference trees from ../LRI_C7_D2_HPC (hard links, checked) and the L7 packs (rebuilt, checked)
	$(PY) -B public/setup.py

setup-check:     ## verify that setup is complete, change nothing
	$(PY) -B public/setup.py --check

setup-l8:        ## the two L8 packs from the shared inventory (after fetch-data of its payload tars; verifies the pin)
	$(PKGMAKE) -f Makefile inputs-l8 INVENTORY=$(SHARED)/inventory/inventory8_d2 PYTHON=$(PY)

replay:          ## recombine the 24 merged groups and recompute every quoted number (PASS/FAIL table)
	$(PY) -B public/replay.py --data $(DATA) --results $(RESULTS) --shared $(SHARED) --out $(OUT)

verify-lists:    ## SHA256SUMS and DELIVERY_MANIFEST.json (after setup; files in public/SCRUBBED.txt: presence only)
	$(PY) -B public/verify_lists.py

replay-tails:    ## the tail table and variance analysis from the hosted group tables (after fetch-data)
	$(PY) -B public/replay_tails.py --data $(DATA) --results $(RESULTS) --out $(OUT)

test: setup      ## the package's test-python suite without L8 packs (about 1 h); stops first on a Python whose os.urandom opens /dev/urandom (public/check_python.py)
	$(PY) -B public/check_python.py
	C8_ALLOW_NO_L8=1 $(PKGMAKE) -f Makefile test-python PYTHON=$(PY)

retest-lane-sigterm: setup ## LOG=<log of a failed test>: if its only failure is the lane_sigterm timing signature (README), rerun that case once, then the test-python steps make skipped (about 30 min)
	$(PY) -B public/check_python.py
	$(PY) -B public/retest_lane_sigterm.py --log "$(LOG)" --python "$(PY)" --out $(OUT)

test-quick: setup ## the steps of test-python that take under a minute each (about 2 min)
	$(PKGENV) $(PY) -B tools/prepare_inputs.py
	$(PKGENV) $(PY) -B tests/check_venv.py
	$(PKGENV) $(PY) -B tests/ast_scan.py
	$(PKGENV) $(PY) -B gen/test_regress.py
	$(PKGENV) $(PY) -B gen/test_handoff_inventory.py
	$(PKGENV) $(PY) -B tests/check_vendored.py --no-review-record
	$(PKGENV) $(PY) -B tests/vendored_isolated.py --in-place
	$(PKGENV) $(PY) -B tests/test_delivery_verifier.py
	C8_ALLOW_NO_L8=1 $(PKGENV) $(PY) -B tests/check_inputs.py
	$(PKGENV) $(PY) -B tests/test_gmp_prefix.py
	$(PKGENV) $(PY) -B tests/test_omp_launch.py
	$(PKGENV) $(PY) -B tests/test_dd_profile.py
	$(PKGENV) $(PY) -B tests/sanitize.py --capture-check

jval1: setup setup-l8 ## the package's J-VAL-1 (make test): whole Linux x86-64 node, GCC, Boost, GMP, about 40 min
	$(PKGMAKE) -f Makefile inspect c7ref PYTHON=$(PY)
	$(PKGMAKE) -f Makefile test PYTHON=$(PY)

fetch-data:      ## the production's group tables and the pilot's records (replay-tails) from the paper's Zenodo record, checked, into ../../data/C8_2/
	$(PY) -B public/fetch.py --base $(ZENODO)
	@echo "The L8 inputs of setup-l8 and jval1 come with the shared payload tars: make -C $(SHARED) -f public.mk fetch-data"

clean:           ## remove public outputs (not the setup files)
	rm -rf $(OUT)
