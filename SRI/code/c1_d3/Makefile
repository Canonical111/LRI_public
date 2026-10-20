# Public-release edit (2026-10-17): the note and code/workflow/build_pdf.py are not shipped; 'pdf' prints a pointer
# to the SRI note and 'all' no longer builds it. public/RE-PINNED.json records the original and published sha256.
PYTHON ?= python
.NOTPARALLEL:
.PHONY: all reproduce assets pdf check integrity smoke
all: reproduce check assets
reproduce:
	$(PYTHON) code/workflow/reproduce.py full --from-scratch
check:
	$(PYTHON) code/workflow/verify.py results
assets:
	$(PYTHON) code/workflow/make_assets.py
pdf:
	@echo "The package's note and its builder are not shipped; the derivation is the SRI note, Appendix G (make note-pdf in SRI/)."
integrity:
	$(PYTHON) code/workflow/verify.py integrity
smoke:
	$(PYTHON) code/workflow/reproduce.py smoke --output outputs/smoke_run
