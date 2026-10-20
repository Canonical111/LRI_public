# C8(2) design: pilot → Neyman allocation, targets, budgets and batches

Stage 3 (PLAN.md component E, D16), 2026-10-03; defaults, the post-pilot decision step and the production-size dry
run J-DES-5 added in Stage 5 (2026-10-05, A-DES-4/5); the F11 fix and route (b) for the approved `dd+mp256` profile
added before the Stage-6 inspection (2026-10-05, 23540b2); the integer optimizer of F13 and the F11 follow-up (both
split rules, a prune pass and a bounded lattice search), route (b)'s keep-cheaper and the allow-list scope added for
the Stage-6 inspection (2026-10-05, "F13" below); Stage-6 fix round 1 (2026-10-06: the gate evidence X1-X3, the
authenticated overrides X14, live allocations X15, the pinned bundle copy X9, cost-model numerics X10). The tool is `tools/design.py` (port of C8(1)'s `design8.py`,
reusable by C8(3) through its parameters, H6: `LRI_C8_shared/inventory/HANDOFF_design.json`). The pilot never enters
an estimate, and its seeds are forbidden in production.

## Inputs

- **A merged pilot campaign** (`production.py plan --pilot --points P`, P ≥ 4096 unless test-only, then lanes or
  arrays and `merge`): per group `graph_replicates.csv` (per-graph replicate jets), `graph_costs.csv` (row seconds per
  graph) and `graph_tails.csv` (the class-B tail fields), each verified through `merged.json`; the group
  efficiencies η_omp,g = row seconds / (threads × integration seconds).
- **η_node** from `tools/accounting.py` over the pilot's ledger (`<prefix>-ledger-1`; work roles lane, array, sweep). A checkpoint naming
  an unregistered job refuses the freeze ("allocation unknown"); checkpoints without a Slurm id are accepted only by
  `--test-only` (η_node = 1, labelled assumed); `--eta-node X` likewise test-only. An assumed efficiency is never used
  for a production (non-test) design (Y9, Stage-6 fix round 2): a production freeze or report refuses a merged pilot
  with a checkpoint missing from a merged group, a checkpoint without a Slurm id, or no checkpoint with a Slurm id at
  all, and `tools/accounting.py` reports missing checkpoints of merged groups (`missing_checkpoints`) as incomplete
  accounting (exit 4), so a missing checkpoint refuses a test-only freeze too. Do not delete a pilot's checkpoints
  before its design is frozen. Incomplete accounting (an sacct line
  that does not parse, a ledger job, array element or recorded attempt without its sacct record, or, since fix round 1
  (X15), a job or array element whose current sacct attempt is not terminal: RUNNING, PENDING, REQUEUED, COMPLETING,
  SUSPENDED or unknown) makes η_node unavailable and refuses `report` and `freeze`; it is never computed from the records that came back. A complete
  η_node above 1 (SMT threads on half as many physical cores) is capped at 1, which only raises the cost.
- **The order-8 Jacobian** J_8 at the pilot means (the vendored module's complex-step `jacobians`, with the B2 of
  `inputs/two_loop.json` or `--two-loop`; `--half-d`).
- **The inventory** (`inputs/inventory.json`, or `--inventory`; `--selection` restricts L8 to a selection.json). For
  a `c8-d2` pilot, `--two-loop` and `--inventory` must be the files its verified inputs manifest pins (the same sha256
  rule as for another package's pilot), and `--selection` is refused, since a `c8-d2` inputs manifest lists none
  (X14, Stage-6 fix round 1; `report` and `freeze` exit 2 and create nothing). Without an override nothing changes.

## Rules

1. **Per graph and campaign** (D16): σ_g² = n_g Var_rep(J_8 · jets_{rep,g}); c_g = row seconds / points. Unpiloted
   graphs are imputed per (campaign, stratum): a log-linear fit of log σ and log c on log addends when at least 3
   graphs are piloted, else the median; a stratum without any piloted graph borrows its (sector, L) group's piloted
   graphs. A σ floor of 3% of the stratum median. The imputed share of the predicted variance is recorded.
2. **Base counts** n_g ∝ σ_g/√c_g per (campaign, stratum), normalized so that a stratum costs what the pilot did per
   replicate, rounded to powers of two, at least `--min-points` (4096).
3. **Strata**: free L3..L8, the free L8 primitives, power L3..L8 (13). V1 and C1 per stratum: the C8 variance and
   the allocated core-seconds per replicate at s = 1 (campaigns at weight 1/2; allocated = task seconds /
   (η_omp,g × η_node)).
4. **Neyman multipliers** m ∝ √(V1/C1), split into replicates r (powers of two in [32, 128], equal for campaigns a and b
   of one (sector, L)) and a power-of-two sample multiplier s ≥ 1 per stratum. **r is the largest power of two in
   [32, 128] not above the (sector, L)'s smallest multiplier** (F11, fixed in 23540b2; below). Only free L8 has two
   strata (the primitives and the rest); every other (sector, L) is one stratum. The integer allocation (`optimize()`,
   "F13" below) is then searched from two starts, this split and the Stage-5 split (r from the largest multiplier):
   - the greedy loop: double the s of the most efficient stratum until the target is met, or halve s (then r) until
     the budget holds;
   - (target) a **prune pass**: halve one stratum's allocation r·s (its s, or r with the group's other stratum at
     twice the s) wherever the predicted SE still meets the target, the halving that saves the most first, repeated to
     a fixed point. Each accepted halving must meet the per-batch caps, and the pass **stops at the first best halving
     that fails a cap** (it does not try the next-best one). A halving adds no task, checkpoint or replicate, so this
     happens only when the greedy design already misses a cap; the lattice search (which skips cap failures) and the
     batch count K (rule 6) then handle it. No cap binds at J-DES-5's sizes;
   - a **bounded local lattice search** over the power-of-two allocations a_k = r·s_k of the strata with variance:
     every combination of a_k·2^d, |d| ≤ 2, in a box around a centre (first the split point, then the incumbent,
     recentred after every improvement, never a centre twice, at most 32 boxes), solved exactly per box by meet in the
     middle; a target takes the least cost with SE ≤ target, a budget the least SE with cost ≤ budget; ties by the
     other quantity, then the box order. A candidate is accepted only if `evaluate_design` confirms it (the target or
     budget met, strictly better than the incumbent by 1e-12) and it meets every per-batch cap (at most 16 cap failures
     per box). r of a (sector, L) becomes min(r after the greedy loop, the smallest allocation of its strata), s_k =
     a_k/r; a (sector, L) with a zero-variance stratum keeps its r;
   - the better design of the two starts is kept, the F11 start's on ties: the result is never costlier (a target) or
     less precise (a budget) than either rule's greedy design **at the same batch count K**, deterministic, and its
     predicted SE is
     `evaluate_design`'s, exact for the integer allocation. `design_meta.json` records both starts (`optimizer`: each
     start's greedy and final cost and SE, prune steps, lattice boxes and moves, r and s; which one was kept).
5. **Margin**: the predicted SE is multiplied by `--variance-margin` (1.5; C8(1)'s realized SE was 1.56× its pilot
   prediction) before it meets a target.
