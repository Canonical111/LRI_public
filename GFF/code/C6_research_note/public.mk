# Public targets for GFF/code/C6_research_note (analytic representation of C6(1)).
# Run from this folder:  make -f public.mk test | replay | rerun-final | clean
# The delivered package has no Makefile; its own entry points are code/reproduce_final.py and
# code/make_outputs.py (README.md). Every target below works on a copy under $(WORK); the shipped
# files, which MANIFEST.sha256 binds, are never written.
#
# Runtimes (one core, measured on the delivering sandbox and on a loaded Mac; memory < 1 GB):
#   test         about 3-30 s    integrity of checksum lists, provenance hashes and run records,
#                                plus three exact stage tasks in a scratch copy
#   replay       about 2-40 s    reassembly from the shipped run records and every quoted number
#   rerun-final  about 2-4 min   fresh run of the 22 final-method tasks, then the comparison (personal desktop, 1 core)
# The package's own note (note/C6_progress_note.tex) is merged into the condensed note GFF/note and not shipped.

PY        ?= python3
WORK      ?= .work
QUOTED    ?= ../../results/C6_1/analytic/quoted_numbers.json
# Graph-sum record of LRI_C6_1D_HPC (C6_final.json). Empty: try ../../results/C6_1/C6_final.json and
# ../LRI_C6_1D_HPC/results/2026-09_symmetry/C6_final.json, else use the pinned value (reported as SKIP).
GRAPH_SUM ?=
TIMEOUT   ?= 900

VERIFY = $(PY) public/verify_c6_analytic.py --work $(WORK)

.PHONY: test replay rerun-final clean

test:
	$(VERIFY) test

replay:
	$(VERIFY) replay --quoted $(QUOTED) $(if $(GRAPH_SUM),--graph-sum $(GRAPH_SUM))

rerun-final:
	$(VERIFY) prepare-rerun
	cd $(WORK)/rerun/pkg && $(PY) code/reproduce_final.py --timeout $(TIMEOUT) && $(PY) code/make_outputs.py
	$(VERIFY) compare-rerun

clean:
	rm -rf $(WORK)
