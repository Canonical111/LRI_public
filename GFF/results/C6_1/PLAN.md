# PLAN (rev 8): C6(1) of the 1D long-range Ising model from exact all-graph sums at increasing quadrature degree

Repository: `<PROJECT>/LRI_C6_1D_HPC`. It is a local git repository; baseline `a4d1ec8`
is a verbatim copy of `lri_C6_numerical_update/reproduction` in `reference/`.
Host/builder: Claude. Plan reviewer and final inspector: Codex gpt-6-astra, effort xhigh.
Compute: symmetry, on Intel AVX-512 nodes. User request (2026-09-28): "do it, then run it on symmetry, make it as
precise as you can".
Rev 2 answered review round 1 (R01–R12). It also rests on a new measurement, recon4 (§2.2): the double engine loses
accuracy on the hard stratum as N grows. Rev 3 answers round 2 (R2-01 to R2-05): record provenance between rounding
and assembly, a weights manifest, the zero-proxy calibration policy, light diagnostics taken from the production
vectors, and a conditioning statement restricted to accessible weight rows. Rev 4 answers round 3 (R3-01 to R3-05),
which concern the scripts: build naming, fail-fast gates run strictly before production, per-job validation
records with a collector, a single validation entry point, and an explicit provisional mode. Rev 5 answers round 4
(R4-01 to R4-04):
- validation attempts are isolated, and approval is bound to the identities of the code and data;
- every production submission path checks that approval;
- production stays within a 12-node budget;
- batch submissions are checked.

Rev 6 answers round 5 (R5-01 to R5-03):
- validation attempts are serialized, with an attempt-ownership token;
- the queue check fails closed and runs under a submission lock;
- production-stage retries are idempotent.

Rev 7 answers round 6 (R6-01, R6-02):
- one strict merged-level validator is shared by the retry check, assembly and rounding;
- dependent jobs are cancelled when a dependency fails, so failures never strand the queue.

Rev 8 answers round 7 (R7-01): non-finite totals are rejected explicitly. Uncommitted drafts of the engine and tools are in the repository; they
are unreviewed, and this plan governs them.

## 1. Goal
The published value is C6(1) = 14331.8 ± 0.5, with estimator 14331.77075 and SE 0.143. It comes from
`reference/analyze_stratified.py`:
- an exact all-graph sum at quadrature degree N = 6;
- exact hard-stratum corrections up to N = 10;
- Monte Carlo differences for the light stratum: 50k draws for 8−6 and 3k draws for 10−8.

The MC terms carry all of the 0.143, and the estimate stops at N = 10.

This project replaces **every** stochastic term by exact sums over all 2,137,415 graphs and all 360 reversal
classes, at N = 6, 8, 10, …. It converges the lower-loop inputs to match. As a result, C6(1) is limited only by
quadrature convergence (geometric in N) and floating point, both measured. The target is the smallest defensible
uncertainty the data support, with every contribution stated.

## 2. Recon facts (measured on symmetry, Xeon Gold 6148, gcc 11.2, 40 threads)

### 2.1 Reproduction
- Job 564716:
  - The unmodified `reference/enumerate.cpp` reproduces the graph sets: 2,427,005 six-loop labelled graphs,
    2,137,415 with w_H ≠ 0, Σw_H = −5519062.5. Five loops: 59,145 / 49,605 / −133,200.
  - The unmodified `reference/full.cpp` at N = 6 reproduces the saved `full_H_L6_N6_0_10000.json`: poles −6…−3 to
    ≤ 1e-14 relative, the double pole to 2e-12. The simple pole agrees only to 4.0e-10 (maxgap) and 2.4e-10 (span)
    relative, i.e. 8.7e-6 and 8.9e-6 in C6.
  - Unmodified `full.cpp` at N = 8, the first exact level: C6 = 14331.81683 (maxgap) and 14331.69490 (span).
    The reference hybrid at N = 8 (saved N6 all-graph + saved hard 8−6 + MC light 8−6) gives 14331.91196 and
    14331.78568. The exact values differ by −0.095 and −0.091, which is −0.57 and −0.60 MC SE.
- Job 564722, summation. The original's discrepancy comes from its uncompensated sums:
  - Plain versus compensated (TwoSum) sums differ by 3e-4 in H6 at N6 (40 threads). Across plain reruns the
    difference depends on the thread count, which fixes the length of each summation chain.
  - The compensated sums with 20 and 40 threads agree to 1e-14 relative.
- Job 564724:
  - At N = 8, plain versus compensated sums differ by 8e-3 in H6, i.e. 2.2e-5 in C6.
  - Compensating the per-group moment accumulation as well changes H6 by 1.1e-7 (N6) and 1.7e-5 (N8), i.e.
    ≤ 5e-8 in C6.

