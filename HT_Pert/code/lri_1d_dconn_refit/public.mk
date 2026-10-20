# Public targets for HT_Pert/code/lri_1d_dconn_refit: the d = 1 complete-window refits of C4..C8 (S1B, 2026-10-08/09):
# the delta-v1 continuation of the exact window shifts dC6..dC8 beyond L = 72 (delta/), the joint linked-tail lens
# (joint/, 256-bit python-flint least squares), the model-independent lens (model-independent/, mpmath 50 digits) and the
# independent verifier (verify/). Shipped: the stage code and its summary outputs verbatim (keep_only subset of the
# archived stage folder; scripts name their inputs by absolute paths of the authors' machine, so the tests run them on a
# re-pointed run-time copy made by public/repoint.py), plus the run-1 table run1/joint/out/variants_full.json and
# public/. HT_Pert note: d = 1 results (C4..C8 with the complete window) and the reproduction table.
# Run from this folder:  make -f public.mk test | replay | fetch-data | clean
#
#   test        public/test_refit.py: delta stage rebuilt from its inputs on a run-time copy (check_inputs, build_delta,
#               regen_variants, smooth_central, check_outputs, validate_hi72 seq/hold/noise) and every rebuilt table
#               compared with the shipped delta/out (bitwise, else 1e-9 field-scaled); the model-independent
#               headline.py and final72.py rerun from the shipped intermediate outputs (bitwise, else 1e-12
#               field-scaled). With FLINT_PY=<python with python-flint> it also runs public/refit_keyfits.py (12
#               joint-lens key fits against the shipped summaries, 1e-9 relative; seconds); without it that step is
#               SKIP. About 3 min, one core, < 2 GB.
#   replay      public/replay_refit.py: rows rf.* (results_map.md): input binding, the blind forecast check, the C4..C8
#               ranges and deviations behind \NOneCfourSolver .. \NOneCfiveSolverDev (note-only macros of the HT_Pert
#               note) and \HTpCsixOne .. \HTpCeightOneUncal, the weighted fixed A-F sensitivity (INFO), paired window
#               shifts, S10 noise.
#               Seconds. Reads ../lri_hpc_Hamitonian/analysis/eps5_window/{reconcile/refit_rc.json,
#               challenge-theory/freelead2.json} and the inputs listed in public/repoint.py (SKIP rows when absent).
#               HTP = the HT_Pert root, DATA = its data/HT_1d.
#   fetch-data  public/fetch_hosted.py: downloads the files of public/hosted.json from the Zenodo data record (raw
#               joint-lens scan records, 97.5 MB, to joint/out/r72/; the model-independent outputs git leaves out, 34
#               grid.json, 34 accel.json and three mem1/ files, one archive unpacked at this folder), checks sizes and
#               sha256 (every archive member too) and skips files already in place. Not needed by test or replay.
#               DATA_URL = the record's file URL (Zenodo record 23466766, DOI 10.5281/zenodo.23466766).
# The full refit (joint scans of 395,280 fits, post-processing, 34 model-independent grids) is documented in REPRODUCE;
# it is not a make target.
PY       ?= python3
FLINT_PY ?=
WORK     ?= .work
HTP      ?= ../..
DATA     ?= $(HTP)/data/HT_1d
DATA_URL ?= https://zenodo.org/records/23466766/files
export PYTHONDONTWRITEBYTECODE = 1
export OPENBLAS_NUM_THREADS = 1
export MKL_NUM_THREADS = 1
export OMP_NUM_THREADS = 1
export MPLBACKEND = Agg
export NUMBA_CACHE_DIR ?= $(WORK)/numba_cache

.PHONY: test replay fetch-data clean
test:
	$(PY) public/test_refit.py --work $(WORK) --htp $(HTP) --data $(DATA) $(if $(FLINT_PY),--flint-py $(FLINT_PY),)

replay:
	$(PY) public/replay_refit.py --htp $(HTP) --data $(DATA) --work $(WORK)

fetch-data:
	$(PY) public/fetch_hosted.py --url $(DATA_URL) --cache $(WORK)/fetch

clean:
	rm -rf $(WORK)
