# FIT_MODEL_2D — Δ_ε(Δ_σ) for the d = 2 long-range Ising model on Expanse
Status: **revision 5 — 2026-09-20, after the fresh-Claude review of rev 1 (8 findings) and three Codex rounds (rev 2: 12 findings; rev 3:
6; rev 4: 5 — FIT2D-001…016, all accepted, see FIT_MODEL_2D-REVIEW-LOG.md). The user closed the review at three Codex rounds; the round-3
fixes are applied without a further pass. Simulation design D1–D4 unchanged; §4/§5 revised; frozen for production
analysis once the preflight (§5.1a) confirms D3 and the wall limit.**
Companion of FIT_MODEL_V3.md (d = 1); same discipline (pre-registration, blind selection, complete decision table, provenance), different
observables and analysis path (multi-temperature MBAR crossings from `lri_precision_v2`, no global temperature fit).

## 1. Goal and acceptance criteria
Determine Δ_ε at a grid of Δ_σ values in the interior long-range regime of d = 2, Δ_σ ∈ (0.125, 0.5) ⇔ s ∈ (1, 1.75), from
size-doubling crossings at L = 64 … 1024, with a statistical error and a systematic estimate under one label of the decision table §4.6.

1. Every grid point ends with exactly one label of §4.6 and, unless the label says otherwise, a quoted Δ_ε ± σ_stat ± σ_sys.
2. At every point the largest-pair finite-size dimension Δ_ε,eff(512→1024; U4) has σ_stat ≤ 0.003 (stage-0 scaling of the bootstrap error, D4).
3. Reproducibility: immutable manifests (`prepare.py --campaign-id`), per-chain SHA-256 and binary identity, analysis on frozen packed
   histograms with fixed bootstrap seeds; window centres and widths come from stage 0 only (never from production Δ_ε values).

## 2. What is known (2026-09-20)
- Code: `lri_precision_v2` audited (AUDIT_2026-09-20.md): exact envelope sampler, cross-checked against the table engine at 2D L = 64,
  pilots reproduced bitwise on Expanse; interrupt/resume on Lustre verified bitwise (job 54367357). Speed (single core, EPYC class): ≈ 0.5 ms/sweep at L = 128, 2.3 at 256 (est.), 9.3 at 512,
  38.6 at 1024, 250 at 2048. Autocorrelation times of K, m², Binder-slope scores ≤ 15 sweeps up to L = 512 (stage 0).
- Pilot at Δ_σ = 0.3 (L ≤ 128): Δ_eff(U4) = 0.9617(102), 0.9721(120) for 32→64, 64→128; Δ_eff(Y) differs by 6σ at 64→128 →
  corrections to scaling dominate at these sizes. Old exploratory L = 64→128 estimates exist for the eight reference points.
- Stage 0 (job 54367298, 58 min, 320 chains on 64 shared cores): eight points, L = 64…512, 5 β at ±0.002·(L/64)^-0.5, 2 replicas,
  10⁴ + 10⁵ sweeps. Every pair has exactly one U4 crossing inside its bracket, no bootstrap failures, τ_int ≤ 15 sweeps, |drift z| ≤ 4.
  β× drifts by ≤ 1.1×10⁻⁴ between successive pairs (mostly ≤ 3×10⁻⁵). ESS on the L = 512 side falls to 0.37–0.39 with that window
  (too wide), hence D3. Δ_eff(U4) ≈ 0.93–0.99 everywhere; Δ_eff(Y) runs from 0.88 (s = 1.05) to 1.14 (s = 1.7) and agrees with U4
  only near s = 1.3: slow corrections at both ends (ω = 2s − 2 → 0 as s → 1; the long-range perturbation becomes marginal as s → 1.75),
  the 2D analogue of the 1D regimes A and C. Rates at 64 chains/node: L = 64/128/256/512 = 0.23/0.90/3.5/16.3 ms per sweep.

