# Amendment P1: implementation record

Implements `AMENDMENT_PROFILED_SIGMA.md` (approved revision 4, sha256 `2a18c0ae…74d0`, not edited) for both productions. Author of all code
below: Claude (host). Independent inspection: Codex, fresh session (see `AMENDMENT_REVIEW-LOG.md`).

## What was built

| file | change |
|---|---|
| `LRI_2d_MC/evaluate_2d.py` (rev 5 → rev 6), `LRI_3d_MC/evaluate_3d.py` (rev 1 → rev 2) | one identical patch (the 3D reblocking block keeps its FIT3D try/except structure): `--sigma-rule {fixed,profiled}` (default fixed), `--calibration`, `--amendment`, `--index-remap OLD=NEW`; `profile_draws` (per-draw ω′ profile, vectorised projector of `reanalyse.py`); profiled σ, per-draw ω′ distribution and profiled σ_D / reblocking values recorded for information in every mode (§3.5); `fit_series` / `truths` (the §4.3 fits, shared with the calibration); `decision_table` / `final_label` (the §4.6 table, unchanged, factored out so the P1 path uses the same rows); `apply_p1` (§3.6, per point, atomic, A4 check, §6 R4 drop-smallest report for a changed label); `load_calibration` / `point_binding` (P1-007); `p1_run` / `p1_md` (main) |
| `LRI_2d3d_reanalysis/calibrate_p1.py` | §4 calibration; imports the evaluators' own `fit_series`, `truths`, `extrapolate`, `stratum_status`, `a3_pooled` (no re-implementation of the fit or of the adoption rules) |
| `LRI_2d3d_reanalysis/tests/test_p1.py`, `tests/frozen/` | §7 proof (pinned copies of the frozen rev 5 / rev 1 evaluators, sha256 = the baselines' `evaluator_sha256`) |
| `LRI_2d3d_reanalysis/oned_xcheck/check_1d_xcheck.py` | exploratory 1D question (below); not part of the amendment |

## Interpretations and deviations (all disclosed in the outputs where they apply)

1. **Index remap (operational deviation).** The histogram indices named in the records lived on Expanse Lustre, which was archived to Google
   Drive and deleted (2026-09-26). The six `index.json` files were restored from the Drive archive; `--index-remap` reads them from the
   restored copies. The hash check against each record's `index_sha256` and the index's manifest hash are unchanged. Every evaluation that
   uses it lists it under `deviations`.
2. **Switch-off reproduction (§1.2 "bit-for-bit").** The frozen evaluators themselves, rerun on another machine, differ from the Expanse
   baselines by ≤ 4×10⁻¹¹ relative (BLAS rounding), and Expanse no longer holds the data, so bit-for-bit equality with the Expanse output is
   not reproducible anywhere. The proof is therefore two-tier: (a) bit-for-bit equality of every per-point field with the pinned frozen
   evaluators run on the same machine and inputs (only the §3.5 fields listed in the test may be new); (b) against the pinned baselines:
   every label, string, boolean, integer and list identical, floats to 10⁻⁹ relative.
3. **Gate (iii) on synthetic data.** σ_stat of the largest pair is the synthetic bootstrap σ of that pair (the recorded
   `statistical_stderr` is exactly the bootstrap σ of the pair: verified on the records).
4. **Points with no eligible series** (E empty: MODEL-LIMITED, COVERAGE-LIMITED) use no calibrated quantity; they stay on the fixed rule
   with the note "P1 not applied: no eligible series …" (their labels do not depend on the σ rule).
5. **A3** is pooled over every A1 stratum with ≥ 200 eligible fits, both dimensions, both ensemble types.
6. **P1-CALIBRATED** additionally requires that the profiled σ of every series in E (and σ_D when used) exists.
7. **Binding (P1-007, tightened after inspection round 1: P1-008 … P1-011).** The calibration is valid only if it is complete and bound
   to this repository: the header's calibration-script and both evaluator hashes equal the files in the repository (so any change of the
   fitting code needs a new calibration); both dimensions, every point of both pinned baselines and all six strata per point are present
   (no `--only` subset; `only` must be recorded as null); every point's record hashes equal the pinned baseline's inputs; every truth of
   BOTH dimensions equals this code's refit of the record (ω′* identical, Δ_ε and amplitudes to 10⁻⁹ absolute) — so every contributor to
   A3 is bound; settings (2000 sets × 500 draws, grid, gates) and thresholds equal the evaluators'; the `--plan` is the frozen protocol
   (pinned sha256); counts are integers within their parent counts; each status follows from its counts; A3 follows from the strata. JSON
   NaN / Infinity is rejected. Any malformed content is a failed check, never an aborted evaluation: every point then uses the fixed rule.
