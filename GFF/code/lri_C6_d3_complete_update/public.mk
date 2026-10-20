# Public targets of lri_C6_d3_complete_update (d=3 power-sector compensation of C6(3) and the d=3 finite-scheme
# inputs). Added for the public release; the package itself has no Makefile. GFF/Makefile runs
#     make -C code/lri_C6_d3_complete_update -f public.mk <target>
# Every target runs the package's original scripts unchanged in a copy under $(WORK) (git-ignored) and writes
# $(WORK)/REPLAY.md, a PASS/FAIL table; a FAIL exits non-zero. Nothing outside $(WORK) is written.
# Needs Python 3 with mpmath 1.3.0, SymPy, NumPy and networkx (public/requirements.txt). One core, under 1 GB.
# No compiler is needed: the C++ sampler of the superseded first-full-C6(3) run is not part of the release.

PY      ?= python3
WORK    ?= .work
RESULTS ?= ../../results/C6_3

.PHONY: test replay clean help

help:    ## list the targets
	@grep -E '^[a-z]+:.*##' public.mk | sed 's/:.*##/:/'

test:    ## checksums, reruns of the seven light audits (Lagrange, unknown core, delta R, Gamma jets, two-loop jets, core propagation, coverage), record checks: about 10 s
	$(PY) public/replay.py --tier test --work $(WORK) --results $(RESULTS)

replay:  ## test, plus the three graph-recursion power audits (power_ms_d3.py at 75, 90, 65 digits) and analyze_power.py: about 2 min
	$(PY) public/replay.py --tier replay --work $(WORK) --results $(RESULTS)

clean:   ## remove the work copy and its outputs
	rm -rf $(WORK)