### 2.2 recon4 (jobs 564739 and 564740): the draft engine `src/c6sum.cpp`, double and long-double builds
- The draft double engine at N = 6 (all) equals the recon compensated `full.cpp` run to ≤ 1e-16 relative on every
  entry.
- Weights:
  - `tools/weights.py` (100 digits) equals `reference/prepare.py` (80 digits) bitwise at N = 6, 8, 10, 12, except
    for 9 entries per N.
  - Those 9 are mathematically zero weights, which the formulas return as ~10^-dps residuals (1e-80 versus
    1e-100). `tools/weights.py` now stores them as exact 0.
- **The hard stratum loses accuracy in double as N grows; the light stratum does not.** This is measured directly
  (table below), with long double as the reference.
  - Accessible weight rows (R2-05, job 564834; rows listed in `LRI_C6_1D_HPC_loop/artifacts/accessible_rows.json`):
    the 2,137,415 graphs × 360 sectors use 682 distinct bucket vectors in the hard stratum and 1183 in the light
    stratum. They touch 36 and 35 (axis, b) rows respectively.
  - Over accessible rows, max|w| grows only about like N²:
    - hard: 3.5e6 at N6, 1.3e7 at N12, 2.3e7 at N16, 3.6e7 at N20, 1.1e8 at N30;
    - light: 1.2e5, 2.7e5, 4.1e5, 5.7e5, 1.0e6.
  - The much larger values in the allocated table (up to 8e15 at N30) sit in rows that no graph reaches, e.g.
    axis 4 with b ≥ 4, since b_4 ≤ 3. The rev-2 statement citing them was wrong.
  - The growth of the double error in the hard stratum therefore comes from cancellation inside that stratum,
    which has ≥ 2 pole axes or power axes; it is not explained by weight magnitudes alone. The measured
    discrepancies are the evidence. The C6 effect is below.

  | N | hard: long double − double | hard: ±1-ulp perturbation (double) | light: perturbation (double) |
  |---|---|---|---|
  | 6 | 5.2e-9 / 6.3e-9 | 1.0e-8 / 9.3e-9 | 5.3e-10 / 5.6e-10 |
  | 8 | 7.6e-8 / 7.4e-8 | 6.9e-8 / 7.4e-8 | 1.1e-10 / 9.0e-11 |
  | 10 | 1.5e-7 / 1.5e-7 | 3.6e-7 / 3.5e-7 | — |
  | 12 | — | 4.8e-7 / 4.6e-7 | — |

  (Each cell gives maxgap / span.) At N = 6, long double minus double for the light stratum is 4.1e-10. The
  perturbation proxy tracks the true error to within a factor of 0.4–1.1.
- **Cost.** Double: N6 all 186 s, N8 all 456 s; hard N6 62 s, N8 101 s, N10 189 s, N12 367 s. Long double: hard N6
  152 s, N8 421 s, N10 1076 s; all N6 959 s. The long-double hard stratum costs about 5.7× its double version. The
  hard stratum is about 13% of the double work at N12.

### 2.3 Projected cost (per 40-core node)
The mixed-precision design below costs about 1.6× the all-double cost:
- N12 1.3 h, N14 2.6 h, N16 5 h, N18 8.6 h, N20 14 h, N22 22 h, N24 34 h, N26 50 h, N28 70 h, N30 100 h (node-hours;
  work is split over nodes by sector ranges);
- the sum through N24 is about 90 node-hours, and through N30 about 310.

The L5 inputs are cheap: (N+1)^4 points × 60 sectors, M40 in long double ≲ 1.5 h per mode.

## 3. Definitions (unchanged from the reference)
For cutoff χ ∈ {maxgap, span}:
`C6^χ = R6^χ + (4/243) J5^χ − (2/729) H6^χ`,
- H6^χ = [ε^-1](3B6 − A6), entry 5 (maxgap) and entry 11 (span) of the L6 H-mode vector of 2L = 12 entries;
- J5^χ = [ε^0](8B5 − 3A5), entries 5 and 11 of the L5 J-mode vector of 2(L+1) = 12 entries. The L5 H-mode vector
  has 2L = 10 entries.
- R6^χ is the Laurent-MS recursion of `reference/assemble6.py` from the lower amplitudes and the five-loop poles
  A5 = 8H5 − 3J5 and B5 = 3H5 − J5.

The two cutoffs converge to the same C6 as N → ∞. Their difference at finite N is an actual error of at least one
of them. The higher H6 poles ε^-6…ε^-2 are fixed exactly by RG (`reference/pole_checks.py` logic). Their errors
are exact-mean convergence diagnostics at every N.

**Strata.** For each (graph, sector), the bucket vector gives a_j = L−2−j−b_j/2:
- hard = (≥ 2 pole axes, i.e. a_j ≤ −1 integral) or (some a_j < −1): the `reference/full_hard.cpp` filter;
- light = the complement.
Every (graph, sector) term is in exactly one stratum.

