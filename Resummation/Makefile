# Resummation and comparison. Run from Resummation/.
#
# Every package in code/<pkg>/ has a public.mk with at least `test` and `replay`. This file runs a target in every
# package, or in the ones you name, and adds the checks that span packages:
#
#   make test                  fast tests of every package (about 1 min in total on one core)
#   make replay                every quoted number of the paper's sections "Resummation" and "Comparison" and every
#                              cell of tab:num1-3 taken from this folder (resummed column; d = 2, 3 HT and d = 2 MC
#                              columns) from the shipped records (PASS/FAIL tables), the CSV data behind the
#                              two comparison figures, and the frozen inputs against the sibling folders. About 1 min.
#   make replay-full           reruns the resummations themselves (resum_d1: the chain, about 2 min; resum_d23: all
#                              scripts, about 1 min) and compares every output with the shipped one
#   make check-inputs          only the frozen inputs and input values against the live sibling folders (GFF, HT, NRG,
#                              MC); SKIP where a sibling folder is absent
#   make figure-data           only the CSV behind the figures (results/figures/*.csv)
#   make figures               rebuild the two figure PDFs with Wolfram Language (wolframscript + TeX; desktop only)
#   make replay PKG="resum_d1 comparison"     a subset of packages; `make list` lists them
#   make note                  check the note's shipped files (note/MANIFEST.json); make note-pdf rebuilds the PDF in .work/
#
# A failing package does not stop the others; the run exits non-zero if any failed, and the summary lists them.
# PY selects the interpreter (default python3; Python >= 3.10 with numpy, scipy, mpmath, matplotlib, sympy).

PKGS := resum_d1 resum_d23 instanton comparison
PKG  ?= $(PKGS)
PY   ?= python3
export PY

.PHONY: help list test replay replay-full check-inputs figure-data figures note note-pdf
help:
	@sed -n '1,22p' Makefile

list:
	@printf '%s\n' $(PKGS)

test replay:
	@fail=""; for p in $(PKG); do \
	  echo "===== $$p: $@"; \
	  $(MAKE) -C code/$$p -f public.mk $@ PY=$(PY) || fail="$$fail $$p"; \
	done; \
	if [ "$@" = replay ]; then \
	  echo "===== figure data"; $(PY) verify/figure_data.py --check || fail="$$fail figure-data"; \
	  echo "===== inputs"; $(PY) verify/check_inputs.py || fail="$$fail inputs"; \
	fi; \
	if [ -n "$$fail" ]; then echo "===== $@ FAILED in:$$fail"; exit 1; else echo "===== $@ passed"; fi

replay-full:
	@fail=""; for p in resum_d1 resum_d23; do \
	  echo "===== $$p: replay-full"; $(MAKE) -C code/$$p -f public.mk replay-full PY=$(PY) || fail="$$fail $$p"; \
	done; \
	if [ -n "$$fail" ]; then echo "===== replay-full FAILED in:$$fail"; exit 1; else echo "===== replay-full passed"; fi

check-inputs:
	$(PY) verify/check_inputs.py

figure-data:
	$(PY) verify/figure_data.py --check

figures:
	$(MAKE) -C code/resum_d1 -f public.mk figures
	$(MAKE) -C code/resum_d23 -f public.mk figures

note:
	$(PY) note/tools/check_note.py

note-pdf:
	rm -rf .work/note && mkdir -p .work && cp -R note .work/note && cd .work/note && latexmk -pdf lri_resummation.tex
	@echo "built .work/note/lri_resummation.pdf"
