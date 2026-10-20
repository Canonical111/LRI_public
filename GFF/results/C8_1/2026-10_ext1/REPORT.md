# C8(1) of the 1D long-range Ising model: extension result, K = 14 (10–13 October 2026)

Convention ε = 2s − 1, Δ_ℰ = Σ C_n(1) εⁿ. Frozen design prod4_34000, batches b1–b14 (seeds 80840001–14), combined
under amendments A1 (docs/EXTENSION_A1.md), A2 (EXTENSION_A2.md) and A3 (EXTENSION_A3.md), closed complete.

## Result

**C8(1) = 8,059,767, sampling SE 4,210, pre-registered empirical allowance ±17,000**, quoted as
**C8(1) = (8.060 ± 0.017) × 10⁶** (0.21 %).

- **Allowance rule** (PLAN.md, unchanged): ceil_2sf of the largest candidate. It is empirical, not a rigorous bound.

  | Candidate | Value |
  |---|---|
  | 4 SE | 16,838 |
  | Half-split shift | 4,316 |
  | 2\|R8\| + 4 SE_R8 | 524 |
  | 2\|R9\| + 4 SE_R9 | 499 |
  | 2 × loop-5 degree step | 5.5 |

- **Sampling.** The bootstrap SE is 4,140. The inter-batch χ² is 8.49 for 13 degrees of freedom. Half splits give
  8,055,451 and 8,064,082.
- **Ratio trend.** C8/C7 = −24.99, continuing −12.2, −16.1, −19.6, −22.5.

## The three quoted results

| Result | Batches | C8(1) | SE | Allowance |
|---|---|---|---|---|
| Original (results/2026-10_expanse) | b1–b4 | 8,066,723 | 8,015 | 33,000 |
| A1 close, 12 Oct (deadline 18:21, snapshot 19:14 EDT; C8_A1_close/, interim) | b1–b9 | 8,061,480 | 5,300 | 22,000 |
| **A3 final (C8_final_A3/)** | **b1–b14** | **8,059,767** | **4,210** | **17,000** |

The A1 result is the combination fixed by the A1 rule (at the A1 close, from the closing snapshot: b10 57.7 %
complete, b11–b14 untouched); it is reported, not quoted as final.

**Inclusion rules.** A1 (10 October) planned b5–b14 with a 48-hour deadline: no element starts after T0 + 48 h,
running elements finish, and once all lanes have ended each batch with all planned checkpoints present is included
(the A1-close snapshot: deadline 18:21:25, last lane end 19:12:17, snapshot 19:14:27 EDT); a finishing wave only for
batches already started. A2 (12 October, user decision after the b1–b5 … b1–b8 interims had
been seen, on grounds of precision) overrode this: complete all of b10–b14. From then on the target was all fourteen
planned batches, included on completion; A3 changed only the machine for b12–b14. The design and the allowance rule
are unchanged throughout.

## Vendor of each batch

| Batches | CPU | Site |
|---|---|---|
| b1–b4, b12–b14 | AMD EPYC 7742 | Expanse (shared, 16-core elements) |
| b5–b11 | Intel Xeon Gold 6148 | symmetry (lane8 whole-node lanes) |

Each batch ran wholly on one vendor. Post hoc (not pre-registered) vendor split, inverse-variance means of the per-batch
estimates: AMD 8,063,282 ± 5,975, Intel 8,056,245 ± 5,918, difference 7,037 ± 8,410 (0.84σ).

## Composition

| Piece | C8 contribution |
|---|---|
| K (loops ≤ 4, deterministic) | 1,531,302.35 |
| Loop 5 (exact all-tree quadrature, degree 14) | −1,297,392.1 |
| Free (QMC) sector of loops 6–8 | 7,879,087 ± 791 |
| Power sector, degree 1→3→5→6→7→8 | coarse +316,544 ± 1,690; 1→3 −364,982 ± 2,887; 3→5 −4,590 ± 2,346; 5→6 −26 ± 528; 6→7 −202 ± 321; 7→8 +26 ± 118 |
| Check level 8→9 (never added) | −113 ± 68 |

- **Resolution sequence** (C8 by top degree): 8,429,541 (1), 8,064,559 (3), 8,059,969 (5), 8,059,943 (6),
  8,059,740 (7), 8,059,767 (8).