## 4. Approach

### 4.1 Engine `src/c6sum.cpp`, derived from `reference/full.cpp`
Same mathematics, graph file, weight layout, sector enumeration, group / left–right factorization and Laurent
recursion. **Two builds, both production:**
- `bin/c6sum`: AVX-512 double, 8 points per block. Used for the **light** stratum and for diagnostics.
- `bin/c6sum_ld` (`-DC6_REFERENCE`): scalar x87 long double (64-bit mantissa), 1 point per block. Node data come
  from `cosl/sqrtl/logl`, and weights from the double-double file (§4.2). Used for the **hard** stratum and for all
  L5 production.

Changes relative to the reference:
1. **Compensated, order-fixed accumulation.**
   - Within each block, the group contributions (maxgap and span orders) are accumulated with TwoSum per lane.
   - The lanes plus compensation terms are reduced in long double and stored per block.
   - Blocks are summed in index order with a long-double TwoSum.
   - Active groups are processed in ascending immutable bucket-key order (R05), not first-seen order.
   Each sector value is therefore a deterministic function of (sector, inputs, build): bitwise independent of the
   thread count, the scheduling, the sector splitting and resumption. Per-group moments stay uncompensated by
   default; `--comp 2` compensates them as a check.
2. **No weight cache.** The Laurent weight tensor and km are recomputed per (group, block), from per-axis weights
   gathered once per (axis, r), with the reference's (k, r) order and explicit FMA. Memory is O(points). At N6
   the result equals the cached computation to 1e-16 relative (§2.2).
3. **Strata** `--stratum all|hard|light`, with hard and light as in §3.
4. **Sector ranges, subset and resume.** `c6sum L N threads root mode --out FILE [--first a] [--stop b] [--mod K]
   [--stratum S] [--comp 1|2] [--perturb SEED]`.
   - `--mod K` processes only the sectors with s ≡ 0 (mod K) in [a, b).
   - **Header = numerical fingerprint only (R11):** engine kind, git revision (from `GIT_SHA`, written at sync),
     SHA256 of the source file (embedded at build), SHA256 of the executable, of the graph file and of the weights
     file, L, N, mode, stratum, comp, perturb, first, stop, mod, sectors_total.
   - Each start or restart appends an **attempt record**: host, CPU model, threads, compiler version, start time,
     sectors already done.
   - Resume requires an identical fingerprint. It skips completed sectors and drops a torn last line. A mismatch
     is a hard error.
   - One JSONL line per completed sector: its 2·(L+[mode=J]) values (long double, 21 significant digits), active
     groups and seconds.
5. **Input validation (R07).** The graph file must have exactly the expected size: 2,427,005 (L6) or 59,145 (L5)
   records of NE+2 ints. The read must be complete. Every record must have multiplicities in 0…3, total 2L, and
   vertex degrees in 2…4. Otherwise the engine exits nonzero. The weights file must have exactly the expected
   size.
6. **Perturbation (R12).** `--perturb SEED` moves every nonzero node datum, per-axis weight and tensor weight by
   exactly one ulp of its type, up or down with equal probability (hash of the seed and the element's immutable
   key). Zeros stay zero, since they are structural. It is only for the rounding estimates (§4.5).

The double kernel uses AVX-512 intrinsics, so production runs on symmetry's Intel nodes (defq first, then preq with
requeue and resume; longq only if strictly necessary). The AMD nodes are AVX2-only and are not used; this is a
stated deviation from the usual amdq-first routing.

### 4.2 Weights `tools/weights.py`
- Same formulas as `reference/prepare.py`, at 100 digits. It writes `w_{L}_{N}.bin` (float64) and
  `w_{L}_{N}.dd.bin` (hi, lo). Mathematically zero entries (|v| < 10^-50) are stored as 0.
- **Weights manifest (R2-02).** `data/weights_manifest.json` maps each (L, N) to the SHA256 of its float64 and
  double-double files and the digits used.
  - Assembly and rounding require every level's `weights_sha256` to equal the manifest hash for its (L, N) and
    precision: float64 for double levels, double-double for long-double levels.
  - L5 H and J at the same M therefore use the same weights, as do production and replicate records at the same
    degree.
- **Reproduction check:** at every N used, the float64 file equals the unmodified `reference/prepare.py` output
  bitwise, except at entries where the reference value is below 1e-60 in magnitude, which must be 0.
- **Self-checks (R08).** For random polynomial smooth factors p of degree ≤ N and every (axis, b2, r), with
  S = Σ_i |w_i p(t_i)|:
  - the double-double weights reproduce the exact Laurent coefficients of ∫ t^{a+εb2/2} p dt with forward error
    ≤ 1e-12 · max(|exact|, 1e-20·S);
  - the float64 weights do so within 1e-15 · S.
  Both worst values are reported. Measured at N = 6…12: ≤ 7e-25 and ≤ 9e-17.

