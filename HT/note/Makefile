# HT note: make (PDF), make check (numbers and manifest), make numbers (regenerate the d = 1 macros and rows).
MAIN = lri_ht_finite_coupling
all: $(MAIN).pdf
$(MAIN).pdf: $(MAIN).tex sections/*.tex sections/d2/*.tex sections/d3/*.tex numbers_d1.tex figures/*.pdf
	latexmk -pdf -interaction=nonstopmode -halt-on-error $(MAIN).tex
numbers:
	python3 tools/gen_numbers_d1.py && python3 tools/gen_repro_d1.py
check:
	python3 tools/check_note.py
clean:
	latexmk -C $(MAIN).tex
.PHONY: all numbers check clean