| s | Δσ | pairs: β×, Δ_eff(U4)(σ), Δ_eff(Y) (z_Y−U4), min ESS |
|---|---|---|
| 1.05 | 0.475 | 64→128: β×=0.130093, U4 0.9496(0.0111), Y 0.8179 (z=-15.8), ESS 0.72 ; 128→256: β×=0.130014, U4 0.9653(0.0157), Y 0.8758 (z=-8.3), ESS 0.53 ; 256→512: β×=0.130016, U4 0.9788(0.0193), Y 0.8875 (z=-6.2), ESS 0.37 |
| 1.1 | 0.450 | 64→128: β×=0.135545, U4 0.9544(0.0108), Y 0.8452 (z=-14.7), ESS 0.72 ; 128→256: β×=0.135483, U4 0.9689(0.0149), Y 0.8963 (z=-6.7), ESS 0.53 ; 256→512: β×=0.135458, U4 0.9736(0.0203), Y 0.9275 (z=-3.0), ESS 0.37 |
| 1.2 | 0.400 | 64→128: β×=0.146363, U4 0.9556(0.0099), Y 0.9113 (z=-6.1), ESS 0.74 ; 128→256: β×=0.146335, U4 0.9812(0.0140), Y 0.9337 (z=-5.7), ESS 0.54 ; 256→512: β×=0.146337, U4 0.9639(0.0195), Y 0.9331 (z=-2.4), ESS 0.37 |
| 1.3 | 0.350 | 64→128: β×=0.157099, U4 0.9624(0.0096), Y 0.9663 (z=+0.6), ESS 0.74 ; 128→256: β×=0.157131, U4 0.9749(0.0137), Y 0.9724 (z=-0.3), ESS 0.54 ; 256→512: β×=0.157115, U4 0.9280(0.0182), Y 0.9430 (z=+1.3), ESS 0.37 |
| 1.4 | 0.300 | 64→128: β×=0.167812, U4 0.9531(0.0101), Y 0.9976 (z=+6.9), ESS 0.75 ; 128→256: β×=0.167809, U4 0.9631(0.0124), Y 1.0078 (z=+5.7), ESS 0.55 ; 256→512: β×=0.167828, U4 0.9740(0.0148), Y 1.0137 (z=+4.0), ESS 0.37 |
| 1.5 | 0.250 | 64→128: β×=0.178377, U4 0.9509(0.0092), Y 1.0377 (z=+16.2), ESS 0.76 ; 128→256: β×=0.178406, U4 0.9699(0.0116), Y 1.0483 (z=+10.8), ESS 0.56 ; 256→512: β×=0.178439, U4 0.9893(0.0183), Y 1.0405 (z=+5.1), ESS 0.37 |
| 1.6 | 0.200 | 64→128: β×=0.188808, U4 0.9570(0.0099), Y 1.0886 (z=+22.6), ESS 0.77 ; 128→256: β×=0.188874, U4 0.9827(0.0119), Y 1.0981 (z=+16.8), ESS 0.57 ; 256→512: β×=0.188896, U4 0.9786(0.0149), Y 1.0818 (z=+12.4), ESS 0.38 |
| 1.7 | 0.150 | 64→128: β×=0.199051, U4 0.9714(0.0092), Y 1.1524 (z=+30.4), ESS 0.78 ; 128→256: β×=0.199161, U4 0.9530(0.0112), Y 1.1288 (z=+28.7), ESS 0.58 ; 256→512: β×=0.199194, U4 0.9819(0.0138), Y 1.1345 (z=+20.1), ESS 0.39 |
 Whole-node contention at 128 chains/node (job 54367299, exp-7-41): factor 1.0–1.1 (L=256 median 3.84 ms/sweep vs 3.6–4.5 single; L=512
  15.7 vs 14.4); Expanse cores are ≈ 1.55× slower than the delivery's benchmark host → production rates L=512 ≈ 15 ms, L=1024 ≈ 60 ms/sweep.

