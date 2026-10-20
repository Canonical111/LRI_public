.PHONY: all check clean
all:
	latexmk -pdf -interaction=nonstopmode -halt-on-error long_range_ising_condensed.tex
check:
	python tools/check_note.py
clean:
	latexmk -c long_range_ising_condensed.tex
