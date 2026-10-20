# GFF: the perturbative coefficients C0..C8 in d = 1, 2, 3. Run from GFF/.
#
# Every package in code/<pkg>/ has a public.mk with at least `test` and `replay`; its own Makefile, if any, is the
# verbatim production one and is not used here. This file runs a target in every package, or in the ones you name:
#
#   make test                      fast tests of every package
#   make replay                    recompute every quoted number from the shipped records and compare (PASS/FAIL)
#   make replay PKG="LRI_C8_HPC LRI_C7_HPC"
#   make list                      the packages
#   make note                      check the shipped note (tools/check_note.py --checksums)
#   make note-pdf                  rebuild the PDF from the TeX in .work/note/ (needs latexmk); the shipped PDF is untouched
#
# Each package's own targets (smoke, replay-full, fetch-data, ...) are listed by `make -C code/<pkg> -f public.mk help`
# where it has a help target, and described in code/<pkg>/public/README.md. A failing package does not stop the
# others; the run exits non-zero if any failed, and the summary lists them.

PKGS := $(patsubst code/%/public.mk,%,$(wildcard code/*/public.mk))
PKG  ?= $(PKGS)

.PHONY: help list test replay note note-pdf
help:
	@sed -n '1,17p' Makefile

list:
	@printf '%s\n' $(PKGS)

test replay:
	@fail=""; for p in $(PKG); do \
	  echo "===== $$p: $@"; \
	  $(MAKE) -C code/$$p -f public.mk $@ || fail="$$fail $$p"; \
	done; \
	if [ -n "$$fail" ]; then echo "===== $@ FAILED in:$$fail"; exit 1; else echo "===== $@ passed in all $(words $(PKG)) packages"; fi

note:
	cd note && python3 tools/check_note.py --checksums

note-pdf:
	rm -rf .work/note && mkdir -p .work && cp -R note .work/note && $(MAKE) -C .work/note all
	@echo "built .work/note/long_range_ising_condensed.pdf"
