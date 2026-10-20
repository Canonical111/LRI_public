# 3D long-range Ising: production plan and analysis protocol for Δ_ε(Δ_σ) (FIT_MODEL_3D)

Status: revision 5 (2026-09-21) — after Codex review rounds 1–4 (20 findings FIT3D-001…020, all accepted and applied; round cap raised to 7 by the user);
for round 5. Changes since revision 4 are in the tooling only (frozen extension ledger per snapshot; empty-primary evaluation), see FIT_MODEL_3D-REVIEW-LOG.md.
whole-node benchmarks (54383841, 54384046) are in; the preflight (arrays 54385146/54385147, analysis 54385148) is queued/running and its two numbers
(pinned L = 128 rate; 64→128 bracket/ESS) enter §5.1 as the gate record; D4 below fixes 10⁶ sweeps at every size; the preflight rate sets only the array-A wall limit (§5.1 gate record).
Sister document: `../LRI_2d_MC/FIT_MODEL_2D.md` (revision 5, Codex-reviewed 2026-09-20, evaluator `evaluate_2d.py` rev 5); everything not stated here
is inherited from it unchanged.
Notation: `$C3 = /expanse/lustre/scratch/zzheng8/temp_project/lri3d`; code = the audited `lri_precision_v2` build in Expanse `~/lri2d/code`
(`bin/lri_mc` sha f384737c…; the dimension is a runtime flag `--dim 3`); scripts and records in `LRI_3d_MC/` (Mac) and `~/lri3d/` (Expanse).

## 1. Goal and acceptance criteria
Goal: the leading Z₂-even scalar dimension Δ_ε of the 3D long-range Ising model along the non-trivial line 1.5 < s < s* = 2 − η_3D ≈ 1.964
(Δ_σ = (3 − s)/2 exact), at the eight reference points s ∈ {1.55, 1.6, 1.7, 1.75, 1.8, 1.85, 1.9, 1.95}, from size-doubling crossings of
U4 (primary), U6, U8 and Y extrapolated over four doubling pairs, with the decision table of §4 (one label per point, never a gap).
Expectation from theory: Δ_ε → 1.5 at the Gaussian end (s → 1.5, ε = 2s − 3 → 0) and → 3 − 1/ν_3D = 1.413 at the short-range end.
Criteria (evaluated by `evaluate_3d.py`, the d = 3 instance of `evaluate_2d.py` with the constants of §3–§4):
1. every point receives exactly one label of §4.6; ACCEPTED or ACCEPTED (σ_sys-dominated) is the target at the central points
   (s = 1.7 … 1.85), with MODEL-LIMITED / CONDITIONAL allowed at the two ends (§4.7);
2. precision: σ_stat(Δ_eff^U4, 64→128) ≤ 0.003 at every point (stage-0 σ(32→64) = 0.015–0.017 with 2 × 10⁵ sweeps → ≈ 0.002 with 60× the statistics), else the label carries "[σ_stat above target]";
3. provenance: every production record verifies the chain of §4.8 (raw hashes, index/manifest hashes, binary identity, frozen design).

## 2. What is known (2026-09-21)
- Code: `lri_precision_v2` audited 2026-09-20 (sampler exact, 3D pilot L = 32 reproduced bitwise on Expanse, cross-check χ² 2.95/5);
  interrupt/resume on Lustre verified bitwise (2D job 54367357; the same code path). Hybrid sampler rates on the delivery host (EPYC 9V74):
  L = 32: 0.91, 64: 8.0, 128: 73.6 ms/sweep; Expanse cores ≈ 1.55× slower (2D measurement).
- Pilot s = 1.8 (L = 8, 16, 32): β× 0.10018 (8→16), 0.10008 (16→32); Δ_eff(U4) 1.436(10), 1.451(15); Δ_eff(Y) 1.447(12), 1.548(16) → corrections
  to scaling dominate at L ≤ 32 (Y and U4 differ by 6σ at 16→32). τ ≤ 10 sweeps.
- Reference centres (old exploratory 16→32 U4 crossings, stderr ≈ 1.5×10⁻⁵) for the eight points: 0.089327 (1.55), 0.091558 (1.6), 0.095882 (1.7),
  0.098006 (1.75), 0.100108 (1.8), 0.102147 (1.85), 0.104169 (1.9), 0.106216 (1.95). Mean-field 1/ΣJ = 0.0823 … 0.0949; β_c/β_MF ≈ 1.106 at 1.8.
