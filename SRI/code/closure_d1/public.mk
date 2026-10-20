# Public targets for SRI/code/closure_d1: finite checks of the two-coupling closure and prescription arguments for the
# d = 1 dual (OpenAI GPT-6 astra, supplied 2026-10-15; the arguments themselves are in the SRI note, appendix "The
# two-coupling closure and the prescription"). prescription/ holds the second argument's checker archive verbatim,
# without its note; public/ is added. Run from this folder:
#   make -f public.mk test | replay | clean
#
#   test      public/check_closure.py: the snapshot sha256; the closure argument's finite algebra (matrix-word charges
#             for all 29,523 words of length <= 9, the radial-power identity, the O_g O_g product); the prescription
#             archive's MANIFEST.json, its checker rerun (sympy), and an independent re-derivation of the beta
#             recurrence b3..b9, h4..h8. A few seconds.
#   replay    the same table (the package has no quoted number).
PY   ?= python3
WORK ?= .work
export PYTHONDONTWRITEBYTECODE = 1
.PHONY: help test replay clean
help:
	@sed -n '1,11p' public.mk
test replay:
	$(PY) public/check_closure.py
clean:
	rm -rf $(WORK)
