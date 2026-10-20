# C8(2) production on symmetry: the result (2026-10-07)

These are the post-run steps for the C8(2) production batch: `docs/HPC.md` "Pilot runbook" step 4 for a production
batch, `docs/DESIGN.md` "Production batches" and "After the pilot" step 2, and `../submit_sequence.sh` section 7.

- Batch `<SCRATCH>/c8-d2/prod1-2.5e-4-ddmp256-20261006-ba68f401e46e`:
  - manifest `be215e0e…`, seed 6274393056071737300;
  - export `pkg/ba68f401e46e` (commit ba68f40), executable `c8d2_gmp_dd+mp256` `a46f3060…` (gate 570574);
  - numerics `dd+mp256`, route (b);
  - bundle `pilot1-20261006-ddmp256-2.5e-4` (`6afb6dd6…`), K = 1.
- Pins: AuthenticAMD EPYC 7543, runtime identity `04f1e51d…`.
- Preparation: `../README.md`. Submission and the two rounds: `LRI_C8_D2_HPC_loop/PLAN-REVIEW-LOG.md`.

The batch's data were only read. The post-run tools wrote two things:
- the combine output, `<SCRATCH>/c8-d2/prod1-2.5e-4-ddmp256-final/C8_final.json` (new directory, no-clobber);
- the evidence folders `<SCRATCH>/c8d2/evidence/ba68f401e46e/prres.571287.0/` and `prres2.571296.0/`.

The batch's `manifest.json`, `C8_result.json` and `submissions.jsonl` have the same sha256 before and after
(`*/batch_after.sha256`).

Site rules: symmetry only. Three sharedq jobs ran, each with `--no-requeue`, `--mem`, `--time` and a `c8d2-` name, 1.16
core-hours together. No AMD-pool job was used and no other job was touched.

## 1. The final result

**C8(2) = 45,990.00 ± 8.22** (estimated sampling SE; relative 1.79e-4, against the 2.5e-4 target of ±11.5). Numerics
`dd+mp256`, final, non-test.

**How to quote it** (after the tail check, `../tailcheck/README.md` section 1, revised 2026-10-08 after Codex's
verification): C8(2) = 45,990.0 ± 8.2, where the uncertainty is the estimated sampling standard error. A boundary
analysis supports finite second moments at both rates and bounded weights for all L7 and L8 kernels. It is backed by a
multi-prime randomized cancellation verification of all 24,173 kernels, with an estimated error probability below
10^−53. The 4,832 L8 tail warnings of section 4 are consistent with bounded, sharply peaked weights. Variance-inflation
calculations are sensitivity scenarios, not error bounds.

| Record | C8_full | Sampling SE | `verify_result.py` |
|---|---:|---:|---|
| `C8_result.json` (`assemble.py`, merge job 571153) | 45990.0026361445 | 8.216820957752926 | verified, problem_count 0 (symmetry and Mac) |
| **`C8_final.json`** (`combine.py`, K = 1; `batch_copy/`, sha256 `b14da47c…`) | **45990.00263614446** | **8.216820957752926** | verified, problem_count 0 (symmetry and Mac) |

The two records agree:
- the coefficients agree to 7.9e-16 relative, and the SEs and covariance diagonal are identical;
- the power correction agrees to 2.3e-11 relative;
- the only real difference is the diagnostic bootstrap: `combine.py`'s default is 1,024 draws (SE 8.13) against the
  assembly's 4,096 (SE 8.09);
- the record is `final: true`, "final combination of all 1 planned batches", with χ² null (K = 1).

`combine.py` took 11 s at 87 MB.

`production.py status` (full) exited 0:
- 24,848 of 24,848 blocks are committed in 24 merged groups;
- every OpenMP team is verified;
- every block carries the same fingerprint (`50d66502779d`, EPYC 7543, glibc 2.35).

## 2. Checks

Every check below passes.

