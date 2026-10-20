# Stage 4c R4b `mp256`: development evidence (Expanse, 2026-10-05; PLAN A-FLAG-3/5, D1)

> **Integration note (2026-10-05, c8 5569c53).** Each profile now defines only `C8_NX_F1_CHECKS_<P>`;
> `src/numerics/numerics.hpp`'s `nx::f1_checks` (`C8_NX_F1_CHECKS`) runs those of every profile in a build (order
> exp1, mp256, dd), so the combination checks all three. The worker executables are unchanged by this
> (`docs/NUMERICS.md`, "Stage 4c gate").

R4b is an **opt-in numerics profile, off by default** (D1). It is built only by `make gmp NUMERICS=mp256` (or a
combination naming mp256) as `bin/c8d2_gmp_mp256`, and a campaign can use it only through `plan --numerics mp256
--approved-numerics-change "<user approval>"`. The code is `src/numerics/mp256.hpp` (branch `flag-mp256`, commit
10b19d9 for every job below). Everything here is **development evidence**: the full-scale J-FLAG gate run (F1–F5 on
one node) belongs to the gate agent.

## What the profile does

A point that fails the binary128 1e-23 test reaches the MP tier. In this profile the tier is staged:
1. `calculate_shared<MP77,true>`, the kernel's own shared-prefix evaluation with the error estimate that the binary128
   tier computes (err = Σ_t Σ_j |c_tj x_j| / U_t / S), at `gmp_float<77>`. GMP rounds the 257 requested bits up to
   whole limbs, so the significands carry 320 bits (`--describe`: `"mpf_precision_bits":320`), against 1,216 for
   `gmp_float<350>`.
2. The value is accepted when |v| ≥ `C8_MP256_RATIO` × err, with the plan's 1e-63; it is then converted to long double
   by Boost, as in the exact tier.
3. Otherwise the point goes to the unchanged 350-digit tier (`nx::mp_tier_exact`).

Both outcomes have `lev = 2`, so the rows' `quad` and `mp` counters mean what they mean in the default build. The
process prints one stderr line at exit with its accepted and escalated counts. The F1 tool also gets
`C8_NX_F1_CHECKS` (counters at every MP-promoted point; see the header comment of `mp256.hpp`).

## Jobs

| Job | What | Result |
|---|---|---|
| 54672884 (`shared` 16, 0:52) | `submit_s4c.sh precheck` of the working tree, profiles `mp256` and `dd,mp256,exp1` | Default `bin/c8d2_decimal` and `bin/c8d2_gmp` byte-identical to the final default binary; both profile builds and their F1 tools compile, no warnings (`precheck/`) |
| 54673623 (`shared` 16, 0:45), export 10b19d9a0ae3 | `submit_s4c.sh build` | **A-RPL-8:** `bin/c8d2_decimal` `99a51c1d…` and `bin/c8d2_gmp` `1d2a2181…`, the final default binary; preprocessed program token-identical to the reference. `bin/c8d2_gmp_mp256` `9e884b1b…`, `bin/c8d2_gmp_dd+mp256+exp1` `0caf1ec8…` (dd, exp1 stubs) (`s4cbuild.54673623.0/`) |
| 54673624 (`shared` 32, 3:57) | `submit_s4c.sh dev mp256`: `numerics_flags.py --profile mp256 --f1-scale 1 --f2-graphs 16 --f4-sample 25 --f4-repeats 2 --f5-threads 1 8 16 --f5-lanes 4 --f5-lane-threads 4` | "development run (would pass)": F1 at **full scale**, F2/F4/F5 at development scales (`s4cflags.54673624.0/`) |
| 54673625 (`compute`, exclusive, 13:03, <NODE>) | `submit_mp256.sh speed`: `mp256_speed.py` | Speed and per-tier timing on the heavy L8 blocks (`mp256speed.54673625.0/`) |
| 54673762 (`shared` 16, 3:01) | `submit_mp256.sh prof`: Stage 4b's `r3a_prof.py`, perf symbol profiles of both executables (informative) | Rows identical; see "Where the 77-digit time goes" (`mp256prof.54673762.0/`) |

## F1 on every MP-promoted point (full scale)

The F1 set is A-RPL-5's point set at scale 1: per sector 200 L7 graphs × 256 points and 400 L8 graphs × 64 points,
153,600 points. The exact path met the need of 10^4 binary128-accepted and 10^3 MP points per sector without doubling
(free 29,284 and 3,541, power 50,625 and 12,568). The 450-digit baseline took 162 s on 32 cores; it is reusable for
the same `bin/c8d2_gmp` at `$C8_DATA/evidence/10b19d9a0ae3/s4cflags.54673624.0/dev_mp256/f1_baseline` (refs not
copied here; their sha256 are in `f1_baseline/refs.sha256` and pinned in `baseline.json`).

