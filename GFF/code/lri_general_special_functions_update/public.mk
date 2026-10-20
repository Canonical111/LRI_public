# Public targets of lri_general_special_functions_update: the general-dimensional C0..C5 (note Sections 12-13), as
# delivered in LRI_complete_research_bundle.zip (sha256 3715f545...). Run from this folder: make -f public.mk <target>.
# Paths are relative. Shipped files are never modified; the delivered scripts write their records in place, so every
# rerun happens in a copy under public/out/work/.
#
#   replay  the exact fixed-point assembly (SymPy), the C0..C5 values at d=1,2,3 from the saved masters (mpmath) and the
#           C1..C3 Lagrange inversion, compared with the delivered records; the note's general formulas compared
#           symbolically; every quoted number at its printed digits; cross-checks with the d=2, d=3 and d=1 units
#           (about 5 s, one core; Python >= 3.10 with numpy, scipy, sympy, mpmath; macOS or Linux)
#   test    replay, then a full regeneration in a second copy: graph reduction (collect.py, about 1 min), masters
#           (spectral_evaluate.py), reassembly, and every other delivered check (about 2.5 min, one core, < 1 GB)

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

test:            ## replay plus regeneration of all inputs and the remaining delivered checks
	$(PY) -B public/replay.py --full --expected $(EXPECTED) --out $(OUT)

clean:
	rm -rf $(OUT)
