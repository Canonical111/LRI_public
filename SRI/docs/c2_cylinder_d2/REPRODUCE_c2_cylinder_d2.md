# Reproduce c2_cylinder_d2

Run everything from `SRI/code/c2_cylinder_d2/` (or `make -C code/c2_cylinder_d2 -f public.mk <target>` from `SRI/`).

## Environment

Python >= 3.10 with numpy, scipy, mpmath, sympy and matplotlib (`requirements_c2_cylinder_d2.txt`). Tested versions:

| Where | Versions |
|---|---|
| Production | Python 3.13.3/3.13.5, numpy 2.3.5, scipy 1.17.0, sympy 1.14.0, mpmath 1.3.0, matplotlib 3.10.8 (`requirements-tested.txt`) |
| Acceptance run of this export | Python 3.12.9, numpy 2.3.5, scipy 1.17.1, mpmath 1.3.0, sympy 1.14.0, matplotlib 3.11.2 (symmetry, see `TESTS_c2_cylinder_d2.md`) |

`public.mk` sets `OPENBLAS_NUM_THREADS=1`, `OMP_NUM_THREADS=1` and `PYTHONDONTWRITEBYTECODE=1`. Run-time products go
to `.work/`.

## Steps

1. `make -f public.mk test` (about 3 min, one core):
   - `public/selftest_c2cyl.py`:
     - `MANIFEST.sha256` for the shipped tracked files (`public/NOT_EXPORTED.txt` and `public/SCRUBBED.txt` honoured);
       record-bound files must match exactly;
     - the task `SHA256SUMS` of the cluster records;
     - the dated snapshot `public/SNAPSHOT.sha256` of `outputs/`;
     - the `CURRENT` generation;
     - the closed form at 30 and 40 digits;
     - the rounding rule;
     - no path filter on "local";
     - the no-unlisted-file rule on a synthetic package. The files the public export writes are tolerated, present
       or not: `public/SCRUBBED.txt`, and `RE-PINNED.json`, `RE-PINNED.md` and `MANIFEST.json` at the package root.
       Any other file that neither `MANIFEST.sha256`, `public/SNAPSHOT.sha256` nor the overlay accounts for fails.
   - `public/run_suites.py`: the package's own suites through their verbatim entry points: `test_continuum` (36 tests)
     in place; `test_cluster`, `test_sitekit`, `test_expanse` and `test_symmetry` in a staged code copy under
     `.work/suites/`. Git is hidden and no scheduler is contacted. The only accepted skips are:
     - the two legacy A6-2 tests: they `git archive` the pristine commit 474487c, and the export has no history;
     - the three tarball tests of `make_tarball.sh`, which archives a git commit;
     - on non-GNU systems, the GNU-coreutils tests.
2. `make -f public.mk replay` (seconds): `public/replay_c2cyl.py`, from the shipped generation. See `results_map.md`.
   - The per-order regulator fits (154), the joint fit and its 84 variants, the outcome table, every error component,
     E and C2 +- dC2 are recomputed with the verbatim functions and compared leaf by leaf with `regulator_fits.json`
     and `C2_estimate.json`.
   - The same quantities are recomputed by an independent numpy/mpmath implementation.
   - Then the quoted numbers `\SRtwoCtwoHT`, `\SRtwoCtwoHTDev`, the note-only `\SRtwoCtwoHTNmax` (INFO) and the c_2 row of tab:htpert
     with its caption (read live from `results/quoted_numbers.json`, key `tab_htpert_c2`).
3. `make -f public.mk replay-full` (about 10 s, one core): `public/replay_full_c2cyl.py`.
   - It reruns the production analysis from the raw records:
     ```
     python scripts/run.py continuum -- run \
         --records outputs/merged_production_plan_20261013.json \
         --diagnostic-records outputs/merged_analysis_checks_plan_20261013.json \
                              outputs/merged_analysis_checks_plan_rev6_20261014.json \
         --aux-dir outputs/symmetry/c2aux_574247 \
         --legacy-receipt results/continuum_2026-10/evidence/legacy_macos/legacy_reproduction.json \
         --deviations results/continuum_2026-10/evidence/DEVIATIONS_ANALYSIS.md \
         --output .work/replay_full/continuum_2026-10
     ```
     This is the production command. Only the `--deviations` path differs: the production run read that file from
     the plan folder, which is not shipped, and the copy here has the same sha256.
   - The driver verifies every input hash itself.
   - The replay then compares all outputs leaf by leaf with the shipped generation, and REPORT.md number by number.
     The input set and its sha256 must be identical. Run-description fields are skipped.

