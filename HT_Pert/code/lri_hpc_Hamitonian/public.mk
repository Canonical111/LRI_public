# Public targets for HT_Pert/code/lri_hpc_Hamitonian: the d = 1 frozen-cutoff perturbative HT solver lri_hpc 1.0.0
# (source fingerprint c0c30783db5dd9a1..., Expanse production 2026-09-29..10-01) and its analysis (joint tail fits,
# complete vacuum window through eps^5, descendant identities, cutoff-placement test). Shipped verbatim at commit
# c55d134; public.mk and public/ are added. Records: ../../data/HT_1d/thermal_expanse (111 Expanse records).
# Needs the sibling package ../lri_eh_hpc (lri_eh: K and the exact g^2 D shift; on PYTHONPATH of the re-pointed copy).
# The analysis scripts name the analysis session's absolute paths; public/repoint.py runs them on a re-pointed copy in
# $(WORK)/tree (the shipped files are never modified).
# Run from this folder:  make -f public.mk test | replay | smoke | replay-full | fetch-data | clean
#
#   test         public/run_tests.py: analysis/extended/check_identity.py; public/engine_smokes.py (ht5.py 2 4,
#                htb5_exact.py 16, topsum.py 8 16 32 64 vs their records); tests/run_all.py (11 scripts) on a copy in
#                $(WORK)/pkg with GIT_SHA; the validation regression V (thermal d7 Lambda 40, 50, phi6 d5 50, d3 128 vs
#                validation_data/, cluster/expanse/check_regression.py). Needs >= 4 CPUs, < 2 GB.
#                About 140 s on symmetry (Xeon Gold 6148, 4 threads).
#   replay       public/replay_hpcham.py: every quoted number of the package (rows a1.*, results_map.md) from the
#                shipped records, with 16 analysis scripts rerun on the re-pointed copy plus public/omega3_eff.py and
#                public/engine_agree.py. About 25 s, < 1 GB.
#   smoke        public/smoke_hpcham.py: production items thermal d7 Lambda 52, 60, phi6 d5 52, phi6 d3 136 rerun and
#                compared with their records (1e-7 + 2e-11 |rec|). About 90 s on 4 threads (bitwise on symmetry), < 5 GB.
#   replay-full  public/replay_full_hpcham.py: top-level sums topsum.py at all 108 cutoffs 4..288 and the
#                independent engine ht5.py at Lambda 6..28 regenerated and compared with their records; shift4 limit
#                and engine agreement (iii) recomputed from them. About 30 min on 8 threads (970 + 815 s on symmetry).
#   fetch-data   nothing is hosted: every record of this package is in git.
# The production campaign (cluster/expanse/, about 1180 core-h, 2 TB nodes for thermal Lambda >= ~96) is documented
# in REPRODUCE, not run by any target.
PY      ?= python3
WORK    ?= .work
DATA    ?= ../../data/HT_1d
EH      ?= ../lri_eh_hpc
THREADS ?= 4
export PYTHONDONTWRITEBYTECODE = 1
export OPENBLAS_NUM_THREADS = 1
export MKL_NUM_THREADS = 1
export OMP_NUM_THREADS = 1
export NUMBA_CACHE_DIR ?= $(abspath $(WORK))/numba_cache

.PHONY: help test replay smoke replay-full fetch-data clean
help:
	@sed -n '1,25p' public.mk

test:
	$(PY) public/run_tests.py --work $(WORK) --threads $(THREADS)

replay:
	$(PY) public/replay_hpcham.py --data $(DATA) --eh $(EH) --work $(WORK)

smoke:
	$(PY) public/smoke_hpcham.py --data $(DATA) --work $(WORK) --threads $(THREADS)

replay-full:
	$(PY) public/replay_full_hpcham.py --work $(WORK) --threads $(THREADS)

fetch-data:
	@echo "lri_hpc_Hamitonian: nothing hosted yet, and nothing needed: the records are in git under $(DATA)/thermal_expanse"

clean:
	rm -rf $(WORK)