6. **Batches**: the minimum K for which every batch meets the caps (tasks per campaign ≤ `--max-tasks`, checkpoint
   blocks ≤ `--max-checkpoints`, r ≤ 128, the shortest allowed task ≤ `--max-task-seconds`, chunking and index sizing
   as `production.py plan` with the measured costs). A smaller `--batches` is refused, naming K. The search for K runs
   to 64 batches, and with `--batches K` above 64 up to K (W12, Stage-6 fix round 4: before, a target needing 128
   batches was refused even with `--batches 128`); a search that ends without K says whether it hit its limit (the
   minimum design of one batch, r = `--min-replicates` and s = 1, meets the caps, so more batches would) or the
   target is infeasible (it does not), and the allocation of an explicit `--batches` is checked against every cap
   before anything is frozen. K is the smallest
   batch count whose **optimized** design meets the caps; the Stage-6 search can meet them at a smaller K than the old
   greedy designs did, so a freeze's K may be smaller than the old tool's (the comparison in rule 4 holds at a fixed
   K). J-DES-5 has K = 1 at every target, so nothing there changes. A route-(b) bundle that keeps the exact design
   records the exact path's minimum K (`batches_minimum`) and the exact search (`optimizer`); the re-optimized branch
   is in `route_b_choice` (cost, SE, K, r, s, the start kept).
7. **Budget gate**: `--budget-core-hours B` (integer core-hours) with `--spent-core-hours X` and `--total-cap Y`:
   B + X ≤ Y, the design's total cost ≤ B; an infeasible budget is refused with the minimum (s = 1, r = 32) printed.

## Defaults

| Option | Default | Meaning |
|---|---|---|
| `--min-points` | 4,096 | smallest per-graph count per replicate (a power of two; ≥ 4,096 for production) |
| `--min-replicates`, `--max-replicates` | 32, 128 | the replicates r of a (sector, L), powers of two, equal for campaigns a and b; production bounds enforced (below) |
| `--variance-margin` | 1.5 | multiplies the predicted SE before it meets a target (≥ 1 for production) |
| `--c8-magnitude` | 4.6e4 | \|C8\| for the relative targets 1e-3, 5e-4, 2.5e-4, 1.35e-4 |
| `--impute` | `addends` | unpiloted graphs: log-linear in the inventory's addends (≥ 3 piloted graphs), else the median |
| σ floor | 3% of the stratum median | |
| `--task-seconds`, `--min-chunk`, `--max-task-seconds` | 60 s, 256 points, 120 s | chunking, as `production.py plan` with measured costs |
| `--threads`, `--checkpoint-tasks`, `--index-hours` | 8, max(16 × threads, 256), 1.5 h | index sizing of the caps check |
| `--max-tasks`, `--max-checkpoints` | 5 × 10^7 per campaign, 2 × 10^5 | per-batch caps; the minimum K is searched up to 64 batches |
| `--spent-core-hours`, `--total-cap` | 0, none | the budget gate (both integer core-hours) |
| `--seeds-log` | `$C8_SEEDS` | every seed in it, and the pilot's, is forbidden in the bundle's plans |
| `--eta-node` | none | test-only pilots and freezes only; a non-test freeze takes η_node from the pilot's ledger |
| `--numerics`, `--approved-numerics-change`, `--cost-model`, `--numerics-gate` | `exact`, none | route (b) only (below): an approved profile for a bundle frozen from an exact pilot; on the exact path they are refused |

**The allocation options are checked before anything is designed (Y10, Stage-6 fix round 2).** `design.py`
`check_options` runs first in `report` and `freeze`: for a production bundle `--min-replicates` is a power of two ≥ 32,
`--max-replicates` a power of two ≤ 128 and ≥ the minimum (so every r is a power of two in [32, 128]), `--min-points` a
power of two ≥ 4,096 and `--variance-margin` ≥ 1; a `--test-only` bundle may reduce them (replicates powers of two ≥ 2,
never one, `--min-points` a power of two, a margin > 0). Always: positive integer sizes, `--min-chunk` a power of two,
`--checkpoint-tasks` in [1, 100000] and ≥ `--threads`, finite positive seconds, hours and targets, `--spent-core-hours`
≥ 0, `--batches` ≥ 1, `--eta-node` in (0, 1]. `check_allocation` checks the designed r, s and per-graph counts against
the same bounds before the bundle is published. `production.py plan --design` checks the bundle's replicates again
before anything else (`bundle_replicates`): exactly the twelve `<sector>_L<L>` entries, integers ≥ 2 in any bundle and
powers of two in [32, 128] in a production bundle; a one-replicate group could be run and merged but never assembled.

**F11 (found by J-DES-5; fixed in 23540b2).** The Stage-5 split gave a (sector, L) the replicates of its LARGEST
stratum multiplier. At free L8 the primitives (248 graphs, cheap) are their own stratum, and at a loose target their
multiplier is several times the other free L8 graphs': at 1e-3 on the J-SWEEP-2 sweep 176.8 against 35.1, so the
dominant stratum (83% of the cost) ran at r = 128 where 32 would do and the 1e-3 bundle over-delivered (SE 32.6 against
46) at 2.98× the continuous Neyman optimum.

*Which stratum sets r: the smallest multiplier, by the variance-cost optimum.* Since s ≥ 1, a group's r is a floor on
the allocation r·s of each of its strata. The Neyman optimum is r·s = m for every stratum; a stratum with m < r is
forced to r, over-allocated by ρ = r/m, which multiplies the design's variance × cost by 1 + w(1 − w)(ρ − 1)²/ρ (w its
share of Σ√(V1·C1)). With r at most the smallest multiplier nothing is forced, and every stratum gets
r · pow2_round(m/r) = pow2_round(m), its best power-of-two allocation, whatever r; the largest such r keeps the most
replicates. Taking r from the costliest stratum is the same choice whenever the costliest stratum has the smallest
multiplier (free L8 on J-SWEEP-2, at every target), and otherwise forces the cheaper strata above their optimum.

