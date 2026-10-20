# Stage 4c R7 (opt-in rate maps): A-FLAG-6 statistical validation on Expanse

Branch `flag-r7` (worktree `LRI_C8_D2_HPC_wt_r7`), from the Stage-4c framework head 64287cb. Site deviation U1
(Expanse). R7 stays opt-in: the default binaries, commands and plans are unchanged. The export ebf01f62e833 (build
54673788) gives `bin/c8d2_decimal` `99a51c1d…` and `bin/c8d2_gmp` `1d2a2181…`, the final default binary byte for byte
(A-RPL-8; `expanse/s4cbuild.54673788.0/identity.json`).

**Result.** A provisional per-(campaign, sector, L) map derived from J-SWEEP-1 was published, measured and frozen
again on real data. The R14/R19 path works end to end. Under the map, every per-(sector, L) contribution and the total
agree with a fresh exact-path campaign within 3σ (unpaired; largest |z| = 2.06). The variance × cost falls by about
16%: the continuous Neyman figure is ×0.842 [0.810, 0.874], and the integer test-only freezes at the four targets,
with one η_node, give ×0.82–0.88 in core-hours. These numbers come from 2 × 512-point sweeps with a stand-in pilot.
They are development evidence, not a production approval.

## A-FLAG-6 coverage (Mac tests)

Before this branch, `tests/unit_orchestration.py` (`rates`) and `tests/test_pipeline.py` (R14/R19) covered most
bullets. Both suites pass: unit_orchestration 36/36 tests, test_pipeline 13/13 (`mac/`). The gaps found, and what
closed them:

