# Stage-6 fix round 3, group G3: design and verification (2026-10-06)

Branch `fx3-g3` from a42cfb7 (the tree inspected in round 3), on the Mac (arm64, anaconda Python 3.10.11, numpy
1.23.5, scipy 1.10.0), `C8_ALLOW_NO_L8=1 OPENBLAS_NUM_THREADS=1`. Items Z8, Z9, Z10 and Z12 of
`LRI_C8_D2_HPC_loop/artifacts/s6_fix3_dispositions.md` (findings S6D-R3-01, S6D-R3-02, S6D-R3-03, S6D-R3-05). Only
`tools/verify_result.py`, `tools/design.py` and the tests `tests/verify_result_tamper.py`, `tests/combine_core.py` and
`tests/test_pipeline.py` changed, plus this folder. No `src/` change and no cluster job.

Unchanged for valid inputs: every stored result verifies as before (16 of 16). A bundle frozen at the default settings
(margin 1.5, imputation `addends`, as every stored bundle's `design_meta.json` records) is reported with the same SE,
summed in the same order. Freeze, rates and plan outputs are unchanged.

## The fixes

- **Z8 (S6D-R3-01): the covariance must be a covariance.** `verify_result.covariance_problems` runs before anything is
  recomputed. Before the fix, the recomputation used only the diagonal and `[order][order]`, so off-diagonal elements
  were copied unchecked. The checks are in correlation units, because the assembler's `J V J^T` is symmetric and PSD up
  to rounding relative to `sqrt(c_ii c_jj)`. The stored diagonal spans 1e-9 to 1e6, so a tolerance scaled by the
  largest variance would be loose for low orders. Definitions:
  - `D` is the largest variance and `tau^2 = EPS D`.
  - `t_k = max(sqrt(max(c_kk, 0)), tau)`; `tau` stands in for the exactly zero rows of orders 0..2.

  The three checks:
  - symmetric: `|c_ij - c_ji| <= COV_REL t_i t_j`;
  - nonnegative diagonal: `c_kk >= -COV_REL t_k^2`;
  - PSD: the smallest eigenvalue of `T^-1 (C + C^T)/2 T^-1` is at least `-m COV_REL`, with `m = 9`.

  `COV_REL = 1e-10`. The stored results are asymmetric by at most 11.5 eps (2.6e-15), and their correlation matrices'
  smallest eigenvalue is at least 0.02. A matrix with no positive variance must be all zero, and an overflowing
  correlation matrix is refused. Same class (`sign_problems`):
  - `power_difference_errors`, the campaigns' `sampling_se` and the bootstrap's `full_se` and `correction_se` must be
    `>= 0`;
  - every `error_by_loop` variance must be `>= -REL Var(C_order)`.

  In the same class (Z9), `verify_result.py`'s CLI records the sha256 of the bytes it verified, reading the file once.
- **Z9 (S6D-R3-02): one verified, schema-aware bundle reader.** `design.read_bundle(bundle, schema_prefix,
  allow_provisional)` reads each file once and checks its sha256 against `design_meta.json`. It parses only those
  bytes:
  - `design.json`, at `design_sha256`, with its schema and kind;
  - exactly the 24 counts files, at `counts_sha256`, each line `<graph> <positive count>\n` with distinct graphs;
  - for a provisional bundle, `rates.json` at `rates_sha256` (which must equal `rates_identity`).

  The schema follows the reuse prefix (O11). Users:
  - `report --bundle` (main and `report()`, verified before anything is designed);
  - `freeze --rates-bundle`, which records the `meta_sha256` of the bytes it parsed;
  - `rates --source-bundle`, which now verifies the source bundle's design and counts.

  `bundle_prediction` also requires the bundle's groups and graphs to be the pilot's inventory, and every
  `s`, `r` and `K` to be a positive integer.
- **Z10 (S6D-R3-03): the frozen settings.** `bundle_prediction` recomputes the bundle SE at the bundle's frozen margin
  (`parameters.variance_margin`, equal to `design.json` `predicted.variance_margin`) and its frozen imputation
  (`imputed.impute`), never at the report command's own settings. It records:
  - `frozen_settings`, `relative_difference` and `agrees` (to 1e-9, and only for the pilot the bundle was frozen from);
  - `pilot_is_the_frozen_pilot`; a report from another pilot is labelled a PROJECTION in `kind`.

  An explicit `--variance-margin` or `--impute` other than the frozen ones adds `projection`, labelled "PROJECTION ...
  not the frozen prediction". The report subparser's defaults are `None`, so explicit settings can be told apart.
  `print_report` prints the frozen settings, whether the SE agrees, and the projection.
- **Z12 (S6D-R3-05): `nested_alpha` per graph ratio, and the identity check.** Every graph keeps its own point ratio,
  oriented so that `n_lo < n_hi`. Graphs at equal counts are left out and counted.
  - One ratio in a stratum: the closed form, which is the old formula.
  - Several ratios: the root of `sum v_lo rho^(-2 alpha) = sum v_hi`, strictly decreasing in alpha, found by
    bisection.

  Per stratum, the record holds the alpha per ratio, the ratios, the point pairs and the estimator. `check_nested`
  refuses a nested pilot whose `NESTED_IDENTITY` differs: dimension, prefix, half_d, inputs manifest, two-loop jet,
  numerics, rates identity and backend. `nested_alpha` and `report` call it, and the report records the nested
  campaign, the identity checked and the rule.

## Tests: each fails on a42cfb7's code and passes here

"Before" runs use a `git archive a42cfb7` export with only the three new test files copied in (`<a42cfb7-export>`
below). `before_driver.py` runs test_pipeline parts 1 and 2 with each new function wrapped, so that every function
fails or passes on its own and the rest of the part continues.

| Item | Test | Before (a42cfb7) | After |
|---|---|---|---|
| Z8 | `tests/verify_result_tamper.py` (`z8_cases` and the Z8 checks): 31 new, 206 in all | `before_verify_result_tamper.txt`: 176/206; 30 checks fail. The 20 tamper cases are accepted: the finding (`covariance[3][8] = 1e30`), a 1e-6 asymmetry at a low order, symmetric correlations 0.9/0.9/-0.9, a zero-variance row's covariance, a coordinated negative variance, and the same class (campaign `sampling_se`, bootstrap SEs, `error_by_loop`), in a result, a test-only result and both combinations. The tolerance checks fail because there is no `COV_REL`. The negative `power_difference_errors` guard passes both before and after: the recomputation refused it already | `verify_result_tamper.txt`: 206/206 |
| Z8 | `tests/combine_core.py`: combine refuses an assembly whose combined covariance is asymmetric or indefinite, and accepts it untouched | `before_combine_core.txt`: 12/14 (both are accepted) | `combine_core.txt`: 14/14 |
| Z10 | `test_pipeline.py` `z10_synthetic` (part 1) and `z10_cli` (part 2) | `before_test_pipeline_part1.txt`: report gives 0.01108 (the command's 1.5 and `addends`) against the frozen 0.01520 (27% below). `before_test_pipeline_part2.txt`: the CLI report without `--variance-margin` gives 0.002372 against the frozen 0.003162 (0.75 x) | pass |
| Z9 | `z9_synthetic` (part 1), `z9_cli` and `z9_class_cli` (part 2) | report accepts a doubled count with its digest unchanged (in-process; CLI exit 0, expected 2); freeze `--rates-bundle` accepts a changed `rates.json` (exit 0, expected 2) | pass |
| Z12 | `z12_nested` (part 1) | the finding's case gives alpha 0.2797, not 0.5 | pass |

The 16 stored results (`benchmarks/` and `tests/fixtures/verify_result_cross_machine/`) verify before and after:
`verify_result_all_stored_results.txt` and `before_verify_result_all_stored_results.txt`, 16 of 16 each.

## Suites on the final tree (records in this folder)

| Suite | Result |
|---|---|
| `tests/verify_result_tamper.py` | 206/206 (`verify_result_tamper.{txt,json}`) |
| `tests/combine_core.py` | 14/14 |
| `tests/assembly_checks.py` | 32/32 (A-ASM-5 through `verify_result`) |
| `tests/compat_2026.py` | passed |
| `tests/test_pipeline.py` | 3 parts, 35 tests (29 before, plus the 6 new ones); about 7 min |
| `tests/unit_orchestration.py` | 60 groups, 72 tests, 0 failed; about 13 min |
| `tests/test_numerics_flags.py` | 11 tests (imports `design.check_gate`) |
| `tests/ast_scan.py` (tools) and over `gen/*.py tests/*.py` | 27 and 46 files, 0 findings |
| stored results (`verify_all.sh`) | 16/16, and 16/16 on a42cfb7 |

pyflakes on the five changed files reports only the six unused locals that `tests/test_pipeline.py` already had at
a42cfb7.

Not run here: the native suites (`make test`, J-VAL), because no native code changed; and `make test-python`'s
other members, which do not import the changed modules.