*Effect* (`benchmarks/symmetry_2026-10-c8/stage5/pre6/`, `optimize()` on J-DES-5's frozen strata; the Stage-5 rule,
re-implemented there, reproduces all four frozen designs exactly): at 1e-3 free L8 gets r = 32 and its primitives
s = 8 (the target loop also raises s at free L5, free L7 and power L3-L5); the design costs **1,738 lane core-hours on
symmetry (SE 44.2 against 46)** instead of 3,963, 1.31× the continuous bound (the rest is the r ≥ 32 floor of strata
whose multiplier is below 32, power L8's 7.3 among them, and the power-of-two rounding). The 5e-4, 2.5e-4 and 1.35e-4
designs are unchanged (the same r and s). The predicted SE of a bundle is computed from its own r and s and stays
exact (`report --bundle` recomputes it from the counts).

*The fix is optimal for the split, not for the whole optimizer* (the pre-Stage-6 verifier, 2026-10-05): with the
greedy target loop after it, the F11 split ended costlier than the Stage-5 split in 418 of 20,000 random stratum sets
(up to ×1.84), because a lower start can miss the target by a little and the loop then doubles a dominant stratum.
J-DES-5's strata were not affected (better or equal at every target). The Stage-6 optimizer (rule 4, "F13" below)
runs both splits and keeps the cheaper, so it is never costlier than either; with the prune pass and the lattice
search J-DES-5's exact designs become 1,702 / 5,740 / 22,961 / 74,573 lane core-hours (SE at the targets 46.00 /
23.00 / 11.50 / 6.21), 2.0-2.7% below the F11 greedy designs. `tests/test_pipeline.py` reproduces F11 on a synthetic
full-size pilot (the old rule at 2.85× the continuous optimum, the F11 greedy design at 1.09×, the optimizer at 1.07×)
and checks every target bundle independently (`check_optimizer`: the target met, never costlier than either old
rule's greedy design, no cheaper feasible single halving or halve-one-double-another move).

## The target table (`design.py report`)

```bash
python3 -B tools/design.py report --pilot PILOT [--bundle B] [--nested PILOT_4X] [--json FILE] [--tails-out FILE]
```

Predicted SE (with the margin) against allocated core-hours and batches for the relative targets 1e-3, 5e-4, 2.5e-4
and 1.35e-4 of |C8| (`--c8-magnitude`, 4.6e4), plus `--target-se` and `--budget-core-hours`. Per stratum: the
variance and cost per replicate, kurtosis, skewness, largest |z|, the largest single-graph share, the split-half P8
and α (from `--nested`, the same graphs at more points: Var ∝ n^(−2α); otherwise 0.5 assumed and said). With
`--bundle`, the predicted SE of that frozen design recomputed from its own counts (A-DES-2).

- **The bundle is read verified (Z9, Stage-6 fix round 3).** `report --bundle`, `freeze --rates-bundle` and
  `rates --source-bundle` read a bundle through one schema-aware reader (`design.read_bundle`, keyed on
  `<prefix>-design-1`): each file is read once, its sha256 checked against `design_meta.json`, and only those verified
  bytes are parsed (`design.json` with its schema and kind; exactly the 24 counts files, each line `<graph> <count>`
  with distinct graphs and positive counts, `design.parse_counts`; a provisional bundle's `rates.json`, whose sha256
  must equal its rates identity). Before, a graph's count doubled without its digest changed the reported SE under the
  original meta sha256. `production.py plan --design` parses the counts with the same `parse_counts` (a repeated graph
  line, a `+n` or 0 count or an unterminated last line is refused; before, the last of two lines won). The report also
  checks that the bundle's groups and graphs are the pilot's and that s, r and K are positive integers.
- **The bundle's SE at its own settings (Z10).** `report --bundle` recomputes the bundle's prediction at the bundle's
  frozen variance margin and imputation (`frozen_settings`, from `design_meta.json` `parameters.variance_margin`, equal
  to `design.json` `predicted.variance_margin`, and `imputed.impute`), and records `relative_difference` and `agrees`
  (to 1e-9, only when the pilot is the bundle's frozen pilot, matched by manifest sha256,
  `pilot_is_the_frozen_pilot`); a report from another pilot is labelled a PROJECTION (`kind`). An explicit
  `--variance-margin` or `--impute` other than the frozen value adds a separately labelled `projection` block; without
  them the report uses the frozen ones (the defaults 1.5 and addends apply to the target table only). Before, a bundle
  frozen with `--variance-margin 2` was reported 25% below its frozen SE.
- **α with each graph's own point ratio (Z12).** `--nested` must be a pilot of the same scientific identity
  (`NESTED_IDENTITY`: dimension, schema prefix, half_d, inputs manifest, two-loop jet, numerics, rates identity,
  backend; `check_nested`, refused otherwise). Each graph keeps its own point ratio (oriented so that the nested pilot
  has more points; graphs at equal point counts are left out and counted): one ratio in a stratum gives the closed
  form, several the pooled root of Σ v_lo ρ^(−2α) = Σ v_hi (bisection). The report records `nested` (the campaign, the
  identity checked, `ALPHA_RULE`, per stratum `alpha_by_ratio`, `ratios`, `point_pairs`, `graphs`, the estimator).
  Before, the last graph's ratio was used for the whole stratum (two graphs at 2n and 8n with variances 1/2 and 1/8
  gave α = 0.28 instead of 0.5). α comes from `--nested` only; the tail statistics come from `--pilot` (below).

**Heavy tails** (plan addition (ii); C63d's rule, `LRI_C8_D3_HPC_loop/PLAN.md` C.3 and E.6, `RECON.md` §6.3.6 and
`recon/cost_d3/tail_calib.py`, same statistics and thresholds), from the class-B native fields. As in C63d's rule, the
thresholds and actions apply to **L8 graphs only**, the loop they were calibrated on; L ≤ 7 graphs get the same
statistics as diagnostics (a summary per sector and loop, and every row in `--tails-out`), with no threshold and no
"screened" or "confirmed" label.

| Statistic | Definition | Threshold (L8 only) |
|---|---|---|
| ξ̂ (per graph and campaign) | mean over replicates of the Hill estimate from the 16 largest \|t\| (15 log-spacings above the 16th) | screen 0.38 |
| largest share | max over replicates of max\|t\| / Σ\|t\| | screen 0.05 |
| undefined | a replicate with fewer than 16 tail values, a 16th \|t\| ≤ 0, Σ\|t\| ≤ 0 or a value that is not finite makes the graph-campaign entry "undefined (reason)", with no mean over the other replicates | an L8 graph undefined in either campaign is listed and counted, never compared with a threshold |
| screen | either campaign at ≥ 4,096 points per replicate | |
| confirmed "possible infinite variance" | two-campaign mean ξ̂ at ≥ 32,768 points per replicate | > 0.44 |
| P8, per sector (C63d action 4) | 1.0865 exp(0.0890 (Var(Q) − 1.8696)), Q = ln(s²[reps 1-4]/s²[reps 5-8]) per graph, campaign and block of 8; Var(Q) pooled over the sector's **L8 graph-campaigns at 4,096 points per replicate** | R = 16 advised > 1.13 |
| P8, per stratum (action 5) | the same per stratum | L8 strata: flag > 1.196 with ≥ 500 graph-campaigns; L ≤ 7 strata: diagnostic only |

t is the weight-free base integrand at a point (`docs/NUMERICS.md`, class-B tail fields); ξ = 1/a for
P(|t| > x) ~ x^−a, and ξ ≥ 1/2 means infinite variance.

**Outcome at d = 2 (C8(2) production, tail check 2026-10-07/08,
`benchmarks/symmetry_2026-10-c8/production/tailcheck/README.md`).** The rule confirmed 4,832 L8 graphs. These were tail
warnings, not established infinite variance:
- a boundary analysis with a multi-prime randomized cancellation verification of all 24,173 kernels supports bounded
  L7/L8 weights at both rates;
- the fixed-k Hill estimate falls with N for bounded, sharply peaked weights, so with confirmation at ≥ 32,768 points
  most peaked graphs are confirmed.

A confirmation should therefore be read as a warning, to be followed by an N-trend check or the boundary analysis.

**The R = 16 switch without a stage A.** C63d pools P8 for action 4 over its stage-A graph-campaigns: the first eighth
of its L8 pass at 4,096 points and R = 8, with its nested graphs entering through their 4,096-point prefix rows. This
design flow has no separate stage A; its pilot is one pass. The closest faithful equivalent, implemented here, pools
the pilot's L8 graph-campaigns at exactly 4,096 points per replicate (the free L8 primitives included). L8
graph-campaigns at other point counts (P8 is calibrated at 4,096) and every L ≤ 7 graph are left out; the report
records both counts (`sector_P8`: `graph_campaigns`, `excluded_L8_other_points`, `excluded_L_le_7`). A nested pilot
(`--nested`) never enters P8.

## Freezing a bundle (`design.py freeze`)

```bash
python3 -B tools/design.py freeze --pilot PILOT --out BUNDLE (--target-rel R | --target-se S | --budget-core-hours B) \
    [--batches K] [--spent-core-hours X --total-cap Y] [--seeds-log LOG] [--test-only]    # LOG: the site's $C8_SEEDS
```