## 3. Design decisions
| decision | choice | reason | risk |
|---|---|---|---|
| D1 grid | the 8 stage-0 points Δ_σ = 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.475 (s = 1.7 … 1.05) | stage-0 centres exist only there; interpolated centres at new s would risk the narrow L = 1024 windows | coarse near the crossover s → 1.75; extra points need their own stage 0 |
| D2 sizes | L = 64, 128, 256, 512, 1024 (4 doubling pairs) | 1024 is the largest size whose 10⁶-sweep chain fits one 48 h job; 2048 (≈ 70 h/chain) deferred to a later phase off Expanse | 4 pairs is the minimum for an extrapolation with a free ω |
| D3 temperatures | 5 β per size; centre β_c(L) = β×(L/2→L) from stage 0 for L = 128…512, β×(64→128) for L = 64, and for L = 1024 the L = 512 centre plus the last observed drift (≤ 3.4×10⁻⁵); `production_centers.csv`. Half-width w(L) = 0.0015 (L/64)^(−0.75): 1.5×10⁻³, 8.9×10⁻⁴, 5.3×10⁻⁴, 3.2×10⁻⁴, 1.9×10⁻⁴ for L = 64 … 1024 (spacing 9×10⁻⁵ at 1024, |Δ log β|·sd(K) ≈ 1) | each pair's crossing must lie inside the shared bracket with ESS ≥ 0.5 on both sizes; the narrowest windows give the best slopes | a centre off by more than w(L) at L = 1024 leaves the crossing outside the bracket → the point falls to COVERAGE-LIMITED |
| D4 statistics | 12 replicas (hot/cold alternating) × 10⁶ measured sweeps + 5×10⁴ warm-up per (L, β), extended 8-column record | 60× the stage-0 statistics per (L, β): σ_stat(256→512) 0.015–0.020 → ≈ 0.002–0.003; the same at 512→1024 | budget, see §5 |
| D5 analysis | crossing dimensions from U4 (primary), U6, U8, Y at the U4 crossing, per pair; extrapolation across the four pairs with a profiled ω; observable spread as σ_sys; paired-bootstrap cross-check (§4) | matches what the code measures; no global fit whose windows would have to be pre-registered | corrections may not be a single power at L ≤ 1024 (crossover to the short-range fixed point near s → 1.75) |

## 4. Analysis protocol (frozen before production data are analysed; implemented by `LRI_2d_MC/evaluate_2d.py`)
4.0 Pre-registered pairs: (64,128), (128,256), (256,512), (512,1024). A pair absent from a record (crossing outside its bracket, ≠ 1 root,
    ESS < 0.2, non-positive slope ratio) is a coverage failure; the evaluator never extrapolates with fewer than the four pairs.
4.1 Inputs: packed histograms at b = 2000 (primary) and b = 1000, 4000 (reblocking) of every DONE chain; `precision_analysis.py --bootstrap
    500 --seed 571239 --min-ess 0.2` per s. A record is PRODUCTION only if it carries the campaign id and manifest hash of the campaign
    manifest given to the evaluator, the settings above (min_ess recorded; no accepted crossing with ESS < 0.2), d = 2, nn_extra = 0, and
    EVERY chain of the point (12 balanced hot/cold chains per (L, β), all DONE at exactly 10⁶ measurements and packed); the manifest itself
    must be the frozen design (D1–D4 constants incl. the D3 window rule and the frozen centres table `production_centers.csv`, all checked by
    the evaluator against constants, never read from the manifest); the provenance chain must verify
    (index hash, index→manifest hash, binary identity unique across chains, raw hashes present); the reblock records must pass the same
    checks and share the primary's per-chain raw hashes (same raw snapshot). Any failure, in the primary or a reblock record, labels the
    point NON-PRODUCTION with the reasons (an incomplete or extended-in-between campaign can never receive a production label). Equilibration
    (population rule, m² block means per (L, β) group of 12 chains, block standard errors): no chain with |pull| > 4, at most 2 % of chains
    with |pull| > 3, and no group in which half or more of the chains fail the drift (|z| ≤ 4), block/τ ≥ 20 or finiteness (non-finite or
    zero block error = degenerate) diagnostics; otherwise EQUILIBRATION FAILED (chains listed).
4.2 Per pair, b = 2000: MBAR over the 5 temperatures of each size, U4 crossing β× inside the shared bracket, Δ_eff^Q(L) = 2 − log₂(Q′_{2L}/Q′_L)
    for Q ∈ {U4, U6, U8, Y}; 500 joint bootstrap draws (every chain resampled once per draw, all sizes jointly) → covariance across pairs and
    observables; a draw is complete if every pair converged (≥ 90 % complete draws required).
4.3 Extrapolation: Δ_eff^Q(L) = Δ_ε + c_Q L^(−ω′) over the four pairs by GLS with the bootstrap covariance, ω′ profiled on [0.2, 2.0] step 0.01
    (a profiled parameter: dof = 4 − 3 = 1). Series: U4, U6, U8, Y separately, and the JOINT series J = {U4, Y} with common Δ_ε and ω′ and
    separate amplitudes (8 values, 4 parameters, dof 4). Eligible only if (i) χ²_min/dof ≤ 2, (ii) the Δχ² ≤ 1 interval of ω′ stays inside
    [0.22, 1.98] (resolved exponent), (iii) σ_∞ ≤ 5 × σ_stat of the largest pair of the same observable (U4 for J). σ_∞ = standard deviation
    of Δ_ε refitted on the complete draws at ω′*; Δ_ω′ = half-range of Δ_ε over the Δχ² ≤ 1 interval. Identical central sequences are deduplicated.
