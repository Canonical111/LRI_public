# Public targets of LRI_C8_shared: the shared eighth-order inputs of the C8(2) and C8(3) calculations (note Sections 31,
# 32): the nine-vertex inventory and d = 2 payloads inventory/inventory8_d2/ (pinned by C8_H1_PIN = sha256 of its
# MANIFEST.json) and the d-general order-8 assembly assembly/ (vendored byte for byte by both packages).
# Run from this folder: make -f public.mk <target>. Nothing here is modified by any target.
#
#   test        check the pinned tree and the assembly handoff (seconds; Python only). Without the payload tars it checks
#               everything else and says the tars are missing; with them it also runs the tree's own verifier.
#   replay      the same as test: this package quotes no numbers of its own (GFF/Makefile calls replay everywhere)
#   verify      the tree's own verifier, all four steps (needs the four payload tars, 7.8 GB; about 1 min)
#   fetch-data  download the four payload tars from the paper's Zenodo record into inventory/inventory8_d2/payload/
#               (public/fetch.py, public/hosted.json; ../../data/C8_2/DATA.md, part a)

PY ?= python3
ZENODO ?= https://zenodo.org/records/23466766/files
C8_H1_PIN := 46341a3c0f11d74f0cf7c08cdd685d9cf073a142160de5a0ca408e021b4ff099

.PHONY: help test replay verify fetch-data

help:        ## list the targets
	@grep -E '^[a-z-]+:.*##' public.mk | sed 's/:.*##/:/'

test:        ## the pin, SHA256SUMS, every non-payload file, the assembly handoff
	$(PY) -B public/check.py

replay: test ## no quoted numbers here; checks the inputs as test does

verify:      ## inventory8_d2 against C8_H1_PIN, all four steps (payload tars required)
	$(PY) -B inventory/inventory8_d2/src/gen/verify_inventory.py inventory/inventory8_d2 --pin $(C8_H1_PIN)

fetch-data:  ## the four payload tars (7.8 GB) from the paper's Zenodo record, checked, placed in inventory/inventory8_d2/payload/
	$(PY) -B public/fetch.py --base $(ZENODO)