| Check | Value | Verdict |
|---|---|---|
| Hard gates (top slot, loop 7, affinity) | pass (`verify_result` problem_count 0) | **pass** |
| C3 | −0.874848726 ± 1.24e-6 vs −0.8748500127 (archived 13-digit closed form) | pull **+1.04** |
| C4 | 5.04897591 ± 6.80e-5 vs 5.048868431 (archived 13-digit closed form) | pull **+1.58** |
| C5 | −38.8332792 ± 9.37e-4 vs −38.8336459 (archived 13-digit closed form) | pull **+0.39** |
| C6 | 362.36251 ± 0.0116 vs **362.36647 ± 0.0008** (C6(2) production M=8192) | pull **−0.34** (secondary archived MC 362.349 ± 0.153: +0.09) |
| C7 | −3875.545 ± 0.290 vs **−3876.126 ± 0.524** (C7(2) symmetry production) | pull **+0.97** |
| Lower-order pulls together | Σ pull² = 4.78 for 5 | consistent (p ≈ 0.44) |
| Power null rows (\|pull\| > 3 flags) | order 3 exactly zero by the weights; orders 4 / 5 / 6 / 7: +0.34 / +0.33 / +0.47 / +0.28 | **no flag** |
| Power correction (order 8; diagnostic, never a gate) | −1.27 ± 2.92, pull −0.43; power-free part 45,991.27 ± 7.68 | consistent with 0 |
| Campaign a vs b | 45,993.58 ± 12.15 vs 45,986.42 ± 11.06: difference 7.16 ± 16.43 | **0.44σ** |
| Half streams | 45,987.61 and 45,992.39 | consistent |
| Bootstrap (diagnostic) | SE 8.09 (4,096 draws), ratio 0.985 to the sampling SE; bias −0.19 | consistent |
| **Pilot** (exact path, 45,620.18 ± 214.16, an independent seed) | difference 369.82 ± 214.32 | **1.73σ** (two-sided p ≈ 0.08) |
| Realized SE vs the frozen prediction | 8.217 vs 7.667 raw (variance 58.78) and 11.50 with the margin 1.5 | ×1.072 raw; **×0.714 of the prediction with margin** |

**Where the variance comes from** (`error_by_loop`; the SE contribution is √variance):

| (sector, L) | Variance share | SE contribution |
|---|---:|---:|
| free L8 | **66.8%** | 6.71 |
| free L7 | **19.9%** | 3.67 |
| power L8 | **10.8%** | 2.70 |
| power L7 | 1.55% | 1.02 |
| free L6 | 0.62% | 0.65 |
| power L6 | 0.28% | 0.43 |
| everything else | < 0.1% | |

The pilot's uniform allocation had free L7 at 71% and free L8 at 18%. The Neyman design moved the variance to where it
is cheapest to reduce. The free strata landed near the shares the pilot analysis gave for its designs (exact 1e-3: free L8
65%, free L7 21%, power L8 4.7%). Power L8 is higher here, at 10.8%, because its variance came in at ×1.32 the prediction.

**Realized against predicted, per stratum** (`prres.571287.0/analysis.json`, `variance`):
- **predicted** is Σ_g ¼ σ²_pilot,g / (n_g r) at the batch's points, from the pilot's per-graph σ with no margin;
- **realized** is the assembly's replicate-group-sum variance, which reproduces `error_by_loop` exactly.

| (sector, L) | Realized / predicted variance | Per-point variance, batch / pilot (pooled) | Points per replicate (min / median / max) |
|---|---:|---:|---|
| free L8 | 1.161 | 0.904 | 32,768 / 32,768 / 524,288 |
| free L7 | 1.090 | 0.784 | 262,144 / 262,144 / 4,194,304 |
| power L8 | 1.318 | 0.960 | 8,192 / 8,192 / 131,072 |
| power L7 | 0.980 | 0.883 | 65,536 / 65,536 / 1,048,576 |
| free L6 | 0.619 | 0.558 | 524,288 and up |
| free L3-L5, power L3-L5 | 0.01-0.69 | 0.01-0.55 | 131,072 and up |

- **Totals.** The realized variance is 67.52 (SE 8.217) against the predicted 58.78 (SE 7.667). Summed per graph the
  realized variance is 62.41 (SE 7.90). The same figure appears in `design.py report --bundle` with the batch's σ: the
  bundle's SE "projected" at 7.90 raw and 11.85 with the margin, against its frozen 7.667 / 11.50.
- **Group sums against the per-graph sum.** The two differ by 8%. That is about 1.3σ of a variance estimated from 128
  replicates.
- **The low loops are far below their prediction.** The sampler is a randomized (scrambled, digitally shifted) Sobol
  net, so the replicate variance falls faster than 1/n where the integrand is smooth (α > 0.5). The design assumes
  α = 0.5 for every stratum, which over-allocates the low loops. They are cheap, so it costs almost nothing.
