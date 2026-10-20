.PHONY: all baseline check regenerate
all: lri_combined_notes.pdf

lri_combined_notes.pdf: lri_combined_notes.tex preface.tex $(shell find parts -type f)
	latexmk -pdf -synctex=1 -interaction=nonstopmode -halt-on-error lri_combined_notes.tex
	python3 -c "import gzip; assert gzip.open('lri_combined_notes.synctex.gz','rb').read(16)"

baseline:
	python3 tools/build_standalone.py

check: all baseline
	python3 tools/check_combined.py

regenerate:
	python3 tools/build_combined.py --from-snapshot
