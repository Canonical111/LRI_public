# HT_Pert note: make (PDF), make numbers (regenerate the d = 1 macros and rows), make check (read-only consistency).
MAIN = lri_ht_perturbative
all: $(MAIN).pdf
$(MAIN).pdf: $(MAIN).tex sections/*.tex $(wildcard sections/d2/*) $(wildcard sections/d3/*) numbers_d1.tex
	latexmk -pdf -interaction=nonstopmode -halt-on-error $(MAIN).tex
numbers:
	python3 tools/gen_numbers_d1.py && python3 tools/gen_repro_d1.py
check:
	python3 -B tools/check_note.py --checksums
clean:
	latexmk -C $(MAIN).tex
.PHONY: all numbers check clean