4.4 Quoted value: from the reference series (J if eligible, else U4, else the first eligible): Δ_ε = its Δ_ε, σ_stat = its σ_∞; σ_sys =
    half-range of Δ_ε over E plus the reference Δ_ω′ (defined only with |E| ≥ 2); ratio label when σ_sys > 3 × median σ_∞ over E.
4.5 Cross-check: paired difference Δ_ε^{U4} − Δ_ε^{Y} on the common complete draws; pass if |difference| ≤ 2σ_D.
4.6 Decision table, applied in order: 1 EQUILIBRATION FAILED; 2 COVERAGE-LIMITED (a pair missing, or ESS < 0.5 at one of the two largest
    pairs → the largest usable pairs' Δ_eff quoted); 3 MODEL-LIMITED, EXTRAPOLATION UNAVAILABLE (|E| = 0 → two largest pairs quoted);
    4 CONDITIONAL (|E| = 1 → Δ_ε ± σ_stat, no σ_sys); 5 REBLOCKING UNAVAILABLE (a b = 1000 or 4000 record missing); 6 REBLOCKING FAILED
    (σ_stat of the quoted quantity at b = 1000 or 4000 outside ±30 % of the primary); 7 CROSS-CHECK UNAVAILABLE (U4 or Y not in E);
    8 CROSS-CHECK FAILED; 9 ACCEPTED; 10 ACCEPTED (σ_sys-dominated). Rows 1–3 quote finite-size pairs only (no extrapolated value is
    printed). Every label carries the suffix "[σ_stat above target]" when σ_U4(512→1024) exceeds criterion 2 (0.003), or "[precision
    unknown]" when that pair is absent; a precision statement, not a validity statement; it triggers §5.4.
4.7 Expectations stated before the data: at s = 1.05 and 1.1 the leading correction exponent (ω ≈ 2s − 2 ≈ 0.1–0.2) lies below the
    resolvable range, and at s = 1.6, 1.7 the long-range perturbation is nearly marginal; MODEL-LIMITED or CONDITIONAL with the 512→1024
    Δ_eff as the deliverable is the expected outcome there (regime-A/C analogue of the 1D plan); the central points s = 1.2–1.5 are where
    ACCEPTED is plausible.
4.8 Blindness and provenance: everything above is fixed here. Chain: `pack_histograms.py` records per chain the raw `samples.bin` SHA-256
    and the binary identity, plus the manifest hash; `precision_analysis.py` records campaign id, manifest and index hashes, min_ess and
    its code hashes; the evaluator (given the campaign manifest) verifies the chain, records the SHA-256 of this document and of itself, and
    labels NON-PRODUCTION any record that fails §4.1; the analysis verifies each packed histogram's content hash against the index before
    use. Packed histograms, analysis records and evaluations are immutable (every tool claims a fresh output directory atomically with
    mkdir before computing, so neither sequential nor concurrent runs can overwrite a record). No rerun with changed settings replaces a published record.

## 5. Numerics plan and schedule (allocation ends 2026-09-30)
5.1 Stage 0 (done 2026-09-20): centres, ESS, τ, contention (§2); interrupt/resume verified on Lustre; no grid additions (D1).
5.1a Preflight (review item 3; jobs 54367736 array + 54367738 analysis): 8 points × L ∈ {512, 1024} × 5 production β × 2 replicas × 5×10⁴
    sweeps through the package's submit.py/array.slurm path (first use on Expanse): measures the L = 1024 rate under whole-node load,
    checks the 512→1024 crossing inside its ±1.9×10⁻⁴ bracket with ESS ≥ 0.5, and exercises the array/requeue path. Production is
    submitted only if the crossings sit inside their brackets and the measured rate keeps the L = 1024 chains inside the wall limit with
    ≥ 30 % margin; otherwise D3/§5.2 are amended here first. RESULT (2026-09-20 19:53 EDT): gate met — all eight 512→1024 crossings at
    0.41–0.59 of their brackets, ESS 0.75/0.64–0.67, no bootstrap failures, τ_int ≤ 29 sweeps at L = 1024; L = 1024 at 88 ms/sweep median
    (78–108) with 80 concurrent chains → 96 per node, `--time 46:00:00` (≥ 1.37× the slowest chain), checked continuation behind it.
