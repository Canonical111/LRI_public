# Public targets for SRI/code/c2_closed_d2: c_2 in d = 2 (Delta_eps = 1 + c_2 delta^2, delta = (7/4 - s)/2).
# The closed-form study (README.md, code/, inputs/, outputs/, provenance/, MANIFEST.json; its note is not shipped, see
# public/NOT_SHIPPED.txt and the SRI note, App. E) and the review's
# end-to-end Monte Carlo (mc/) ship verbatim (dated snapshot, public/SNAPSHOT.sha256); public/ and this file are added.
# Run from this folder:  make -f public.mk test | replay | rerun-mc-smoke | mc-batch-check | clean
#
#   test     public/selftest_c2.py: snapshot sha256, the study's own MANIFEST.json, the closed form at 50 digits,
#            the verbatim three-4F3 evaluator rerun (byte-identical output), the MC chunk inventory and its
#            recombination (-4.075 +- 0.019). Seconds.
#   replay   public/replay_c2.py: the study's eight-stage runner in a copy (about 1 min; outputs compared with the
#            shipped ones), every constant of the appendix subsection cf:sec:cr2 at 50 digits, the verbatim summ.py on
#            the Monte Carlo chunks against the production logs, the recombination, \SRtwoCtwo, \SRtwoCtwoMC and the
#            d = 2 row of tab:sr. About 1 min on one core; Python >= 3.10, mpmath, sympy, numpy, scipy, matplotlib.
#   rerun-mc-smoke  builds mc/c2mc3.c in .work/ (gcc with libquadmath) and runs one short chunk (2e6 samples,
#            under a minute): a check that the code builds and runs.
#   mc-batch-check  public/mc_batch_check.py: builds mc/c2mc3.c with the production flags and reruns batch 0 of
#            chunk 1 of configuration A (1.5e7 samples, about 3 min, x86-64-v3 CPU); its three histogram lines must
#            match mc/run_A/out_1.txt. The production rerun (4.26e10 samples, about 135 core-hours) is described in
#            REPRODUCE_c2_closed_d2.md.

PY      ?= python3
MCC     ?= gcc
WORK    ?= .work
export PYTHONDONTWRITEBYTECODE = 1
export OPENBLAS_NUM_THREADS = 1
export MPLBACKEND = Agg

.PHONY: help test replay rerun-mc-smoke mc-batch-check clean
help:
	@sed -n '1,20p' public.mk

test:
	$(PY) public/selftest_c2.py

replay:
	$(PY) public/replay_c2.py --work $(WORK)

rerun-mc-smoke:
	mkdir -p $(WORK)/mc_smoke
	$(MCC) -O2 -w -DUSE_QUAD -o $(WORK)/mc_smoke/c2mc3 mc/c2mc3.c -lquadmath -lm
	cd $(WORK)/mc_smoke && LMIN=-16 ERRTOL=1e-2 KAP=0.35 NBATCH=20 ALPHAFILE=$(CURDIR)/mc/alpha_e0.05_L16_k35.txt \
	  ./c2mc3 0.05 2000000 1001 > out_smoke.txt && head -2 out_smoke.txt

mc-batch-check:
	$(PY) public/mc_batch_check.py --work $(WORK) --cc $(MCC)

clean:
	rm -rf $(WORK)
