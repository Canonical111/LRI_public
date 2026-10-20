# Public targets of lri_d3_reduction_update (d=3 half-shift determinant reduction of the primitive periods).
# Added for the public release; the package itself has no Makefile. GFF/Makefile runs
#     make -C code/lri_d3_reduction_update -f public.mk <target>
# Every target runs the package's original scripts unchanged in a copy under $(WORK) (git-ignored) and writes
# $(WORK)/REPLAY.md, a PASS/FAIL table; a FAIL exits non-zero. Nothing outside $(WORK) is written.
# Needs Python 3 with mpmath 1.3.0 and SymPy (public/requirements.txt). One core, well under 1 GB of memory.

PY      ?= python3
WORK    ?= .work
RESULTS ?= ../../results/closed_forms_3

.PHONY: test replay clean help

help:    ## list the targets
	@grep -E '^[a-z]+:.*##' public.mk | sed 's/:.*##/:/'

test:    ## checksums, rerun of check_exact.py (exact algebra and Horn arrays), record checks against the note: about 5 s
	$(PY) public/replay.py --tier test --work $(WORK) --results $(RESULTS)

replay:  ## test, plus reruns of verify_d3.py (about 80 s) and check_spectral.py (about 160 s), compared with the records and the note
	$(PY) public/replay.py --tier replay --work $(WORK) --results $(RESULTS)

clean:   ## remove the work copy and its outputs
	rm -rf $(WORK)
