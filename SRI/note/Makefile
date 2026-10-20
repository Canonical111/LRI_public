# SRI note: make (PDF, with SyncTeX), make check (read-only checks), make strict (check, and fail on open TODOs).
MAIN = sri_short_range
all: $(MAIN).pdf
$(MAIN).pdf: $(MAIN).tex
	latexmk -pdf -synctex=1 -interaction=nonstopmode -halt-on-error $(MAIN).tex
check:
	python3 -B tools/check_note.py
strict:
	python3 -B tools/check_note.py --strict
.PHONY: all check strict
