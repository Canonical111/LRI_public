# Public targets for SRI/code/c1_d3: c_1 in d = 3 at the short-range Ising end,
# Delta_eps = Delta_eps^SR + c_1 delta + O(delta^2), delta = (s_* - s)/2, from the retained 60-primary spectrum of the
# 3d Ising CFT (c_1 = a0/b0 = 0.273152), with its conditional working range [0.269, 0.276] (gaps 8 even, 7 odd).
# Everything outside public/ and public.mk ships verbatim (dated snapshot 2026-10-08; public/SNAPSHOT.sha256).
# Run from this folder:  make -f public.mk test | replay | replay-full | clean
#
#   test         public/selftest_c1_d3.py: snapshot and the authors' delivery list (SHA256SUMS, subset mode); the
#                package's smoke profile in a copy (a0, b0, C1 against outputs/reference, 5e-10; block checks); the
#                revision guards (python -O). About 1 min.
#   replay       public/replay_c1_d3.py: the package's full 20-stage workflow from scratch in a copy (about 8 min),
#                its 23 regression checks, every output against the shipped full run, current_summary.json and the
#                tables regenerated, and \SRthreeCone, \SRthreeConeRange, \SRthreeConeBRRZ (cited), the d = 3 row of
#                tab:sr against ../../results/quoted_numbers.json, and the note-only \SRthreeConeImplDev, "two
#                independent implementations agree to 10^{-12}" (review_indep/: the review's two re-implementations rerun,
#                each within 1e-12 of the package (PASS/FAIL); their agreement, a bound, is an INFO row).
#   replay-full  public/replay_full_c1_d3.py: the review-revision diagnostics (central inputs infeasible in the
#                nominal LP; 11 gap/padding and 8 input-box scenarios; sensitivity tables). About 25 min.
# One core; Python >= 3.10 with numpy, scipy, mpmath, threadpoolctl, matplotlib, sympy
# (SRI/docs/c1_d3/requirements_c1_d3.txt; reproduction guide SRI/docs/c1_d3/REPRODUCE_c1_d3.md).

PY      ?= python3
WORK    ?= .work
export PYTHONDONTWRITEBYTECODE = 1
export OPENBLAS_NUM_THREADS = 1

.PHONY: help test replay replay-full clean
help:
	@sed -n '1,21p' public.mk

test:
	$(PY) public/selftest_c1_d3.py --work $(WORK)

replay:
	$(PY) public/replay_c1_d3.py --work $(WORK)

replay-full:
	$(PY) public/replay_full_c1_d3.py --work $(WORK)

clean:
	rm -rf $(WORK)
