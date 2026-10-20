# Public targets of lri_C6_d2_complete_update: the analytic d = 2 power-sector compensation of C6(2) and the finite-scheme
# audits (note Secs 24.1-24.3, 25.1-25.3). The package is a subset of bundle package 21 of LRI_complete_research_bundle.zip,
# shipped as delivered. Run from this folder: make -f public.mk <target>.
# Paths are relative. Shipped files are never modified: the delivered scripts write next to themselves, so every target
# runs them in a writable copy under public/out/.
#
#   test        integrity (SHA256SUMS.json) and the three fastest checks: two-loop jets, fixed-point identities, kite
#               normalization (about 3 s; any machine; Python >= 3.8 with mpmath, sympy, networkx; no compiler)
#   replay      every number the note quotes from these records, by rerunning the delivered scripts on the saved
#               counterterms and comparing field by field (about 10 s; same requirements)
#   regen       regenerate the counterterms of all power-containing graphs from the graph inventory, with the shipped kite
#               cache, then recompute Delta_p (about 4 min; same requirements, 4 processes)
#   regen-cold  the same with the kite cache deleted (the 164 kite jets recomputed; about 6-7 min on symmetry, 4 processes)

PY      ?= python3
RESULTS ?= ../../results/C6_2/power_compensation
C6      ?= ../../results/C6_2/C6_result.json
C7      ?= ../../results/C7_2/C7_result.json
HPC     ?= ../LRI_C6_D2_HPC
OUT     ?= public/out

.PHONY: help test replay regen regen-cold clean

help:            ## list the targets
	@grep -E '^[a-z-]+:.*##' public.mk | sed 's/:.*##/:/'

test:            ## SHA256SUMS.json binding and three fast reruns (two-loop jets, fixed point, kite normalization)
	$(PY) -B public/test.py --results $(RESULTS) --out $(OUT)

replay:          ## recompute every quoted number from the saved counterterms and compare (PASS/FAIL table)
	$(PY) -B public/replay.py --results $(RESULTS) --c6 $(C6) --c7 $(C7) --hpc $(HPC) --out $(OUT)

regen:           ## regenerate all power-sector counterterms (warm kite cache) and recompute Delta_p
	$(PY) -B public/regen.py --results $(RESULTS) --out $(OUT)

regen-cold:      ## the same, recomputing the kite jets too
	$(PY) -B public/regen.py --results $(RESULTS) --out $(OUT) --cold

clean:
	rm -rf $(OUT)
