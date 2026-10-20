# C8(2) L8 pilot: analysis and the production cost table (2026-10-06)

This is the post-pilot design and decision step (`docs/DESIGN.md`, "After the pilot"; `docs/HPC.md`, "Pilot runbook",
step 4) for the exact L8 pilot on symmetry.

- Campaign: `<SCRATCH>/c8-d2/pilot1-20261006-ba68f401e46e`.
- Export: `<SCRATCH>/c8d2/pkg/ba68f401e46e`, which is commit ba68f40.
- Seed: 3049594997687674958.
- Jobs: lane workers 570638-570640 on <NODE>/<NODE>/<NODE>, merge 570641.

**Nothing was planned or submitted for production, and no seed was drawn.** The pilot's data were only read.

Two sharedq jobs did the work, using 0.455 core-hours of the 20 allowed:
- **570669** (`scripts/pa.slurm`, 404 s): status, verify, accounting, the two design reports, eight freezes, the bundle
  reports and `scripts/pa_analysis.py`;
- **570672** (`scripts/pa2.slurm`, 10 s): the heavy-tail context, `scripts/pa_tails.py`.

`scripts/pa_tables.py` builds `cost_table.json` and `cost_table.md` from the committed evidence on the Mac.

Site rules: these jobs ran on symmetry only, in sharedq with `--no-requeue`, `--mem`, `--time` and `c8d2-` names. No
AMD-pool job was used. No other job was touched.

## 1. The cost table (the user chooses from this)

`design.py freeze` was run (non-test) on this pilot at the four relative targets of |C8| = 4.6e4 (the
`--c8-magnitude` default; the pilot measured 45,620, 0.8% below):
- **(a) the exact path**, with no extra options;
- **(b) route (b) for the approved `dd+mp256` profile**, with these options:
  - `--approved-numerics-change "user check-in 2026-10-05: dd+mp256 approved for production after the pilot (C62d PLAN-REVIEW-LOG)"`;
  - `--cost-model cost_models/gmp_symmetry_amd_c8_dd+mp256.json` (`18e50440…`);
  - `--numerics-gate benchmarks/symmetry_2026-10-c8/s6fix4/s4flag.570574.0/jflag_dd+mp256/numerics_flags.json` (`42e6d2d8…`).

Every freeze also had these options:
- `--spent-core-hours 2157`: the development total of about 1,930, plus the pilot's 226.87 allocated core-hours rounded
  up;
- `--total-cap 1000000`: chosen so that it does not bind (the largest design plus the spent hours is 148,674);
- `--seeds-log $C8_SEEDS`: 119 seeds, the pilot's included, all forbidden in the bundles.

Every bundle has these properties:
- **K = 1** is its minimum batch count;
- every per-batch cap holds:
  - at most 6.52 × 10^6 tasks per campaign;
  - at most 59,618 checkpoints;
  - longest predicted task 50-60 s;
  - longest index 1.50 h of an 8-core lane;
- `design.py report --bundle` recomputes its SE from its counts and **agrees**.

The table's columns:
- **Core-hours** are the freeze's own: lane core-hours at the pilot's measured **η_node = 0.837** (`accounting.py`;
  section 2).
- **Wall** is a lane schedule on N amdq nodes of 8 × 8 lanes (`pa_analysis.py`). Each index is sized as
  `production.py plan` sizes it (≤ 1.5 h at 8 threads × 0.9), and the heaviest index goes first onto the lane that frees
  first. Two models are given:
  - "steady" runs indices at the pilot's in-index efficiency 0.990, so the only idle time is the schedule's own tail;
  - in parentheses, every index is stretched by the pilot's η_node instead. This model is pessimistic: it counts the
    pilot's own tail on top of the schedule's tail.
- **Expanse SU** = core-hours × the bundle's work under `cost_models/gmp_expanse_amd_c8.json` divided by its work under
  `gmp_symmetry_amd_c8.json` (same counts, r and s; the same η_node is assumed, since Expanse has no measured lane
  η_node for a long campaign).