5.2 Stage 1 production: ONE campaign `prod2d-20260921` (prepare.py, seed base 20260921): 8 points × 5 sizes × 5 β × 12 replicas = 2400
    chains, 2.4×10⁹ measured sweeps, 154 GB raw on Lustre. Work at Expanse rates × 1.1: L = 1024: 480 × 18 h = 8640 core-h; 512: 2100;
    256: 520; ≤ 128: 180 → ≈ 11 400 core-h ≈ 90 node-h. Packing (review item 2): slots grouped BY SIZE CLASS so that a node never idles
    behind a single long chain — array A: the 480 L = 1024 chains in 5 slots of 96 (96 workers; preflight: 88 ms/sweep median, 108 max, with 80 concurrent L = 1024
    chains → ≈ 26–33 h per chain; `--time 46:00:00`); array B: the 1920 chains with L ≤ 512 in 4 LPT-balanced slots of 480 (128 workers, work ≈ 5.5 h per slot + tail,
    `--time 12:00:00`). Both arrays read the same manifest through `run_pack.py --plan <slots.json> --slot $SLURM_ARRAY_TASK_ID` (plan
    files written by `LRI_2d_MC/make_plan.py`, campaign id checked by run_pack); 9 whole-node jobs, ≈ 170 node-h charged (the L = 1024 cache-contention penalty), at most 9
    of my 22 running-job slots. Each array is submitted twice; the second copy (`continue.slurm`, `--dependency=afterany` on the whole predecessor array —
    `aftercorr` would release a slot only after a SUCCESSFUL predecessor) checks its own predecessor slot with sacct and continues from the
    checkpoints only after TIMEOUT or a checkpointed stop (exit 75); after COMPLETED it exits at once; after any other end (hard chain
    failure) it exits 3 and the slot is diagnosed before a manual resubmission (§5.5). Launch plans are named
    by their parameters and immutable; the submission script refuses to run while jobs of the campaign are queued or a submission record exists. Submission 2026-09-21 after the preflight; completion expected ≤ 09-23; analysis (§4) as Slurm jobs
    (pack at b = 1000/2000/4000, one analysis per s and block, 500 draws) the same day; slack until 09-29.
5.3 Stage 2 (post-deadline, optional): L = 2048 at the points where |E| ≥ 2 but σ_sys > 3σ_stat, on symmetry longq / canonical.
5.4 Extension rule: a point whose 512→1024 pair misses criterion 2 (σ_U4 > 0.003) is extended by the factor (σ/0.003)² if the
    allocation allows: `make_plan.py --only-s <s> --tag ext1` writes per-point plans and `array.slurm` runs them with LRI_MEASUREMENTS set
    to the new total (the same chains continue from their checkpoints; never new temperatures). The new total is registered BEFORE the
    extension runs in `extensions.json` ({"<s>": total}), which the evaluator takes as the required per-chain measurement count for that
    point (all chains of the point, all block sizes, one raw snapshot); otherwise the point is reported with the suffix.
5.5 Runbook: monitor the arrays with `squeue` by job id (a failed query is UNKNOWN); a hard chain failure (exit ≠ 0, 75) stops that node —
    its other chains checkpoint — diagnose the chain's runner.log, then resubmit the slot; never cancel a running job; pack/analysis run
    as shared-partition jobs, never on the login node; copy `analysis_*` records and the evaluation to the Mac (`LRI_2d_MC/prod/`) and keep
    the raw chains on Lustre until the evaluation is published, then archive them off Expanse before 2026-09-30.
5.6 Not planned: temperature fits across sizes; observables beyond U4/U6/U8/Y; nn-extra tuning; grid points without a stage 0.

## 6. Assumptions and risks
A1 The stage-0 centres predict β×(512, 1024) to within w(1024) (a few 10⁻⁴); if not, stage 1 is preceded by a short recentering run at
   L = 1024 (one node-hour per point). A2 Contention: 1.0–1.1× at L ≤ 512 (job 54367299), but ≈ 1.5× for L = 1024 chains at 80 per node (preflight; 6 MB working set per
   chain exceeds the L3 share) — hence 96 L = 1024 chains per node and the 42 h limit with a pre-submitted continuation. A3 Corrections
   near s → 1.75 are logarithmic; those points (Δ_σ = 0.15, 0.2) may end MODEL-LIMITED — an allowed outcome. A4 Codex review is unavailable
   until 2026-09-26: this plan is reviewed by a fresh Claude session; the Codex inspection of the evaluator follows after the deadline and
   before any publication.
