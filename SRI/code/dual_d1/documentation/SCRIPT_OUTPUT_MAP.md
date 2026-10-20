# Programs, inputs, and outputs

All paths below are relative to the archive root unless prefixed by `work/`.
Historical source paths are virtual names resolved by `reproduction/layout.json`.
Use `python code/locate.py NAME` to locate the immutable stored copy.

| Program / task | Principal input | Output / purpose | Scope |
|---|---|---|---|
| `run_checks.py` | Global manifest, latest P6 terminal vectors, full trace and P8/J9 scalar expressions | `outputs/verification/replayed/quick_check.json` plus exact-check logs | Saved-expression/integrity replay; no raw integration |
| `code/reproduce_summary.py` | Stated coefficient formulas; 35 rational beta inputs; latest C8/P6 numerical record | `data/coefficients.json`, `outputs/tables/*.csv`, `outputs/tables/invariants.json`, `outputs/verification/summary_algebra.json` | Coefficient algebra and numerical comparison; C8 labelled conjectural |
| `code/reproduce.py --task certificates` | D3/C6/C7 targets, source-relation labels and complete certificates | `outputs/verification/replayed/certificates.json` and logs | Full exact certificate replay including the C7 product identity |
| C7 `code/verify_input_map.py` | 25 exact beta expressions and assembly definitions | Rebuilt 25,212-word target | Connects certificate to archived beta inputs |
| `--task c8-saved` | Latest 64 P6 output partitions and inherited numerical beta records | Saved-sum, Jacobian and candidate-comparison reports in `work/C8_zeta_candidate/verification/` | Exact scalar sum plus numerical relation recognition |
| `--task c8-numerical` | Entire 66,404-term P6 expression | `work/C8_zeta_candidate/verification/replay_P6_70.json`, `replay_P6_100.json`, period tables | Fresh complete period evaluation, not reintegration of the kernel |
| `--task c8-positive-check` | Full P8 divergence actual/predicted expressions | `work/C8_full_numerical_completion/verification/replay/fresh_periods.json` | Fresh numerical full-period consistency test |
| `--task low-integrals` | Closed low-order one-dimensional integral representations | Console/log numerical comparisons | Independent low-order integral checks |
| `--task conjectures` | Exact Gamma endpoint data and fixed model definitions | Endpoint exclusion and rational-prediction audit | Tests specified guesses, not physical extrapolations |
| P6 `boundary_mixed.py` | n=6, face=1/2/3, mixed derivative kernel | First-stage boundary source blocks | Raw source construction |
| P6 `run_mixed_stage2.py`, `bucket_source_sum.py`, `run_moving.py`, `finish_moving_sum.py` | Complete previous stage and source manifest | Next exact ordered-integration / combination stage | Regenerates omitted intermediate stages |
| P6 `final_fibration.py`, `precompute_terminal_apart.py`, `evaluate_terminal_bucket.py` | Retained full moving source | 64 terminal scalar partitions and divergence outputs | Full last-integration replay |
| P8 `terminal_fibration.py`, `precompute_terminal_apart.py`, `evaluate_terminal_bucket.py` | Retained complete P8 moving source | 256 terminal partitions | Full final P8 replay |
| Rational `tail_boundary.py`, `endpoint_odd.py`, `finite_lower.py` | Explicit moments and derivatives | Rational boundary/endpoint/finite-response outputs | Rational calculation; not full positive-weight data |

Archived original stage runners can expect intermediate files and snapshot-wide
manifests omitted from this curated distribution. Recreate generated stages in
order before calling those legacy whole-snapshot runners. The current top-level
commands above know the curated layout and do not silently substitute zeros.

## Key data products

* `data/coefficients.json`: current C1–C8 formulas, values, rational parts and status.
* Virtual `C8_zeta_candidate/data/P6.expr`: latest full six-kink mixed integral.
* Virtual `C8_full_numerical_completion/data/P8.expr`, `Kv.expr`, `J9.expr`:
  complete new eight-kink/current and ninth-order expressions.
* Virtual `C7_closed_form_proof/proof/C7_linear_words.json`: the exact C7 proof target.
* Virtual `C7_closed_form_proof/proof/C7.wN.certificate.txt`: all proof rows.
* Virtual `C8_zeta_candidate/inherited/six_new_inputs.json`: six full numerical
  beta inputs used in the latest high-precision assembly; not exact restored
  period expressions.
* Virtual `C8_rational_completion/result.json`: exact rational C8=88 checkpoint.
* Virtual `F2_F3_delivery/F2/data/U.expr`: complete surviving F2 scalar expression.
* Numerical period tables and coefficient results remain paired with settings,
  hashes and evidence-scope reports. Decimal agreement alone is never relabelled
  an exact period identity.
