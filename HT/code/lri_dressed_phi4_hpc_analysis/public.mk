# Public targets for HT/code/lri_dressed_phi4_hpc_analysis: the d = 1 finite-coupling HT analysis (cutoff fits,
# local exponent, held-out test, descendant identities, comparisons). The scripts and their inputs ship verbatim from
# the production analysis folder; public/ is added. HT note: "Results in one dimension" and the reproduction section.
# Run from this folder:  make -f public.mk test | replay | clean
#
#   test     public/selftest.py: the shipped fit code recovers synthetic limits, the local exponent is constant on a
#            power law, the comparison rules behave. A few seconds; Python >= 3.10, numpy, scipy.
#   replay   public/replay_ht1d.py: verifies the 1106 record envelopes under ../../data/HT_1d and binds them to
#            ../lri_dressed_phi4_hpc, rebuilds dens_v1_rows.json from the records, reruns the shipped dens_v1.py and
#            dens_v1_holdout.py unchanged on the rebuilt rows, and recomputes every quoted d = 1 number of
#            ../../results/HT_1d/quoted_numbers.json (PASS/FAIL table in $(WORK)/replay_ht1d.txt). About 1 min, one
#            core, < 1 GB.

PY      ?= python3
WORK    ?= .work
DATA    ?= ../../data/HT_1d
RESULTS ?= ../../results/HT_1d
CODE    ?= ../lri_dressed_phi4_hpc
export PYTHONDONTWRITEBYTECODE = 1
export OPENBLAS_NUM_THREADS = 1

.PHONY: test replay clean
test:
	$(PY) public/selftest.py

replay:
	$(PY) public/replay_ht1d.py --data $(DATA) --results $(RESULTS) --code $(CODE) --work $(WORK)

clean:
	rm -rf $(WORK)
