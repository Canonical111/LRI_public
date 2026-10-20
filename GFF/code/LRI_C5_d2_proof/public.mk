# Public targets of LRI_C5_d2_proof: the proofs of the d = 2 closed forms L2 = -2 log2 P4(2) and
# K2 = 32 G^2 - 28 zeta(3) log2 (all five proofs are written out in note Section 18; their md write-ups are merged
# into the note and not shipped),
# with their machine checks and the check computations behind the numbers the note quotes. Plain folder, shipped as it
# was on 2026-10-02.
# Run from this folder: make -f public.mk <target>.
# Paths are relative. Shipped files are never modified. Every shipped script runs in a work copy under public/out/work/,
# where public/cf2common.py maps the hard-coded research-tree prefix to GFF/code. Inputs from the sibling package
# ../LRI_C5_d2_simplify (confirm_dps70.json, L2_factorized.json) and ../LRI_C5_d3/wf_d2check (optional checks) are read
# there.
#
#   test       the exact machine checks the note cites (verify_symbolic.py, region_sum_matrix.py, laurent_K2_sympy.py)
#              and drafter/check_algebra.py (about 12 s; Python >= 3.10 with sympy 1.11.1 and mpmath >= 1.2.1)
#   replay     test, plus the numerical checks re-run from shipped inputs (elliptic cross-check at 75 digits, the W4(2;2x)
#              spectral tail fit, the 3F2 value at tau = 3/10) and every other check number the note quotes, read from the
#              shipped check outputs (about 30 s; same requirements)
#   replay-wl  optional: the Mathematica checks (laurent_K2.wl cited by the note, check_series.wl, ...), result lines
#              compared with the shipped outputs (needs wolframscript; minutes; s3_modes.wl hours)
#   checks     optional: the other numerical checks the proofs cite, each in a work copy, compared with the shipped
#              outputs where they exist (minutes to an hour; one node)

PY  ?= python3
OUT ?= public/out

.PHONY: help test replay replay-wl checks clean

help:            ## list the targets
	@grep -E '^[a-z0-9-]+:.*##' public.mk | sed 's/:.*##/:/'

test:            ## exact machine checks (about 12 s)
	$(PY) -B public/replay.py --test --out $(OUT)

replay:          ## every check number the note quotes for the proofs (PASS/FAIL table, public/out/replay.json)
	$(PY) -B public/replay.py --out $(OUT)

replay-wl:       ## optional Mathematica checks (wolframscript)
	$(PY) -B public/replay_wl.py

checks:          ## optional numerical checks cited by the proofs (outputs in public/out/work/<script>/)
	$(PY) -B public/cf2common.py run L2_singlesums/verify_numeric.py 40
	for s in numcheck_moments numcheck_moments2 numcheck_K2_fit check_telescoper selberg_frames numcheck_spectral; do \
	  $(PY) -B public/cf2common.py run K2_selberg/$$s.py || exit 1; done
	for s in check_klt_mp check_residues_mp check_routeA_chain_mp; do \
	  $(PY) -B public/cf2common.py run K2_d1template/$$s.py || exit 1; done
	$(PY) -B public/cf2common.py run K2_d1template_fix1/check_boundary_values_mp.py
	$(PY) -B public/cf2common.py run K2_gauss/rowspace.py
	$(PY) -B public/cf2common.py run K2_gauss/pslq_singles.py

clean:
	rm -rf $(OUT)
