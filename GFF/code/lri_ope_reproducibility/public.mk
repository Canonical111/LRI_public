# Public targets for GFF/code/lri_ope_reproducibility (bulk one-point coefficient a_phi2 through eps^6).
# Run from this folder:  make -f public.mk test | replay | full | clean
# The package ships verbatim except the three files listed in DROPPED of public/replay_ope.py (MANIFEST.sha256 still
# lists them); every target writes only under $(WORK).
# Python >= 3.11 with requirements.txt (mpmath 1.3.0, sympy 1.14.0, numpy 2.3.5, scipy 1.17.0, matplotlib 3.10.8).
#
# Runtimes (one core of an Intel Xeon Gold 6148 node of symmetry; memory < 2 GB):
#   test    about 10 s     manifest check and the package's "quick" task into $(WORK)/quick
#   replay  minutes        "quick" if needed, then every check of Section 34 in ../ope_checks/<d1,d2,d3>/commands.json
#   full    about 9 min    the package's symbolic, numeric (d = 1, 60 digits, about 5 min), integrals, masters and
#                          figures tasks into $(WORK)/full
# The package's note (note/lri_ope_note.tex) is merged into the condensed note GFF/note (Section 34) and not shipped.

PY      ?= python3
WORK    ?= .work
CHECKS  ?= ../ope_checks

.PHONY: test replay full clean

test:
	$(PY) -I public/replay_ope.py test --work $(WORK)

replay:
	$(PY) -I public/replay_ope.py replay --work $(WORK) --checks $(CHECKS)

full:
	mkdir -p $(WORK)/full
	$(PY) -I run.py symbolic numeric integrals masters figures --output-dir $(abspath $(WORK))/full

clean:
	rm -rf $(WORK)
