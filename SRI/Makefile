# Expansions about the short-range end (SRI/). Run from SRI/.
#
# Every package in code/<pkg>/ has a public.mk with at least `test` and `replay`. This file runs a target in every
# package, or in the ones you name, and adds the checks that span packages:
#
#   make test                  fast tests of every package (about 12 min on one node; indep_d1 4-5 min, integ_d1 about
#                              4 min, c2_cylinder_d2 about 3 min with the production suites)
#   make replay                every quoted number of the paper's Sec. 3.2 (the \SR* macros, eq:sr-closed, eq:sr-C8,
#                              tab:sr, the c_2 row of tab:htpert, the constants of the closed-forms appendix on c_2)
#                              from the shipped records (PASS/FAIL tables), then results/sr_values.json against the
#                              tree. About 17 min (c1_d3 reruns its workflow from scratch, 8-9 min; indep_d1 4 min;
#                              integ_d1 1.5 min).
#   make replay-full           the heavier reruns where a package has them (dual_d1: every compendium task including
#                              the C7 certificate, ~10 min, needs `make fetch-data`; c2_cylinder_d2: the continuum
#                              analysis from the raw records; c1_d3: the review-revision diagnostics; indep_d1 and
#                              integ_d1: print the production-rerun recipe). indep_d1's assembly from its raw run outputs is
#                              `make -C code/indep_d1 -f public.mk replay-raw RAW=<dir>` (raw outputs not hosted yet).
#   make fetch-data            the hosted inputs from the Zenodo data record (dual_d1: the 57 MB C7 certificate; indep_d1:
#                              its raw outputs, 31 MB tar.gz); URL_BASE=<url> for a mirror
#   make check-values          only results/sr_values.json against the tree
#   make replay PKG="dual_d1 c1_d3"     a subset of packages; `make list` lists them
#   make note                  check the note (note/tools/check_note.py); make note-pdf rebuilds the PDF in .work/
#
# A failing package does not stop the others; the run exits non-zero if any failed, and the summary lists them.
# PY selects the interpreter (default python3; Python >= 3.10 with numpy, scipy, mpmath; see requirements.txt).

PKGS := dual_d1 indep_d1 integ_d1 c2_closed_d2 c2_cylinder_d2 c1_d3 closure_d1
PKG  ?= $(PKGS)
PY   ?= python3
export PY

.PHONY: help list test replay replay-full fetch-data check-values note note-pdf
help:
	@sed -n '1,29p' Makefile

list:
	@printf '%s\n' $(PKGS)

test replay:
	@fail=""; for p in $(PKG); do \
	  echo "===== $$p: $@"; \
	  $(MAKE) -C code/$$p -f public.mk $@ PY=$(PY) || fail="$$fail $$p"; \
	done; \
	if [ "$@" = replay ]; then \
	  echo "===== values"; $(PY) verify/check_sr_values.py || fail="$$fail values"; \
	fi; \
	if [ -n "$$fail" ]; then echo "===== $@ FAILED in:$$fail"; exit 1; else echo "===== $@ passed"; fi

replay-full:
	@fail=""; for p in $(PKG); do \
	  if grep -q '^replay-full:' code/$$p/public.mk; then \
	    echo "===== $$p: replay-full"; $(MAKE) -C code/$$p -f public.mk replay-full PY=$(PY) || fail="$$fail $$p"; \
	  fi; \
	done; \
	if [ -n "$$fail" ]; then echo "===== replay-full FAILED in:$$fail"; exit 1; else echo "===== replay-full passed"; fi

fetch-data:
	@for p in $(PKG); do \
	  if grep -q '^fetch-data:' code/$$p/public.mk; then echo "===== $$p: fetch-data"; $(MAKE) -C code/$$p -f public.mk fetch-data PY=$(PY) || exit 1; fi; \
	done

check-values:
	$(PY) verify/check_sr_values.py

note:
	$(PY) note/tools/check_note.py

note-pdf:
	rm -rf .work/note && mkdir -p .work && cp -R note .work/note && cd .work/note && latexmk -pdf sri_short_range.tex
	@echo "built .work/note/sri_short_range.pdf"
