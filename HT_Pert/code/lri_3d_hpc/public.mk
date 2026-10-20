# Public targets of lri_3d_hpc (d = 3 perturbative Hamiltonian truncation: C_2..C_8 at finite level cutoff L).
# Run from this folder: make -f public.mk <target>   (HT_Pert/Makefile runs make -C code/lri_3d_hpc -f public.mk <target>).
# The package's own files ship unchanged at git ref 7c8a67e (cluster/RUNBOOK.md scrubbed, see public/SCRUBBED.txt);
# everything public-specific is in public/.
#
# replay needs Python >= 3.9 only. test needs Linux x86-64 (80-bit long double), a C++17 compiler with OpenMP and
# Python 3.12 with numpy, scipy, numba, threadpoolctl (public/requirements.txt; production: numpy 2.5.3, scipy 1.17.0,
# numba 0.68.0, g++ 13.3.0 on Expanse AMD EPYC 7742).
#
#   target      what                                                          measured runtime and node
#   replay      every quoted d = 3 number from the shipped records in         ~1 s, 1 core, any OS (standard library)
#               ../../data/HT_3d/pert3d and the table in ../../results/HT_3d
#               (public/replay_pert3d.py); PASS/FAIL table, exit 1 on FAIL
#   test        RELEASE_MANIFEST check, the package's checks, the L4 fixture  see public/REPRODUCE.md (symmetry runs)
#               at 1e-16, an L14 store built from scratch and solved at
#               L = 0..14 against the original code (public/run_tests.py);
#               MPIEXEC=<launcher taking -n N> adds the 2- and 4-rank tests
#   smoke       solve the shipped L4 fixture, consistent scheme, vs the       seconds
#               original code at 1e-16
#   fetch-data  nothing is hosted: prints what a production rerun rebuilds    instant
#   clean       remove .work/
PY      ?= python3
WORK    ?= .work
DATA    ?= ../../data/HT_3d
RESULTS ?= ../../results/HT_3d
# compiled kernel library: node-local, as in production (a parallel file system can refuse the atomic publish)
NATIVE  ?= $(or $(TMPDIR),/tmp)/lri_3d_hpc_native_$(shell id -u)

.PHONY: help replay test smoke fetch-data clean

help:        ## list the targets
	@grep -E '^[a-z-]+:.*##' public.mk | sed 's/:.*##/:/'

replay:      ## recompute every quoted d = 3 number from the shipped records; PASS/FAIL table in .work/replay/
	$(PY) -B public/replay_pert3d.py --data $(DATA)/pert3d --manifest $(DATA)/MANIFEST.sha256 \
	  --summary $(RESULTS)/SUMMARY.md --out $(WORK)/replay

test:        ## manifest check + the package's own checks + L4 fixture + L14 store vs the original code
	HT3D_PUBLIC_WORK=$(WORK)/test $(PY) -B public/run_tests.py

smoke:       ## the shipped L4 fixture, consistent scheme, against the original code's reference at 1e-16
	OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMBA_NUM_THREADS=1 HT3D_NATIVE_CACHE=$(NATIVE) \
	  $(PY) -B code/ht3d_coefficients.py solve --store fixtures/vertices_L4 --cutoff 4 --scheme consistent \
	  --native-cache $(NATIVE) --output $(WORK)/smoke/fixture_consistent.json \
	  --compare-reference results/reference_coefficients_L14.json --tolerance 1e-16 --lock-dir $(WORK)/locks

fetch-data:  ## nothing to fetch; see ../../data/HT_3d/DATA.md
	@echo "fetch-data: every record the replay reads is in git ($(DATA)/pert3d, 194 files, 1.5 MB)."
	@echo "The vertex stores of the production run (L16 2.6 GiB, L18 22 GiB, L20 177 GiB) and the L20 intermediate"
	@echo "pipeline files (363 GiB) are not hosted: a production rerun rebuilds them (public/REPRODUCE.md)."

clean:       ## remove .work/
	rm -rf $(WORK)
