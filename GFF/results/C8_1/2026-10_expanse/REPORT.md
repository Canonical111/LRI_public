# C8(1) of the 1D long-range Ising model: Expanse result (2–3 October 2026)

Convention ε = 2s − 1, Δ_ℰ = Σ C_n(1) εⁿ.

## Result

**C8(1) = 8,066,723, sampling SE 8,015, pre-registered empirical allowance ±33,000**, quoted as
**C8(1) = (8.067 ± 0.033) × 10⁶** (0.41 %).

- **Allowance rule** (PLAN.md, fixed before production): ceil_2sf of the largest of the following candidates.
  It is empirical, not a rigorous bound.

  | Candidate | Value |
  |---|---|
  | 4 SE | 32,060 |
  | 2|R8| + 4 SE_R8 | 1,007 |
  | 2|R9| + 4 SE_R9 | 428 |
  | Half-split shift | 3,377 |
  | 2 × loop-5 degree step | 5.5 |

- **Sampling.** The bootstrap SE is 7,988. The inter-batch χ² is 2.72 for 3 degrees of freedom. The four batches
  give 8,059,132, 8,089,624, 8,058,723 and 8,059,415, each with SE ≈ 16,000.
- **Ratio trend.** C8/C7 = −25.0, continuing −12.2, −16.1, −19.6, −22.5.

## Composition

| Piece | C8 contribution |
|---|---|
| K (loops ≤ 4, deterministic exact quadrature at degree 24) | 1,531,302.35 |
| Loop 5 (exact all-tree quadrature at degree 14) | −1,297,392.1 (last degree step 12→14: +2.8) |
| Free (power-free, QMC) sector of loops 6–8 | 7,879,524 ± 1,498 |
| Power sector, telescoped degree 1→3→5→6→7→8 | coarse +319,951 ± 3,022; 1→3 −361,923 ± 5,579; 3→5 −5,362 ± 4,514; 5→6 +1,003 ± 1,003; 6→7 −347 ± 545; 7→8 −32 ± 236 |
| Check level 8→9 (never added) | −10 ± 102 |

- **Largest error sources:** L8 refine 1→3 (5,374), L8 refine 3→5 (4,429), L8 coarse (2,436 and 1,611), L7 refine
  1→3 (1,451), L8 free (1,007).
- **Zero-pole controls.** The uncontrolled estimator is 8,029,494 ± 45,978; the frozen controls applied −37,229 and
  cut the SE 5.7×.

## Checks

| Check | Result |
|---|---|
| C2, C3, C4 (deterministic) | Equal to the exact values to 1.3e-12 (C3) and 1.1e-9 (C4) |
| C5 (deterministic, loop 5 at degree 14) | −731.140052 vs exact −731.139477 (−5.8e-4, radial truncation of loop 5) |
| C6 | 14332.254 ± 4.82 vs exact 14331.687033 (+0.12σ) |
| C7 | −322,351.9 ± 139.8 vs C7(1) = −322,549.9 ± 10.1 (+1.41σ combined; +1.2σ vs the truncation-aware −322,524) |
| Radial truncation | R8 = −32 ± 236, R9 = −10 ± 102, tail −4.5 (post hoc): negligible |
| Spurious Laurent poles | 30 columns, max abs(z) = 1.50 |
| Coverage guard | Every active class of loops 6–8 integrated with weight 1 at every level (L8: 21,143 classes) |
| Frozen design | Every source bound to the frozen bundle (counts, multipliers, input hashes, loop-5 input, affine map) |
| Pilot and training seeds | Never reused |

## What changed relative to C7(1)

- One more Taylor slot (NW = 8), loops up to 8 (26,540 eight-loop classes) and 128-bit keys.
- The radial quadrature runs to degree 8 with an 8→9 check. C7 stopped at degree 6; its truncation dominated.
- Loops 2–5 are exact all-tree sums (no sampling). C5 is now a deterministic check.
- QMC uses at least 4,096 points per graph. The pilot showed that 64 points per graph give a skewed sampling
  distribution: a ~4σ shift of the C7-row L7 free contribution, removed at 4,096 points.

## Provenance

- **Code.** `LRI_C8_HPC` branch c8, commit c0ffa63 (Codex inspection APPROVED in round 10); binary sha256
  ffb200d4…. Inventory generators in `gen/`, validated by byte-identical regeneration of L ≤ 7. Kernel
  regressions against the C7 binary are in `validation/`.
- **Frozen design.** `frozen_design/` (prod4_34000): per-graph Neyman counts, replicate and sample multipliers, a
  34k core-hour budget for 4 batches. Built from the pilot (Expanse job 54592020) and the controls in
  `full_affine8.json` (trained on the pilot coarse campaigns).
- **Production.**
  - Four batches of 498 elements: jobs 54597794–54597797, 2026-10-02 15:13 → 2026-10-03 00:08 PDT.
  - Two transient srun step-creation failures (b2 #91, b4 #489), each resubmitted once (54599840, 54608070);
    see `RESUBMISSIONS.txt`.
  - Merges 54608150, 54612308, 54613121, 54613130; final combination 54613132.
- **Compute.** About 25.2k core-hours for all C8 jobs, including development, exact stage, pilot and production,
  within the user's 10–50k budget.
- **Expanse data.** `<SCRATCH>/temp_project/c8_hpc/` (runs/prod4, runs/pilot8,
  runs/exact8*, analysis/v1, designs_frozen, results).
- **Interim record.** The batch-1-only partial combination is `C8_partial_b1.json` (final = false).

## Scope

- The allowance is the registered policy output: an empirical allowance, not a total-error bound. It is
  sampling-dominated here.
- The post hoc truncation assessment (−14 in total) is far below it.
- The numerical errors do not cover shared mistakes of the common graph/renormalization framework.