| (sector, L) | Points | MP-promoted | Accepted at 77 digits | Escalated | Escalated fraction |
|---|---:|---:|---:|---:|---:|
| free L7 | 51,200 | 1,761 | 1,760 | 1 | 5.7e-4 |
| free L8 | 25,600 | 1,780 | 1,777 | 3 | 1.7e-3 |
| power L7 | 51,200 | 6,218 | 6,218 | 0 | 0 |
| power L8 | 25,600 | 6,350 | 6,342 | 8 | 1.3e-3 |
| **total** | 153,600 | 16,109 | 16,097 | 12 | **7.4e-4** |

- **The F1 gate passes:** 0 points with relative error > 1e-6 against 450 digits, 0 level mismatches, 0 violation
  counters. The largest relative error of an mp256-accepted value is 1.02e-19, the same as the exact path's MP tier
  (1.0e-19); long double accepted 5.1e-10 and binary128 1.4e-11.
- **All 153,600 values are identical to the exact path's**, bit for bit. Every mp256-accepted point converts to the
  same long double as the 350-digit value (`mp256_ld_identical` 16,097 of 16,097). Tier transitions: `mp350 → mp256`
  16,097, `mp350 → mp350` 12, the others diagonal.
- **The mp256 checks** (each MP-promoted point recomputed at 77 and at 350 digits):
  - the recomputed accept/escalate decision equals the one `evaluate()` took at every point;
  - accepted points: |v77 − v350|/err77 lies between 1e-118 and 1e-96 (decades e-118 to e-97), against the bound
    1e-69 (which keeps the relative error ≤ 1e-6 at the acceptance threshold); |v77 − v350|/|v350| < 1e-39;
  - the 77-digit ratio |v|/err of the MP points lies between 1e-79 and 1e-23;
  - the 12 escalated points (ratios between 1e-79 and 1e-63) would have had relative errors below 1e-28 at 77 digits:
    the 320-bit significand leaves a wide margin under the plan's 1e-63.

## Speed on the heavy L8 blocks (one node, median of 3)

`mp256_speed.py`, job 54673625 on <NODE> (2 × EPYC 7742). heavy_free_L8 ran on socket 0 and heavy_power_L8 on
socket 1 at the same time, 64 pinned threads each (256 tasks × 16,384 points per block). The rounds alternate
exact/mp256 and mp256/exact.

| Block | exact: integration s (3 runs) | mp256: integration s (3 runs) | Speedup (medians) | Wall speedup |
|---|---|---|---:|---:|
| heavy_free_L8 | 109.15 (109.11, 109.30, 109.15) | 77.78 (77.73, 77.78, 78.01) | **×1.403** | ×1.404 |
| heavy_power_L8 | 114.62 (114.62, 114.82, 114.48) | 75.62 (76.07, 75.62, 75.55) | **×1.516** | ×1.513 |

- **Rows.** Every run of a block, exact and mp256 alike, gives one rows digest: `92eec91c…` (free) and `c9b8e059…`
  (power), the Stage-4a/4b digests of these blocks. All 256 rows per block are identical in every scientific field,
  with the same quad and mp counters (free 3,494,580 and 1,003,400; power 3,940,609 and 1,504,626).
