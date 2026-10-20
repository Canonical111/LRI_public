# Public targets for SRI/code/dual_d1: the d = 1 dual (s -> 1) series C^SR_1..C^SR_8 of the long-range Ising chain.
# The compendium (another AI system; archive of 2026-10-02) ships verbatim as a pruned dated snapshot
# (public/SNAPSHOT.sha256); public/ is added. Its scripts run unchanged on a work copy in $(WORK)/compendium whose
# layout and MANIFEST lists are restricted to the shipped files. The work directory must be case-sensitive (Linux) for
# the C6/C7 input maps (see DATA_dual_d1.md); elsewhere those rows are SKIP.
# Run from this folder:  make -f public.mk test | replay | fetch-data | replay-full | clean
#
#   test         snapshot sha256; the paper's equations vs the records (exact); quoted macros; C8 residual and
#                rational part; the compendium's run_checks.py. About 25 s.
#   replay       test + reproduce.py c8-saved and c8-rational-algebra (regenerated records compared), the C5 (D3) and C6
#                certificates, the C7 and C6 input maps, the C7 certificate at weights 2..5, low-integrals. About 1 min.
#   fetch-data   the hosted weight-6 C7 certificate (57 MB) into $(WORK)/hosted: downloaded from the Zenodo data record
#                (URL_BASE=<url> for a mirror or file:///<dir>), or from ZIP=<original archive> or DIR=<unpacked copy>.
#   replay-full  replay with the complete reproduce.py --task certificates (needs fetch-data; about 6.5 min, 0.5 GB),
#                reproduce.py c8-positive-check and c8-numerical (C++17 compiler and GMP headers). About 9 min.
# Python >= 3.10 with mpmath and sympy (requirements_dual_d1.txt); no other package.

PY      ?= python3
WORK    ?= .work
ZIP     ?=
DIR     ?=
URL_BASE ?=
export PYTHONDONTWRITEBYTECODE = 1
export OPENBLAS_NUM_THREADS = 1

.PHONY: help test replay fetch-data replay-full clean
help:
	@sed -n '1,20p' public.mk

test:
	$(PY) public/replay_dual_d1.py --mode test --work $(WORK)

replay:
	$(PY) public/replay_dual_d1.py --mode replay --work $(WORK)

fetch-data:
	$(PY) public/fetch_data.py --work $(WORK) $(if $(ZIP),--zip $(ZIP)) $(if $(DIR),--dir $(DIR)) $(if $(URL_BASE),--url-base $(URL_BASE))

replay-full:
	-$(PY) public/fetch_data.py --work $(WORK)
	$(PY) public/replay_dual_d1.py --mode full --work $(WORK)

clean:
	rm -rf $(WORK)/compendium $(WORK)/logs $(WORK)/*.txt $(WORK)/*.json