| A-FLAG-6 bullet | Gap | Now |
|---|---|---|
| `design.py rates` … per graph … the source bundle stays byte-unchanged | Per-graph spec entries untested; the source bundle checked only through its pin | `rates_extra_checks`: per-graph entries (the other graphs keep the default; every graph of both campaigns present); every file of the source bundle byte-identical after `rates` (also on Expanse: `r7prep…/src_bundle_*_rates.sha256`) |
| … keeping campaigns a and b different | Equal a/b refused only by `plan --rates`, not by `design.py rates` | A spec with one graph equal in a and b is refused, nothing created |
| (real data) a pilot planned with older tools | **`design.py rates` refused J-SWEEP-1**: production.py, common.py, lanes.py and slurm_submit.py changed after Stage 3, and it called `verify_base` without accepting tool changes, unlike `freeze` and `report` | **Fixed** (`tools/design.py`): accepted, recorded as `accepted_tool_changes` (and `pilot`) in the provisional `design_meta.json`; test with a changed pinned tool |
| freeze --rates-bundle refuses … any run … whose rates identity is not the map's | Only the default-identity source pilot was tested | A pilot and a sweep measured under the map, frozen with ANOTHER map's provisional bundle: refused (R14) |
| A sweep (`sweep.py --rates`) and a pilot … feed a fresh freeze … equal an independent recomputation | Only the pilot fed a freeze | `rates_sweep_freeze`: the sweep's labelled allocation; its fresh freeze equals the independent recomputation and is not the default sweep's allocation |
| `design.py rates` *chooses* rates … from the pilot | `design.py rates` takes the choice as an explicit `--spec`; it computes nothing from the pilot | Not changed in the tool. The choice rule lives in `scripts/r7_spec.py` and is recorded with its data (see below). **Open for the host:** whether the rule belongs in `design.py` |
| A non-test plan accepts the fresh bundle (D15) | Not testable with the fixture (a non-test plan uses the package's inputs only), and the fresh bundles here are test-only | Covered by the D15 cost-model check (`load_cost_model(..., test_only=False)`) and, on real data, by a test-only plan accepting the fresh bundle (below). **Residual:** a non-test plan needs a non-test pilot under the map (P ≥ 4096) |

## The map (provisional bundle, rates identity `98a215a8…20fc`)

J-SWEEP-1 (Stage 3b, job 54641706; a test-only bootstrap sweep of all 24,173 graphs at 2 × 512 points on the Stage-3
binary `5c5328af…`) **stands in for the pilot** (host decision 2026-10-04). It is not a design pilot. The rule
(`scripts/r7_spec.py`; record `expanse/r7prep.54673789.0/spec_derivation.json`):

- per (sector, L), compute r = W_b² / W_a², the Neyman variance × cost W² = (Σ_g σ_g √c_g)² at .9 over .8 (σ_g² = n Var_rep of the graph's C8 projection J8·jet, c_g in seconds per point);
- step up (a .9, b 1) when r < 0.9, step down (a .7, b .8) when r > 1/0.9, otherwise keep a .8, b .9; strata with fewer than 100 graphs are kept.

| Stratum | Graphs | r (J-SWEEP-1) [95% graph bootstrap] | Map a / b |
|---|---|---|---|
| free L3, L4, L5 | 5, 16, 76 | 9.08, 0.53, 1.22 (too few graphs) | .8 / .9 (kept) |
| free L6 | 395 | 1.008 [0.746, 1.371] | .8 / .9 (kept) |
| free L7 | 2,441 | 1.014 [0.870, 1.175] | .8 / .9 (kept) |
| **free L8** | 16,064 | **0.763 [0.715, 0.814]** | **.9 / 1** |
| power L3, L4, L5 | 1, 3, 20 | 0.02, 1.90, 8.10 (too few graphs) | .8 / .9 (kept) |
| **power L6** | 107 | **0.469 [0.206, 1.055]** | **.9 / 1** |
| **power L7** | 709 | **0.783 [0.551, 1.156]** | **.9 / 1** |
| **power L8** | 4,336 | **0.782 [0.634, 0.968]** | **.9 / 1** |

- **Source bundle.** A test-only freeze of J-SWEEP-1 at 1.35e-4, `src_bundle`, with η_node from its ledger and sacct.
- **Provisional bundle.** `prov/`, holding only `rates.json` and `design_meta.json`, with `provisional: true`. Its `accepted_tool_changes` lists the four tools changed since Stage 3. Copies: `expanse/r7prep.54673789.0/prov_*`.
- **Report.** `design.py report --bundle prov` prints "unavailable (provisional)".

## Jobs (all COMPLETED; `expanse/sacct.txt`)

| Job | Partition, CPUs | Elapsed | What |
|---|---|---|---|
| 54673788 | shared 16 | 0:41 | `submit_s4c.sh build` of ebf01f62e833 (export check `setup/export_check_ebf01f62e833.json`): A-RPL-8, stub identity |
| 54673789 | shared 8 | 0:52 | `r7_prep.slurm`: seeds checked, source bundle, J-SWEEP-1 report, spec, provisional bundle |
| 54673790 | compute 128 (<NODE>) | 15:10 | `r7_sweep.slurm` map: `sweep.py --rates prov/rates.json --approved-numerics-change …`, all graphs, 2 × 512, seed 2722425707250628025 |
| 54673791 | shared 32 | 16:58 | `r7_pilot.slurm`: `plan --pilot --rates` complement and its exact twin, 32 × 512 points, L3–L6 complete plus the 400 cheapest L7/L8 graphs per group |
| 54673843 | compute 128 (<NODE>, the same node) | 5:18 | `r7_sweep.slurm` exact: default rates, all graphs, 2 × 512, seed 8022834103257619820 |
| 54673844 | shared 16 | 3:43 | `r7_analysis.slurm`: accounting, assembly, freezes, R14/R19 checks on real data, `r7_compare.py` |
| 54673870 | shared 4 | 5:07 | `r7_refreeze.slurm` (a verified copy of the committed file): freezes with one η_node, plan timing, comparison |

Total 195,628 core-seconds = **54.3 SU** (budget 150). One compute node at a time. No job is live.

## Agreement (unpaired, A-FLAG-6)

Method (`scripts/r7_compare.py`):

- y = J8·jet is each graph-replicate's C8 projection, with J8 the vendored order-8 Jacobian at the exact sweep's loop means (as in F2).
- A contribution is (mean_a + mean_b)/2 of the graph-summed replicate means. Its variance comes from the per-graph replicate variances, which have R − 1 degrees of freedom each.
- Δ = map − exact; SE² = var_map + var_exact; ν_eff is Welch–Satterthwaite.
- A "dof-aware" verdict (the t_ν p-value at the 3σ level) is reported next to |z| ≤ 3, because a 2-replicate stratum of a few graphs has an SE of 2–10 degrees of freedom.

**Sweeps (all graphs, 2 × 512 points):**

| Sector | L | Graphs | Map | Exact | Δ | SE | z | ν_eff |
|---|---|---|---|---|---|---|---|---|
| free | 3 | 5 | -12833.0 | -12827.4 | -5.6 | 71.6 | -0.08 | 3 |
| free | 4 | 16 | -8620.8 | -8547.3 | -73.5 | 119.2 | -0.62 | 10 |
| free | 5 | 76 | -9977.1 | -10355.4 | 378.4 | 375.0 | +1.01 | 7 |
| free | 6 | 395 | -12365.8 | -11883.8 | -482.0 | 552.5 | -0.87 | 75 |
| free | 7 | 2441 | 8129.4 | 8217.4 | -88.0 | 1426.4 | -0.06 | 901 |
| free | 8 | 16064 | 55197.2 | 55925.4 | -728.1 | 878.9 | -0.83 | 4203 |
| power | 3 | 1 | 156.6 | 158.2 | -1.6 | 3.3 | -0.49 | 3 |
| power | 4 | 3 | 106.6 | 105.1 | 1.6 | 26.9 | +0.06 | 2 |
| power | 5 | 20 | 67.7 | 67.3 | 0.4 | 47.3 | +0.01 | 10 |
| power | 6 | 107 | -23.4 | 237.7 | -261.1 | 133.8 | -1.95 | 11 |
| power | 7 | 709 | -386.6 | 167.7 | -554.3 | 268.7 | -2.06 | 49 |
| power | 8 | 4336 | -434.0 | -532.0 | 98.1 | 174.8 | +0.56 | 232 |
| **total (linear)** | | | 19016.8 | 20732.7 | -1715.9 | 1842.8 | -0.93 | 1293 |

- **Per (sector, L) and total:** all within 3σ, and every dof-aware verdict passes.
- **Per (campaign, sector, L):** largest |z| 1.92.
- **Nonlinear C8 (`assemble.py`):** map 46195 ± 1997, exact 47914 ± 1675, z = −0.66.
- **Scale:** these are test-only sweeps at 2 × 512 points, not physical results.

**Many-replicate complement (32 × 512; L3–L6 complete, the same 400 cheapest L7/L8 graphs in both arms):** this is
the dof-adequate check of the strata that have few graphs.

| Sector | L | Graphs | Δ | SE | z | ν_eff |
|---|---|---|---|---|---|---|
| free | 3 | 5 | 5.2 | 16.7 | +0.31 | 181 |
| free | 4 | 16 | -56.8 | 35.7 | -1.59 | 440 |
| free | 5 | 76 | -84.2 | 81.1 | -1.04 | 1006 |
| free | 6 | 395 | -179.1 | 153.5 | -1.17 | 4371 |
| free | 7 | 400 | -88.7 | 176.4 | -0.50 | 22344 |
| free | 8 | 400 | -41.1 | 38.5 | -1.07 | 26767 |
| power | 3 | 1 | 1.2 | 1.0 | +1.27 | 95 |
| power | 4 | 3 | -3.6 | 4.7 | -0.76 | 246 |
| power | 5 | 20 | 0.9 | 13.2 | +0.07 | 606 |
| power | 6 | 107 | 33.5 | 42.9 | +0.78 | 1917 |
| power | 7 | 400 | 27.2 | 41.3 | +0.66 | 7177 |
| power | 8 | 400 | -9.2 | 13.9 | -0.66 | 14332 |
| **total (linear, partial sums)** | | | -394.6 | 261.2 | -1.51 | 21196 |

- **Result:** all within 3σ; per (campaign, sector, L) the largest |z| is 1.79.
- **Control, J-SWEEP-1 against the fresh exact sweep:** both at default rates, on different binaries. All per-(sector, L) values and the total are within 3σ (total z = −1.04). One campaign-level pull, a_power_L3 at z = 3.32, comes from one graph whose 2-replicate SE has 1 degree of freedom. That stratum's dof-aware verdict passes, and it is why the complement exists.

## Variance × cost (A-FLAG-6)

The sweeps ran on the same node, one after the other. In the strata whose rates the map keeps, the cost ratio is
0.987, the node and run control. In the changed strata it is 0.806. Per (campaign, sector, L), map over exact,
L ≥ 6:

| Campaign | Sector | L | Rate exact → map | W² ratio [95%] | V ratio | C ratio | Share of √F (exact) |
|---|---|---|---|---|---|---|---|
| a | free | 6 | .8 → .8 | 1.082 [0.781, 1.505] | 1.117 | 1.001 | 0.004 |
| b | free | 6 | .9 → .9 | 0.885 [0.649, 1.178] | 0.714 | 0.999 | 0.005 |
| a | free | 7 | .8 → .8 | 0.990 [0.870, 1.122] | 1.012 | 1.000 | 0.112 |
| b | free | 7 | .9 → .9 | 1.088 [0.954, 1.235] | 1.107 | 0.971 | 0.106 |
| a | free | 8 | .8 → .9 | **0.693 [0.652, 0.733]** | 0.860 | 0.795 | 0.375 |
| b | free | 8 | .9 → 1 | **0.916 [0.861, 0.976]** | 1.244 | 0.824 | 0.318 |
| a | power | 6 | .8 → .9 | 1.071 [0.471, 2.244] | 2.825 | 0.734 | 0.001 |
| b | power | 6 | .9 → 1 | 0.511 [0.198, 1.263] | 0.327 | 0.783 | 0.001 |
| a | power | 7 | .8 → .9 | 1.012 [0.704, 1.500] | 1.695 | 0.752 | 0.009 |
| b | power | 7 | .9 → 1 | 0.736 [0.456, 1.183] | 1.430 | 0.784 | 0.009 |
| a | power | 8 | .8 → .9 | 0.728 [0.584, 0.899] | 0.959 | 0.801 | 0.031 |
| b | power | 8 | .9 → 1 | 0.731 [0.595, 0.922] | 0.937 | 0.809 | 0.027 |

- **Total, F = (Σ over (c, s, L) of W/2)² at a fixed target (continuous Neyman):** **×0.842 [0.810, 0.874]**. The plain variance × cost of the two sweeps at their own equal allocation is ×0.838.
- **Where the gain comes from:** mostly campaign a at free L8 (.8 → .9). Campaign b's step from .9 to 1 raises the free-L8 variance by 24%, and the cost falls by 18%, so its net W² is 0.92.
- **Why the cost falls:** fewer MP promotions at the higher rate. At free L8 the MP fraction goes from 6.6% to 4.4% (a) and from 4.4% to 3.0% (b), from the cost models.
- **Consistency check at the same rate:** map campaign a at .9 against exact campaign b at .9 gives W² 0.966, V 1.029 and C 0.969 at free L8.
- **Heavy tails:** at 512 points no calibrated tail screen applies (the screen is at 4,096 points). The Hill diagnostics of the two arms are similar. At free L8, campaign b, 0.90 of graph-campaigns have ξ̂ > 0.38 under the map against 0.83 at .9.

**Test-only freezes at the four targets (relative to |C8| = 4.6e4).** The fresh bundles are frozen from the map sweep
with `--rates-bundle prov`; the exact bundles from the exact sweep.

| Target | Exact core-h | Fresh core-h | Ratio, one η_node 0.481 (54673870) | Ratio, own η_node (54673844) |
|---|---|---|---|---|
| 1e-3 | 7,118 | 5,859 | **0.823** | 2.90 |
| 5e-4 | 10,512 | 9,202 | **0.875** | 3.09 |
| 2.5e-4 | 42,047 | 36,809 | **0.875** | 3.09 |
| 1.35e-4 | 137,883 | 118,912 | **0.862** | 3.04 |

- **Why the last column misleads:** design.py takes η_node from the campaign's accounting. The map sweep's plan step (hashing the 7.5 GB L8 packs and writing tasks.sqlite on Lustre) took about 11 minutes longer, in contention with the complement's plan, so its η_node is 0.136 against 0.481 for the exact sweep. Its busy core-hours were in fact lower (4.41 against 5.44).
- **The map does not slow the plan:** back-to-back timing in 54673870 gives `plan --rates` 74 s and 80 s, and the default plan 79 s.
- **For the host:** η_node of a sweep includes its plan step, so a slow filesystem inflates a fresh freeze's allocated core-hours.

## R14/R19 on real data (54673844, `expanse/r7analysis.54673844.0/refusal_*.txt`)

- `plan --design prov` is refused ("provisional rates bundle … no allocation source in any plan (R19)") and creates nothing.
- `freeze --rates-bundle prov` of the exact sweep is refused (R14).
- A freeze of the map sweep without `--rates-bundle` is refused.
- The fresh bundles are non-provisional. They pin the map's sha256 and the provisional `design_meta.json` sha256 `2478e1f4…`.
- A test-only `plan --design fresh_1.35e-4 --rates prov/rates.json --approved-numerics-change …` is accepted: rates identity = the map's, allocation source `design`. It was recorded and removed, never run.
- The same plan without `--rates` is refused ("the design bundle pins rates identity …").

## Seeds (all in `$C8_SEEDS`; `scripts/r7_seeds.env`)

| Campaign | Seed |
|---|---|
| map sweep | 2722425707250628025 |
| exact sweep | 8022834103257619820 |
| map complement | 1105895641646430410 |
| exact complement | 5381295915103878074 |
| plan-only check (never run) | 5253374642973259395 |

## Approval text and limits

- **Approval text.** The `--approved-numerics-change` text says what this run is: "D1 (user, 2026-10-03): R7 opt-in, Stage-4c A-FLAG-6 test-only validation measurement; NOT a production approval". The user approves R7 for future campaigns or not.
- **Not a design pilot.** J-SWEEP-1 is a stand-in, and the map is a one-step rule from two measured rates.
- **Variance estimates.** The W² and σ come from 2 × 512-point sweeps. RQMC variance at production counts (4,096 points and up) can scale differently, so a real pilot under the map (`plan --pilot --rates`, P ≥ 4096) must re-measure before any production freeze (R14).
- **Rate 1.** The step to 1 in campaign b is the weaker half of the map: higher variance, lower cost. A map with b = .95 was not measured.
- **Location.** The work directories stay on Lustre: `$C8_DATA/r7-ebf01f62e833/` (prov, src_bundle, both sweeps, both complements, the fresh, exact and equal-η bundles; 4,474 files) and the export `pkg/ebf01f62e833` (6,558 files). Evidence copies are in `expanse/`; the tails CSVs are gzipped.