- **The SE ratio.** The ×1.07 at L7 and L8 is the size the pilot analysis expected from σ estimated with 7 degrees of
  freedom (about ×1.08; `../../pilot/analysis/README.md`, section 4). The margin 1.5 covered it with room to spare.

## 3. Accounting (`prres.571287.0/accounting.json`; `tools/accounting.py`, complete)

The ledger holds 26 jobs with 26 `sacct -X --duplicates` records (`prres.571287.0/sacct.txt`). Every current attempt is
terminal, 24,848 checkpoints carry a Slurm id, and no checkpoint is missing. Physical cores are 64 per AMD node and
AllocCPUS / 2 on the Intel sharedq nodes.

| Jobs | Role | State | Elapsed | Core-h |
|---|---|---|---|---:|
| 570722 | plan (sharedq <NODE>) | COMPLETED | 9:21 | 0.62 |
| 570755-570762 (round 1, 8 nodes) | lane | COMPLETED | 22:21:35-23:01:09 each | **11,617.39** |
| 571130 (round 2, 8 h) | lane | COMPLETED | 5:38:24 | 360.96 |
| 571148-571152 (round 2, 7 h) | lane | COMPLETED | 4:21:14-5:27:07 | 1,473.67 |
| 571153 | merge (final) | COMPLETED | 1:07 | 1.19 |
| 570763, 571126, 571131, 571146 (merges); 571125, 571141-571145 (round-2 workers) | superseded or replaced | CANCELLED while PENDING | 0 | 0 |
| **total** | 26 records | | | **13,453.83** |

The start-latency probe 570753 is not a ledger job. It ran on <NODE> for 0 s (`prres.571287.0/sacct_probe.txt`).

| Quantity | Value |
|---|---:|
| Allocated core-h | **13,453.83** (lanes 13,452.02; merge 1.19; plan 0.62) |
| Busy thread core-h (merged.json `thread_seconds_sum`) | **13,217.48** |
| **η_node** = busy / lane core-h | **0.9826** (the pilot: 0.837) |
| Lane occupancy (Σ index walls × 8 / lane core-h) | 0.985; in-index efficiency 0.997 |
| Against the design's 14,465 lane core-h (η_node 0.837) | **×0.930** |
| Against the plan's 12,025 estimated core-h | busy ×1.099; allocated ×1.119 |
| Against the schedule's projection for two rounds (`../README.md` section 4) | inside 12,273 (pilot model) to 13,634 (planner model) |
| Lane walls against the planner's estimates | 0.992 overall (round 1 0.982-1.007 per worker, round 2 0.966-0.989) |
| Indices | 1,129 done once each, none twice, no failure |
| Wall | 28.7 h from the first submission (2026-10-06 16:33 EDT) to the merge's end (2026-10-07 21:12 EDT) |

**Busy time against the plan's index estimates, by stratum:**

| Stratum | Estimate (core-h) | Busy (core-h) | Ratio |
|---|---:|---:|---:|
| free L8 | 8,345.5 | 9,239.9 | ×1.107 |
| free L7 | 2,517.7 | 2,746.1 | ×1.091 |
| power L8 | 751.9 | 794.0 | ×1.056 |
| power L7 | 230.1 | 247.5 | ×1.076 |
| free L6 / power L6 | 131.1 / 18.3 | 140.4 / 19.6 | ×1.07 |
| L3-L5 | 30.6 | 30.0 | ×0.98 |
| **total** | **12,025.1** | **13,217.5** | **×1.099** |

The `dd+mp256` cost model under-estimates L7 and L8 by 6-11%, as the exact model did in the pilot (free L8 ×1.08). The
planner's assumed lane efficiency of 0.9 hides this in the walls, because the lanes ran at 0.997. The design's 14,465
was the conservative figure: its η_node of 0.837 carried the pilot's 3-node tail, while this long run had almost none.

The three analysis jobs here used 1.16 core-h (`sacct_analysis_jobs.txt`):
- 571285, a test of the analysis on the pilot: 24 s, 0.03 core-h;
- 571287: 9:18, 0.62 core-h;
- 571296: 5:05, 0.51 core-h.

## 4. The heavy-tail screen at production scale (C63d's rule; docs/DESIGN.md, "After the pilot", step 2)

At 2.5e-4 every free L8 graph had at least 32,768 points per replicate in both campaigns (the minimum is 32,768, the
maximum 524,288). Power L8 had 8,192 to 131,072. So the batch can confirm or clear the pilot's free L8 screen.