Expected: every row PASS (INFO rows are reported values). Any FAIL makes the target exit non-zero.

## Production rerun (cluster; not needed for any replay)

The records were made by the shipped launch layer. To redo them on symmetry or SDSC Expanse, read `cluster/README.md`,
`cluster/sitekit/README.md` and the site READMEs. In short:

1. `make_tarball.sh` builds the code tarball from a git commit, so first make the package a git repository of its
   own: copy this folder without `outputs/`, `public/` and `.work/`, then `git init`, `git add -A`, `git commit`.
2. `cluster/<site>/make_tarball.sh --upload <site>`, then on the login node `cluster/<site>/setup_env.sh` and
   `submit.py --check`. Then `submit.py --stage PILOT P1 P2 --submit` for the production records
   (`cluster/production_plan.json`).
3. The extraction checks: `submit.py --plan cluster/analysis_checks_plan.json` and
   `cluster/analysis_checks_plan_rev6.json`.
4. The auxiliary inputs: `sbatch code/continuum/aux_job.sbatch`; the header of that script has the sbatch line.
5. `cluster/<site>/collect.sh`, then `cluster/sitekit/merge_records.py`, then the `replay-full` command above with
   the new indexes.

The science sources must keep the digest `eebafa82d841...`, which `test_continuum` checks; the records carry it.

In the public tree the SDSC Expanse allocation is the placeholder `<ACCOUNT>`, the same token in
`cluster/expanse/profile.json`, the launch layer and the tests that assert it (`test_expanse`, `test_sitekit`). For a
production run, put your own allocation into the profile. That makes those two tests disagree, so run them before you
edit the profile.

Measured cost:

| Stage | Where | Cost |
|---|---|---|
| P1: N = 768 grid and 3 row jobs | symmetry | about 1.5 node-hours |
| P2: N = 1024 grid and 2 row jobs | SDSC Expanse | about 220 SU |
| Extraction checks: N = 1024 variant grid and 5 rows | SDSC Expanse | 252 SU |
| Completion rows, D1 | symmetry defq | 2 N = 1024 grid rebuilds (2.6-2.7 h each), 9 + 3 rows (0.3-1.6 h each) |
| Auxiliary-input job | symmetry, one node | 6 min |

Each N = 1024 grid occupies about 52 GB of node-local scratch, plus about 115 GB of memory with 16 workers. The site
profiles encode the limits.

## Decisions you must not make

- The analysis rules are fixed in `code/continuum/continuum_analysis.py` (`RULES`) and copied into every output as
  `meta.rules`. They cover:
  - the fractional windows and selected spectral fits;
  - the mixed, collapsed and tail cutoffs;
  - the PRIMARY and DIAGNOSTIC pools;
  - the lambda*N minima;
  - the regulator term sets, windows and admissibility;
  - the preferred model {2, 2log, 3} unweighted;
  - the joint fit;
  - the pre-declared outcome table;
  - the linear sum E.
- Do not change them. Do not quote another branch, and do not quote a per-order value as the result.
- The error is a linear sum of systematic diagnostics, not a standard deviation; keep that wording.
- The closed form must not enter the analysis. The code is checked for its digits.
- Tolerances of the replays:
  - quoted numbers: half-up rounding to the printed digits;
  - `replay`, the verbatim chain M6-M8 on the shipped points: 1e-9 relative for h0, the influence rows, E, the
    components and C2; regulator coefficients beyond the intercept, residuals and condition numbers 1e-6 relative or
    1e-12 absolute; flags and counts equal;
  - `replay-full`, the rerun from the raw records:
    - every discrete leaf equal: selections, admissibility, validation, counts, statuses, branch;
    - tier A, the chain to the quoted number: 1e-7 absolute (h of every point and every error component, the h0 of
      every fit, E, C2, dC2, the outcome table, the error budget);
    - tier B, fit diagnostics: 1e-6 + 1e-3 |x|, condition numbers 1e-2 relative.

  On the production platform (macOS arm64, CPython 3.13.5, numpy 2.3.5) the rerun is bit-identical. Elsewhere the
  spectral fits, whose condition numbers reach about 1e15 (truncated SVD at rcond 1e-13), differ in their last digits;
  see `TESTS_c2_cylinder_d2.md` for the measured differences. If a comparison fails, report the numbers; do not loosen
  the tolerance.