| Route | Target (SE) | Predicted SE (rel. to 4.6e4; to the pilot's 45,620) | Lane core-h (η_node 0.837) | K | Replicates r (free L8, power L8; others) | Points | Indices | Tasks | Wall 4 / 8 / 16 nodes, h (steady; design-η) | Expanse SU (× ratio) | Stand-in core-h (ratio) |
|---|---|---|---:|---:|---|---:|---:|---:|---|---:|---:|
| exact | 1e-3 (46.00) | 46.00 (1.00e-3; 1.01e-3) | **2,552** | 1 | 32, 32; 64/128 | 4.47e10 | 216 | 2.18e6 | 9.3 / 5.3 / 2.7 (11.0 / 6.2 / 3.2) | 2,405 (×0.943) | 1,702 (×1.50) |
| exact | 5e-4 (23.00) | 23.00 (5.00e-4; 5.04e-4) | **9,698** | 1 | 128, 64; 128 | 1.95e11 | 764 | 5.63e6 | 32.7 / 16.4 / 8.2 (38.7 / 19.4 / 9.7) | 9,115 (×0.940) | 5,740 (×1.69) |
| exact | 2.5e-4 (11.50) | 11.50 (2.50e-4; 2.52e-4) | **38,792** | 1 | 128, 128; 128 | 7.80e11 | 3,003 | 6.44e6 | 128.7 / 64.4 / 32.9 (152.3 / 76.2 / 38.9) | 36,460 (×0.940) | 22,961 (×1.69) |
| exact | 1.35e-4 (6.21) | 6.21 (1.35e-4; 1.36e-4) | **146,517** | 1 | 128, 128; 128 | 2.77e12 | 11,291 | 1.24e7 | 484 / 243 / 122 (573 / 287 / 144) | 137,515 (×0.939) | 74,573 (×1.96) |
| `dd+mp256`, route (b): exact allocation kept | 1e-3 (46.00) | 46.00 (1.00e-3; 1.01e-3) | **943** | 1 | 32, 32; 64/128 | 4.47e10 | 91 | 2.18e6 | 4.0 / 2.7 / 1.4 (4.8 / 3.1 / 1.6) | n/a | 638 (×1.48) |
| `dd+mp256`, route (b): exact allocation kept | 5e-4 (23.00) | 23.00 (5.00e-4; 5.04e-4) | **3,616** | 1 | 128, 64; 128 | 1.95e11 | 296 | 5.63e6 | 12.2 / 6.8 / 4.0 (14.4 / 8.0 / 4.8) | n/a | 2,241 (×1.61) |
| `dd+mp256`, route (b): exact allocation kept | 2.5e-4 (11.50) | 11.50 (2.50e-4; 2.52e-4) | **14,465** | 1 | 128, 128; 128 | 7.80e11 | 1,129 | 6.19e6 | 47.9 / 24.6 / 12.3 (56.7 / 29.1 / 14.6) | n/a | 8,963 (×1.61) |
| `dd+mp256`, route (b): re-optimized | 1.35e-4 (6.21) | 6.21 (1.35e-4; 1.36e-4) | **52,326** | 1 | 128, 128; 128 | 2.61e12 | 4,043 | 6.87e6 | 174 / 87 / 44 (206 / 103 / 52) | n/a | 29,328 (×1.78) |

Notes on the table:
- **Route (b) costs ×0.370 / 0.373 / 0.373 / 0.357 of the exact path.** On the stand-in it cost ×0.375 / 0.390 / 0.390 /
  0.393.
- **Route (b)'s choice between its two branches** (`route_b_choice`, F13): it kept the exact path's allocation at 1e-3,
  5e-4 and 2.5e-4. There the re-optimized branch cost 965 / 3,860 / 15,440. At 1.35e-4 it re-optimized (52,326, against
  54,790 for the kept allocation). The exact freezes kept the F11 start ("smallest"); both starts reached the same
  final cost.
- **Allocation at the steady walls**, the core-hours a run would actually hold (wall × 64 × N; an upper bound, because a
  worker exits when its lanes find nothing left to claim):

  | Bundle | 4 nodes | 8 nodes | 16 nodes |
  |---|---:|---:|---:|
  | exact 1e-3 | 2,390 | 2,697 | 2,779 |
  | exact 5e-4 | 8,370 | 8,373 | 8,383 |
  | exact 2.5e-4 | 32,942 | 32,985 | 33,684 |
  | exact 1.35e-4 | 123,963 | 124,260 | 124,852 |
  | `dd+mp256` 1e-3 | 1,029 | 1,361 | 1,397 |
  | `dd+mp256` 5e-4 | 3,122 | 3,462 | 4,123 |
  | `dd+mp256` 2.5e-4 | 12,264 | 12,608 | 12,614 |
  | `dd+mp256` 1.35e-4 | 44,477 | 44,732 | 44,919 |

  At 5e-4 and tighter these are 0.85-0.87× the design core-hours (1e-3: 0.94-1.09×, a short run where the tail matters). The design figure keeps the pilot's 3-node tail inside
  η_node (section 2), so it is the conservative number, and it is the one the freeze and the budget gate use.
- **Expanse.** The exact path costs ×0.939-0.943 the symmetry core-hours in SU.
  - **`dd+mp256` is gated on symmetry only** (gate 570574, GCC 11.4, build `a46f3060…`). Expanse has neither a gate
    record nor a cost model for it, so route (b) has no Expanse row.
  - The Stage-4c Expanse factors (×0.452-0.467 of the default) would put it near 1,100 / 4,200 / 16,600 / 64,000 SU.
    This is indicative only and not authorized.
  - **`GMP_PREFIX` is not cleared for production** (Y1). Every figure here is for the default GMP build.
- **Walls at 8 or 16 nodes need a new H7/H11 window.** The development cap is 4 live `c8d2-` AMD-pool jobs, and the
  pilot window was 5. Running 8 or 16 needs the user's go and C63d's agreement. amdq had about 14 reachable nodes at the
  survey (`../survey/`).
- **Batches.** K = 1 is the minimum everywhere. A design split into more batches costs the same in total.

## 2. Pilot accounting

`tools/accounting.py` (`pa.570669.0/accounting.json`) is **complete**, with 5 sacct records:

| Job | Role | Node | Elapsed | Core-h |
|---|---|---|---:|---:|
| 570635 | plan | sharedq <NODE> (4 physical cores) | 52 s | 0.058 |
| 570638 | lane | amdq <NODE> | 3,207 s | 57.01 |
| 570639 | lane | amdq <NODE> | 4,813 s | 85.56 |
| 570640 | lane | amdq <NODE> | 4,729 s | 84.07 |
| 570641 | merge | amdq <NODE> | 9 s | 0.16 |
| **total** | | | | **226.87** (lanes 226.65, overhead 0.22) |

**Efficiencies:**
- **Busy thread time** is 189.73 core-h. This is the sum of the 1,534 blocks' threads × integration seconds, taken from
  the validated `merged.json` files.
- **η_node = busy / lane core-h = 0.8371.** It factors into two parts:
  - **lane occupancy 0.845:** the summed index lane walls are 191.56 lane core-h out of 226.65;
  - **in-index efficiency 0.990.**
- **η_omp,g:** 0.992-0.994 at L8, 0.995-0.996 at L7, and 0.93-0.99 at L3-L6.
- **Why η_node is below J-SMK-4's 0.915: the pilot's tail.** Worker 570638 drew the three b_power_L8 indices
  (3,184-3,207 s) and the short L3-L7 indices. Its other five lanes were idle after at most 1,105 s, but they stayed
  allocated for the job's 53 minutes. A production batch with hundreds or thousands of indices has a much smaller
  tail; that is the steady model of section 1.

**Measured against the plan's estimate of 179.9 core-hours** (`pa_analysis.json`, `per_index` and `per_group`):

| Quantity | Estimate | Measured | Ratio |
|---|---:|---:|---:|
| work (cost-model core-h; measured: busy thread core-h) | 179.9 | 189.7 | ×1.055 |
| free L8 (a / b) | 67.14 / 57.10 | 72.44 / 61.51 | ×1.079 / ×1.077 |
| power L8 (a / b) | 26.62 / 22.21 | 27.82 / 21.22 | ×1.045 / ×0.956 |
| L7 (free a, b; power a, b) | 2.50, 2.09; 1.18, 0.93 | 2.44, 2.09; 1.12, 0.94 | ×0.95-1.01 |
| lane wall of the 19 L8 indices (est / (8 × 0.9)) | 24.04 lane-h | 23.10 lane-h | ×0.961 (per index 0.86-1.01) |
| lane wall of the 4 L7 indices | 0.93 lane-h | 0.83 lane-h | ×0.892 |
| the largest index (a_free_L8, 34,531 core-s) | 4,796 s | 4,693-4,728 s | ×0.98 |
| allocated (3 nodes) | about 256 (`../plan/pilot_lanes.json`) | 226.87 | ×0.89 |
| wall | 1.33 h | 1.34 h (14:09:43-15:29:56 EDT; merge 9 s) | |

The symmetry cost model (J-SWEEP-2) under-estimates the free L8 work by 7-8%. The lanes ran at 0.99 in-index efficiency
against the planner's assumed 0.9, so the walls came in 4% under the estimate. Every per-graph c_g of the design is the
pilot's own measurement on EPYC 7543 (<NODE>/094/108), so none of this enters the design as an error.

## 3. Diagnostics

### The pilot result (`../pilot_copy/C8_result.json`; `verify_result.py`: verified, problem_count 0; `production.py status`: exit 0)

- **C8_full = 45,620.18 ± 214.16** (sampling SE; relative 4.69e-3).
  - Campaigns: a = 45,483.3 ± 328.5, b = 45,757.0 ± 274.9. They differ by 273.7 ± 428.2 (0.64σ).
  - The bootstrap SE (diagnostic) is 202.3, with bias +0.94.
- **Power correction −42.85 ± 37.33** (diagnostic pull −1.15, not a gate). The power-free part is 45,663.03 ± 210.86.
- **The hard gates pass:** top slot, loop 7 and affinity.

**Lower-order checks** (diagnostics; no flag):

| Order | Estimate | SE | Reference | Pull |
|---:|---:|---:|---|---:|
| 3 | −0.874595 | 0.00129 | −0.8748500 (archived closed form) | +0.20 |
| 4 | 5.03802 | 0.0172 | 5.0488684 (archived closed form) | −0.63 |
| 5 | −39.0848 | 0.176 | −38.833646 (archived closed form) | −1.43 |
| 6 | 364.910 | 1.21 | 362.36647 ± 0.0008 (C6(2) production M=8192) | **+2.11** (secondary, archived MC 362.349 ± 0.153: +2.11) |
| 7 | −3869.44 | 18.6 | −3876.126 ± 0.524 (C7(2) production) | +0.36 |

The largest pull is C6's 2.1σ. That is one of five checks; for five Gaussian pulls, P(max |pull| ≥ 2.11) ≈ 16%.

**Power null rows** (|pull| > 3 would be flagged; none is): order 4 −0.97, 5 **−2.02**, 6 −0.05, 7 +0.14. Order 3 is
zero at rounding level by the weights.

**Where the variance comes from** (`error_by_loop`; the pilot's uniform allocation of 8 × 4,096 points per graph),
against the pilot's own cost (busy thread core-h per (sector, L)):

| (sector, L) | variance share | SE contribution | cost share |
|---|---:|---:|---:|
| free L7 | **71.3%** | 180.8 | 2.4% |
| free L8 | **18.0%** | 90.7 | **70.6%** |
| free L6 | 4.2% | 44.0 | 0.03% |
| free L5 | 3.0% | 37.1 | < 0.01% |
| power L7 | 1.4% | 25.3 | 1.1% |
| power L8 | 0.9% | 20.6 | **25.8%** |
| power L6 | 0.6% | 16.6 | 0.04% |
| free L4, free L3, power L5, power L4, power L3 | 0.31%, 0.15%, 0.10%, 0.01%, < 0.01% | 12.0, 8.4, 6.8, 2.5, 0.29 | ≈ 0 |

The Neyman design moves the points to where variance per cost is largest. For the exact 1e-3 design (and similarly at
every target):

| Stratum | cost share | variance share |
|---|---:|---:|
| free L8 | 67% | 65% |
| free L7 | 18% | 21% |
| power L8 | 13% | 4.7% |
| power L7 | 1% | 3.6% |
| free L6 | 0.2% | 2.3% |

Free L7 gets s = 4 / 16 / 64 / 256 at the four targets, with r = 128. Free L8 gets s = 2 / 2 / 8 / 32, with r = 32 at
1e-3 and 128 at the others.

### The design report (`pa.570669.0/report_exact.txt`, `report_exact.json.gz`; route (b): `report_ddmp256.txt`)

The target table (predicted SE with the margin 1.5) gives exactly the freezes' numbers:
- exact: 2,551.5 / 9,698.0 / 38,792.2 / 146,517.0 core-h;
- `dd+mp256`: 943.0 / 3,616.3 / 14,465.4 / 52,325.5 core-h, with the branch per target as in section 1.

Per stratum (pilot, 8 replicates × 4,096 points):

| Stratum | graphs | kurtosis | skewness | largest single-graph share | P8 |
|---|---:|---:|---:|---:|---:|
| free L5 / L6 / L7 | 152 / 790 / 4,882 | −0.66 / −0.61 / −0.63 | ≈ 0 | 0.21 / 0.037 / 0.0048 | 1.08 / 1.10 / 1.09 |
| free L8 (non-primitive) | 31,632 | −0.59 | ≈ 0 | 0.0033 | 1.107 |
| free L8 primitives | 496 | −0.72 | −0.05 | 0.012 | 1.077 |
| power L5 / L6 / L7 | 40 / 214 / 1,418 | −0.69 / −0.40 / **−0.27** | ≈ 0 | 0.33 / 0.060 / 0.055 | 1.12 / 1.15 / **1.26** |
| power L8 | 8,672 | **−0.01** | ≈ 0 | 0.0081 | **1.428 FLAG** |

Reading the table:
- **Kurtosis.** The column is the excess kurtosis of the standardized replicate values, pooled over graphs and
  campaigns. For Gaussian replicate means at 8 replicates it is −0.67 (simulated; t5: −0.42, t3: −0.21). So the free
  strata look Gaussian at the replicate level, power L7 has t3-like replicate means, and power L8 is heavier.
- **Largest |z|** is bounded at 2.47 for 8 replicates and is not informative.
- **Alpha:** no nested pilot was run, so α = 0.5 is assumed for every stratum (the report says so).

**P8, per sector** (C63d's action 4, pooled over the L8 graph-campaigns at 4,096 points):
- free: **1.106** over 32,128 graph-campaigns. This is below 1.13, so there is no advice.
- power: **1.428** over 8,672 graph-campaigns. This is above 1.13, so **R = 16 is advised**.

**P8, per stratum** (action 5): power L8 is **flagged** (1.428 > 1.196 with at least 500 graph-campaigns). Every bundle
already gives power L8 r = 32 / 64 / 128 / 128 replicates, above C63d's R = 8 and R = 16. As `docs/DESIGN.md` says, P8
changes no freeze parameter here.

### Heavy tails (C63d's rule; thresholds on L8 only)

`report_exact.txt`, `tails.csv.gz`, `pa2.570672.0/pa_tails.json`.

**The screen flags most of L8.** Of the 20,400 L8 graphs, **14,222 are screened** (Hill ξ̂ > 0.38 or largest share
> 0.05 in either campaign):
- **9,886 of the 16,064 free L8 graphs (61.5%; the 248 primitives included);**
- **all 4,336 power L8 graphs.**

**Confirmed "possible infinite variance": 0**, since no pilot graph has the 32,768 points per replicate that
confirmation needs. **Undefined: 0.**

ξ̂ per graph-campaign (median; 10%-90%; share above 0.38):

| Stratum | ξ̂ median | 10%-90% | above 0.38 | largest share, median |
|---|---:|---|---:|---:|
| free L8 | 0.51 | 0.17-1.29 | 60% | 0.076 |
| power L8 | 1.80 | 1.24-2.31 | 100% | 0.72 |
| free L7 (diagnostic) | 0.45 | 0.14-0.94 | 54% | |
| power L5 (diagnostic) | 0.53 | | | |
| power L6 (diagnostic) | 0.90 | | | |
| power L7 (diagnostic) | 1.36 | | | |
| free L3 to L6 (diagnostic) | 0.05-0.18 | | | |

The screened free L8 graphs carry:
- 83% of the stratum's Neyman weight Σσ_g√c_g, i.e. of its design cost and variance at the optimum;
- 64% of its Σσ_g²;
- 94% of its cost.

**ξ̂ is unrelated to the per-graph standard deviation.** Its Spearman correlation with σ_g is −0.05 at free L8 and −0.15
at power L8. It is almost the same statistic as the largest share (Spearman 0.985 at free L8). So it tracks single-point
spikes of t within a replicate, not the graphs that carry the variance.

The same statistics appear at L7 and in power L5-L7. C7(2) integrated those with this integrand: its production pulls
were all below 1.7σ, and this pilot's C7 pull is 0.36. And the free strata's replicate means are Gaussian-like (above).
This suggests that at d = 2 the d = 3-calibrated screen mostly measures per-point spikes, not a failure of the
replicate-level error. **This is for the user to judge, not a conclusion of the rule**, which says only "screened,
listed, stays in the design".

**Confirmation coverage of the bundles** (L8 graph-campaigns at ≥ 32,768 points per replicate, counts × s):

| Bundles | screened free L8 graphs with both campaigns at ≥ 32,768 points | power L8 |
|---|---|---|
| 1e-3 and 5e-4 (both routes) | 453 of 9,886 | 75 of 4,336 |
| 2.5e-4 | **all 9,886** (minimum 32,768) | 362 |
| 1.35e-4 | **all 9,886** (minimum 131,072) | 1,059 (exact), 1,086 (`dd+mp256`) |

So a production batch at 2.5e-4 or tighter would itself confirm or clear the free L8 screen
(`design.py report --pilot <that batch>`). At 1e-3 or 5e-4 that would need a follow-up pilot at ≥ 32,768 points.

**User decision** (`docs/DESIGN.md`, step 2): proceed, nest, or drop a confirmed graph. Dropping one changes the
estimand and is the user's call only.

## 4. Against the stand-in projections

The Stage-6 stand-in tables had these lane core-hours (`../../pre6b/p6b_tables.json`; J-DES-5's strata from J-SWEEP-2,
at J-SMK-4's lane η_node 0.9146):
- exact: 1,702 / 5,740 / 22,961 / 74,573;
- route (b): 638 / 2,241 / 8,963 / 29,328.

The fix-round-4 re-freeze 570579, with the re-measured profile model, gave 639 / 2,251 / 9,002 / 29,473.

**The pilot's designs cost ×1.50 / 1.69 / 1.69 / 1.96 (exact) and ×1.48 / 1.61 / 1.61 / 1.78 (route (b)) as much.**
`pa_analysis.py` splits the per-graph continuous Neyman bound
cost = 1.5² (Σ_g ½ σ_g √(c_g/η_omp,g))² / (SE² η_node) into three factors:

| Factor | Value | What changed |
|---|---:|---|
| η_node | ×1.093 | 0.9146 (J-SMK-4, one node, 1.4 h) → 0.837 (the pilot, with its 3-node tail; section 2) |
| cost (c_g / η_omp,g: the pilot's measured seconds against J-SWEEP-2's) | ×1.036 | free L8 ×1.062, free L7 ×0.98, power L8 ×1.00 |
| **variance** (Σσ_g√c, the pilot's σ against J-SWEEP-2's at the pilot's c) | **×1.831** | free L8 ×1.81, free L7 ×1.57, power L8 ×3.37, power L7 ×2.61 |
| total | **×2.07** | bounds: stand-in 949 / 3,796 / 15,185 / 52,074 → pilot 1,968 / 7,873 / 31,490 / 107,992 |

**The variance factor is mostly an estimator effect, not larger variances.** The unbiased per-point variance sums Σσ_g²
are not larger in the pilot: free L8 ×0.95, free L7 ×0.85, power L8 ×0.86. The Neyman weight, however, sums per-graph
*standard deviations*:
- J-SWEEP-2 estimated each σ_g from **2 replicates × 512 points (1 degree of freedom)**, and E[σ̂]/σ = 0.798 for
  Gaussian replicate means at ν = 1;
- the pilot used **8 × 4,096 points (ν = 7)**, where E[σ̂]/σ = 0.965;
- that alone is a factor (0.965/0.798)² = **1.46**. The spiky integrand of section 3 makes a 2-sample σ̂ low more often
  still, which gives the rest.

**The stand-in designs were also further above their own bound** (×1.79 / 1.51 / 1.51 / 1.43). Their 1-dof σ̂ put many
graphs on the 4,096-point floor. The pilot's designs are ×1.30 / 1.23 / 1.23 / 1.36 of their own bound, so the design
ratios are below 2.07.

**The 1.35e-4 column is the highest** because of the power-of-two lattice. From 2.5e-4 the SE must fall ×1.85, which is
a variance factor of 3.43. The pilot's allocation reaches it at ×3.78 in cost (r is at 128 everywhere, so only s moves);
the stand-in's reached it at ×3.25.

Route (b)'s ratio to the exact path is unchanged in kind: ×0.357-0.373 now, ×0.375-0.393 before.

**What this means for the realized SE.** With σ_g estimated from 8 replicates, a design that allocates n_g ∝ σ̂_g and
predicts its SE from the same σ̂_g is still optimistic:
- for Gaussian replicate means the realized variance is about E[X^(−1/2)] / E[X^(1/2)] = 1.17 times the prediction at
  ν = 7, i.e. **SE about ×1.08**;
- heavy tails make it more;
- the margin 1.5 is meant to cover this (C8(1): realized 1.56× its pilot prediction).

The stand-in's ν = 1 σ̂ would have under-delivered far more. Its tables were optimistic in both cost and realized SE.

## 5. The bundles

All eight are at `<SCRATCH>/c8-d2/designs/<name>`. Each is atomic and never overwritten. Each
`design_meta.json` sha256 is that bundle's identity. Copies of `design.json` and `design_meta.json` are in
`pa.570669.0/`, every counts file's sha256 is in `pa.570669.0/bundles.sha256`, and all eight bundles are in
`pa.570669.0/bundles.tgz`.

| Bundle | design_meta.json sha256 | numerics |
|---|---|---|
| `pilot1-20261006-exact-1e-3` | `2a669726ce08f26a…` | exact |
| `pilot1-20261006-exact-5e-4` | `852d92cdc9599529…` | exact |
| `pilot1-20261006-exact-2.5e-4` | `8cc101c7ba68fee7…` | exact |
| `pilot1-20261006-exact-1.35e-4` | `46f373afde70306e…` | exact |
| `pilot1-20261006-ddmp256-1e-3` | `0d323b2f4a321de0…` | `dd+mp256` (route (b), gate 570574) |
| `pilot1-20261006-ddmp256-5e-4` | `6b8a8ea01fafd97e…` | `dd+mp256` |
| `pilot1-20261006-ddmp256-2.5e-4` | `6afb6dd662167f31…` | `dd+mp256` |
| `pilot1-20261006-ddmp256-1.35e-4` | `80280bd6b4203815…` | `dd+mp256` |

These are candidates, not a decision. Production needs the following:
1. the user's choice of target, numerics, sites and K;
2. a fresh seed per batch;
3. a plan job (`slurm/plan.sh … --design <bundle>`);
4. a window.

None of this was done here.

## 6. Unexpected

1. **The heavy-tail screen flags 61.5% of the free L8 graphs and every power L8 graph.** The power sector's P8 of 1.43
   advises R = 16, and the power L8 stratum is flagged (section 3). This is a user decision item.
2. **Production costs ×1.5-2.0 the stand-in tables**, mostly because the stand-in's 2-replicate σ̂ under-estimated the
   per-graph standard deviations (section 4).
3. **Free L7 holds 71% of the pilot's variance at 2.4% of its cost.** The designs shift heavily into L7 (s up to 256).
4. **η_node is 0.837, not about 0.915:** the pilot's own 3-node tail. The design core-hours are therefore about 15%
   above what a long run would allocate (section 1).
5. **The symmetry cost model under-estimates free L8 by 7-8%.** The planner's assumed 0.9 lane efficiency
   (measured: 0.99) more than hides this in the walls.
6. **C6's pull is +2.11** and **power null row 5's pull is −2.02.** Neither is flagged.
7. **Operational slip (no effect).** While checking whether the export directory was writable (the runbook allows
   `--out designs/<name>` inside it), an empty file `x` was created in `<SCRATCH>/c8d2/pkg/ba68f401e46e/` at
   15:33:37 EDT. It was removed at once, after confirming it was the zero-byte probe. No export file changed, only the
   directory's mtime. The bundles went to `<SCRATCH>/c8-d2/designs/` instead, so the export stays equal to its
   archive.

## Files

- `cost_table.md`, `cost_table.json`: the table of section 1 and the stand-in factors (`scripts/pa_tables.py`).
- `scripts/`:
  - `pa.slurm`, `pa_analysis.py` (job 570669);
  - `pa2.slurm`, `pa_tails.py` (job 570672);
  - `pa_tables.py` (Mac).
  - The two jobs ran the read-only uploads in `<SCRATCH>/c8d2/work/pilot-analysis-ba68f401e46e/`, whose
    sha256 are in each job's `inputs.sha256`.
- `pa.570669.0/`, from `<SCRATCH>/c8d2/evidence/ba68f401e46e/pa.570669.0/`:
  - `accounting.json`, `sacct.txt`, `status.txt`, `verify_result.txt`;
  - `report_exact.txt`, `report_exact.json.gz`, `report_ddmp256.txt`, `report_ddmp256.json.gz`, `tails.csv.gz`;
  - the freezes' stdout and `/usr/bin/time`;
  - `design_*.json` and `design_meta_*.json`;
  - `report_bundle_*.txt` and `report_bundle_*.bundle.json` (the bundle block of each bundle report);
  - `bundles.sha256`, `bundles.tgz`;
  - `pa_analysis.json`, `pa_analysis.stdout`;
  - `inputs.sha256`, `pilot_after.sha256` (the pilot's manifest and result unchanged).
- `large_files.sha256`: the uncompressed reports, the full bundle reports and `tails.csv`, which stay on BeeGFS.
- `pa2.570672.0/`: `pa_tails.json` and its stdout.
- `pilot_copy/`: the pilot's `C8_result.json`, `manifest.json`, `submissions.jsonl`, `cpu_vendor.json`,
  `runtime_identity.json` and the worker and merge logs, checked against BeeGFS (`sha256_on_beegfs.txt`).
- `logs/`: the two job logs.
- `sacct.txt`: the two analysis jobs.