8. **Misspecified family (reported only).** The second correction a·L^(−2ω′*_J) goes into U4, or into Y when no amplitude in U4 reproduces
   the recorded U4 − Y difference: a single-correction fit absorbs a large a by moving ω′, so the reachable difference is bounded. The fitted
   difference is only piecewise continuous in a (discrete ω′ argmin), so the candidates are the scanned amplitudes already within tolerance
   (P1-015) and the bisected sign changes of a quarter-octave scan, each accepted only within 2 % of the target (P1-012); points where neither
   series works are reported with the reachable ranges.
10. **Information for every fitted series (P1-013).** Series stopped by gate (i) or (ii) also record the profiled σ, the per-draw ω′
   distribution and, as `sigma_inf_fixed_information`, the fixed-ω′ σ; the frozen `sigma_inf` is still recorded only where the frozen rule
   computes it, and no gate or label uses the information fields.
9. **Immutability.** The calibration directory and its files are made read-only after writing; evaluations keep the frozen atomic-mkdir
   rule.

## Proof (personal desktop, python 3.8.8, numpy 1.20.1, via Slurm)

`python -m pytest LRI_2d3d_reanalysis/tests/` — 56 tests: switch-off bit-for-bit vs frozen (2D, 3D); switch-off vs pinned baselines
(2D, 3D); index check still enforced; profiled σ, σ_D and reblocking σ equal `reanalyse.py` to 10⁻¹² (43 quantities); calibration
deterministic by seed and independent of the worker count; all-PASS fabricated calibration → every calibrated point entirely profiled and
the §5 prediction reproduced (3D s = 1.6 ACCEPTED 1.47314 ± 0.00118 ± 0.00230, z −0.45; z +2.49, −4.90, −28.1; 2D σ_stat 0.0177,
0.0101, 0.0018; R4 drop-smallest U4 1.4724, Y 1.4746 = `reanalyse.cutoff`); 12 header/record tampering cases, an unapproved amendment, an
edited protocol and an inconsistent status each invalidate the whole calibration; so do the 23 round-1/2 cases (script or either evaluator
hash, a missing dimension or strata dimension, a partial or unrecorded subset, another dimension's record hash, truth or settings, a
missing point or stratum, a null or non-object point header / strata entry of either dimension (P1-014), NaN / infinite truths, out-of-range or non-integer counts, null header / dimension / strata — the evaluation
still completes); every fitted series carries the profiled information; every constructed misspecified family meets its tolerance (every point then identical to the fixed evaluation); A3
failure withdraws the amendment; one failed or UNCALIBRATED stratum (A1 J, A1 U6, A2) keeps only its point on the fixed rule; CLI
argument checks.

## 1D (exploratory, existing records, not a protocol decision)

The 1D protocol (FIT_MODEL_V3) is already nuisance-aware: each bootstrap draw of the global fit refits every nonlinear parameter including
the correction exponent (`fit_fss.run_fit`), and each crossing series re-profiles ω′ per draw (`select_model.crosscheck_series`).
`oned_xcheck/` reproduces the recorded per-draw values to 10⁻¹² and shows that with ω′ held at its central value the per-series
crossing errors would be 9–16 % and σ_D 9–13 % smaller (z 2.10 → 2.30 at Δσ = 0.15, 2.00 → 2.30 at 0.175). The two 1D cross-check failures are therefore not an artefact of a conditional σ.
