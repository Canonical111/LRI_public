# Public targets for SRI/code/c2_cylinder_d2: c_2 in d = 2 from fourth-order perturbation theory with the truncated
# cylinder Hamiltonian (short-range Ising CFT x generalized free field), extrapolated to N -> infinity and lambda -> 0.
# The repository LRI_C2_expanse ships at commit 98e1935 (its tracked files) with its cluster records under outputs/
# (dated snapshot public/SNAPSHOT.sha256); public/ and this file are added.
# Run from this folder:  make -f public.mk test | replay | replay-full | clean
#
#   test         public/selftest_c2cyl.py (MANIFEST.sha256 of the pruned export, the records snapshot, the closed form)
#                and public/run_suites.py (the package's own suites: test_continuum, test_cluster, test_sitekit,
#                test_expanse, test_symmetry; no git history, no scheduler; stated skips only). About 3 min, one core.
#   replay       public/replay_c2cyl.py: from the shipped result generation, the per-order regulator fits, the joint fit,
#                every error component, E and C2 +- dC2 (verbatim functions and an independent refit), compared with
#                C2_estimate.json and with \SRtwoCtwoHT, \SRtwoCtwoHTDev, \SRtwoCtwoHTNmax (note only) and the c_2 row of tab:htpert.
#                Seconds.
#   replay-full  public/replay_full_c2cyl.py: reruns `scripts/run.py continuum -- run ...` on the 16 production, 25
#                extraction-check and 17 archived records and the auxiliary-input job, and compares every output leaf
#                with the shipped generation (tiered tolerances; bit-identical on the production platform). Seconds.
# Python >= 3.10 with numpy, scipy, mpmath, sympy, matplotlib (requirements.txt; production versions in
# requirements-tested.txt). Production reruns (cluster grids and rows): cluster/README.md, cluster/sitekit/README.md.

PY      ?= python3
WORK    ?= .work
export PYTHONDONTWRITEBYTECODE = 1
export OPENBLAS_NUM_THREADS = 1
export OMP_NUM_THREADS = 1

.PHONY: help test replay replay-full clean
help:
	@sed -n '1,20p' public.mk

test:
	$(PY) public/selftest_c2cyl.py --out $(WORK)/selftest_c2cyl.txt
	$(PY) public/run_suites.py --python $(PY) --work $(WORK)/suites --out $(WORK)/run_suites.txt

replay:
	$(PY) public/replay_c2cyl.py --out $(WORK)/replay_c2cyl.txt

replay-full:
	$(PY) public/replay_full_c2cyl.py --python $(PY) --work $(WORK)/replay_full --out $(WORK)/replay_full_c2cyl.txt

clean:
	rm -rf $(WORK)
