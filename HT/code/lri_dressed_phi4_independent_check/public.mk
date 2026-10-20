# Public targets for HT/code/lri_dressed_phi4_independent_check: the blind re-implementation of the d = 1 finite-coupling
# HT (written from the definition of the model without the production code; HT note section on
# independent checks). Shipped as written; public/ is added.
# Run from this folder:  make -f public.mk test | replay | smoke | clean
#
#   test     tests/test_indep_ht.py: 64 unit checks (free limit, Hermiticity, truncation-projection, DVR against an
#            oscillator basis, quartic-oscillator references, Hellmann-Feynman Jacobians against finite differences,
#            window fixed-point identities, ARPACK against dense). A few minutes, one core; numpy, scipy.
#   replay   public/replay_indep.py: rebuilds results/indep_results.json from results/raw_runs with the shipped
#            analyze.py, rebuilds the production reference from ../../data/HT_1d, and recomputes the agreement
#            (<= 5e-9) and the C2(N) check (<= 3e-7). About 10 s.
#   smoke    one point of the comparison, Ds = 0.2, N = 12, raw (task file tasks/), compared with its shipped result
#            to 1e-10. About 1-2 min, one core.

PY   ?= python3
WORK ?= .work
DATA ?= ../../data/HT_1d
export PYTHONDONTWRITEBYTECODE = 1
export OPENBLAS_NUM_THREADS = 1

.PHONY: test replay smoke clean
test:
	$(PY) tests/test_indep_ht.py

replay:
	$(PY) public/replay_indep.py --data $(DATA) --work $(WORK)

smoke:
	$(PY) public/smoke_indep.py --work $(WORK)

clean:
	rm -rf $(WORK)