- Stage 0 (job 54383840, 53 min, 320 chains on 64 shared cores): every pair has exactly one U4 crossing inside its bracket, 0 bootstrap failures,
  τ_int ≤ 19 sweeps, block(1000)/τ ≥ 53, |half-drift z| ≤ 3.15 (2 of 640 chains above 3). ESS at the crossing 0.98–1.00 (8→16), 0.90–0.92 (16→32),
  0.67–0.71 (L = 64 side of 32→64, half-width 2.8×10⁻⁴). β× drifts by −1.0…−1.4×10⁻⁴ from 8→16 to 16→32 and by −0.1…−3.8×10⁻⁵ from 16→32
  to 32→64. Rates at 64 chains per shared node: L = 8/16/32/64 = 0.042/0.21/1.60/14.3 ms per sweep. Confirmation of the package's earlier 3D
  numbers: β×(16→32) within 3.1×10⁻⁵ of `reference/dimension_curve.csv` at all points; Δ_eff within the old errors at 6 of 8 points, pulls −2.5
  (s = 1.55, old error 0.046) and +2.6 (s = 1.8, an older exploratory row; stage 0 agrees with the bitwise-reproduced pilot there to 0.2σ).
  Δ_eff(U4) ≈ 1.43–1.48 at every point and pair; Δ_eff(Y) runs from 1.41 (s = 1.55) to 1.68 (s = 1.95) at 32→64: corrections to scaling grow
  towards the short-range crossover (the 2D "regime C" analogue), and towards the Gaussian end Y and U4 also disagree (1.55: 1.41 vs 1.48).

| s | Δσ | 8→16: β×, U4, Y | 16→32: β×, U4 (pull vs CSV), Y (pull) | 32→64: β×, U4, Y, ESS(L=64) |
|---|---|---|---|---|
| 1.55 | 0.725 | 0.089482, 1.4531(89), 1.2611(107) | 0.089340, 1.4366(118) (-2.5), 1.3404(130) (-1.6) | 0.089317, 1.4847(168), 1.4148(167), 0.68 |
| 1.6 | 0.700 | 0.091678, 1.4469(95), 1.3007(109) | 0.091559, 1.4485(126) (+0.1), 1.3693(143) (+0.4) | 0.091521, 1.4685(167), 1.4504(175), 0.67 |
| 1.7 | 0.650 | 0.095995, 1.4341(74), 1.3658(96) | 0.095876, 1.4433(111) (+0.2), 1.4606(122) (+0.2) | 0.095851, 1.4608(163), 1.5205(163), 0.68 |
| 1.75 | 0.625 | 0.098111, 1.4294(92), 1.4125(105) | 0.097993, 1.4507(107) (-0.5), 1.5008(124) (-0.0) | 0.097977, 1.4329(155), 1.5185(164), 0.68 |
| 1.8 | 0.600 | 0.100207, 1.4386(85), 1.4527(93) | 0.100084, 1.4475(128) (+2.6), 1.5449(131) (+2.2) | 0.100069, 1.4567(164), 1.5830(164), 0.69 |
| 1.85 | 0.575 | 0.102267, 1.4329(81), 1.4902(93) | 0.102135, 1.4489(108) (+0.3), 1.5882(116) (+0.7) | 0.102135, 1.4563(148), 1.6066(150), 0.70 |
| 1.9 | 0.550 | 0.104286, 1.4411(78), 1.5372(99) | 0.104180, 1.4397(107) (+1.4), 1.6101(118) (+0.0) | 0.104164, 1.4453(161), 1.6491(165), 0.71 |
| 1.95 | 0.525 | 0.106281, 1.4300(76), 1.5671(92) | 0.106184, 1.4433(113) (+0.8), 1.6598(119) (+1.6) | 0.106176, 1.4564(152), 1.6783(162), 0.69 |
- Whole-node benchmark (job 54383841, exp-8-27, 13.6 min): with 128 concurrent chains (64 of L = 64 + 64 of L = 128) the medians are
  L = 64: 14.8 ms/sweep (13.9–30.0), L = 128: 246 ms/sweep (236–269); alone on the same node: L = 64: 13.1, L = 128: 105 ms/sweep. Contention
  factor 1.13 at L = 64 but 2.3 at L = 128 (2.1×10⁶ spins per chain: memory-bandwidth bound). At 246 ms a 10⁶-sweep L = 128 chain needs 68 h
  (> 48 h; ≈ 510 node-h for 480 chains). Follow-up benchmark bench2 (job 54384046): 249 ms at 16 and at 32 concurrent L = 128 chains — independent of the count,
  i.e. an L3-sharing effect (run_pack pins consecutive workers onto the 4-core CCXs; four ≈ 10 MB working sets per 16 MB L3). The preflight (array 54385146: 32 L = 128 chains per node, one per CCX via `taskset -c 0-127:4`) measures the
  pinned production rate directly; bench3 (54384773, queued) adds the two-per-CCX number. Expected pinned rate: 105–130 ms/sweep.