### 4.3 Levels
- **L6, every production degree N:**
  - light stratum, all sectors, double;
  - hard stratum, all sectors, long double;
  - H6(N) = light + hard.
  N = 6, 8, 10, 12, 14, 16 are unconditional; then N = 18, 20, … up to N_cap = 30 under the stopping rule (§4.5).
- **L6 rounding replicates, every production N:** light, double, `--perturb 1 --mod 10`; and hard, long double,
  `--perturb 1 --mod 10`.
- **L6 calibration runs** at N = 6, 8, 10: hard stratum in double, all sectors, unperturbed and `--perturb 1`.
  Together with the production long-double hard runs, these measure the true double error against the
  perturbation proxy.
- **L6 diagnostic runs:**
  - all-sector double at N = 6 and 8, for the partition check and the reproduction gates;
  - hard stratum in double at N = 6, 8, 10, for reproduction against the saved hard files.
- **L5 production:** H and J, all sectors, long double, M = 12, 16, …, 40. Plus H and J at M = 40 with
  `--perturb 1` (all sectors; R04).
- **L5 diagnostics:** H and J in double at M = 12 and 16, for reproduction against the saved files, and at M = 40
  (long double minus double is reported).
- **Lower amplitudes (L2–L4):** the saved `reference/lower6_{χ}_28.json`, unchanged. The 22 → 28 change is
  1.5e-9 and 4e-10 in C6.

### 4.4 Merge and assembly
- `tools/merge.py` merges one (L, N, mode, stratum, kind, perturb, mod) set of JSONL files. Invariants:
  - every input starts with a fingerprint header, and all headers agree apart from first and stop;
  - each file has at least one attempt record;
  - the expected sectors are derived from L (L!/2: 360 or 60, R06), or the fixed mod-10 subset for mod 10, each
    exactly once;
  - the vector width is derived from L and mode: 2L for H, 2(L+1) for J;
  - all values are finite;
  - values are summed in mpmath at 50 digits in sector order.
  The output records the per-sector values, totals, headers, attempts and input SHA256s.
- **Level file names (R01, R02).** Levels are named `L{L}_{mode}_{stratum}_N{N}.{kind}[.pert][.mod10].json`, with
  kind `dbl` or `ld`.
  - `tools/assemble.py` loads only exact full-name matches. It checks that header L, N, mode, stratum, kind,
    perturb, comp and mod match the name and the production settings.
  - All production L6 light levels must share one double-engine fingerprint (source, executable, graphs). All L6
    hard and L5 production levels must share one long-double-engine fingerprint.
  - The H and J degree sets of each L5 group must be equal.
  - Every level's weights hash must match the manifest (§4.2).
- **Record identities (R2-01).** Assembly and rounding each record the SHA256 of every level file they read, and
  of the manifest. The analysis refuses a headline or stopping decision unless:
  - for every production degree, the two reports name the same L6 light and hard records (identical file hashes);
  - the two reports used the same manifest.
  The final report keeps these identities.
- **Assembly.**
  - H6(N) = light(N) + hard(N), per entry. For every N, both strata must be present.
  - R6^χ uses `reference/assemble6.py`'s `assemble()` with the saved lower amplitudes and the five-loop poles of
    the chosen L5 degree M. Configurations: `L5_M{M}`, the `L5pert_M40` replicate, and `retained_poles_J16ref`
    for comparison with the reference.
  - The RG higher-pole predictions and errors are computed for the same inputs.

### 4.5 Pre-registered estimator, uncertainty and stopping rule
This section is fixed before any N ≥ 10 all-graph production result exists. N = 6 and 8 are known from recon; the
production pipeline recomputes them.

Notation:
- Δ^χ(N) = C6^χ(N) − C6^χ(N−2);
- N* is the highest completed production L6 degree;
- M* = 40.

**Rounding estimate ρ(N), in C6 units:**
- Subset statistic for a perturbed-minus-unperturbed mod-10 subset, with e_s the per-sector C6 contribution
  difference: σ_S = max(10·|Σ_S e_s|, √(10·Σ_S e_s²)).
- ρ_light(N) = σ_S of the light double replicate; ρ_hard(N) = σ_S of the hard long-double replicate.
- Calibration: cal = max(1, max over N ∈ {6, 8, 10} of |Σ (hard_ld − hard_dbl)| / |Σ (hard_dbl,pert − hard_dbl)|),
  with both sums over all sectors. This is the true error in double relative to the perturbation proxy in double
  (§2.2: 0.4–1.1).
  - Zero-proxy policy (R2-04): a ratio with proxy = 0 counts as 0 if the true difference is also 0. If the true
    difference is positive, the calibration is invalid.
  - Invalid or missing calibration, or a non-finite cal or ρ, means no ρ, no stopping decision and no headline.
