# Public targets for SRI/code/indep_d1: the independent re-derivation of the inputs of C^SR_5..C^SR_8 of the d = 1
# dual series (Mellin-Hepp sector engine + own RG framework). The project files ship verbatim as a dated snapshot
# (public/SNAPSHOT.sha256); public/ is added. Run from this folder:
#   make -f public.mk test | replay | replay-raw RAW=<dir> | replay-full | fetch-data | clean
#
#   test        public/selftest_indep.py: snapshot and recorded sha256 values; the framework unit tests; the engine
#               built from source and four production chunks rerun from their .cfg (about 5 min on 8 cores).
#   replay      public/replay_indep.py: the verbatim assembly in work copies (run_assembly.py, run_assembly_C8.py step 1,
#               compare_archive*.py, make_report*.py), with the raw per-sector engine outputs replaced by their exact
#               sufficient statistics (public/pooled_sector_record.json); regenerated RESULTS*.json/.md compared with
#               the shipped ones; the note-only \SRCeightIndep, \SRCeightPull, \SRindepPullMax (INFO) and the cited checks (C5..C7 pulls,
#               25-input rms pull, J9, A9) against ../../results/quoted_numbers.json (about 4 min on one core).
#   replay-raw  the same on the raw chunk outputs (RAW = a directory with engine/runs/<run>/*.cfg.json, see
#               fetch-data), after rebuilding the pooled record from them and checking it against the shipped one.
#   replay-full prints the documented production rerun (about 22k core-hours on symmetry amdq; REPRODUCE_indep_d1.md).
#   fetch-data  public/fetch_raw.py: the raw chunk outputs (31 MB tar.gz from the Zenodo data record; URL_BASE=<url>
#               for a mirror or file:///<dir>, FILE=<archive> for a local copy), checked and unpacked into $(WORK)/raw.
# Python >= 3.10 with mpmath, sympy, scipy (requirements_indep_d1.txt); test also needs g++ with OpenMP (x86-64-v3).

PY      ?= python3
WORK    ?= .work
RAW     ?=
URL_BASE ?=
FILE    ?=
export PYTHONDONTWRITEBYTECODE = 1
export OPENBLAS_NUM_THREADS = 1

.PHONY: help test replay replay-raw replay-full fetch-data clean
help:
	@sed -n '1,20p' public.mk

test:
	$(PY) public/selftest_indep.py --work $(WORK)

replay:
	$(PY) public/replay_indep.py --work $(WORK)

replay-raw:
	@test -n "$(RAW)" || { echo "set RAW=<dir with engine/runs/<run>/*.cfg.json> (make -f public.mk fetch-data)"; exit 2; }
	$(PY) public/replay_indep.py --work $(WORK) --raw $(RAW)

replay-full:
	@sed -n '/^## Production rerun/,/^## End of production rerun/p' public/REPLAY_FULL.md

fetch-data:
	$(PY) public/fetch_raw.py --work $(WORK) $(if $(URL_BASE),--url-base $(URL_BASE)) $(if $(FILE),--file $(FILE))

clean:
	rm -rf $(WORK)