**The confirmation report** is `prres2.571296.0/report.txt`, `report.json.gz` and `tails.csv.gz`, from `tools/design.py
report --pilot <the batch> --max-checkpoints 100000000 --max-tasks 2000000000`, job 571296. In job 571287 the report run
with default caps exited 2 before it wrote anything (`prres.571287.0/report.txt`); "Unexpected", item 1, explains why
the caps were raised.

**The verdict:**
- 40,800 L8 graph-campaigns (20,400 graphs) were tested, and none is undefined;
- **4,832 L8 graphs are confirmed "possible infinite variance"**: two-campaign mean ξ̂ > 0.44 at ≥ 32,768 points per
  replicate. 4,631 are free L8 and 201 are power L8;
- at production points, 9,628 L8 graphs pass the screen (ξ̂ > 0.38 or largest share > 0.05).

`prres.571287.0/analysis.json` (`tails`) reproduces these counts with the same function (`design.tail_table`), and its
classification is consistent with the report.

**The pilot's 14,222 screened L8 graphs, followed up:**

| Pilot screen | Screened in the pilot | **Confirmed** | **Cleared** (both campaigns at ≥ 32,768 points, mean ξ̂ ≤ 0.44) | Not testable (< 32,768 points) | Undefined |
|---|---:|---:|---:|---:|---:|
| free L8 (no primitive was screened) | 9,886 | **4,631** | **5,255** | 0 | 0 |
| power L8 | 4,336 | **201** | **161** | **3,974** (power L8 has s = 2: 8,192 or 16,384 points in at least one campaign) | 0 |
| **total** | **14,222** | **4,832** | **5,416** | **3,974** | 0 |

No graph is confirmed outside the pilot's screen. The 248 free L8 primitives had pilot ξ̂ ≤ 0.15 and were never
screened.

**ξ̂ (two-campaign mean per graph) falls with the point count for every confirmed graph:**

| Class | Graphs | ξ̂ pilot (median) | ξ̂ batch (median) | Change, median / largest | Graphs whose ξ̂ rose |
|---|---:|---:|---:|---|---:|
| free L8 confirmed | 4,631 | 1.21 | 0.61 (q10 0.48, q90 0.84, max 1.20) | −0.58 / −0.32 | **0** |
| free L8 not confirmed | 11,433 | 0.33 | 0.17 | −0.17 / −0.02 | 0 |
| power L8 confirmed | 201 | 1.66 | 0.73 (max 1.33) | −0.95 / −0.38 | **0** |
| power L8 cleared | 161 | 1.12 | 0.32 | −0.78 / −0.21 | 0 |
| power L8 below 32,768 points | 3,974 | 1.84 | 1.51 | −0.33 / +0.15 | 52 |

Most graphs went from 4,096 to 32,768 points per replicate, a ratio of 8. For a regularly varying tail of index ξ, the
Hill estimate at a fixed k = 16 does not drift systematically with n (for an exact Pareto tail its distribution does
not depend on n). A halving at 8× the points is what a spike-dominated but finite
tail gives. The pilot analysis found the same signature (ξ̂ tracks the largest single-point share, Spearman 0.985, and
not the per-graph σ). At L7, which has no threshold, every graph's batch ξ̂ is below 0.41; in the pilot, 51% were above
0.44.

**Does a confirmed tail threaten the SE?** (`prres.571287.0/analysis.json` `tails.threat`, `prres2.571296.0/followup.json`)

