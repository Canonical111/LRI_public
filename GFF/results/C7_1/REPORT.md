# C7(1) of the 1D long-range Ising model: final Expanse result (September 2026)

Convention: epsilon = 2s − 1. The result combines **399 independent fresh-seed batches** of one frozen, pre-registered design with a **direct, verified integration of the 44 L7 primitive classes**.

## Result

| Quantity | Value |
|---|---|
| **C7(1)**, pre-registered degree-6 estimator | **-322549.9** |
| Sampling SE (includes the primitive SE 0.87) | 10.09 |
| Bootstrap SE | 10.11 |
| **Empirical allowance (pre-registered, 2 s.f.)** | **±41** |
| Allowance, literal archived policy (ceil to 1000) | ±1000 |
| **Result as quoted (pre-registered policy)** | **C7(1) = -322550 ± 41** (empirical allowance, not a rigorous bound) |
| Truncation-aware estimate (post hoc, see below) | -322524 ± 38 (2 × [sampling ⊕ measured degree-7 step ⊕ 100 % tail-model uncertainty]) |

Allowance candidates: 4SE 40.4, half_split_shift 12.6, refine6 39.5, refine7 22.5.

Precision history:

| Stage | C7 | Allowance |
|---|---|---|
| Archived package (2026-09-23) | -323405 ± 5862 (SE) | ±24000 |
| 46 batches, retained primitive (2026-09-26) | -322554 ± 39 | ±160 |
| **399 batches, direct primitive (2026-09-28)** | **-322550 ± 10** | **±41** |

## Consistency checks

- Archive: z = 0.15. Result v1: z = 0.11.
- Inter-batch scatter: χ² = 348.9 for 398 degrees of freedom. The replicate-based SEs are reliable.
- Direct vs retained primitive: -696179.47 ± 0.87 vs -696147.45 ± 25.37; z = -1.26.
- Zero-pole control term: -71.6 ± 41.0. Uncontrolled estimator: -322621.5 ± 41.1.
- Spurious-pole checks: 24 columns, max |z| = 2.31. Half-split shift: 12.6.

## Lower-order checks and the degree-6 truncation (pre-registered flag)

The pre-registered check raised a flag: **systematic tension: C5 differs from its reference by -4.15 SE**. At this precision the lower-order coefficients resolve the degree-6 quadrature truncation. The degree 6→7 check level (never part of the estimate) and a geometric tail explain it quantitatively:

| | degree 6 (estimate) | + degree 6→7 step | + geometric tail beyond 7 | reference |
|---|---|---|---|---|
| C5 | -731.17419 ± 0.00836 (z -4.15) | -731.15515 (z -1.88) | -731.14201 (z -0.30) | -731.13948 |
| C6 | 14332.43593 ± 0.30500 (z +2.18) | 14331.98210 (z +0.69) | 14331.62055 (z -0.49) | 14331.77075 |
| C7 | -322549.9 ± 10.1 | -322539.5 | -322523.9 (ratio 0.60) | — |

- References: C5 is the exact closed-form value. C6 is **not** exact: it is the earlier independent six-loop numerical result (reference/long_range_ising_complete.tex, app. C6Numerical), 14331.77075 with sampling SE 0.14344, quoted as 14331.8 ± 0.5. The pre-registered z divides by this run's SE only. Including the reference SE gives C6 z = +1.97 (degree 6), +0.63 (+ step), −0.45 (+ tail).
- With the measured degree-7 step plus the post hoc geometric tail, C5 and C6 move to |z| ≤ 0.5 (≤ 0.3 against the new exact C6, see addendum). This is **conditional consistency with the tail model at the lower orders**, where the last-step ratios are 0.408 (C5) and 0.443 (C6). It does not validate the C7 tail, whose ratio is 0.600, and it does not exclude other systematics in C7.
- The C6 truncation correction here (degree 6 → tail-corrected: −0.815) matches the reference's own degree 6 → degree 10–12 change with its span cutoff (14332.554 → 14331.755, then −0.007: −0.81).
- For C7 the same analysis gives a truncation correction of about **+26**: a measured degree-7 step of +10.40 ± 0.43, plus a geometric tail of +15.59 extrapolated with ratio 0.600 = step7/refine6 = 10.395/17.329. C7 converges more slowly than C5 and C6, so the tail is model-dependent.
- **What ±41 is, and is not.** ±41 is the registered policy output: the maximum of the candidates 4SE 40.4, 2|R6| + 4 SE_R6 39.5, 2|R7| + 4 SE_R7 22.5 and half-split 12.6. It does **not** add the modelled truncation bias to the sampling uncertainty, so it is not a demonstrated total accuracy. The modelled shift (+26) is smaller than 41, but +26 plus 2 sampling SE (≈ 46) exceeds it.
- **Truncation-aware assessment (post hoc, not pre-registered):**
  - E6 = −322549.9 (SE 10.09);
  - adding the measured step gives E7 = −322539.5;
  - adding the modelled tail gives **−322523.9**.
  - Assigning the extrapolated tail a 100 % model uncertainty, the combined 1σ-type uncertainty is 10.09 ⊕ 0.43 ⊕ 15.59 = 18.6, and twice that, in the style of the empirical allowance, is **±38**. The covariance between the estimate and the check level is neglected.
  - The pre-registered interval [−322591, −322509] and the truncation-aware interval [−322562, −322486] overlap.
  - Neither establishes the total error at the ±40 level; that would need degree-8 radial data or an independently validated tail model.
