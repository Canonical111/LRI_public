# Reproduce indep_d1

Environment: Python >= 3.10 with mpmath, sympy, scipy (`requirements_indep_d1.txt`); `make test` also builds the C++
engine (g++ with OpenMP, x86-64-v3; without it the engine rows are SKIP). Run from `SRI/code/indep_d1/`
(or `make -C code/indep_d1 -f public.mk <target>` from `SRI/`). Nothing needs a cluster except the production rerun.

1. `make -f public.mk test` (about 5 min on 8 cores): the snapshot sha256 list (original pins; the 22 files of
   `RE-PINNED.json` match their published sha256, files listed in `public/SCRUBBED.txt` are checked for presence only);
   the sha256 values the project recorded
   for its own records (engine deliverables, sealed comparison files, RESULTS json files); the framework unit tests
   (two of them read the compendium from the sibling package `../dual_d1`, SKIP without it); the engine built from
   `engine/src` with `engine/slurm/build.sh` and four production chunks rerun from their `.cfg` and compared with the
   shipped outputs (1e-12 of the L1 scale).
2. `make -f public.mk replay` (about 4 min on one core; measured 229-264 s): in work copies under `.work/replay/`,
   * `assembly/make_report.py`, `make_report_C8.py`, `make_report_C8_tierA.py` regenerate `RESULTS.md`,
     `RESULTS_C8.md` (byte-identical) and `RESULTS_C8_tierA.md` (identical except a status note added by hand);
   * `assembly/run_assembly.py` (phase 2, steps 1-2) regenerates `RESULTS_independent.json` from the 116 raw scalars;
   * `assembly/run_assembly_C8.py` step 1 recomputes C8 from production + tiers A, B, C (201 raw scalars) and the
     comparison with `RESULTS_C8_independent.json`;
   * `assembly/compare_archive.py` and `compare_archive_C8.py` regenerate the two comparison files;
   * the note-only \SRCeightIndep (since paper e89a94a0), \SRCeightPull, \SRCeightPullMax, \SRindepPullMax (INFO rows)
     and the cited checks are recomputed from the
     regenerated values, with the claims evaluated from the paper's eq:sr-closed and eq:sr-C8.
   The raw per-sector engine outputs are replaced by `public/pooled_sector_record.json` (`public/pooled_shim.py`):
   exact per-job sufficient statistics of the sector-pooled error (the per-sector values themselves for the jobs with at
   most 360 sectors). Tolerances: central values 1e-24 relative (the framework is deterministic at 50 digits), linear
   and replicate errors 1e-12, everything that depends on the sector-pooled errors 1e-6 of the quoted error, and the
   per-job diagnostics that enter no quoted error (replicate projections, per-job maxima, shares) 1e-2 of it: the
   verbatim code sums them in double precision over up to 20,160 sectors, and Python 3.12's compensated `sum()` changes
   the rounding-level ones (for the input q, 3.16e-14 written with Python 3.10 against 2.76e-14, sigma 3.0e-12; the
   same difference appears on the raw path). PASS/FAIL table in `.work/replay/replay_indep.txt`.
3. `make -f public.mk fetch-data` then `make -f public.mk replay-raw RAW=.work/raw` (about 6 min). `fetch-data`
   downloads the raw chunk outputs from the project's Zenodo data record (`SRI__indep_d1__raw_engine_outputs.tar.gz`,
   `public/HOSTED.json`; `URL_BASE=<url>` for a mirror, `FILE=<archive>` for a local copy), checks the archive and
   unpacks it into `.work/raw`; any `RAW` directory holding `engine/runs/<run>/*.cfg.json` works:
   checks `public/RAW_SHA256SUMS.txt`, rebuilds the pooled record from the raw outputs with the verbatim
   `pooled_errors.job_sector_values()` and compares it with the shipped one, then runs step 2 with the verbatim
   `pooled_errors.py` on the raw outputs.
4. `make -f public.mk replay-full` prints the production rerun (about 22k core-hours, symmetry `amdq`):
   rebuild the engine, rerun the shipped `.cfg` chunks of the eleven production runs, collect and merge
   (`engine/py/campaign.py`, `merge_runs.py`, `engine/tests/merge_tiers_C8.py`), then `replay-raw` on the new outputs.

## Decisions you must not make
* The quoted error is the largest of the three estimators (linear, replicate, sector-pooled), fixed before the
  comparison; for C8 it is the sector-pooled one (2.37). The linear and replicate errors (1.37, 1.15) would give pulls
  of -3.3 and -4.0; the statistics verifier's chunk-pooled estimate gives -2.09. Report the protocol value.
* The C8 difference: the magnetization-scheme value of the SRI note (Sec. 2.7, Appendix I; package integ_d1) agrees with the record, which indicates that this package's C8 is the one in error; this package's own input
  comparison locates the difference in A9[eps^0 l^1]. Whether it is a fluctuation or a systematic error needs an
  independent A9 run.
* This package tests the compendium's numbers within its matched two-coupling prescription; it does not test the
  prescription, nor the zeta-value form of C8.
