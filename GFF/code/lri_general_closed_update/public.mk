# Public targets of lri_general_closed_update: finite multivariable Horn arrays of the six C5 masters and the Q2, Z2
# identities (note Section 14), as delivered in LRI_complete_research_bundle.zip (sha256 3715f545...). Run from this
# folder: make -f public.mk <target>. Paths are relative. Shipped files are never modified; the delivered scripts write
# their records in place, so every rerun happens in a copy under public/out/work/.
#
#   replay  integrity (SOURCE_SHA256SUMS, array_manifest.json complete, release_manifest.json ignore-missing); reruns
#           kappa_regularization.py, check_insertion_prefactors.py, check_new_identities.py (60 digits) and the Horn
#           compiler for Q, P4, L, Z, K, compared with the delivered records; Q2, Z2 and the Horn counts quoted in the
#           note (about 20 s, one core; Python >= 3.10 with numpy, scipy, sympy, mpmath; macOS or Linux)
#   test    replay plus the full compiler (P5a, P5b: 2.4 min, 0.25 GB), check_horn_compiler.py (about 1 min),
#           check_primitive_sums.py and primitive_series.py (about 4 min in all, one core)

PY       ?= python3
EXPECTED ?= ../../results/closed_forms_general/C0_C5/expected.json
OUT      ?= public/out
export OPENBLAS_NUM_THREADS := 1
export OMP_NUM_THREADS := 1

.PHONY: help test replay clean

help:            ## list the targets
	@grep -E '^[a-z-]+:.*##' public.mk | sed 's/:.*##/:/'

replay:          ## recompute the records and every quoted number from the shipped inputs (PASS/FAIL table)
	$(PY) -B public/replay.py --expected $(EXPECTED) --out $(OUT)

test:            ## replay plus the full Horn compiler and the remaining delivered checks
	$(PY) -B public/replay.py --full --expected $(EXPECTED) --out $(OUT)

clean:
	rm -rf $(OUT)
