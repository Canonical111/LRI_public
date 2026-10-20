# Public targets of lri_d3_matrix_update (rank-two, Jack alpha=2, identification of the d=3 Horn functions).
# Added for the public release; the package itself has no Makefile. GFF/Makefile runs
#     make -C code/lri_d3_matrix_update -f public.mk <target>
# Every target runs the package's original scripts unchanged in a copy under $(WORK) (git-ignored) and writes
# $(WORK)/REPLAY.md, a PASS/FAIL table; a FAIL exits non-zero. Nothing outside $(WORK) is written.
# Needs Python 3 with mpmath 1.3.0 and SymPy (public/requirements.txt). One core, well under 1 GB of memory.

PY      ?= python3
WORK    ?= .work
RESULTS ?= ../../results/closed_forms_3

.PHONY: test replay search clean help

help:    ## list the targets
	@grep -E '^[a-z]+:.*##' public.mk | sed 's/:.*##/:/'

test:    ## checksums, rerun of rank_two_checks.py (1107 exact checks, 90-digit partial sums), record checks: about 5 s
	$(PY) public/replay.py --tier test --work $(WORK) --results $(RESULTS)

replay:  ## test, plus a rerun of recompute_d3_periods.py (Q_3, P_4(3), P_5(3) at 100 digits, about 30 s), compared with the record and the note
	$(PY) public/replay.py --tier replay --work $(WORK) --results $(RESULTS)

search:  ## optional: rerun of the bounded 6479-entry scalar catalogue search quoted in note Section 19 (about 1 min)
	$(PY) public/replay.py --tier search --work $(WORK) --results $(RESULTS)

clean:   ## remove the work copy and its outputs
	rm -rf $(WORK)