- Pair checks (R2-02) apply to every production/replicate pair and every calibration pair:
  - same L, N, mode, stratum, graphs and source;
  - for same-precision pairs, also the same executable, weights hash and comp;
  - replicates must have perturb = 1 exactly and mod = 10 (subset mod10);
  - calibration replicates must have perturb = 1 and mod = 1;
  - production records must be unperturbed and complete.
- ρ(N) = cal · (ρ_light(N) + ρ_hard(N)) + 1e-12.

**Stopping rule.** After completing N ≥ 16, run N+2 unless one of the following holds:
- (a) max_χ|Δ^χ(N)| ≤ 2ρ(N) and |C6^max(N) − C6^span(N)| ≤ 2ρ(N);
- (b) N = 30;
- (c) cumulative production exceeds 400 node-hours;
- (d) the projected N+2 wall time exceeds 36 h on 12 nodes.
The reason for stopping is recorded.

**Headline.** C6 = ½[C6^max(N*) + C6^span(N*)], with
`U = ceil_2sf( 2·f·max_χ|Δ^χ(N*)| + |C6^max(N*) − C6^span(N*)| + 4ρ(N*) + U5 + U5round + Ulow )`, where:
- f = 1 if, for both χ, |Δ^χ(N*)| ≤ ½|Δ^χ(N*−2)| or |Δ^χ(N*)| ≤ 2ρ(N*). Otherwise f = 4.
- U5 = 2·max_χ|C6^χ(N*; L5_M40) − C6^χ(N*; L5_M36)|.
- U5round = 4·cal·max_χ|C6^χ(N*; L5pert_M40) − C6^χ(N*; L5_M40)| (R04). The replicate covers all 60 sectors.
- Ulow = 2·max_χ|R6 change, lower degree 28 vs 22| = 3.1e-9.
- ceil_2sf rounds up to two significant figures. The headline is quoted to the decimal place of U's second
  significant figure.

U is an empirical convergence-and-rounding allowance, not a rigorous bound.

**Refusal rule (R03).** `tools/analyze.py` produces no headline or stopping decision unless all of these exist:
- every L6 degree 6, 8, …, N* with N* ≥ 16, each with light, hard and both mod-10 replicates;
- the calibration runs at N = 6, 8, 10;
- the L5 configurations for M = 12…40, including the M40 replicate.
With `--provisional` it reports the table without an allowance.

**Diagnostics** (reported, never in the headline):
- Aitken Δ² and geometric-tail extrapolations per χ;
- higher-pole errors versus RG at every N;
- the double − long double hard-stratum differences at N ≤ 12, and the L5 double − long double differences at
  M = 40;
- exact light-stratum level differences versus the reference MC, computed from the production light vectors of
  the assembly (R2-03), never from separately globbed files:
  - 8−6 and 10−8, against the saved level statistics;
  - 12−10 (R09), against the light-masked statistic recomputed from the saved samples
    (`samples_H_L6_N{12,10}_s135799`, first 1000 rows, with the `features_s135799_M3000` light mask), with a
    z-score;
  - the all-graph 12−10 against the unmasked statistic, with a z-score. Those samples overlap the reference's
    10−8 level; this is noted.
- the old C6 (14331.77075, SE 0.14344) versus the headline, z using the old SE;
- the retained five-loop pole assembly versus the new L5 inputs;
- the C7-package by-product value 14331.62 ± 0.31, from an independent method.

### 4.6 Validation gates (symmetry; all pass before any production beyond the gate runs)
**Protocol (R3-02 to R3-04, R4-01, R5-01).** `bash cluster/validate_all.sh`:
- takes the `validation` lock, an atomic `mkdir` of `$C6_HOME/.validation.lock`, released on exit;
- refuses if any validation job is queued or running, or if `squeue` fails, so attempts never overlap;
- creates a collision-resistant attempt directory `validation/attempts/<timestamp>_<git>_<random>/`;
- deletes `validation/APPROVED.json`, withdrawing any previous approval;
- atomically writes the attempt name to `validation/CURRENT_ATTEMPT`.

It then submits the following chain:
- `prepare.slurm`, for V1 and V2;
- three gate jobs, `validate.slurm` with PART = dbl, ld and l5, after `prepare` succeeds (`afterok`);
- a collector, `tools/validate.py collect`, which writes `validation/summary.json`. It passes only if every required
  gate record exists and passed.

- Each job writes only its own record file in the attempt directory (`{prepare,dbl,ld,l5}.json`, replaced
  atomically) and stops at its first failed gate (nonzero exit).
- `prepare` ends by writing `identities.json`: SHA256 of `src/c6sum.cpp`, `bin/c6sum`, `bin/c6sum_ld`,
  `graphs6.bin`, `graphs7.bin` and `weights_manifest.json`, plus the code directory. Each gate job refuses to start
  if the current identities differ.
