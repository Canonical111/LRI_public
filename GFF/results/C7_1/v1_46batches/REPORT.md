# C7(1) of the 1D long-range Ising model: Expanse production, September 2026

Convention: epsilon = 2s − 1. Combined from **46 independent fresh-seed batches** of one frozen, pre-registered design, plus the retained primitive input once.

## Result

| Quantity | Value |
|---|---|
| **C7(1)** | **-322554.2** |
| Sampling SE (includes the retained primitive SE 25.37) | 39.0 |
| Bootstrap SE | 38.1 |
| **Empirical allowance (pre-registered headline, 2 s.f.)** | **±160** |
| Allowance, literal archived policy (ceil to 1000) | ±1000 |
| Result as quoted | **C7(1) = -322554 ± 160** (empirical allowance, not a rigorous bound) |

Allowance candidates (the headline is the maximum plus 0.01, rounded up to 2 significant figures):

| Candidate | Value |
|---|---|
| 4SE | 155.9 |
| half_split_shift | 29.3 |
| refine6 | 49.8 |
| refine7 | 25.1 |

## Consistency checks

- Archive (2026-09-23 package): -323405.3 ± 5861.8; difference z = 0.15.
- Pilot (independent, multiplier 1, ≥32 replicates): -321906.1 ± 3282.8; z = -0.20.
- Inter-batch scatter: χ² = 49.4 for 45 degrees of freedom (per-batch SE excludes the shared primitive).
- Per-batch C7 range: -323168 … -322114; median per-batch SE 202 (predicted 203 plus primitive).
- C5: -731.1585 ± 0.0246 vs exact -731.1395; z = -0.77.
- C6: 14331.5303 ± 0.8977 vs exact 14331.7707; z = -0.27.
- Flags: none (no |z| > 3 in the C5/C6 checks).

## Quadrature resolution (telescoped, C7)

| Degree | C7 prefix | SE |
|---|---|---|
| 1 | -331292.9 | 31.1 |
| 3 | -322610.8 | 37.0 |
| 5 | -322571.9 | 38.8 |
| 6 | -322554.2 | 39.0 |

| Level | C7 contribution | SE |
|---|---|---|
| coarse | -7210.1 | 15.7 |
| refine3 | 8682.1 | 20.2 |
| refine5 | 39.0 | 11.6 |
| refine6 | 17.7 | 3.6 |
| refine7 (degree 6→7; check only, not in the estimate) | 10.0 | 1.3 |

Observation, not a correction: the degree 6→7 check (10.0 ± 1.3) is significantly nonzero. Its ratio to the 5→6 step is 0.56. If the steps keep decreasing geometrically, the whole tail beyond degree 6 is about 23. That is covered by the ±160 allowance, which is set by 4·SE. The estimator stays the pre-registered degree-6 sum.

- Zero-pole control term: -11.0 ± 121.1 in total; uncontrolled estimator -322565.2 ± 123.9.
  - L5: 0.1 ± 1.3
  - L6: -16.7 ± 29.5
  - L7: 5.6 ± 117.4
- Spurious-pole checks: 24 columns, max |z| = 1.85 (L7 column 2).

## Production

- code (workers, planning): LRI_C7_HPC commit 3213ce0 (frozen copy on Expanse); final combine with commit 3129a97 tools
- executable sha256: 33bab738a258f80561f6bb980ec6fa1f0416879b4132eff77276433eeee5518c (GCC 13.3 Spack module, Boost 1.86, x86-64 AMD EPYC 7742)
- design: design_v1.json sha256 fd356a15ecb4cc8eaa829ee9d4a6cfbc8d2e592ce10c1739769a0700fb668fb0e; predicted SE 203.2 per batch; K_max 46
- pilot: independent, multiplier 1, >=32 replicates, seed 2026092501 (design and validation only; not combined)
- batches: 46 (b001-b046), seed_k = int.from_bytes(sha256(b"C7-expanse-2026-09:batch:k")[:8], "little"); stopping rule (iv) K_max reached
- elements: 2530 x 16 CPUs on the shared partition; 2 transient srun step failures (b011#37, b018#13) rerun
- wall clock: 2026-09-25 20:59 to 2026-09-26 06:58 PDT (elements); final combine 1 h 29 min
- cost: 29,725 core-hours (SU) for the batches; about 25 more for the pilot and checks
- machine: SDSC Expanse, account <ACCOUNT>, Slurm 23.02.7

## Scope and limits

- This is an empirical allowance policy, fixed before any production data, not a rigorous interval. Quadrature convergence is assessed by the degree 5→6 level and the degree 6→7 check, inherited lower inputs by the C5/C6 checks.
- Plan acceptance criterion A5 (optimized replay no less accurate than the original, element by element) is **not met**: at degree 7, 9 of 112 replay elements are less accurate (worst 18×, 4.2e-14 relative). The aggregate error is smaller. This is about 1e-10 of the sampling noise and does not affect the result; see docs/NUMERICS.md.
- The final code review loop ended with fix round 5 tested but uninspected (inspection budget exhausted). It changed only the design-input validation, and the frozen design reproduces byte-identically under it.
