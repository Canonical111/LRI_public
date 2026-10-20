# Public targets for HT_Pert/code/lri_d1_fullblock_tail_response: the cited check behind the caveat "a second channel
# with the leading power Lambda^{-1/2} enters at eps^4" (paper, Hamiltonian truncation section). The package is the
# OpenAI GPT-6 astra research bundle lri_d1_fullblock_tail_response (2026-10-07), shipped verbatim and bound by its own
# MANIFEST.sha256 (108 files); public/ is added. Its scripts rewrite results/, so every rerun uses a copy under $(WORK).
# Run from this folder:  make -f public.mk test | replay | replay-full | fetch-data | clean
#
#   test         public/run_tests_fb.py: MANIFEST.sha256 (SCRUBBED-aware) and the verbatim tests/verify_manifest.py on
#                the shipped tree; then, on a copy, tests/check_annulus.py, code/mixing_asymptotics.py,
#                tests/check_finite_response.py and tests/validate.py (x86-64 only: it needs 80-bit long double,
#                np.finfo(np.longdouble).nmant >= 63; SKIP with a message elsewhere). Seconds.
#   replay       public/replay_fb.py: rows fb.* of results_map.md (manifest, outer power, onset at eps^4, prefactor
#                arithmetic, B, the 36 annulus comparisons, two INFO rows); float reruns of the response records up
#                to low cutoff 16. About 15 s (13 s on symmetry Intel).
#   replay-full  the same with float reruns of all 13 full-J response records (low cutoff up to 28). About 3.5 min, one core.
#   fetch-data   nothing is hosted for this package.
# Tested 2026-10-14 on symmetry defq, job 574954 (Intel Xeon 6148, Python 3.12.9, numpy 2.3.5, scipy 1.17.1, sympy 1.14.0):
# test 6 PASS (16 s), replay 6 PASS 2 INFO (13 s), replay-full 6 PASS 2 INFO (209 s); on Apple arm64 validate.py SKIPs.
PY    ?= python3
WORK  ?= .work
DATA  ?= ../../data/HT_1d
export PYTHONDONTWRITEBYTECODE = 1
export OPENBLAS_NUM_THREADS = 1
export MKL_NUM_THREADS = 1
export OMP_NUM_THREADS = 1
export MPLBACKEND = Agg
export NUMBA_CACHE_DIR ?= $(WORK)/numba_cache

.PHONY: test replay replay-full fetch-data clean
test:
	$(PY) public/run_tests_fb.py --work $(WORK)

replay:
	$(PY) public/replay_fb.py --work $(WORK)

replay-full:
	$(PY) public/replay_fb.py --work $(WORK) --full

fetch-data:
	@echo "lri_d1_fullblock_tail_response: nothing is hosted; every input of test and replay is in this folder."

clean:
	rm -rf $(WORK)