The bundle is published atomically and never overwritten: `design.json` (strata with s, V1, C1; replicates per
(sector, L); batches and their minimum; predictions; caps; efficiencies), `counts/<campaign>_<sector>_L<L>.txt` (base
counts of every inventory graph) and `design_meta.json` (its sha256 is the bundle identity). The meta pins the pilot,
the executable, the numerics, the rates identity (one per freeze), the inputs manifest, the forbidden seeds (the pilot
seed and every seed of the seed log), the predictions, the efficiencies and the rule. A test-only pilot gives only a
`--test-only` bundle, which only test-only plans accept.

### Route (b): an approved numerics profile for a bundle frozen from the exact pilot

**Finding F13 (measured 2026-10-05, `benchmarks/symmetry_2026-10-c8/pre6/`; fixed for the Stage-6 inspection).** On
J-SWEEP-2 the route-(b) freezes re-optimized the allocation under the profile's costs and over-delivered (SE 35.8 /
18.5 / 9.3 / 5.9 against 46 / 23 / 11.5 / 6.2) at 1.13-1.44× the cost of the exact freeze's allocation kept and
re-costed under the profile (669 / 2,309 / 9,236 / 30,067 lane core-hours), which meets every target. *Cause*
(`optimize()`'s greedy loop, replayed on the route-(b) strata): the split starts 2.2-9.9% short of the target; at
1e-3, 5e-4 and 2.5e-4 the loop doubles free L7, power L6 and power L5 first and then free L8 (about half the cost,
+48-56%) to close a remaining SE gap of 0.57% (1e-3) or 2.64% (5e-4, 2.5e-4); at 1.35e-4 it doubles free L6 and then
free L7 (+20%) to close 1.76%, and free L8 is not doubled. *Fix* (both of the verifier's remedies): the optimizer of
rule 4 (prune pass and lattice search, from both splits), and **route (b) designs both ways and keeps the cheaper
feasible design**: (1) re-optimized, the base counts and the allocation designed with the profile model's c_g; (2)
the exact path's design (its base counts, r, s and K) kept and re-costed with the profile model (its SE is the exact
design's; σ is the exact pilot's either way). (2) is kept only when it meets the target (or budget) and every cap
under the profile's costs and is strictly cheaper (a budget: strictly more precise) by 1e-12; ties keep (1).
`design_meta.json` records both (`route_b_choice`: each candidate's cost, SE, K, r, s and feasibility, the exact
design's own cost, which was kept); `design.py report --numerics P` prints the same choice per target.
On J-DES-5's strata (`tests/test_pipeline.py`, `jdes5_records`, from the committed records; lane core-hours; the
Stage-6 rows **measured on symmetry** by the real freezes of 77fab71, job 570302, `benchmarks/symmetry_2026-10-c8/pre6b/`,
equal to the recomputation in r, s, branch and cost):

| Target | 1e-3 | 5e-4 | 2.5e-4 | 1.35e-4 |
|---|---:|---:|---:|---:|
| exact path, F11 greedy (frozen, 570241) | 1,738 | 5,856 | 23,423 | 76,623 |
| exact path, Stage-6 optimizer | **1,702** | **5,740** | **22,961** | **74,573** |
| route (b), re-optimized as frozen (570241) | 923 | 3,322 | 13,289 | 33,978 |
| route (b), re-optimized, Stage-6 optimizer (the verifier's lattice optimum near the split) | 638 | 2,554 | 10,215 | 31,371 |
| route (b), the old exact allocation kept (570241's measurement) | 669 | 2,309 | 9,236 | 30,067 |
| route (b), the new exact allocation kept | 646 | 2,241 | 8,963 | 29,328 |
| **route (b), kept by the freeze** | **638** (re-optimized) | **2,241** (kept) | **8,963** (kept) | **29,328** (kept) |

Every SE equals its target to 0.01% (46.00 / 23.00 / 11.50 / 6.21). The kept design wins at the three tighter
targets because the profile's own base counts put more graphs at the 4,096-point floor (free L8: 19,603 against
18,334 graph-campaigns), which leaves their continuous Neyman bound 1.7% above the exact base counts' under the same
profile costs, and their power-of-two lattice lands less well; the strata-level recomputation does not re-check caps
(the freeze does, under the profile's costs: on symmetry every cap holds in all eight bundles, the kept exact designs
under the profile's costs included, and in their test-only plans; 570302).

Host decision of 2026-10-05 (`LRI_C8_D2_HPC_loop/PLAN-REVIEW-LOG.md`, "Stage-5 close"), implemented in 23540b2 so that
the Stage-6 inspection covers it. The pilot stays exact; production may run under a profile the user approved without
a second pilot under it (route (a), about 80 core-hours, needs the user's go: a key in
`production.APPROVED_PROFILE_PILOTS`, which is empty, and the gate record of the build; below).

```bash
source ~/c8d2/env.sh; : "${C8_SEEDS:?source the site environment}" "${PILOT:?the merged exact pilot}"   # W17
python3 -B tools/sweep.py SWEEP_DIR --seed <fresh> --cost-model cost_models/gmp_symmetry_amd_c8.json --numerics dd+mp256 \
    --approved-numerics-change "<ref>" --cost-model-out <profile model> --calibration <its own calibration file> \
    --seeds-log "$C8_SEEDS"   # in a job; the seed is added right after the plan (Y13)
python3 -B tools/design.py freeze --pilot "$PILOT" --target-rel R ... --seeds-log "$C8_SEEDS" --out designs/<name> \
    --numerics dd+mp256 --approved-numerics-change "<ref>" --cost-model <profile model> \
    --numerics-gate benchmarks/symmetry_2026-10-c8/s6fix4/s4flag.570574.0/jflag_dd+mp256/numerics_flags.json
```

- **Allowed profiles:** only the user-approved set, `production.APPROVED_PROFILES` = {`dd+mp256`}, with the approval
  reference "user check-in 2026-10-05: dd+mp256 approved for production after the pilot (C62d PLAN-REVIEW-LOG)".
  `freeze --numerics` and `report --numerics` refuse `dd`, `mp256`, `exp1`, `dd+mp256+exp1` and anything else; the
  set is C8(2)'s, so a c8-d3 pilot is refused. **Every non-test plan** enforces the set for every non-exact numerics
  (`production.py plan`, Stage 6): `plan --pilot --numerics P`, `plan --design` of a route-(a) bundle (frozen from a
  pilot that ran under P) and `plan --design` of a route-(b) bundle are refused for any P outside it, with or without
  `--approved-numerics-change`. **R7 stays off:** a non-test plan with `--rates` is refused unless the map's rates
  identity (its sha256) is in `production.APPROVED_RATES`, which is empty. **The pilot stays exact** (the user's
  decision of 2026-10-05): a non-test `plan --pilot` under any numerics other than exact or under `--rates` is refused
  unless its key (numerics, rates identity) is in `production.APPROVED_PROFILE_PILOTS`, which is empty (a route-(a)
  pilot or an R7 measurement pilot would need the user's explicit go there, besides the two sets above). **A gated
  build for every non-test plan whose numerics are not exact:** a route-(b) plan's executable must be a profile
  executable of one of the bundle's gate records (below); every other such plan (a route-(a) bundle, an approved
  profile pilot) must pass `--numerics-gate RECORD` (repeatable), each a passed full-scale J-FLAG gate record of the
  profile build (the checks of `design.py freeze --numerics-gate`, `check_gate`, with F2 over every graph of the
  plan's inventory) whose profile executable is the plan's; the manifest's `numerics_route` records it (route `a` or
  `pilot`, the gates, the go). `--numerics-gate` is refused on an exact plan and on a route-(b) bundle, which carries
  its own gates. Test-only plans (the J-FLAG gates' measurements, `tools/sweep.py` sweeps, the smoke, the test suites)
  keep taking any implemented profile or valid map with `--approved-numerics-change` and need no gate (a gate given
  must cover the build). `design.py rates` and `freeze --rates-bundle` still build a map's bundles (they spend
  nothing); the plan is where compute would be spent, so the allow-lists sit there. Changing any of the three sets is
  a user decision.
- **The pilot** must be exact and at the default rates (a pilot under a profile is frozen as before, route (a), and a
  non-test one needs the user's go in `APPROVED_PROFILE_PILOTS`; a rate map is not combined with a profile).
- **The cost model** must be measured under the profile (`tools/sweep.py --numerics P`, which needs
  `--approved-numerics-change` and its own `--calibration` file): its numerics identity must equal P (since fix round 1
  every non-test plan checks it, exact plans included: `production.load_cost_model` refuses a model of other numerics
  or of none, "cost model numerics identity"; a test-only plan keeps such a model with a warning recorded in
  `cost_model_numerics_exception`; and `make_cost_model.py class-factors` derives CPU-class factors only from a model
  and a run of the same numerics, exit 3 otherwise; X10), its backend and
  rates identity the pilot's, it must hold every inventory graph of both campaigns, and (freeze, Stage 6) the
  executable it was measured with must be one of the `--numerics-gate` records' gated builds
  (`cost_model.executable_gated`; on symmetry both are the fix-round-3 profile build `a46f3060…`, jobs 570536 and
  570538, `benchmarks/symmetry_2026-10-c8/s6fix3/`; before fix round 3, `d5df32ac…`). Every graph's c_g is the
  model's (no cost is imputed), so the base counts, the multipliers, the allocated cost and the caps (task chunking) are
  re-costed under P. η_omp,g and η_node stay the exact pilot's: tasks are sized to the same 60 s under either numerics.
- **The variance stays the exact pilot's σ_g²,** justified by the profile's F2 gate: dd+mp256 moves C8 by
  |dC8| + 3 SE_d = 4.25e-16 (job 570210; the fix-round-1 re-run job 570373: the same 4.25e-16, field for field; the
  fix-round-3 re-run on the new build, job 570536: the same 4.25e-16, field for field)
  against target SEs of 6-46, and its per-task values by at most 5.6e-14.
  So the predicted SE of a route-(b) bundle is computed exactly as for an exact one.
- **The gate record(s)** (`--numerics-gate`, repeatable): a passed, full-scale J-FLAG record of P's production build
  (`tests/numerics_flags.py --profile P`): status passed, no development option, F1, F2 and F5 passed, F2's total gate
  passed and resolved, the profile executable not a development build (no parameter override), F2 over at least every
  inventory graph. Since Stage-6 fix round 1 the record must also carry (`design.check_gate`): **F1's coverage** (X1:
  `F1.coverage` complete: scale 1, both sectors, the prescribed graphs per (sector, L) with 200 × 256 points at L7
  and 400 × 64 at L8 in contiguous ranges, binary128 and MP counts recounted against the need of 10,000 and 1,000,
  every baseline point evaluated by the profile), **the build binding** (X2: `build_binding`, every executable rebuilt
  byte for byte in a read-only source snapshot from its build record's Makefile command, the F1 tools compiled in the
  same snapshot, `F1.tool_snapshot_sha256` and `F1.baseline_binding`) and **verified OpenMP team sizes** (X3:
  `F5.team_sizes_verified`, every run and lane observed at its requested team). Job 570210's record has none of the
  three (its F1 coverage itself was complete) and is refused. Since Stage-6 fix round 3 the record must also show the
  **libgmp provenance of both F1 tools** (Z19, `design.gate_gmp_library`): the profile's `F1.tool_gmp_library` and the
  baseline's `f1_baseline.tool_gmp_library` each matched (want, tool and worker_now) to the libgmp sha256 its
  executable's build record names, `f1_baseline.reused` saying whether the baseline was reused, and for a reused one
  the check of the exact executable as it resolves its library now (`f1_baseline.reused_gmp_library`); `check_gate`
  returns `gmp_library` (both sha256 and the reuse flag). Job 570373's record (sha256 `2eaaebcf…`, profile executable
  `d5df32ac…`) predates Y1's `tool_gmp_library` and is refused for exactly that; its build is gone anyway (Z4). The
  approved build's record is the fix-round-3 re-run on the new build: job 570536 (sha256 `a8de4037…`, profile
  executable `a46f3060…`, exact `7741f733…`, libgmp `4dc20a90…` for both, GCC 11.4;
  `benchmarks/symmetry_2026-10-c8/s6fix3/`).
  The baseline's exact tool must come from the same source snapshot as the binding (`F1.baseline_binding`
  `snapshot_sha256`; a reused `--f1-baseline` of other sources is refused by the harness and by `check_gate`).
  `production.py plan` refuses a route-(b) bundle whose recorded gate entries lack the evidence the current
  `check_gate` returns (`F1_coverage` of both sectors at the need, `source_snapshot_sha256`,
  `F5_team_sizes_verified`, since fix round 3 `gmp_library`, since fix round 4 `inputs_manifest_sha256`;
  `production.gate_evidence_missing`): a bundle frozen with the 570210 record (pre6b, 570302), with 570373's (570379)
  or with 570536's (570539) cannot plan.
  **Since Stage-6 fix round 4 the record must carry its authenticated input set** (W18, `design.gate_inputs`): the
  `inputs` block of `tests/numerics_flags.py` (the sha256 of the inputs manifest the gate ran on, every input, pack and
  vendored pin verified against it at the start and again at the end of the run, complete) and an F1 baseline of the
  same inputs. `freeze` requires it to equal the pilot's inputs manifest and records it in each gate entry
  (`inputs_manifest_sha256`); `plan` requires every gate entry's to equal the bundle's (and its exact pilot's), and a
  plan given `--numerics-gate` checks the gate against its own inputs manifest. Before, an inventory revision that
  kept the graph counts and executables could reuse a gate measured on other kernels. Job 570536's record predates
  the block and is refused for exactly that; the gate ran again on the unchanged build `a46f3060…` and passed: **the
  approved build's record is now job 570574's** (sha256 `42e6d2d8…`, inputs manifest `3813f24a…`, a fresh F1 baseline,
  libgmp `4dc20a90…`; `benchmarks/symmetry_2026-10-c8/s6fix4/`), and the bundles re-frozen with it (job 570579, the
  same designs as 570539's byte for byte) can plan.
- **Recorded** in `design_meta.json`: `numerics` = P (what `plan --design` pins), `route_b_choice` (F13 above) and
  `profile_recost`: the route, the
  rule, the profile, the approval given to the freeze, the allow-list and its reference, each gate (path, sha256,
  Slurm job from its evidence folder, the gated profile and exact executables, host, CPU, compiler, F2 totals), the
  exact pilot's identity (campaign, manifest sha256, seed, executable, numerics, rates identity, inputs manifest,
  backend), and the cost model (path, sha256, numerics, backend, rates identity, executable and whether a gate passed
  it, CPU models, source manifest).
- **`design.py report --numerics P --cost-model <profile model>`** prints the target table re-costed the same way, each
  row the design a route-(b) freeze would keep (`route_b_chosen`; no approval or gate needed: nothing is frozen).

## Production batches and the combination

```bash
source ~/c8d2/env.sh                                  # the site environment first (Expanse: ~/c8d2/env_expanse.sh; W17)
: "${C8_SEEDS:?source the site environment}" "${C8_PACKAGE:?the export}"
# a batch has millions of tasks (J-DES-5: 5.2-8.5 million), so it is planned in a plan job, never on a login node, where
# production.py refuses a plan above 10^6 tasks without SLURM_JOB_ID (site options: docs/HPC.md, "Plan jobs")
sbatch [site options] --export=ALL,C8_PACKAGE="$C8_PACKAGE" "$C8_PACKAGE/slurm/plan.sh" BATCH_k \
  --design BUNDLE --cost-model CM --forbid-seeds-from "$C8_SEEDS" --seed <fresh> ...
# only after the plan job succeeded (sacct -j <id>, its log) and the seed sync: lanes or arrays, merge, assemble
python3 -B tools/combine.py BATCH_1 ... BATCH_K --output OUT            # C8_final.json: all K planned batches
python3 -B tools/combine.py BATCH_1 --output OUT --partial              # C8_partial.json: an interim combination
```

The plan job publishes the batch atomically and registers its seed (`slurm/plan.sh`; README "Quickstart", Stage-6 fix
round 3, Z15/Z16). Before fix round 4 (W16) this example ran `production.py plan` directly: a non-test batch has at
least 24,173 graphs x 2 campaigns x 32 replicates = 1,547,072 tasks, above the 10^6 that a plan outside a job may have,
so it failed on a login node.

`plan --design` reproduces the bundle's counts × s exactly with its replicates r, records the bundle sha256 and
refuses the bundle's forbidden seeds, a different inputs manifest, numerics or rates identity. It copies the bundle's
verified `design_meta.json`, `design.json` and `counts/*` into `<campaign>/design_bundle` (manifest
`design.pinned_copy`; X9, Stage-6 fix round 1), so a batch can be moved: `assemble.py` and `combine.py` read
`--bundle DIR` if given, else the pinned copy, else the path recorded at planning, and require the pinned
`design_meta.json` sha256 of whichever they read (it pins every counts file; the manifest is never rewritten). A batch
planned before fix round 1 is combined with `--bundle DIR`. A route-(b) bundle is
planned with `--numerics P --approved-numerics-change "<ref>"` (still required at plan time) and a `--cost-model`
measured under P; `plan` refuses a profile outside `APPROVED_PROFILES`, a bundle whose numerics differ from its pilot's
without a complete route-(b) record, a cost model of another numerics identity, a development build and, in a non-test
plan, an executable that none of the bundle's gates passed (its sha256 must be a gate's profile executable), and a
plan-time `--numerics-gate` (the bundle's gates are the record). The manifest records `numerics_route`: the profile,
the allow-list reference, the bundle's and the plan's approvals, the gates, the exact pilot, the bundle's and the
plan's cost models, the executable and whether it was gated. A route-(a) bundle (frozen from a pilot that ran under the
profile) is planned non-test only with `--numerics-gate RECORD` of the plan's build (the manifest's `numerics_route`
then has route `a`). `combine.py` accepts
batches of one bundle only (same design, inputs, numerics and rates identity, distinct group seeds, the coverage
guard per batch) and reports C8 of every batch and the inter-batch χ² about the combination; `verify_result.py`
checks the result before it is published (no-clobber), including, since fix round 1, `dimension` 2, `epsilon` `2s-2`
and `assembly.half_d` 1 leaf by leaf with their types (X16). Exact and profile batches never combine: they come from
different bundles, and `combine.py` also refuses batches whose numerics differ.