- **Zero-pole controls.** The uncontrolled estimator is 8,048,689 ± 23,730; the frozen controls cut the SE 5.6×.

## Checks

| Check | Result |
|---|---|
| C3, C4 (deterministic) | Equal to the exact values to 1.3e-12 and 1.1e-9 |
| C5 (deterministic) | −731.140052 vs exact −731.139477 (−5.8e-4, radial truncation of loop 5) |
| C6 | 14,332.82 ± 2.52 vs exact 14,331.687 (+0.45σ) |
| C7 | −322,495.6 ± 74.4 vs C7(1) = −322,549.9 ± 10.1 (+0.72σ combined); it was +1.41σ at K = 4 and +2.23σ at the A1 close (K = 9) |
| Radial truncation | R8 = +26 ± 118, R9 = −113 ± 68 (post hoc; inside the allowance) |
| Spurious Laurent poles | Exact zeros, used as the zero-pole controls. 30 columns, max \|z\| = 2.18 (4 columns above 2, in two pairs that move together at every stage: L7 cols 12/13, L8 cols 1/9); Σz² = 39.8 is descriptive only (correlated columns); no flag |
| Control correction on C8 | +11,078 ± 24,734 (controlled − uncontrolled; SE from the per-loop terms): consistent with zero, but it does not exclude a nonzero pole expectation at the allowance scale. Finite-degree control errors are refined with the levels and enter the R8, R9 terms of the allowance (assessed empirically, not bounded); a failure of the exact pole identity would be a framework error outside the allowance |
| Flags | none |
| Coverage guard | Every active class of loops 6–8 integrated with weight 1 at every level (L8: 21,143 classes) |
| Mechanical inclusion | All 14 planned batches complete and included (extension closed, none omitted) |

External comparison: the HT extrapolation 8.0655(50)×10⁶ differs by −5,700 (−0.88σ).

## Operations (A3 on Expanse, A2 on symmetry)

- b10, b11 (symmetry queue_a2): 996/996 elements, no failures; b10 merged 12 Oct 21:42, b11 13 Oct 05:09 EDT. One
  preq lane (573599) was preempted after 11 minutes; its two elements were taken over and completed.
- b12–b14 (Expanse, arrays 54876752, 54877010, 54877012, submitted 12 Oct 15:13 EDT under the early export gate, a
  scheduling estimate rather than a guarantee; the A1-close snapshot later recorded b12–b14 untouched by A1 workers,
  as the close requires).
- 15 elements failed before doing any work and were rerun with `submit_expanse.sh resubmit` (records_expanse/
  A3_RESUBMISSIONS.txt), each on its first rerun:
  - b12 #342, 343, 355, 356, 360, 361 and b13 #136, 137: node <NODE> (Lmod: module cpu/0.21.2a unknown); pending
    tasks were then given ExcNodeList=<NODE>;
  - b14 #475–481: srun "Unable to create step ... Unexpected message received" (a scheduler fault at 03:55 PDT).
- The afterok merges could therefore not run; they were cancelled while pending and replaced by
  `submit_expanse.sh merge` (manual merges 54894060, 54894069, 54894262), each after its batch was complete.
- An Expanse Lustre incident (OST I/O errors, ~80 nodes drained, 13 Oct ~02:00 EDT) paused the arrays; no task ended
  abnormally.
- Imports (`cluster/a3/import.sh bd13a63`): b12, b13, b14 staged 08:40, 09:01, 09:58 EDT (6,622 files each; about
  20 minutes per batch); early checks c8x-a3check 574113, 574130, 574144 passed.
- Close: job 574145 (defq, <NODE>), 10:03–10:43 EDT; queues finalized, b12–b14 verified (receipts A3_verified_*.json),
  installed and re-validated, combined with `--closed`, published as results/C8_final_A3.

## Files

- `C8_final_A3/`: C8_final.json (sha256 115d614f…c32ad763, equal to symmetry's), combined_assembly.json, A3_close.json.
- `C8_A1_close/`: the A1-close snapshot and the A1 interim combination.
- `records_symmetry/`, `records_expanse/`: markers, job lists, journals, Expanse manifests, close and A1-close logs.
- Paths inside the JSON files are relative to their directory on symmetry (<SCRATCH>/c8_hpc/results/...).