| Evidence | Free L8 confirmed | Power L8 confirmed |
|---|---|---|
| Share of Var(C8) | **26.3%** (SE contribution 4.22 of 8.22; 42.8% of free L8) | 1.2% (SE contribution 0.91) |
| Largest single graph-campaign share of Var(C8) | 0.080% (graph 26268, campaign a: the largest of the whole batch) | 0.023% |
| Per-point variance, batch / pilot (pooled) | **1.035** (cleared 0.912, never screened 0.811) | 0.808 (cleared 0.758) |
| The same, cross-split (selected on one campaign's ξ̂ > 0.44, measured on the other) | heavy 1.030 / 0.971 against light 0.870 / 0.880 | heavy 1.028 / 0.944 against light 0.805 / 0.882 |
| What infinite variance would give at the ratio 8 (n^(2ξ−1), against a finite-variance graph at the Monte Carlo rate) | ×1.23 at ξ = 0.55, ×1.52 at 0.6, ×2.30 at 0.7 | the same |
| Replicate-level excess kurtosis (128 replicates; Gaussian reference −0.093) | **+0.113** (without the 20 largest: +0.103; per graph median −0.004, max 6.4) | +0.169 (per graph median −0.017, max 5.6) |
| SE of C8 if their variance were ×2 / ×4 / ×10 (sensitivity scenarios, not bounds) | 9.24 / **10.99** / 15.09 | 8.27 / 8.37 / 8.66 |

How the variance is spread:
- the largest graph-campaign holds 0.08% of Var(C8);
- the largest 10 hold 0.50%, the largest 100 3.1%, and the largest 1,000 15.5%;
- so no single graph or small set of graphs dominates.

The batch-level checks of section 2 are all consistent: a against b at 0.44σ, bootstrap/analytic 0.985, the lower-order
pulls at most 1.58, and the pilot at 1.73σ.

**The rule's verdict and its implications.** The rule fires: 4,832 L8 graphs are confirmed "possible infinite
variance".
- By `docs/DESIGN.md` this is a user decision: proceed, nest (more points for the confirmed graphs, with α measured), or
  drop a confirmed graph. **Dropping changes the estimand**, and these graphs carry 27.5% of the variance.
- The package has no automatic production monitor. Nothing was changed, and the result stands as computed.
- The evidence above bears on the decision without replacing it:
  - the confirmed graphs' per-point variance grows ×1.03 against ×0.87-0.91 for the others. A relative factor of
    1.10-1.18 at 8× the points is far below what ξ = 0.55-0.7 would give;
  - their replicate means are close to Gaussian (descriptive);
  - their ξ̂ halves when the points grow 8×;
  - the result keeps the 11.5 target unless their true variance is more than about 4× what was measured.
- The thresholds were calibrated at d = 3 (C63d). At d = 2 the screen mainly measures per-point spikes, as the pilot
  analysis suggested. **This reading is for the user to judge; it is not a conclusion of the rule.**

**Disposition (tail check, 2026-10-07; revised 2026-10-08 after Codex's verification; `../tailcheck/README.md`).**
- The confirmations are **tail warnings, not established infinite variance**. A boundary analysis with a multi-prime
  randomized cancellation verification covers all 24,173 kernels: 4 random primes × 2 random points per prime per graph,
  0 failures, union-bound error estimate ≤ 10^−53. It supports finite second moments at both production rates and
  bounded weights for every L7 and L8 kernel, the 4,832 confirmed and the 3,974 untestable graphs included.
- The fixed-k Hill estimate falls with N in every class (exponents −0.34 to −0.17). This finite-sample behaviour is
  consistent with bounded, sharply peaked weights.
- A fresh nested-N test (common window 2^12..2^17, joint replicate bootstrap, conditional on the selected panel) gives
  slopes of N·Var: −0.018 [−0.051, +0.030] for confirmed free L8 and −0.062 [−0.110, +0.060] for confirmed power L8.
- The 380 double-lift power L8 graphs carry 0.058% of the measured variance. A targeted test of the 16 largest (52% of
  that) shows rare-peak sampling effects. Inflating that class's variance ×18.9 / ×45 / ×335 gives an SE of
  8.26 / 8.32 / 8.97: scenarios, not bounds.
- Every graph stays in the estimand. No production rerun is needed.

**The P8-flagged stratum: power L8.**
- Per stratum, the report gives power L8 P8 **1.266 FLAG** (> 1.196 with at least 500 graph-campaigns), and a pooled
  replicate excess kurtosis of **4.71**.
- `followup.json` places this kurtosis in the 3,974 power L8 graphs below 32,768 points (7,948 graph-campaigns at
  8,192-65,536 points per replicate, 9.0% of Var(C8)): pooled 5.0, per-graph median 1.5, q90 13.6, max 120 (largest
  \|z\| 11.2).
- These are the graphs the screen cannot test at this target. Their most kurtotic graph-campaigns carry about 1e-9 of
  Var(C8) each. Graph-campaigns with their own excess kurtosis above 3 carry 2.6% of Var(C8), and above 10 carry 0.56%.
- With r = 128 here (P8's R = 16 advice is already exceeded), the flag changes nothing in the design (`docs/DESIGN.md`).
- Per-sector P8 is undefined for a production batch, because no L8 graph-campaign has exactly 4,096 points.

The report's target table (2.49 SE at 600,875 core-h for every target) sizes hypothetical designs at this batch's
524,288-point replicates. **It is not a design input.**

## 5. Unexpected

1. **`design.py report --pilot <production batch>` fails with the default caps** (job 571287, exit 2):
   - the error is "infeasible: even the minimum design of one batch (r = 32, s = 1) breaks the per-batch caps …
     checkpoints 252,175 (cap 200,000)";
   - the cause is that the report's target table normalizes base counts to the campaign's largest per-replicate point
     count. That is 524,288 here, against 4,096 in a pilot, and the table is built before the tails are written;
   - the runbook (`docs/DESIGN.md` step 2, `../submit_sequence.sh` section 7) tells you to run exactly this on a
     production batch. Neither says to raise the caps;
   - the workaround is explicit `--max-checkpoints 100000000 --max-tasks 2000000000` (job 571296). The caps bound only
     the hypothetical designs of the table; the tails and the bundle block do not depend on them;
   - a fix (the table skipped or capped for a non-pilot `--pilot`, or a doc line) is open. No code or runbook was
     changed here.
2. **The tail rule confirms 4,832 L8 graphs** (section 4). This was a user decision item. The tail check
   (`../tailcheck/README.md`) found the warnings consistent with bounded, sharply peaked weights; see the disposition
   in section 4.
3. **Power L8 replicate means are heavy-tailed** (kurtosis 4.7, P8 1.27 FLAG), concentrated in the 3,974 graphs at
   8,192-65,536 points, which carry 9.0% of the variance. The SE of that stratum is from 128 replicates, so it is
   estimated, not assumed.
4. **The realized SE is ×1.07 the raw frozen prediction**, and power L8 is ×1.32 in variance. Both are well inside the
   margin 1.5 (realized 8.22 against 11.50).
5. **The cost model under-estimates L7 and L8 by 6-11%** (busy ×1.099 overall). η_node 0.983 against the design's 0.837
   more than compensates, so the run allocated ×0.930 of the design's core-hours.
6. `C8_final.json` is not bitwise equal to `C8_result.json`: it differs at 8e-16 relative in C8 (summation order), and
   its bootstrap has 1,024 draws, not 4,096. Both verify.

## Files

- `scripts/`:
  - `prres.slurm` and `pr_result_analysis.py` (job 571287; test mode, job 571285);
  - `prres2.slurm` and `pr_followup.py` (job 571296);
  - the uploads are read-only in `<SCRATCH>/c8d2/work/prod-ba68f401e46e/`, and the sha256 of each job's are in
    its `inputs.sha256`.
- `prres.571287.0/`: `status.txt`, `verify_result.txt` and `verify_final.txt`, `accounting.json` and `accounting.stdout`,
  `sacct.txt` (every ledger job) and `sacct_probe.txt`, the combine output (`combine.*`, `final_vs_result.txt`,
  `combine_output_listing.txt`), the failed report (`report.txt`, `report.exit`, `report_bundle.txt`), `analysis.json`
  and `analysis.stdout`, `time_*.txt`, `inputs.sha256`, `batch_after.sha256`.
- `prres2.571296.0/`:
  - `report.txt`, `report_summary.txt`, `report.json.gz` and `tails.csv.gz` (the official tail report);
  - `report_bundle.txt` and `report_bundle.bundle.json` (the bundle block: the PROJECTION 7.90 raw, 11.85 with margin);
  - `followup.json` and `followup.stdout`, `time_*.txt`, `inputs.sha256`, `large_files.sha256`, `batch_after.sha256`.
- `xi_change_by_class.json`: the pilot-to-batch ξ̂ table of section 4, from the two committed `tails.csv.gz`.
- `batch_copy/`:
  - `C8_result.json` and **`C8_final.json`**;
  - `submissions.jsonl`, `cpu_vendor.json`, `runtime_identity.json`;
  - `slurm_logs/` (the 14 lane workers and merge 571153);
  - `sha256_on_beegfs.txt` (the batch's `manifest.json` is `../plan/prplan.570722.0/manifest.json`, the same sha256).
- `large_files.sha256`: the files that stay on BeeGFS: the uncompressed `tails.csv`, `report.json` and
  `report_bundle.json`, `C8_final.json` there, and the batch's manifest and result.
- `logs/`: the three job logs. `sacct_analysis_jobs.txt`: the three analysis jobs.