## After the pilot: the design and decision step (A-DES-4, A-PIL-2)

The pilot runs as in `docs/HPC.md`, "Pilot runbook". When its status exits 0, its result verifies and its accounting is
complete:

1. **The table.** `python3 -B tools/design.py report --pilot $PILOT --json <ev>/report.json --tails-out <ev>/tails.csv`
   (no `--test-only`: η_node comes from the pilot's own ledger over its work roles, the lane workers; plan and merge
   jobs are reported as overhead). It prints the predicted
   SE (with the margin 1.5) against allocated core-hours and the batch count K at the four targets, and per stratum
   V1, C1, kurtosis, skewness, largest |z|, largest single-graph share, P8 and α (0.5 assumed and said, unless a nested
   pilot was run). The pilot's 8 replicates make these statistics defined (a 2-replicate sweep leaves them null).
2. **The heavy-tail flags** (L8 only, C63d's rule). A screened graph (ξ̂ > 0.38 or largest share > 0.05 at 4,096
   points in either campaign) is listed for the user; it stays in the design. Confirmation needs ≥ 32,768 points per
   replicate, from the campaign that has them: run a separate report **with that campaign as `--pilot`**
   (`python3 -B tools/design.py report --pilot $FOLLOWUP --json <ev>/report_followup.json --tails-out
   <ev>/tails_followup.csv`), where `$FOLLOWUP` is a follow-up pilot of the same graphs at ≥ 32,768 points, or a
   production batch, whose merged tables give the heavy L8 graphs more points. The tail statistics (`tails.confirmed`)
   always come from `--pilot`; `--nested` feeds only α (Z14, Stage-6 fix round 3: this step used to recommend
   `report --nested`, which leaves the tails at the original 4,096 points and so can never confirm a graph). This package has no automatic
   production monitor (C63d's plan has one); a confirmed "possible infinite variance" graph is a user decision. P8 per
   sector and stratum is recorded with the table; this design's r ≥ 32 replicates per (sector, L) are above C63d's
   R = 8 and R = 16 designs, so P8 changes no freeze parameter here.
3. **The user decides**, from the table and `docs/PERFORMANCE.md` ("Pilot (2026-10-06)": the measured table of the
   symmetry pilot, which supersedes "Stage 5: the refined cost table"; evidence `benchmarks/symmetry_2026-10-c8/pilot/analysis/`):
   - the target (`--target-rel`, `--target-se`) or a budget (`--budget-core-hours`), with `--spent-core-hours` (the
     development total plus the pilot's `accounting.py` hours) and `--total-cap`;
   - the sites and the batch count: K ≥ the minimum K; more batches let symmetry and Expanse batches of one bundle run
     side by side and give `combine.py` an inter-batch χ²;
   - the numerics. The exact path is the default and needs nothing more. **The user approved `dd+mp256` for
     production after the pilot** (check-in 2026-10-05; `docs/NUMERICS.md`, "User decision"), with a short J-FLAG
     gate of the exact `dd+mp256` build (no `exp1`) before its first use: **that gate passed on symmetry** (job 570210,
     GCC 11.4: F1 dd max error 5.18e-12, F2 |dC8| + 3 SE_d = 4.25e-16 against 0.062, F4 ×2.530; `docs/NUMERICS.md`),
     passed again with the fix-round-1 harness (job 570373), and, since Stage-6 fix round 3 changed every kernel
     executable (Z4), passed on the new build with the fix-round-3 harness (job 570536), and, since fix round 4 requires
     the gate's authenticated input set (W18), passed once more on the same build: that record is the one `check_gate`
     accepts (job 570574; `benchmarks/symmetry_2026-10-c8/s6fix4/`).
     `exp1` and R7 stay off. Production under `dd+mp256` from this exact pilot is **route (b)** ("Route (b)" above,
     implemented in 23540b2): a sweep under the profile for its cost model (on symmetry it exists:
     `cost_models/gmp_symmetry_amd_c8_dd+mp256.json`, re-measured in fix round 3 with the new gated build `a46f3060…`,
     job 570538, sha256 `18e50440…`; the model of job 570240, valid for the old build `d5df32ac…`, is replaced), then
     `freeze --numerics dd+mp256` with the approval, that cost model and the gate record of job 570574 (570210's is
     refused since fix round 1, 570373's since fix round 3, 570536's since fix round 4);
     batches are planned with
     `--numerics dd+mp256 --approved-numerics-change`
     on a gated build (a build of another site or compiler needs its own gate record in the freeze). Route (a), a
     second pilot under the profile (about 80 core-hours), stays possible but needs the user's go as a key of
     `production.APPROVED_PROFILE_PILOTS` (empty: a non-test profile pilot is refused) and `--numerics-gate` with the
     gate record of the build, at the pilot's plan and at every batch's.
     An R7 map (not approved) would need `design.py rates --rule one-step` on this pilot, a measurement under the map
     and `freeze --rates-bundle` ("Opt-in rate maps" below).

   | Decision | Options | Read from |
   |---|---|---|
   | Target | relative SE 1e-3, 5e-4, 2.5e-4, 1.35e-4, or an SE or a budget | `report`: predicted SE (margin 1.5) and allocated core-hours per site |
   | Numerics | exact (default); `dd+mp256` (approved for production after the pilot; its build gate passed, 570210, re-run with the fix-round-1 evidence as job 570373, on the fix-round-3 build as job 570536, and with the input set of fix round 4 as job 570574; route (b) above, or route (a) with the user's go in `APPROVED_PROFILE_PILOTS` and a gated build); `exp1`, `dd` or `mp256` alone, R7: not approved | `docs/PERFORMANCE.md` cost table (per site, both); `docs/NUMERICS.md` A-FLAG-7 accuracy and the user decision |
   | Sites, batches | symmetry amdq and/or Expanse compute (AMD nodes only, F5), K ≥ minimum | the freeze's K and caps; site wall from the lane schedule; J-DES-5's plan sizes |
   | Heavy tails | proceed, nest, or drop a confirmed graph (changes the estimand: user only) | `report` tails and `--tails-out` |

   The production-size dry run J-DES-5 (`benchmarks/symmetry_2026-10-c8/stage5/des5/README.md`) froze the four
   targets from the J-SWEEP-2 sweep and planned each bundle in a job: K = 1 at every target; 5.2-8.5 million tasks,
   20,533-36,475 checkpoints and 351-6,424 indices per batch; plan wall 5-11 minutes and peak RSS 0.84-1.31 GiB on an
   Intel sharedq node; every cap held. A batch at 1.35e-4 projects 55,971 files (mind the Expanse Lustre quota).

4. **Freeze** the chosen design (non-test; the pilot's ledger gives η_node):

   ```bash
   source ~/c8d2/env.sh; : "${C8_SEEDS:?source the site environment}" "${PILOT:?the merged pilot}"   # W17
   python3 -B tools/design.py freeze --pilot "$PILOT" --target-rel <R> --spent-core-hours <X> --total-cap <Y> [--batches K] \
     --seeds-log "$C8_SEEDS" --out designs/<name>
   python3 -B tools/design.py report --pilot "$PILOT" --bundle designs/<name>     # the bundle's SE, recomputed from its counts
   ```

   The freeze refuses an infeasible budget (printing the minimum), a total over the cap (printing the minimum cap) and a
   K below the minimum; the bundle's `design_meta.json` sha256 is its identity. Under `dd+mp256` (route (b)) add
   `--numerics dd+mp256 --approved-numerics-change "<ref>" --cost-model <profile model> --numerics-gate <record>`.
5. **Batches.** For each k: a fresh seed (`tools/seeds.py check` against both logs), `slurm/plan.sh BATCH_k --design
   designs/<name> --cost-model <the site's model> --forbid-seeds-from $C8_SEEDS --seed <fresh>` in a plan job (route
   (b): `--numerics dd+mp256 --approved-numerics-change "<ref>"` and the site's model measured under the profile). The
   plan registers its seed in the first `--forbid-seeds-from` log itself, under that log's lock, before the batch is
   published (Z15; the manifest records `seed_log`); then sync the other site's log and the mirror (`docs/HPC.md`, "The
   seed log"). Lanes on AMD nodes inside an agreed window, merge and assembly per batch. Then
   `tools/combine.py BATCH_1 … BATCH_K --output OUT_DIR` (all K: `C8_final.json` inside `OUT_DIR`) or `--partial` for
   an interim `C8_partial.json`; `--output` names a directory (J-SMK-3's job 570111 passed a `.json` path and then
   verified the directory).

## Opt-in rate maps (R7; R04, R14, R19)

Rates change the integrand's variance and cost, so a map is designed, measured and frozen again:

1. `design.py rates --pilot PILOT --source-bundle B --rule one-step --out PROV` (or `--spec SPEC` in place of the
   rule) writes a NEW provisional bundle holding only `rates.json` (schema `c8-d2-rates-1`: every graph of both
   campaigns, campaigns a and b different) and a `design_meta.json` with `"provisional": true`, the map's sha256, the
   source bundle's meta sha256 and its rates identity. It carries no counts, no `design.json` and no multipliers:
   `plan --design PROV` refuses it in every plan (R19), and `design.py report --bundle PROV` says "unavailable
   (provisional)".
   - **`--rule one-step` chooses the rates from the pilot** (A-FLAG-6; the rule that derived the Stage-4c map from
     J-SWEEP-1, moved from `benchmarks/expanse_2026-10-c8/stage4c/dev_r7/scripts/r7_spec.py` into `design.py` in
     Stage 5). Per (sector, L): W_c = Σ_g σ_g √c_g of campaign c (σ_g² = n_g Var_rep(J8·jet_g) at the pilot means, c_g
     = row seconds / (replicates · n_g)), the Neyman variance × cost W_c² of the stratum at its optimal allocation, and
     r = W_b²/W_a² (.9 over .8). Fewer than `--min-graphs` (100) graphs, or 1 − band ≤ r ≤ 1/(1 − band) (`--band`
     0.10), keeps a .8, b .9; r < 1 − band steps up (a .9, b 1); r > 1/(1 − band) steps down (a .7, b .8). a and b
     stay `--step` (0.1) apart, so they differ for every graph. The pilot must have run at the default rates (a pilot
     under a map is refused). A graph bootstrap (`--boot` 1000 resamples, seed 7082026) gives 68% and 95% intervals
     of r for the record only. `design_meta.json` records the rule as `rate_rule`: its text and parameters, the
     pilot's identity (manifest sha256, seed, executable, numerics, rates identity) and per stratum the graphs, W, V,
     C, the ratios, the interval and the decision.
   - **`--spec SPEC`** is the explicit alternative: `{campaign: {sector: {L: "rate" | {graph: "rate"}}}}`; whatever it
     does not name keeps the campaign's default (.8 or .9); `rate_rule` records the file, its sha256 and its content.
   As in `freeze` and `report`, a pilot whose pinned tools changed after it was planned is accepted, and the change is
   recorded (`accepted_tool_changes`).
2. Measure under the map: `tools/sweep.py --rates PROV/rates.json --approved-numerics-change "<approval>"` (a cost
   model whose rates identity is the map's sha256) and `production.py plan --pilot --rates PROV/rates.json
   --approved-numerics-change "<approval>"` (its allocation recorded and labelled with the map's sha256). A NON-test
   plan under the map also needs the map in `production.APPROVED_RATES` (empty: R7 is off), and a non-test pilot
   under it the key ('exact', the map's sha256) in `production.APPROVED_PROFILE_PILOTS` (empty: the pilot stays
   exact); both are user decisions, and the non-test acceptance in `tests/test_pipeline.py` part 3 monkeypatches them.
3. `design.py freeze --pilot PILOT_UNDER_MAP --rates-bundle PROV ...` makes a fresh, non-provisional bundle pinning the
   map's sha256 and the provisional bundle's meta sha256 (R14). It refuses a pilot measured under another identity
   (the source pilot included), and a pilot under a map is frozen only this way.
4. A plan of the fresh bundle needs `--rates PROV/rates.json --approved-numerics-change ...` and, when non-test, a cost
   model measured under the same identity (D15). `tests/test_pipeline.py` part 3 runs this chain non-test end to end
   on a scratch package with minimal non-test inputs: the non-test plan of the fresh bundle is accepted with the
   approval and the cost model under the map, and refused without the approval, with the default-rates cost model,
   without a cost model and without the map.

A non-test plan refuses a cost model measured under another rates identity. Reusing the source allocation under a
new map would miss the target SE and under-predict the cost (`tests/test_pipeline.py`: the fake integrand under a map
keeps its mean with 2× the variance and 1.5× the cost per point; the source allocation's SE grows by √2 and its cost by
1.5, the fresh freeze meets the target).

## Reuse (H6)

`--dimension D`, `--schema-prefix c8-dD` (`c8-d2`), `--half-d D/2` (1), `--two-loop`, `--inventory` and `--selection`
make the tool usable for C8(3): `--dimension 3 --schema-prefix c8-d3 --half-d 1.5 --two-loop inputs/two_loop.json
--inventory inputs/inventory.json --selection inputs/selection.json` (C63d's E.5). The three must agree, and they
must name the pilot's own campaign; every schema read or written follows the prefix.

| Read or written | Schema |
|---|---|
| the pilot's manifest (`order` 8, `dimension` D) | `<prefix>-production-1` |
| its group configs, at the manifest's sha256 pins | `<prefix>-group-1` |
| its `merged.json` (complete, its manifest and config hashes, payload checksum, the three tables at their digests) | `<prefix>-merged-1` |
| its ledger `submissions.jsonl` (η_node; every record, `tools/ledger.py --schema-prefix`) | `<prefix>-ledger-1` |
| its accounting (η_node; `tools/accounting.py --schema-prefix`) | `<prefix>-accounting-1` |
| a bundle's `design.json` and `design_meta.json` | `<prefix>-design-1` |
| a provisional bundle's `rates.json` | `<prefix>-rates-1` |
| the report (`--json`) | `<prefix>-design-report-1` |

A `c8-d2` pilot is verified as `production.py` does (pinned tools, inputs, vendored assembly); its `--inventory` and
`--two-loop` overrides must be the files its inputs manifest pins, and `--selection` is refused (X14). Another package's
pilot is read through this campaign interface (the tables `graph_replicates.csv`, `graph_costs.csv`,
`graph_tails.csv`; the manifest fields `seed`, `executable_sha256`, `numerics`, `rates_identity`,
`inputs_manifest_sha256`, `test_only`, `backend`, `threads`, `allocation`, `groups`, `jobs`; the configs' `campaign`,
`sector`, `L`, `replicates`, `counts`; the checkpoints' fingerprints and the ledger for η_node), and its `--inventory`
and `--two-loop` are required: they, and `--selection` when given, must be the files its inputs manifest lists by
sha256 (the `manifest.json` beside `--inventory`, whose sha256 is the pilot's `inputs_manifest_sha256`). A `c8-d2`
plan refuses a bundle of another prefix. The prefix of a campaign must match its ledger: a ledger record of another
prefix (a `c8-d2-ledger-1` record under a c8-d3 pilot, or the reverse) refuses `freeze` and `report`, whichever path
η_node takes, and `accounting.py` and `ledger.py` refuse a campaign of another prefix. `tests/test_pipeline.py` covers
A-DES-6 (a synthetic d = 3 freeze) and the command line above on a c8-d3 view of the fake pilot with its own
`c8-d3-ledger-1` ledger (η_node through freeze and report), with the refusals.

## Tests

`tests/test_pipeline.py`: A-DES-1 (full-size synthetic pilot of all 24,173 graphs: powers of two ≥ 4096, r in
[32, 128], budget, infeasible minimum, K, atomic bundle, forbidden seeds, caps), A-DES-2 (the report table; the bundle
SE recomputed independently), A-DES-6 (d = 3, imputation of a 1/8 L8 subsample, nested α), F11 (r of every target
bundle against independent checks, `check_optimizer`; a synthetic full-size pilot reproducing F11: the old rule at
2.85× the independently recomputed continuous optimum, the F11 greedy design at 1.09×, the optimizer at 1.07× with the
target met and the SE recomputed from the counts), F13 (a randomized property test: on 2,000 seeded random stratum
sets at a target the optimizer is feasible and never costlier than either old rule's final design, recomputed by hand,
while the old F11 rule alone is costlier than the Stage-5 rule in some sets; on 600 sets at a budget it is never less
precise and refuses exactly when they do; J-DES-5's strata from the committed records give the table under "Route
(b)"), route (b) (in process: re-costing with a non-uniform profile model recomputed independently, σ kept, the
keep-cheaper choice recomputed independently with both branches exercised, the record, the re-costed report, 22 refusals;
on the command line, test-only through `combine` and non-test through `plan`, with the refusals listed under "Route
(b)"), the allow-list scope (non-test `plan --pilot --numerics` for `dd`, `mp256`, `exp1`, `dd+exp1`,
`dd+mp256+exp1` and `plan --design` of route-(a) bundles under `dd` and `dd+mp256+exp1` refused, a test-only `dd` plan
accepted; non-test plans under an R7 map refused, and accepted only with `APPROVED_RATES` monkeypatched to hold the
map, A-FLAG-6, the non-test pilot under the map also with `APPROVED_PROFILE_PILOTS`), the Stage-6 policy (a non-test
`plan --pilot --numerics dd+mp256` refused, with the go monkeypatched refused without a gate of the build, with another
build's gate or a failed one, accepted with the gate; a non-test route-(a) `dd+mp256` bundle planned only with the
gate; `--numerics-gate` refused on an exact plan and a route-(b) bundle; a test-only profile pilot needs none;
`tests/unit_orchestration.py` `route_b_records`: every refusal branch of `production.route_b`, `design.check_gate` and
`production.gated_route`, with the fix-round-1 evidence fields and their refusals), Stage-6 fix round 1
(`tests/test_numerics_flags.py` `coverage`, `binding`, `f5_team`: `f1_coverage`'s refusals, 570210 refused for exactly
the three missing-evidence reasons, 19 `check_gate` refusals, the snapshot rebuild and stale-executable refusals, the
sanitized OpenMP environment and the observed teams; `tests/test_pipeline.py` part 2: X10 class factors, X14
authenticated overrides, X15 live allocations; route (b) refusals for no coverage, one sector and an unmet quota;
`tests/unit_orchestration.py` `cost_numerics` and `bundle_relocation`; `tests/verify_result_tamper.py` X16), and the fake end-to-end chain (sweep → ledger → accounting → freeze; pilot → lanes → merge → freeze →
batches → combine; the rates flow).