## 3. Design decisions
| decision | choice | reason | risk |
|---|---|---|---|
| D1 grid | the 8 reference points s = 1.55, 1.6, 1.7, 1.75, 1.8, 1.85, 1.9, 1.95 (Δσ = 0.725 … 0.525) | centres exist only there (D1 of the 2D plan) | s = 1.95 lies 0.014 below the crossover s*; slow SR crossover corrections expected there |
| D2 sizes and packing | L = 8, 16, 32, 64, 128 (pairs 8→16, 16→32, 32→64, 64→128). L = 128 chains run 32 per whole node, ONE PER 4-core CCX (`expanse/array_pinned.slurm`, `LRI_CPUMASK=0-127:4`, 15 slots of 32); L ≤ 64 chains on separate whole nodes, 128 workers, LPT-balanced slots (`make_plan.py --lbig 128 --slot-big 32`) | the L = 128 working set (≈ 10 MB) needs its own 16 MB L3: packed four per CCX it runs at 246–250 ms/sweep independent of the chain count (benchmarks 54383841/54384046), alone at 105 ms; L ≤ 64 chains are unaffected (14.8 vs 13.1 ms) | 8→16 (512 spins) is a small pair; the extrapolation may be limited by it (§4.7); 15 concurrent node jobs use most of the account cap (≤ 22 running incl. the 2D arrays until 2026-09-22) |
| D3 temperatures | 5 β per size; centre β_c(L) = β×(L/2→L) from stage 0 for L = 16…64, β×(8→16) for L = 8, and for L = 128 the L = 64 centre plus the last observed drift (`make_production_centers_3d.py` → `production_centers_3d.csv`, frozen); half-width w(L) = 1.0×10⁻³ (L/16)^(−1.0): 2.0e-3, 1.0e-3, 5.0e-4, 2.5e-4, 1.25e-4 for L = 8…128 — exponent 1.0 follows the 3D thermal window L^(−1/ν) (1/ν ≈ 1.55) more closely than the 2D 0.75, w(128) = 3.3× the largest observed drift (3.8×10⁻⁵) and ≈ 10× the expected L = 128 centre error, ESS at the 64→128 crossing expected 0.55–0.7 (stage 0 gave 0.67–0.71 at L = 64 with 2.8×10⁻⁴) | the 3D thermal window shrinks like L^(−1/ν) with 1/ν ≈ 1.55, steeper than in 2D | a mis-centred L = 128 bracket → COVERAGE-LIMITED at that point |
| D4 statistics | 12 replicas (hot/cold alternating) × 10⁶ measured sweeps + 5×10⁴ warm-up per (L, β) at EVERY size, extended record — no per-size exception (FIT3D-001: the evaluator's completeness check is one frozen count per point; a reduced L = 128 count would need a per-size target that the toolchain does not have). The pinned L = 128 rate r measured by the preflight sets the array-A wall limit: 1.4 × r × 1.05×10⁶ rounded up to the hour, capped at 46 h; if a chain needs more than 46 h the checked continuation (`continue_3d.slurm`, afterany, TIMEOUT/75 only) finishes it in a second job (as in 2D §5.2); if the implied chain time exceeds 80 h (r > 274 ms) production is not submitted and this plan returns to review | statistics as in 2D: stage-0 σ(32→64) 0.015–0.017 with 2×10⁵ sweeps → ≈ 0.002 with 60×; 10⁶ sweeps at 105–130 ms is 29–36 h per chain | budget §5; a continuation adds queue time, not cost |
| D5 analysis | identical to FIT_MODEL_2D §4 with d = 3: Δ_eff^Q(L) = 3 − log₂(Q′_{2L}/Q′_L) at the U4 crossing; four pre-registered pairs; profiled-ω′ GLS extrapolation; joint series J = {U4, Y}; paired cross-check; reblocking b = 1000/4000 vs 2000; provenance chain | same estimator family; no global fit | none beyond 2D |

## 4. Analysis protocol
Inherited verbatim from FIT_MODEL_2D.md §4.0–4.8 with these substitutions: pairs (8,16), (16,32), (32,64), (64,128); d = 3 everywhere the
evaluator checks the dimension; DESIGN constants of D3/D4 above; criterion 2 refers to the 64→128 pair; `production_centers_3d.csv` is the frozen
centres table; the evaluator is `evaluate_3d.py` (a copy of `evaluate_2d.py` revision 5 with the constant block replaced, unit-tested on the
stage-0 records in preview mode). Decision table §4.6 and expectations §4.7 apply with "s = 1.55, 1.6" (Gaussian end: ω ≈ ε = 2s − 3 → 0) and
"s = 1.9, 1.95" (SR crossover) as the regimes where MODEL-LIMITED / CONDITIONAL is the expected outcome.

## 5. Numerics plan and schedule (allocation ends 2026-09-30; the 2D production occupies 5 nodes until ≈ 2026-09-21 16:00 PDT)
5.1 Stage 0 + benchmarks (2026-09-21, done; §2): centres, ESS, τ, rates, contention — every 16→32 and 32→64 crossing inside its bracket, ESS ≥ 0.67,
    τ ≤ 19 sweeps. Preflight (arrays 54385146/54385147 + analysis 54385148): 8 points × L ∈ {64, 128} × 5 frozen-D3 β × 2 replicas × 5×10⁴ sweeps
    under the production pinning. GATE for production: every 64→128 U4 crossing inside its bracket with ESS ≥ 0.5 at both sizes, no bootstrap
    failures, τ ≤ 30 sweeps; the pinned L = 128 rate r fixes the array-A wall limit (D4). The gate job (`expanse/preflight_analysis_3d.slurm`, FIT3D-005) requires the complete
    chain set and all eight analyses, evaluates every condition, and writes `$C3/preflight/GATE.json` (decision, reasons, r, wall limit, per-point rows,
    manifest/index/results hashes); `submit_production_3d.sh` refuses to run without a passed gate record. RESULT: [preflight].
5.2 Production: one campaign `prod3d-<date>` (prepare.py --dim 3 with the frozen D3/D4 constants, `production_centers_3d.csv`, seed base <date>):
    8 × 5 × 5 × 12 = 2400 chains, 2.4×10⁹ measured sweeps at every size, ≈ 154 GB raw. Work: array A = 480 L = 128 chains in 15 slots of 32 (one per
    CCX): per chain 1.05×10⁶ × r = 31 h (r = 105 ms) … 38 h (130 ms); 15 nodes × 31–38 h ≈ 460–570 node-h (≈ 60–75 k SU); the requested wall limit 1.4 × r × 1.05×10⁶ reaches its 46 h cap at r = 113 ms (a safety-margin threshold, not a runtime); a chain actually
    exceeds 46 h only for r > 158 ms (before overhead), and only then does the first job end by TIMEOUT and the continuation finish the chains in a
    second job (total wall ≤ 2 × 46 h; charged node-hours unchanged) — the continuation runs only after an actual TIMEOUT or checkpointed stop; array B =
    the 1920 chains with L ≤ 64 (480 × 14.8 ms × 1.05×10⁶ ≈ 2070 core-h at L = 64 plus ≈ 200 core-h below) in 4 LPT-balanced whole-node slots of
    128 workers ≈ 5–6 h each. Both arrays are submitted twice; the continuation is `expanse/continue_3d.slurm` (afterany; runs only after TIMEOUT or a checkpointed stop, and
    launches `array_pinned.slurm` so that the CPU mask and the measurement target are preserved, FIT3D-002). Launch plans are created exclusively
    (`open(…, 'x')`) and the submission script `expanse/submit_production_3d.sh` claims an atomic `mkdir` lock before writing any plan or calling sbatch,
    journals every job id, and refuses duplicates (FIT3D-006). Concurrency cap (FIT3D-008): the script computes the array-A throttle as
    22 − (array-B slots) − (my other queued/running normal-QOS jobs at submission time), at most 15 — e.g. %13 while the five 2D array-A slots are
    still running, %15 after they end (≈ 2026-09-22 04:00 PDT); 15 + 4 + 5 = 24 would exceed the cap, so the throttle, not %15, is the rule. Schedule: review and gate 2026-09-21/22; submission 2026-09-22; completion ≈ 09-24; analysis
    09-24/25; slack to 09-30.
5.3 Analysis (§4) as shared-partition jobs behind the arrays: pack b = 2000/1000/4000, 24 precision analyses (500 draws, seed 571239, min-ess 0.2),
    evaluator; records copied to `LRI_3d_MC/prod/`.
5.4 Extension rule: as in 2D §5.4 with two additions — the new per-point total is rounded UP to a multiple of 4000 (the largest reblock; otherwise the
    packer's floor(n/block) leaves the chains short of the registered count and the point becomes NON-PRODUCTION, FIT3D-004), and `extensions.json`
    keys must be registered s values with integer totals ≥ 10⁶ that are multiples of 4000 (validated by the evaluator, which rejects anything else);
    extensions relaunch through `make_plan.py --only-s <s> --lbig 128 --slot-big 32` and `array_pinned.slurm` with `LRI_MEASUREMENTS` set to the new total
    and the same mask, and their continuations through `continue_3d.slurm`. 5.5 Runbook: as in 2D §5.5 (never cancel a running job; pack/analysis never on the login node; raw chains archived
    off Expanse before 2026-09-30 — pi's 1 TB disk holds the 1D data (≈ 660 GB); the 2D (154 GB) and 3D (≈ 154 GB) raw data need another venue
    or a decision to keep only the packed histograms).
5.6 Not planned: L = 256 (≈ 8× the L = 128 cost); temperature fits across sizes; new observables.

## 6. Assumptions and risks
- A1 the reference centres were within the stage-0 brackets at L ≤ 64 at every point (verified 2026-09-21); the L = 128 centres are extrapolated by the last drift (≤ 3.8×10⁻⁵) and covered by w(128) = 1.25×10⁻⁴.
- A2 the pinned (one per CCX) L = 128 rate on a full production node is 105–130 ms/sweep (single chain 105 ms; packed four per CCX 246–250 ms); measured
  by the preflight and recorded in GATE.json; above 113 ms the requested wall limit is capped at 46 h (safety margin < 1.4×), above ≈ 158 ms a chain actually needs the continuation, above 274 ms no production (D4).
- A3 corrections to scaling at the Gaussian end (s = 1.55, 1.6: ω ≈ 0.1–0.2) and at the crossover (s = 1.95) are not resolvable with L ≤ 128;
  the plan reports the labelled finite-size outcome there (§4.7).
- A4 storage: 2400 chains × 64 MB = 154 GB raw on Lustre (quota 9.5 TB, 3.3 TB used).

## 7. Verification
1. `evaluate_3d.py --no-index-check` on the stage-0 analyses (preview): runs end to end and labels every point NON-PRODUCTION for the expected
   reasons (block 1000, 2 replicas, 10⁵ sweeps, stage-0 window constants) — done 2026-09-21, `stage0/evaluation_preview/run1/`.
2. Preflight (§5.1): the array log must show the mask line (32 CPUs for 32 workers), every chain DONE, the 64→128 crossings inside their brackets
   with ESS ≥ 0.5, and the measured pinned rate r; the D4 rule is applied from r and the outcome written into §5.1 RESULT before submission.
3. Stage-0 confirmation of the package's earlier 3D numbers (§2, `compare_stage0_reference.py`): recorded.
4. Production: 2400/2400 DONE before packing (gate in the pack job), then §5.3; the evaluation's provenance chain verifies (§4.8).
5. Production wrappers `expanse/prod_pack_3d.slurm`, `prod_analysis_3d.slurm`, `prod_evaluate_3d.slurm` (derived from the 2D ones: pack b = 2000/1000/4000
   gated on 2400/2400 DONE, 24 analyses with the production settings, evaluator on 8 primaries + 16 reblocks). The gate job and the submission script
   are bound to each other (FIT3D-011): GATE.json records the preflight manifest/index/analysis hashes, the centres hash, the D3 constants and the
   packing (mask, slot size); the submission script re-verifies all of them, validates the production manifest against the frozen design and requires
   every preflight temperature to be a production temperature, also when the campaign directory pre-exists; the gate job works in attempt-scoped
   directories (FIT3D-012) and re-uses only a verified complete packed index. The centres table is created exclusively and never overwritten.
6. `evaluate_3d.py` = `evaluate_2d.py` rev 5 with the constant block replaced plus hardening changes made after review rounds 1–2 (recorded in the
   review log): (a) the manifest task list is validated against the full registered Cartesian product (8 points × 5 sizes × 5 β × 12 replicas, unique ids,
   per-task d/measurements/warmup/nn_extra) — an unchecked manifest is never the completeness oracle (FIT3D-007); (b) every failure inside the processing of a reblock record (loading, field access, record checks, indexing) is attributed to that reblock and yields REBLOCKING UNAVAILABLE for its point while the primary result stands; malformed primaries are reported as NON-PRODUCTION rows, duplicate primaries are refused, and every registered point receives a row (FIT3D-003/009); (c) `extensions.json` is validated as in §5.4 (FIT3D-001/004);
   (d) 3D defaults in `make_plan.py` and exclusive plan creation (FIT3D-002/006). The stage-0 preview (item 1) is re-run after these changes.
