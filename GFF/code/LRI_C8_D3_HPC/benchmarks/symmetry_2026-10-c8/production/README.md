# C8(3) production on symmetry (preparation 2026-10-08; run prod1 2026-10-08 to 2026-10-12)

Copied from symmetry `$C8_ROOT/evidence/` (each job's SHA256SUMS checked after the copy). Decisions and readings:
`LRI_C8_D3_HPC_loop/PLAN-REVIEW-LOG.md`, 2026-10-08.

| dir | job(s) | what |
|---|---|---|
| `price/` | 571410, 571412 | design_fallback report variants A/B/C (user chose A: 15,492 core-h, predicted SE 0.87) |
| `freeze/` | 571486, 571488 | design freeze (target SE 1, PC conservative tail rule) and the production plan job scripts |
| `bld_DP/` | 571482 | J-BLD on the production export D_P 4fbd1bae5a88 |
| `val1_P2/` | 571477 | val1 on P2 ab894ca36f98: 38 PASS, 19 SITE_REFUSED (Mac fakes), 0 FAIL |
| `margin_probe1/` | 571479 | margin_probe8 on 34 graphs (top PC-confirmed per sector, controls, class reps): 5 reported deficits |
| `margin_ladder/` | 571518 (571514 failed at start) | fine depth ladder of the 31 deficit levels: all 1.5 → 1.0 crossovers with one zero of f at shift 80; asymptotic 1.000 = alpha |
| `margin_probe2/` | 571516 | margin_probe8 on the 14 steady-xi power candidates not in probe 1: 0 deficits |
| `prod1/` | 571488 plan; lanes 571793… to 573151; merges to 573541 | **the production run: C8(3) = 1602.6052 ± 0.9516**, verified; see `prod1/README.md` |

Margin re-derivation, combined: 48 graphs, 0 real deficits; no proposal-rate change. A probe, not a certificate (flags
around the double-lift and tightest anchors, sampled above budget, one base point).