- The collector reads only this attempt's records. It writes `validation/APPROVED.json`
  (`{pass, attempt, identities}`) only if every required gate passed, the identities are still unchanged, and
  `CURRENT_ATTEMPT` still names this attempt. A cancelled or failed branch leaves its gates missing, so no approval
  is written. A superseded collector cannot publish.
- All gate levels and runs are written inside the attempt directory (`levels/`, `runs/`). They are never read by
  production, and production levels are never reused as gate evidence.

The gate jobs compute only what the gates need:
- L6 all-sector double at N = 6 and 8;
- hard stratum in double at N = 6, 8, 10;
- light stratum in double at N = 6 and 8;
- hard stratum in long double at N = 6 and 8, and all sectors in long double at N = 6;
- L5 H and J at M = 12 and 16 in both precisions.
**Production (R4-02 to R4-04).** Every production submission goes through `cluster/production.sh` or
`cluster/submit_level.sh`. Both call `c6_require_approval`, which requires `APPROVED.json` with pass = true and
identities equal to the current ones, and both refuse otherwise.
- Production recomputes every level it uses, including N = 6 and 8, into `levels/`.
- `production.sh A` submits:
  - L6 light and hard arrays at N = 10, 12, 14 and 16 (10 nodes at most);
  - one batch node for N = 6 and 8 production, the calibration runs (hard double at N = 6, 8, 10, plain and
    `--perturb 1`) and the replicates for N = 6…16;
  - one batch node for L5 long double at M = 12…40, the M40 replicate and the double M40 diagnostic.
  That is at most 12 nodes.
- `production.sh N=<n>`, for n = 18…30 under the stopping rule, submits both strata as arrays, each throttled to 5
  concurrent tasks, plus one replicate batch node: at most 11 nodes.
- `production.sh` takes the `production` lock. It refuses while any c6 production job is queued or running, and
  also when `squeue` fails, since an unknown queue state is treated as busy (R5-02). Stages therefore never
  overlap.
- **Merged-level validation (R6-01).** `tools/levelio.validate_level` is used by the retry check
  (`levelcheck.py`), by `assemble.py` and by `rounding.py`. A record is accepted only if:
  - its file name equals the canonical name derived from its own header and subset;
  - it has exactly the required sectors (all L!/2, or the mod-10 subset with header mod 10), and matching
    per_sector keys;
  - every vector has width 2·(L+[mode=J]), and every value is a finite number. Totals are included: NaN, inf and
    non-numeric entries are rejected explicitly, before the consistency comparison (R7-01);
  - its totals equal the 50-digit sum of the per-sector values (relative 1e-30).
  A record copied from another degree, or a truncated replicate, is therefore rejected everywhere.
- **Failed dependencies (R6-02).** Every `afterok` dependency carries `--kill-on-invalid-dep=yes`: level merges
  after arrays, and the gate branches after `prepare`. A failed task cancels its dependents instead of leaving
  them pending. The validation collector uses `afterany`, so it still runs, finds the missing gates and publishes
  nothing, after which a fresh attempt is allowed.
- **Idempotent retries (R5-03).** `submit_level.sh`, `production.sh` and `batch.slurm` classify every level with
  `tools/levelcheck.py`:
  - present and matching the approved identities (source, executable of its precision, graph file, weights hash
    from the manifest): skipped;
  - absent: submitted, with partial engine outputs resumed;
  - present but mismatched or corrupt: the script stops.
  Rerunning the same stage command therefore completes exactly the missing work. A batch whose levels are all
  complete is not submitted.
- Job IDs from `sbatch` are captured in checked assignments under `set -euo pipefail` before they are logged. A
  rejected submission stops the script.

Gates:
- V1. **Graphs.** Enumeration counts and sums as in §2.1; graph-file SHA256 recorded. The engine refuses a copy of
  the graph file truncated by 4 bytes and by one full record.