- **Escalations** (the tier's own counts, identical in all three runs): free 1,699 of 1,003,400 MP evaluations
  (**1.69e-3**), power 3,508 of 1,504,626 (**2.33e-3**). P3 expected 2.0e-4 to 2.3e-3.
- **Per tier** (tier-timer variants compiled in the job from each build record's command plus `-DC8_TIER_TIMERS`, the
  full blocks, rows equal to the non-timer runs):

| Block | Tier | exact: µs per call (share) | mp256: µs per call (share) | Speedup per call |
|---|---|---|---|---:|
| heavy_free_L8 | first pass | 128.4 (8.2%) | 128.6 (11.1%) | ×0.998 |
| | binary128 | 731.3 (38.7%) | 732.2 (52.8%) | ×0.999 |
| | MP | 3,492.6 (53.1%) | 1,741.4 (36.1%) | **×2.006** |
| heavy_power_L8 | first pass | 92.2 (5.8%) | 92.1 (8.6%) | ×1.001 |
| | binary128 | 543.7 (32.3%) | 542.9 (47.7%) | ×1.001 |
| | MP | 2,728.0 (61.9%) | 1,299.2 (43.6%) | **×2.100** |

  The MP figure of mp256 is the whole tier per MP-promoted point: the 77-digit evaluation, plus the 350-digit one
  for the escalated 0.17–0.23%. The other tiers do not move, so the gain is the MP tier's alone.

**Development F2/F4/F5** (job 54673624; development scales, never "passed"):
- F2, 5,496 tasks (all L3–L6 graphs, 16 graphs per (sector, L) at L7 and L8, both campaigns, 4 × 256 points):
  dC8 = 0 exactly, in total and per (sector, L); every per-task difference 0; the nonlinear dC8 0; the F3 counter
  changes 0. F2's single-lane task-second ratios (indicative): campaign a free L7 ×1.18, L8 ×1.20, power L7 ×1.47,
  L8 ×1.45; campaign b free ×1.13 and ×1.14, power ×1.34 and ×1.34.
- F4 on the first 25 graphs per sector of the L8 sweep sample, 4 × 8 lanes, 2 repeats: ×1.435 (free ×1.29, power
  ×1.60); rows repeatable and identical between the two executables.
- F5: thread identity at 1, 8 and 16 threads and 4 × 4 lanes, both sectors.

**Projection.** The heavy blocks spend 53–62% of their time in the MP tier. With the MP tier ×2.0–2.1 and nothing
else changed, a population whose L8 time is about 40% MP (free; Stage 4a/4b after R3a) gains about ×1.25, and one
at 50% MP (power) about ×1.34. The gate agent's F4 on the 2,000-graph L8 sweep sample measures this.

## Where the 77-digit time goes

Job 54673762 (`shared` 16 cores, 3:01, <NODE>): Stage 4b's `r3a_prof.py` on the first 32 tasks of each heavy
block at 16 threads, both executables under `perf record -F 999 -N` (`mp256prof.54673762.0/`; the job script is
`scripts/mp256_prof.slurm`, sha256 `8992a42a…`, run from a copy because the export predates it). The rows of the two
executables are identical again (free `3548c7b3…`, power `2b4c4506…`), and mp256 is ×1.41 faster (free, 50.55 →
35.86 s integration) and ×1.53 (power, 52.76 → 34.57 s).

Samples of the MP-tier symbols (absolute counts at the same rate and tasks; heavy_free_L8, heavy_power_L8 in brackets):

| Symbol | exact (350 digits) | mp256 (77 digits) | Ratio |
|---|---:|---:|---:|
| `__gmpf_add` (mpf's own code) | 64,864 [70,307] | 67,757 [73,547] | ×0.96 [×0.96] |
| `__gmpn_add_n` | 78,163 [79,914] | 27,648 [29,280] | ×2.83 [×2.73] |
| `__gmpn_copyi` | 45,818 [49,738] | 22,733 [24,936] | ×2.02 [×1.99] |
| `__gmpn_mul_basecase` | 113,974 [148,405] | 9,877 [12,938] | ×11.5 [×11.5] |
| `__gmpn_divrem_1` | 10,449 [16,143] | 950 [1,538] | ×11.0 [×10.5] |
| the worker's `calculate_shared<gmp_float<…>>` | 46,334 [49,942] | 42,178 [45,926] | ×1.10 [×1.09] |
| `malloc` + `_int_free` | 2,876 [4,268] | 4,943 [7,575] | ×0.58 [×0.56] |
| `hyp0F0` (Boost's exponential series) | 421 [655] | 120 [157] | |

- The multiplications and divisions scale with the limb count as expected (×11), but they are no longer what the
  tier spends its time on. In the 77-digit tier, additions (`__gmpf_add`, `__gmpn_add_n`, `__gmpn_copyi`) take 62–64%
  of the tier's samples (power–free), the worker's own loop code 22–23%, multiplications 8–9%, allocation 4–5% and
  division 2%.
- `__gmpf_add`'s own code does not get cheaper at all with 3.4× fewer limbs: it is a fixed per-call cost (operand
  alignment, normalization), paid once per prefix sum, numerator and term. Together with the worker's loop code it
  sets the floor of the tier at about half the 350-digit cost.
- So a lower precision (`gmp_float<75>` gives 5 limbs instead of 6) would buy little. A further gain in the MP tier
  would need a cheaper addition, for example an inline fixed-size multi-limb accumulator in place of mpf calls. That
  would be a new design, outside the plan's R4b, and it is not proposed here.
- Boost's exponential series (`hyp0F0`) is at most 0.09% of the samples in either tier. A flat profile does not
  separate the multiplications it calls from the prefix products, but all multiplications together are only 8–9% of
  the 77-digit tier.

## Cost

| Job | Partition | Elapsed | Core-seconds | SU |
|---|---|---|---:|---:|
| 54672884 precheck | shared 16 | 0:52 | 832 | 0.23 |
| 54673623 build | shared 16 | 0:45 | 720 | 0.20 |
| 54673624 dev | shared 32 | 3:57 | 7,584 | 2.11 |
| 54673625 speed | compute 128 (exclusive) | 13:03 | 100,224 | 27.84 |
| 54673762 prof | shared 16 | 3:01 | 2,896 | 0.80 |
| **total** | | | **112,256** | **31.18** |

Of this agent's 150-SU share, 31.2 SU were used; no job of this agent was live at the end. Lustre: the export of
10b19d9 (6,544 files), the precheck tree and the evidence (about 150 files). Accounting: `sacct.txt`.

## Files

- `scripts/`: `mp256_speed.py` and `mp256_speed.slurm` (the node job), `mp256_prof.slurm` (the profile job),
  `submit_mp256.sh` (Mac driver with the H7E-R admission and the agent share; precheck, build and dev used
  `stage4c/scripts/submit_s4c.sh` with `C8_S4C_TAG=mp256`). Admission records: `../admission/mp256/`.
- `precheck/`, `s4cbuild.54673623.0/`, `s4cflags.54673624.0/` (the F1 baseline's reference files left on Expanse),
  `mp256speed.54673625.0/` (with the first round's native JSON of each executable), `mp256prof.54673762.0/`, `logs/`,
  `sacct.txt`.
