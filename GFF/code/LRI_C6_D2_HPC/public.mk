# Public targets of LRI_C6_D2_HPC: the two-dimensional sixth-order production, C6(2) = 362.366 +- 0.004 (note Sections 1,
# 24.6-24.9 and 33), exported at git commit 6aaf656, the code that ran the production. Run from this folder:
# make -f public.mk <target>. Paths are relative. Shipped files are never modified; outputs go to bin/ and public/out/.
#
#   test         build + the package's `make test`: the pure-Python suites (archived assembly, input regeneration, archived
#                net replay, 12 orchestration groups) and the native replay of all 492 kernels against the ORIGINAL code
#                built from reference/code (about 1 min on 8-16 cores; x86-64 Linux only: the kernel needs the 80-bit long
#                double; g++ with OpenMP and libquadmath, Boost.Multiprecision headers; Python >= 3.10 with numpy, scipy,
#                mpmath, sympy, networkx)
#   test-all     test + the four native suites test-workflow, test-points, test-levels, test-e2e (about 2 min more)
#   test-python  the pure-Python part of `make test`; runs on any OS (about 30 s; numpy, scipy)
#   smoke        = the package's test-workflow: plan, run with the real worker (restart, duplicates, tampering), merge and
#                assemble a tiny campaign (about 40 s; same node as test)
#   replay       every number the note quotes for C6(2), recomputed from the shipped merged records with the production's
#                own assembler (about 2 s; Python >= 3.10 and numpy only)
#   integrity    the shipped files against SHA256SUMS_HPC.json (as ran, ignoring the files not released) and
#                reference/SHA256SUMS.json (a few seconds)
#   remerge      re-merge the 8 groups from the hosted checkpoints with the unmodified tools and compare byte for byte, then
#                the unmodified tools/assemble.py and the replay on the re-merged copy (after fetch-data; about 20 s)
#   fetch-data   download the hosted run directory from the paper's Zenodo record (public/fetch.py, public/hosted.json;
#                ../../data/C6_2/DATA.md)

PY      ?= python3
DATA    ?= ../../data/C6_2
RESULTS ?= ../../results/C6_2
C7      ?= ../../results/C7_2/C7_result.json
OUT     ?= public/out
ZENODO  ?= https://zenodo.org/records/23466766/files
export OPENBLAS_NUM_THREADS := 1
export MKL_NUM_THREADS := 1

.PHONY: help test test-all test-python smoke replay integrity remerge fetch-data clean

help:            ## list the targets
	@grep -E '^[a-z-]+:.*##' public.mk | sed 's/:.*##/:/'

test:            ## build + make test (x86-64 Linux)
	$(MAKE) clean
	$(MAKE) test PYTHON=$(PY)

test-all: test   ## + test-workflow, test-points, test-levels, test-e2e
	$(MAKE) test-workflow test-points test-levels test-e2e PYTHON=$(PY)

test-python:     ## the pure-Python suites only (any OS)
	$(MAKE) test-python PYTHON=$(PY)

smoke:           ## a tiny campaign through plan, run, merge and assemble with the real worker (x86-64 Linux)
	$(MAKE) test-workflow PYTHON=$(PY)

replay:          ## recompute every quoted number from the merged records and compare (PASS/FAIL table)
	$(PY) -B public/replay.py --data $(DATA)/run-20260928-m8192 --results $(RESULTS) --c7 $(C7) --out $(OUT)

integrity:       ## shipped files against the package's checksum lists
	$(PY) -B public/integrity.py

remerge:         ## re-merge from the hosted checkpoints and compare byte for byte (after fetch-data)
	$(PY) -B public/remerge.py --hosted $(DATA)/hosted/run-20260928-m8192 --sums $(DATA)/hosted_run-20260928-m8192.sha256 \
	  --data $(DATA)/run-20260928-m8192 --results $(RESULTS) --c7 $(C7) --out $(OUT)/remerge

fetch-data:      ## the hosted run directory (392 MiB unpacked) from the paper's Zenodo record, size and sha256 checked, into ../../data/C6_2/hosted/
	$(PY) -B public/fetch.py --base $(ZENODO)

clean:
	rm -rf $(OUT)
	$(MAKE) clean
