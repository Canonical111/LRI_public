# Public targets of lri_general_periodization_update: finite periodization of the primitive sector and the d=2
# factorization of P4(2), P5(2) (note Sections 15.1-15.5), as delivered in LRI_complete_research_bundle.zip
# (sha256 3715f545...). Run from this folder: make -f public.mk <target>. Paths are relative. Shipped files are never
# modified; the delivered scripts write their records in place, so every rerun happens in a copy under public/out/work/.
#
#   replay  integrity (SOURCE_SHA256SUMS; archive_manifest.json with ignore-missing); reruns the exact algebra, the d=2
#           factorization chain (55, 70 and 60 digits), the Horn templates and their check, compared with the delivered
#           records; P4(2), P5(2) and the B7 vector quoted in the note and the paper; cross-checks of the d=2 closed
#           forms (about 10 s, one core; Python >= 3.10 with numpy, scipy, sympy, mpmath; macOS or Linux)
#   test    replay plus check_wheel_periodization.py (35-digit Barnes integrals, about 45 s) and
#           check_p5_periodization.py (about 5 s)

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

test:            ## replay plus the remaining delivered checks
	$(PY) -B public/replay.py --full --expected $(EXPECTED) --out $(OUT)

clean:
	rm -rf $(OUT)