- Beyond this point, more sampling does not help: the degree-6 truncation dominates. The next step would be a degree-7 estimator with a degree-8 check.

## Quadrature resolution (telescoped C7)

| Degree | C7 prefix | SE |
|---|---|---|
| 1 | -331310.0 | 6.1 |
| 3 | -322614.2 | 9.2 |
| 5 | -322567.2 | 10.0 |
| 6 | -322549.9 | 10.1 |

## Production

- code: workers and batch planning: commit 3213ce0 (frozen copy on Expanse); final combine: commit 7320afc tools (PLAN2, Codex-approved)
- executable sha256: 33bab738a258f80561f6bb980ec6fa1f0416879b4132eff77276433eeee5518c
- design: design_v1.json (sha fd356a15…), unchanged for all batches
- batches: 399 included (b001–b400 except b215, whose planning hit a truncated Lustre copy and was never submitted); stop: pre-registered 400-batch cap reached 2026-09-28 01:15 PDT
- primitive: direct campaign primitive/P1: 44 L7 classes, 2^23 points × 64 replicates, −696179.47 ± 0.87 (replaces the retained −696147.45 ± 25.37; z −1.26)
- elements: about 22,000 × 16 CPUs on the shared partition; 17 transient srun step failures, each resubmitted once, all recovered
- wall clock: 2026-09-25 20:59 → 2026-09-28 02:48 PDT (production); final combine 1 h 49 min (16 parallel verifiers)
- cost: about 250k core-hours (SU) for all batches, plus about 20 for P1 and about 60 for the combines
- machine: SDSC Expanse, account <ACCOUNT>, Slurm 23.02.7

## Method in one paragraph

Loops L ≤ 4 are deterministic quadrature (the constant K). Power-free graphs at L = 5–7, including the direct primitive campaign, use randomized quasi-Monte Carlo: scrambled Sobol nets in 2L−1 dimensions over importance-sampled binary cluster trees. Power-containing graphs use Monte Carlo over the tree shape, with deterministic meromorphic Chebyshev quadrature over the radial variables at paired degrees (1→3→5→6, plus the 6→7 check), evaluated on identical trees and telescoped. All errors come from independent randomizations (replicates and batches).

## Scope and limits

- The allowance is an empirical policy, fixed before any data, not a rigorous interval.
- Plan acceptance criterion A5 (optimized replay no less accurate than the original, element by element) is **not met**: at degree 7, 9 of 112 replay elements are less accurate (worst 18×, 4.2e-14 relative), while the aggregate error is smaller. This is about 1e-10 of the sampling noise. See docs/NUMERICS.md.
- The code was reviewed through claudex-loop:
  - PLAN: approved at round 3; 5 inspections; the last fix round (design-input validation only) is uninspected.
  - PLAN2 (direct primitive and parallel combine): approved after 4 plan rounds and 4 inspections.

## Addendum (2026-10-01): C6 reference superseded

The C6(1) cross-check above used the earlier numerical reference 14331.77075 (SE 0.143). That reference is
superseded by the exact all-graph calculation `LRI_C6_1D_HPC/results/2026-09_symmetry`:
**C6(1) = 14331.68703277 ± 4.9e-7**. Its uncertainty is negligible here. This run's C6 by-product against the new
value:

| | this run | − new C6 | z (this run's SE 0.305) |
|---|---|---|---|
| degree 6 (estimate) | 14332.43593 | +0.74890 | +2.46 |
| + degree 6→7 step | 14331.98210 | +0.29507 | +0.97 |
| + geometric tail beyond 7 | 14331.62055 | −0.06648 | −0.22 |

- After the measured degree-7 step and the post hoc geometric tail, both lower-order coefficients agree with their
  references to |z| ≤ 0.3 (C5 −0.30, C6 −0.22). This is conditional consistency with the tail model at the lower
  orders (ratios 0.41 and 0.44). It does not validate the C7 tail (ratio 0.60); see the truncation-aware
  assessment above. A labelled, provenance-linked version of this cross-check is in
  `LRI_C6_1D_HPC/results/2026-09_symmetry/C7_crosscheck.json`.
- The C7 estimate does not use the C6 reference; it enters only this diagnostic. C7(1) = −322550 ± 41 is
  unchanged.
