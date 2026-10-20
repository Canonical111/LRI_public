# Public targets for GFF/code/LRI_C6_closed_form_review (independent review of the C6(1) analytic representation).
# Run from this folder:  make -f public.mk test | replay | rerun | clean
# The review has no Makefile of its own. It reads the package records of ../C6_research_note and the quoted
# numbers in ../../results/C6_1/analytic/quoted_numbers.json; nothing in checks/ is written.
#
# Runtimes (one core, memory < 2 GB):
#   test    a few seconds  every script compiles; recorded outputs present
#   replay  a few seconds  the review's agreements recomputed from its recorded outputs (+ c6_repair.py, 30 digits)
#   rerun   10-25 min      fresh execution of all 49 check commands in .work/checks (personal desktop, 1 core; needs
#                          numpy and scipy), then the same replay on the fresh outputs

PY        ?= python3
WORK      ?= .work
QUOTED    ?= ../../results/C6_1/analytic/quoted_numbers.json
REASSEMBLY ?= ../C6_research_note/outputs/reassembly.json

VERIFY = $(PY) public/verify_review.py --work $(WORK) --quoted $(QUOTED) --reassembly $(REASSEMBLY)

.PHONY: test replay rerun clean

test:
	$(VERIFY) test

replay:
	$(VERIFY) replay

rerun:
	C6_REASSEMBLY=$(abspath $(REASSEMBLY)) $(PY) public/rerun_checks.py $(WORK)
	$(VERIFY) replay --records $(WORK)/checks --name rerun_report

clean:
	rm -rf $(WORK)