- V2. **Weights.** The reproduction and self-checks of §4.2 hold for L6 at N = 6…30 and L5 at M = 12…40.
- V3. **Double engine at N = 6, all sectors:**
  - versus the saved reference vector: poles −6…−3 ≤ 1e-12 relative; double and simple poles ≤ 1e-9 relative
    (the original's measured summation bias);
  - versus the recon compensated `full.cpp` run: ≤ 1e-12 relative on every entry.
- V4. **Reproduction of saved files:**
  - hard stratum (double) at N = 6, 8, 10 versus the saved `full_H_hard*_L6_N{6,8,10}`, and L5 in double (H and J
    at M = 16, J at M = 12) versus the saved files: ≤ 1e-9 relative on every entry, ≤ 1e-12 for poles −6…−3 and
    −5…−3;
  - the long-double engine versus the saved hard files at N = 6 and 8, and the saved L5 files, to the same
    tolerances.
- V5. **Determinism, bitwise equality of sector values:**
  - light, double, N = 8: 20 versus 40 threads; ranges [0,97) + [97,211) + [211,360) versus [0,360);
  - hard, long double, N = 6: the same split, and 20 versus 40 threads.
- V6. **Resume, bitwise.**
  - A double light N = 8 run on [100, 200), killed by `timeout` after its first sectors, is restarted and completed.
    Its sectors equal those of the uninterrupted split run.
  - A restart with a different `--comp` is refused.
- V7. **Merge, assembly, rounding and analysis guards** (local tests, with synthetic and reference data):
  - merge: duplicates, gaps, mixed fingerprints, wrong sectors_total or width, missing attempt records, torn files;
  - assembly: auxiliary files ignored, mislabelled degrees refused, mixed executables or sources refused, weights
    missing from the manifest refused, unpaired L5 refused;
  - rounding: wrong replicate seed refused, zero-proxy calibration invalidated;
  - analysis: refusal without mandatory inputs, and refusal when rounding and assembly name different records.
- V8. **Partition:** light + hard = all (double, N = 6 and 8), ≤ 1e-12 relative on every entry.
- V9. `--comp 2` at N = 8 (light, double): |ΔC6| is reported.
- V10. **Long double versus double at N = 6, all sectors:** the difference is reported; the expectation from §2.2
  is ≲ 1e-8 in C6.

## 5. Non-goals
- No change to the graph enumeration, the weight formulas, the Laurent-MS assembly or the lower (L2–L4) amplitudes.
- No Monte Carlo and no control variates.
- No extrapolation in the headline.
- `reference/` stays byte-identical.
- No attempt at a rigorous interval enclosure.
- No quad-precision (`__float128`) engine. The long-double error is measured through the calibrated perturbation
  proxy, not against a higher-precision truth.

## 6. Risks
- **Slow convergence.** The degree convergence may be slower than geometric at large N. Then f = 4 applies, and the
  run continues to N_cap.
- **Proxy calibration.** The long-double rounding estimate relies on the perturbation proxy, calibrated in double
  (factor cal). If the long-double hard error exceeded its proxy by far more than the double calibration shows,
  U would underestimate it. As a low-degree heuristic only, not a bound at high N: the double hard error at N ≤ 12
  (≤ 5e-7) scaled by the precision ratio 2^-11 is about 2e-10. At high N the measured long-double replicates
  (ρ_hard) carry the estimate.
- **Scheduling.** symmetry is shared. Target ≤ 12 concurrent nodes. preq tasks use `--requeue` with resume.
- **Timings.** Projected wall times may be off. The stopping-rule resource guards (c) and (d) apply as written.

## 7. Toolchain
- symmetry: `module load gcc/11.2.0 anaconda3/2023.07-2` (Python 3.11.4, numpy 1.24.3, mpmath 1.3.0).
  - `make` on an Intel compute node builds `bin/c6sum`, `bin/c6sum_ld` and `bin/enumerate` with `-O3 -std=c++17
    -march=native -fopenmp`, `-DC6_GIT_SHA` and `-DC6_SRC_SHA`.
  - Code: `<SCRATCH>/lri_c6_1d/code/<revision>`, a frozen copy of a committed revision, with `GIT_SHA`.
  - Data: `<SCRATCH>/lri_c6_1d/{data,runs,levels,logs}`.
- Local Mac: `~/anaconda3/bin/python tests/test_tools.py` (merge, assembly and analysis tests; the engine needs
  AVX-512 and Linux).

## 8. Verification (proof commands)
- Local: `~/anaconda3/bin/python tests/test_tools.py`. All pass, including the reproduction of the reference
  `C6_baseline_N6` = [14334.549123637884, 14332.554493138334] and of the reference `five_loop_input_control.json`
  changes (3.5463949903e-6 and 2.6921091360e-6) from the saved files.
- symmetry: `bash cluster/validate_all.sh` runs V1–V6 and V8–V10 as in §4.6. `validation/summary.json` must
  report pass, with every required gate present and passed. V9 and V10 are informational records, which must be
  present.
- Production: `bash cluster/production.sh A`, then `bash cluster/production.sh N=18` and higher, as the stopping
  rule directs. `cluster/submit_level.sh` is the shared array submitter; it also requires the approval.
- Analysis:
  - `tools/assemble.py LEVELS data/weights_manifest.json assembled.json`;
  - `tools/rounding.py LEVELS data/weights_manifest.json rounding.json`;
  - `tools/analyze.py assembled.json rounding.json C6_final.json`.
  The result is `results/C6_final.json` plus `results/REPORT.md`.

## 9. Build-phase amendments (after plan approval; covered by inspection round 2)
- **V2 residual threshold (validation attempt 20260929T100920).** `reference/prepare.py` at 80 digits leaves residuals
  of 3e-59 (M36) and 1e-55 (M40) where a weight is mathematically zero. Those exceed the rev-8 criterion (1e-60).
  The criterion is now: every entry whose reference value is below 1e-40 in magnitude must be exactly 0 in the new
  file. The smallest genuine weight across all files is 3.2e-15, so the two classes are 25 orders of magnitude
  apart. Every other entry must still agree bitwise.
- **Inspection round 1 (REV-001 to REV-005):**
  - REV-001, REV-002: one campaign lock (`$C6_HOME/.campaign.lock`) serializes validation, stage submission and
    standalone `submit_level.sh`. Validation requires an idle campaign, and production requires no active
    validation. Every queued task re-checks the approval when it starts. The engine hashes the graph and weights
    bytes it actually read.
  - REV-003: merges are validated as temporary files and published atomically and write-once (hard link, falling
    back to rename).
  - REV-004: the final report keeps the assembly's complete level identities (L6 and L5), the manifest hash, and
    the hashes of the assembled and rounding reports.
  - REV-005: `analyze.py --resources` (from `c6_resources N*`, based on sacct) evaluates stopping rules (c) and (d).
    Without it the decision is "unresolved", never "continue". `--decision-dir` writes
    `decisions/decision_N{N*}.json`, bound to the N* level hashes. `production.sh N=n` requires a matching
    "continue" decision at n−2.
- **Inspection round 2 (REV2-001 to REV2-003):**
  - REV2-001: a shared continuation guard, `c6_require_continuation N`, is applied by `submit_level.sh`,
    `batch.slurm` and `production.sh` to every L6 degree above 16, replicates included. It requires
    `decisions/decision_N{N−2}.json` with "continue", `next_degree` N, and matching level hashes.
  - REV2-002: `c6_resources` reports `coverage_complete`: both N* arrays have accounting rows and all of them are
    COMPLETED. analyze.py requires finite, non-negative values, a matching N* and complete coverage; otherwise the
    decision is "unresolved".
  - REV2-003: reports and levels are read once, and their hashes come from the parsed bytes. `assemble.py` and
    `rounding.py` publish atomically.
- **V4 tolerance (validation attempt 20260929T101755).** The saved original five-loop J16 record differs from our
  engines in its ε⁰ entry by 2.3e-9 relative (8.8e-6 in C6). Our double and long double agree with each other to
  2.6e-11, so the saved record carries its own uncompensated-summation error, the same size as the 8.7e-6 found for
  the saved L6 N6 H vector in §2.1.
  - The V4 tolerance against saved originals is now 1e-8 relative; poles −6…−3 and −5…−3 stay at 1e-12, and V3
    stays at 1e-9.
  - New gates V4b require our double and long-double engines to agree to 1e-9 relative on every entry (L6 hard
    N6 and N8; L5 H and J at M12 and M16).
- **Portable builds and amdq-first routing (user, 2026-09-29: "when submitting jobs on symmetry, plz prioritize
  amdq").** This supersedes the Intel-only statement in §4.1.
  - `bin/c6sum` is now 8-lane double as two AVX2 halves, built with `-march=x86-64-v3`; the AVX-512 variant stays
    available as `-DC6_AVX512`. Every lane executes the same IEEE operations. On an AMD EPYC 7532 it reproduced
    the Intel AVX-512 results bitwise: L5 J16, 60/60 sectors; light N6, 360/360 sectors (job 565570).
  - `bin/c6sum_ld` is also built for x86-64-v3. The kind name is `double8`.
  - Production submits to amdq alone when it has enough idle nodes, otherwise to `amdq,defq`.
  - Validation: prepare runs on amddebugq,debugq and the gate jobs on amdq. A cross-architecture job on defq,
    which is Intel, runs after them.
  - New gates V11 require bitwise-identical sector values between the AMD and Intel runs of the same executables
    (light double N8, hard long double N6, L5 J16 long double), and V11_xarch_cpus_differ checks that the CPU
    models really differ.
- **Long double across CPU vendors (validation attempt 20260929T114137).** The same `bin/c6sum_ld` executable gives
  results that differ between Intel Xeon 6148 and AMD EPYC 7543 by at most 1.0e-16 relative per entry, i.e. at most
  5e-15 in C6. The cause is that glibc's `logl`/`cosl` use x87 transcendental instructions, whose last bits are
  vendor microcode.
  - The double engine stays bitwise identical across vendors.
  - V11 for the long double is now a tolerance gate: per-entry relative agreement ≤ 1e-14. Bitwise determinism of
    the long double (V5, V6) holds per CPU model.
  - The effect is ten orders of magnitude below every allowance term, so production may place long-double tasks
    on either node type (amdq first).
