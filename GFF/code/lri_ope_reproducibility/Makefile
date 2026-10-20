PYTHON ?= python

.PHONY: all quick symbolic numeric integrals masters figures note standalone integrity manifest
all quick symbolic numeric integrals masters figures note manifest:
	$(PYTHON) run.py $@
standalone:
	$(PYTHON) scripts/check_standalone_note.py
integrity:
	$(PYTHON) scripts/check_manifest.py
