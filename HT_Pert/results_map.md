# Where each HT_Pert number comes from

Every quoted number: the record that holds it, the command that recomputes it, and the comparison tolerance.

Assembled from the package authors' texts. Inside a package section, relative paths are relative to that package's folder `code/<package>/` unless they start with `HT_Pert/`. The values themselves are in `note/README.md` and the note.

- d = 1: exact C2..C5(Lambda) sums: `lri_1d_c4_exact`, `lri_1d_c5_exact`
- d = 1: thermal HT coefficients C2..C7 and the effective Hamiltonian: `lri_hpc_Hamitonian`, `lri_eh_hpc`
- d = 1: HT C8 and the complete-window coefficient flow: `lri_c8_hpc`, `lri_d1_full_coefficient_flow`, `lri_1d_dconn_refit`, `lri_d1_fullblock_tail_response`
- d = 2: coefficients C2..C8 and the independent check: `lri_d2_coeff_hpc`, `lri_2d_coeff_independent_check`
- d = 3: exact C2..C5(L) sums and the coefficients C2..C8: `lri_3d_c4_exact`, `lri_3d_hpc`

## d = 1: exact C2..C5(Lambda) sums

### `lri_1d_c4_exact`

Folder: `code/lri_1d_c4_exact/`.

#### results_map: lri_1d_c4_exact (d = 1, exact C2..C4(Λ))

Paths relative to `HT_Pert/`. Command R = `make -C code/lri_1d_c4_exact -f public.mk replay` (`public/replay_c4.py`,
row id in the first column; `replay-quick` reads the C2/C3 record instead of refitting and skips x4.refit). Records:
E = `data/HT_1d/exact_c4/a8b57b2e8475/` (c4_1d_L{200,400,1000,2000}.npz, gates_L*.txt), F = `code/lri_1d_c4_exact/fits/`.
Expected values: `quoted_lri_1d_c4_exact.json` (merged into `results/HT_1d/quoted_numbers.json`).

| check id | quoted (macro) | value | records | command | tolerance / rule |
|---|---|---|---|---|---|
| x4.records | — | gate records bind the four results; A6d chain | E | R | exact (sha256) |
| x4.code | — | 38 production files equal the result's snapshot manifest | E, code | R | exact (sha256; SCRUBBED.txt honoured) |
| x4.frozen | — | frozen records match their .sha256 | F/frozen | R | exact |
| x4.values | \NOneCfourThousand, \NOneCfourTwoThousand | 37.8351012026, 39.4111422825 | E (L2000) | R | 10 decimals |
| x4.overlap | \NOneCfourOverlap | 3.3e-13 (≤ 1e-12) | E (L1000, L2000) | R | bound |
| x4.blind | \NOneCfourBlind | 4.0e-10 (L2, lo 200) | F/frozen, E (L2000) | R (reruns fits_c4_1d.py check) | equal to fits/blind_check_L1000_to_2000.txt |
| x4.intercept | \NOneCfourFrozen | 45.4249416926 | F/frozen | R (fits_c4_1d.py compare) | 10 decimals |
| x4.refit | \NOneCfourRefit | 45.4249235266 (lo 200) | E (L2000) | R (fits_c4_1d.py explore) | 1e-9 relative vs fits/explore/explore_L2000_coef.txt |
| x4.lexact | \HTpOneLexact | 2000 | E (L2000) | R | equal |
| x4.c2 | \HTpCtwoOne, \HTpCtwoOneDev, \HTCtwoDev | 0.657131263984(10), 4×10⁻¹², 3×10⁻¹² | E (L2000) | R (public/c2c3_rule.py, hi 2000) | 6 fits equal public/c2c3_rule_574918.txt to 1e-12 rel; PDG form and 1-digit deviations exact |
| x4.c3 | \HTpCthreeOne, \HTpCthreeOneDev, \HTCthreeDev | −3.7198563(10), 2×10⁻⁸, 6×10⁻⁸ | E (L2000) | R | as x4.c2 |

Not replayed here, by design: the validation gates A1–A6 of the production (rerun by `make test`, `make smoke` and a
production rerun); the comparison with the HT solver at Λ ≤ 118 (A4), which needs the solver records of
`code/lri_hpc_Hamitonian` and is part of the package's validation (`validate/v4_ht.py`).

### `lri_1d_c5_exact`

Folder: `code/lri_1d_c5_exact/`.

#### results_map: lri_1d_c5_exact (d = 1, exact C2..C5(Λ))

Paths relative to `HT_Pert/`. Command R = `make -C code/lri_1d_c5_exact -f public.mk replay` (`public/replay_c5.py`;
`replay-quick` skips x5.explore, x5.tail and x5.constrained). Records: E = `data/HT_1d/exact_c5/040d92b3bd1d/`,
E4 = `data/HT_1d/exact_c4/a8b57b2e8475/c4_1d_L2000.npz`, F = `code/lri_1d_c5_exact/fits/`. Expected values:
`quoted_lri_1d_c5_exact.json`.

| check id | quoted (macro) | value | records | command | tolerance / rule |
|---|---|---|---|---|---|
| x5.records | — | gate records bind the six results; A6d chain; A6e binds E4 | E, E4 | R | exact (sha256) |
| x5.code | — | 53 production files equal the snapshot manifest | E, code | R | exact (SCRUBBED.txt honoured) |
| x5.frozen | — | 4 frozen records match their .sha256 | F/frozen | R | exact |
| x5.values | \NOneCfiveFourHundred, \NOneCfiveFiveHundred, \NOneDCfiveFiveHundred | −506.619063805112, −519.770442010804, 0.717651334579 (and the README table) | E | R | 12 decimals |
| x5.overlap | \NOneCfiveOverlap | ≤ 6e-12 | E | R | bound |
| x5.blind | \NOneCfiveBlindFour, \NOneCfiveBlindThree | ≤ 3e-9 (frozen Λ ≤ 400), 1.5e-8 (frozen Λ ≤ 320) | F/frozen, E | R (6 reruns of fits_c5_1d.py check) | equal to fits/blind_check_*.txt |
| x5.intercept | \NOneCfiveFreeLtwo, \NOneCfiveFreeMthree | −730.8460638788, −731.0822822059 | F/frozen | R (compare) | 10 decimals |
| x5.explore | — | 96 refits on Λ ≤ 500 | E | R (explore) | intercepts equal fits/explore/L500 (10 decimals) |
| x5.tail | \NOneCfiveTopLog | c13 = 1.945, 1.994 (M3, lo 80, 120) | E | R (tail_fixedA_c5.py) | output lines equal fits/explore/L500/tailA_*.log |
| x5.constrained | \NOneCfiveTopLogPred, \NOneCfiveConstrained | 1.9965; −731.1467, −731.1397, −731.1359 | E, E4 | R (constrained_c5.py) | 1e-9 relative vs constrained_c5_v2.json |
| x5.crosscheck | \NOneCfiveBlindReimpl | −731.13 ± 0.10 | F/explore/constrained_L500/xchk | R | report present (recomputed only by its own jobs) |

Not replayed here: the validation gates (make test, smoke, production rerun); the cited blind re-implementation's fits
(its three node jobs, REPRODUCE).

## d = 1: thermal HT coefficients C2..C7 and the effective Hamiltonian

### `lri_hpc_Hamitonian`

Folder: `code/lri_hpc_Hamitonian/`.

#### results_map: lri_hpc_Hamitonian (d = 1 frozen-cutoff perturbative HT: solver records, window, extrapolations, checks)

Scope: the d = 1 perturbative HT numbers that come from this package. They are quoted in the HT_Pert note, under the
macro names of the paper's `numbers.tex` (`\HTp…`) or the note-only macros (`\NOne…`); the paper's HT section was
removed from main.tex on 2026-10-14, so no paper section or line is cited here. The solver-fit C4/C5 results of this
package (`\NOneCfourSolver`, `\NOneCfivePre`, `\NOneCfiveSolver`) are note-only: the paper's `\HTpCfourOne` and
`\HTpCfiveOne` now come from the exact sums (`code/lri_1d_c4_exact` row x4.c4, `code/lri_1d_c5_exact` row x5.c5).
Paths relative to `HT_Pert/`. Command R = `make -C code/lri_hpc_Hamitonian -f public.mk replay`
(`public/replay_hpcham.py`, rows below; needs `code/lri_eh_hpc`); RF = `replay-full`; S = `smoke`. Records:
X = `data/HT_1d/thermal_expanse/` (111 Expanse records, `campaign/plan.json`), O = `code/lri_hpc_Hamitonian/analysis_original/`
(supplied Λ ≤ 50 rows), A = `code/lri_hpc_Hamitonian/analysis/`, E5 = A`eps5_window/`, IC = A`identity_checks/`,
EXT = A`extended/`, DC = E5`reconcile/dC_reconciled.json`, RC = E5`reconcile/refit_rc.json`,
FL = E5`challenge-theory/freelead2.json`, EH = `code/lri_eh_hpc/lri_eh/exact.py`. Exact values for the ratios:
C4 = 45.42488010356, C5 = −731.13947662454, C7 = −322550 (numbers.tex, Table pt). Expected values:
`quoted_lri_hpc_Hamitonian.json` (also shipped as `public/quoted_lri_hpc_Hamitonian.json`). Rows marked *reading* are
evaluated on the shipped outputs and again on the outputs rerun by R; both must give the quoted value.

| check id | quoted (macro) | value | records | command | tolerance / rule |
|---|---|---|---|---|---|
| a1.code | — | solver fingerprint c0c30783…; 26 shared files; manifests | code, X, A, O | R | exact (sha256; `public/SCRUBBED.txt` honoured; root manifest stale in exactly 5 known files) |
| a1.records | note: exact low orders | C0 = 1/2, C1 = −1/6, r1 = 0, g1 = 1/3; 111 records | X, O, EXT | R | exact counts; ≤ 1e-15 |
| a1.xcheck | — | C8 input table = these records; independent lri_c8 raw C2..C7 | `data/HT_1d/c8/extrapolation/data.json`, X | R | bitwise; ≤ 1e-12 relative (SKIP if the C8 data are absent) |
| a1.lam | \HTpLamThermal | 118 | X, O | R | exact |
| a1.states | \HTpStatesMax | 3.5×10⁹ (3,528,133,673) | X, `public/count_states.py` | R | 2 significant figures; independent count 136/136 exact |
| a1.frac4 | \HTpRawFracFour | 67 | X | R | round(100 C4(118)/C4) |
| a1.frac7 | \HTpRawFracSeven | 44 | X | R | round(100 C7(118)/C7) |
| a1.T2 | note: C2 tail | C2(Λ) − C2 ≈ −40/(81√π) Λ^−1/2 | X, O | R | ratio within 0.5 % at 118, decreasing; fitted amplitude within 1e-3 |
| a1.gates | — | shell ≤ 1e-13 (9e-14), tuning ≤ 1e-10 (9e-11) | X | R | bound |
| a1.reruns | — | 16 analysis scripts + 2 public scripts rerun, 14 JSON outputs compared | A, O, X | R | per-file tolerances (1e-13 … 1e-4 relative; fit diagnostics 50 %, saturated above 1e15); csv identical |
| a1.win4 | \HTpWinCfour | 0.080 (ΔC4(118) = 0.0802302) | DC | R | rounded as quoted; rerun ≤ 1e-13 |
| a1.win5 | \HTpWinCfive | 0.71 (ΔC5(118) = 0.7135827) | DC | R | rounded as quoted; rerun ≤ 1e-13 |
| a1.win4inf | \HTpWinCfourInf | 0.0803 = K + 0.0186910 | EH, IC`challenge-num/{top_a.jsonl, fit_out.txt}` | R; RF (top sums regenerated) | rounded as quoted for every basis on Λ = 24..96; K ≤ 1e-15 |
| a1.offset4 | \HTpRawOffsetFour | 0.19 (0.191–0.199 %) | RC | R (*reading*) | range rounded to the quoted decimals contains 0.19 |
| a1.c4AF | \NOneCfourSolver (A–F part; note only) | 45.4153–45.4189 | RC | R (*reading*) | lower end rounds to 45.415; all inside the range, below exact |
| a1.c5pre | \NOneCfivePre (note only) | 2×10⁻³ (2.09e-3) | RC | R (*reading*) | 1 significant figure |
| a1.c5freed | \NOneCfiveSolver (freed-tail part; note only) | C5 miss −0.217..+0.058 | FL | R (*reading*) | lower end rounds to −731.36; all inside the range |
| a1.omega3 | \HTpOmegaThree | 556 (556.2011) | EXT`extended_summary.json` | R | integer; rerun within 0.05 |
| a1.omega3eff | \HTpOmegaThreeEff | 380–430 (377.7–431.4) | EXT, DC, E5`challenge-num/myfit.py` | R (`public/omega3_eff.py`) | fits with \|C5 − exact\| ≤ 0.25; min, max rounded to 10 |
| a1.protocol | — ("ended unresolved") | unresolved | EXT, A`UPDATED_RESULTS.md` §6 | R (`write_updated_results.py` rerun) | status word exact; verdicts equal on rerun |
| a1.engine | \HTpEngineAgree | 10⁻¹¹ (1.26e-11, 9.6e-12, 2.37e-12) | E5`B/`, E5`A/`, E5`challenge-num/`, DC | R (`public/engine_agree.py`, `cmp_ident.py`); RF (engine iii regenerated) | 1 significant figure; each part bounded; (i) over Λ ≤ 60, the analysis' scope (64: 2.2e-11, printed, not in the bound) |
| a1.ident3 | \HTpIdentThree | 0.003 (max 0.0019) | IC`A/final_fit.json`, IC`reconcile/desc_profile.json` | R (*reading*) | reading (single-state sectors): PASS covers ∂φ, ∂φ², ∂²φ, ∂³φ, a4–a6 only; printed as reported, not bounded: the 2×2 block P = 2, N = 2 (+0.0063 W; reconciler +0.004 W) and ∂φ³, ∂φ⁴ (−0.115 W, −0.369 W; not extrapolable at Λ ≤ 72) |
| a1.ident4 | \HTpIdentFour | 96–100 (95.8–98.3 %) | IC`reconcile/desc_profile.json` | R (*reading*) | reading (range contains): reconciler medians, each sector rounded to an integer lies in the range (engine A's fits, 87–100 %, reported) |
| a1.ident5 | \HTpIdentFive | 0.1–0.2 (0.126) | E5`reconcile/fit_ident_rc.json` | R (*reading*) | reading (range contains): largest \|median\| per W lies in the range |
| a1.phase | note: cutoff placement (exactness) | raw v1..v3 exact at Λ = L + ¼, L + ½ | IC`challenge-theory/offset_ph{0.25,0.5}.json` | R | ≤ 1e-14 (6.2e-15) |
| a1.phase.g2D | note: cutoff placement ("agrees") | g²D alone 0.050 [0.042, 0.056] vs 0.0561 | E5`reconcile/fit_ident_rc.json` | R | judgement (INFO); with D^conn −0.006 [−0.014, +0.000]: residual δC4 ≈ +0.002, about 10 % of 0.0187 |
| a1.W54 | note: raw descendant violation | W/54 at ε² (0.0185235 vs 0.0185185) | IC`A/analysis_extrap.json` | R (*reading*) | within 1e-5, 1/54 inside the fit range |

Other targets (rows of `smoke` and `replay-full`, not of R; their tables go to `.work/`):

| check id | what | records | command | tolerance / rule |
|---|---|---|---|---|
| smoke | production items thermal d7 Λ = 52, 60; φ⁶ d5 52; d3 136 rerun | X | S (`public/smoke_hpcham.py`) | 1e-7 + 2e-11 \|rec\| (bitwise on symmetry); gates |
| full.topsum | top-level sums at Λ = 4..288 regenerated; shift4 limit 0.0186909946 (input of \HTpWinCfourInf) | IC`challenge-num/top_a.jsonl`, `fit_out.txt` | RF (`public/replay_full_hpcham.py`) | 1e-12 relative; limit within 1e-9 |
| full.ht5 | independent engine at Λ = 6..28 regenerated; engine agreement (iii) of \HTpEngineAgree | E5`challenge-num/`, DC | RF | 1e-11 absolute; (iii) ≤ 3e-12 |

Not replayed here, by design:
- The production campaign (Expanse, about 1180 core-hours, 2 TB nodes) and the production runs of the window engines
  (hours on one node): documented in REPRODUCE §5; `smoke` and `replay-full` rerun representative parts.
- The upper ends of `\NOneCfourSolver` (45.420) and `\NOneCfiveSolver` (−730.97), the deviations
  `\NOneCfourSolverDev` (2×10⁻⁴), `\NOneCfiveSolverDev` (3×10⁻⁴), and C6..C8: the S1B refits of
  `code/lri_1d_dconn_refit`. The paper's `\HTpCfourOne`, `\HTpCfiveOne` and their deviations: `code/lri_1d_c4_exact`,
  `code/lri_1d_c5_exact`.
- The second Λ^−1/2 channel: `code/lri_d1_fullblock_tail_response`. C8 to Λ = 92: `code/lri_c8_hpc`.
- K and the exact g²D shift are recomputed here (EH) and in `code/lri_eh_hpc` (rows a1.eh.*), which also regenerates the
  g²D tables d5_all.json, d7_all.json.
- HTN's raw-C4 union 45.335–45.343 includes stress-test lenses that are not shipped; the quoted 0.19 % replays from RC.

### `lri_eh_hpc`

Folder: `code/lri_eh_hpc/`.

#### results_map: lri_eh_hpc (isolated g²D vacuum-window add-on, d = 1)

Paths relative to `HT_Pert/`. Command R = `make -C code/lri_eh_hpc -f public.mk replay` (`public/replay_eh.py`);
S = `smoke`, RF = `replay-full` (`public/g2d_rerun.py`). Records: P = `code/lri_eh_hpc/`, PI =
`code/lri_hpc_Hamitonian/analysis/eh_review/physics-impact/` (cross-folder; rows SKIP without it). Expected values:
`quoted_lri_eh_hpc.json` (also `public/quoted_lri_eh_hpc.json`). No paper macro comes from this package alone; K enters
`\HTpWinCfourInf` (row `a1.win4inf` of `code/lri_hpc_Hamitonian`).

| check id | quoted (macro) | value | records | command | tolerance / rule |
|---|---|---|---|---|---|
| a1.eh.code | — | source 2e2e8ca8…, receipt 648fa9fb… | P (`MANIFEST_SHA256.json`, `BUILD_INFO.json`, receipt) | R | exact (sha256; SCRUBBED.txt honoured) |
| a1.eh.receipt | — | supplier's validation passed, 32 tests | P`benchmarks/validation_local.*` | R (RECORDED); `make test` reruns it | as recorded |
| a1.eh.K | eq. K of the note (enters \HTpWinCfourInf) | K = 0.0616119308426799 | P`lri_eh/exact.py`, PI`dc4_exact.json` | R | 1e-16; ≥ 55 digits equal to dc4_exact.json |
| a1.eh.exact | ΔC4(g²D) ≈ log Λ/17496 + K | exact rationals at even Λ = 2..118 | P`lri_eh/exact.py`, PI`{d5_all,d7_all,dc4_exact}.json` | R | ≤ 1e-16 (fast, dc4_exact); ≤ 1e-15 (tables); remainder shrinking |
| a1.eh.bench | — | supplier's Λ = 118 degree-5 runs = d5_all | P`benchmarks/results/new_L118_d5_t4_*.json`, PI`d5_all.json` | R | 1e-13 relative |

Other targets (their tables go to `.work/`):

| check id | what | records | command | tolerance / rule |
|---|---|---|---|---|
| a1.eh.g2d5 | g²D table degree 5 regenerated (S: Λ = 4..20; RF: 4..118) | PI`d5_all.json`, `gen_deltas.py` | S, RF | 1e-12 max(1,\|ref\|); dimensions exact; gates |
| a1.eh.g2d7 | g²D table degree 7 regenerated (S: Λ = 4..12; RF: 4..90) | PI`d7_all.json`, `gen_deltas.py` | S, RF | as above |

Not replayed here: the package's own performance benchmarks (supplier measurements, `PERFORMANCE.md`) and its
campaign tools (not used for any HT_Pert result).

## d = 1: HT C8 and the complete-window coefficient flow

### `lri_c8_hpc`

Folder: `code/lri_c8_hpc/`.

#### results_map: lri_c8_hpc (d = 1, eighth order, Λ = 52..92)

**Scope.** The quoted numbers this package covers:
- the reach Λ = 92 for C8 (`\HTpLamCeight`, numbers.tex), quoted in the HT_Pert note. The paper's HT section was removed
  from main.tex on 2026-10-14; until the author decides where it goes, the HT_Pert note (with the macro name and the
  row ids below) is the place this number is quoted;
- the C8 campaign, its validation and the C8 data table, as printed in the LRI HT note (`LRI_HT_note`, tab:c8data and
  the validation table) and carried into the HT_Pert note's reproduction table by these rows.

The C8 extrapolations (`\HTpCeightOne`, `\HTpCeightOneCalRange`, `\HTpCeightOneUncal`, `\HTpCeightOneDev`) are fits to
these data; they are replayed by `code/lri_1d_dconn_refit`.

**Commands and records.** Paths are relative to `HT_Pert/`.
- Command R = `make -C code/lri_c8_hpc -f public.mk replay` (`public/replay_c8.py`; row id in the first column).
  Standard library only, about 1 s.
- Command F = `make -C code/lri_c8_hpc -f public.mk replay-full`: the RECORDED rows recomputed with the solver.
- Command T = `make -C code/lri_c8_hpc -f public.mk test`.
- Record abbreviations, all under `data/HT_1d/c8/`:
  - A = `c8_L52-92/accepted/*.json` (42 outputs);
  - J = `c8_L52-92/journals/654fb90d19a573c1/lane_*.json` and `c8_L52-92/submissions.txt`;
  - K = `campaigns/c8_L52-92.json`;
  - X = `exports/*` (2 exports and 2 sidecars);
  - V = `validation/receipt_dd811aca899543c4.json`;
  - DJ = `extrapolation/data.json`.
- Code abbreviations: I = `code/lri_c8_hpc/inputs/` (original runs, Λ ≤ 50); TH =
  `code/lri_hpc_Hamitonian/analysis/extended/{thermal_new.json, C7_extension.json, prior_c7/C7_completed_runs.json}`.
- Expected values and rules: `quoted_lri_c8_hpc.json`.

| row | quoted (macro) | value | records | command | tolerance / rule |
|---|---|---|---|---|---|
| c8.reach | `\HTpLamCeight` | 92 | A, K, DJ | R | exact: outputs and campaign items = {raw, vacuum_only} × even 52..92 (42), largest cutoff equals the macro text |
| c8.lanes | - (LRI HT note) | 42 lanes, one attempt each, exit 0, array 569698 | J, A, K | R | exact: per lane 1 attempt, exit 0, array 569698, task id = lane, item = campaign lane, accepted, output_sha256 = the output's sha256; submissions.txt lanes 0..41; total solver time 8605.5 s reported |
| c8.envelopes | - | 88 self-hashed envelopes verify | A, J, K, V, X | R | exact: sha256 of the canonical JSON payload; campaign id = sha256 prefix 654fb90d19a573c1 |
| c8.exports | - | sha256_export cf3fec9e…, dd98c5a4… | X, A | R | exact: export sha256 = sidecar = quoted; export bytes = re-serialized outputs (indent 2, newline) |
| c8.source | - | source digest dd811aca899543c4… | code src/lri_c8, V, K, A, X | R | exact: digest of the shipped src/lri_c8 recomputed (io.source_digest) and named by every record |
| c8.manifest | - | 164 files | code (MANIFEST_SHA256.json) | R, T | exact; files in public/SCRUBBED.txt (not under src/) count as scrubbed |
| c8.gates | - (LRI HT note, C8 table caption) | shell ≤ 1.6e-14, low order ≤ 7.9e-13, tuning ≤ 1.95e-9 | A | R | bound, every output (measured 1.577e-14, 7.816e-13, 1.9500e-9); the tuning residual recomputed from the energies equals the record; solver acceptance (1e-10, 1e-7, 1e-6; E3 − E0 = C; caps 19/16) holds |
| c8.values | - (LRI HT note) | C8^raw(92) = 2883374.2546683108, C8^vac(92) = 2883433.2067096015 | A, X, DJ | R | exact (repr), in all three |
| c8.table | - (LRI HT note, tab:c8data) | Λ = 50, 52, 56, …, 88, 90, 92: C8^raw, C8^vac, vac − raw, C7^raw, C6^raw | X, I | R | rounded as printed (4, 4, 4 [2 at Λ = 50], 4, 6 decimals) |
| c8.validation | - (LRI HT note) | job 569659: pass, 164 files, 74/74 tests, grid 38/38 bitwise | V, K | R (RECORDED); recomputed by T and F | read from the self-hashed receipt (= the campaign's embedded copy); stack 3.11.4/1.24.3/0.57.0/1.10.1, Xeon Gold 6148, compute node, full |
| c8.original | - (LRI HT note) | Λ = 60: raw 2488157.173328419 vs 2488157.1733284392, max \|ΔC\| 2.0e-8; vacuum_only 2488207.44642163 vs 2488207.4464216377, 7.5e-9; stored = ranked | V, A | R (RECORDED); recomputed by F | as recorded (repr; \|ΔC\| to 2 sig.); the new values equal the production outputs at Λ = 60 exactly; F: within 1e-7 + 2e-11\|ref\| of the receipt (bitwise on the production stack) |
| c8.thermal | - (LRI HT note) | 6.1e-14 (vs the separate thermal campaign: same `lri_hpc` core; different driver, cluster and runs) | DJ | R | 2 sig.: max over 46 common cutoffs (Λ = 2..92) and C0..C7 of \|raw − thermal\| / max(1, \|raw\|) (6.113e-14 at Λ = 46, C5; 2.1e-14 for Λ = 52..92); raw C4(52) 26.246793314472836 vs thermal 26.246793314472797, exact |
| c8.datajson | - | sha256 ccc77dfa1e7d… | DJ, X, I, TH | R | exact: shipped sha256; raw and vacuum_only tables = records; `public/build_data_json.py` rebuild byte-identical (SKIP for the rebuild when TH is absent) |

Row ids are this package's. The provisional rows of the HT_Pert note used `c8.lmax` for the reach; the note takes
`c8.reach` from this package.

Additional checks, not rows of the note:
- `make test` (T): pytest 74 passed and the 38-point grid within 1e-7 + 2e-11 |ref|, on a copy.
- `make smoke`: the production item Λ = 52, both prescriptions, rerun and compared with A (bitwise on the production
  stack, else 1e-7 + 2e-11 |ref|).

##### Not replayed here, by design
- **The C8 extrapolations** (`\HTpCeightOne` and its ranges): `code/lri_1d_dconn_refit`, from DJ and the S10 window.
- **The superseded four-lens extrapolation of 2026-10-04** (8.0655e6): not shipped, archive only.
- **The per-item time and memory table of the HT note**: operational. The journals (J) carry seconds and peak RSS per
  item, and `c8.lanes` reports the total solver time.

### `lri_d1_full_coefficient_flow`

Folder: `code/lri_d1_full_coefficient_flow/`.

#### results_map: lri_d1_full_coefficient_flow (d = 1, complete window C0..C8 to L = 72, "S10")

Paths relative to `HT_Pert/`. Command R = `make -C code/lri_d1_full_coefficient_flow -f public.mk replay`
(`public/replay_s10.py`). Records: S = `code/lri_d1_full_coefficient_flow/` (A = S`/results/new_coefficients`, archive
L = 2..44), P = `data/HT_1d/s10_production/`, DJ = `data/HT_1d/c8/extrapolation/data.json` (package lri_c8_hpc),
RC = `code/lri_hpc_Hamitonian/analysis/eps5_window/reconcile/dC_reconciled.json`. Expected values:
`quoted_lri_d1_full_coefficient_flow.json`. The numbers are quoted in the HT_Pert note under the macro names below.

| check id | quoted (macro) | value | records | command | tolerance / rule |
|---|---|---|---|---|---|
| s10.manifest | — | 85 files of the package at fec60a2 | S/MANIFEST.sha256 | R | sha256 (SCRUBBED.txt honoured) |
| s10.code | — | solver sha256 854fc763… = provenance.code_sha256 of all 14 records | S/code, P | R | exact |
| s10.records | — | 14 records L = 46..72, Dconn, degree 8; L = 72: 109,373,212 states, 11.7 h, 116.6 GiB | P | R | exact fields |
| s10.winlam | \HTpWinLamEight | 72 | A, P | R | exact (no gap in even L) |
| s10.csv | — | dC table regenerated byte for byte, sha256 3105e037… | P, DJ | R (`public/make_dconn_minus_raw.py`) | bitwise |
| s10.dC678 | (note text) | dC6, dC7, dC8 (72) = +1.1717361, −1.828185, −8.5641 | P, DJ | R | quoted decimals |
| s10.match | \HTpSTenMatch | 2e-11 (dC4 4.26e-13, dC5 1.96e-11; C0..C3 unchanged to 1.1e-13) | P, DJ, RC | R | one significant figure |

Also (not quoted numbers): `make test` = manifest + the package's own tests on a copy + a fresh Dconn run at
L = 2..24 against A (rtol 1e-10); `make smoke` = the production gate's validation (L = 40, 42, 44 and raw 44 against
A). The production rerun (38.5 node-hours) is in REPRODUCE.

### `lri_1d_dconn_refit`

Folder: `code/lri_1d_dconn_refit/`.

#### results_map: lri_1d_dconn_refit (d = 1, C4..C8 with the complete window, refits "S1B")

Paths relative to `HT_Pert/`. Command R = `make -C code/lri_1d_dconn_refit -f public.mk replay`
(`public/replay_refit.py`). Records in F = `code/lri_1d_dconn_refit/`: DO = F`/delta/out`, DA =
F`/delta/archived_out_delta_v1`, JS = F`/joint/out/r72/summary_dconn_w.json`, JR = F`/joint/out/r72/r72_summary.json`,
J1 = F`/joint/archived_run1/summary.json`, MH = F`/model-independent/out/headline.json`, MF =
F`/model-independent/out/final72.json`; from lri_hpc_Hamitonian: RR = `.../eps5_window/reconcile/refit_rc.json`,
FL = `.../eps5_window/challenge-theory/freelead2.json`; DC = `data/HT_1d/s10_production/dconn_minus_raw_L46_72.csv`.
Expected values: `quoted_lri_1d_dconn_refit.json`. All fit windows are post hoc. The numbers are quoted in the HT_Pert
note under the macro names below.

Data sets of the union components:
- **fixed A–F**: the unweighted dataset dconn (JR `C_low.dconn_hi118.fixed_AF`);
- **floor+stat**: the weighted dataset dconn_w (JS `dconn_w_hi118_C<k>_floor_stat`);
- **MI**: the model-independent lens (MH, MF).

The C4 and C5 rows are solver-fit results. They are note-only macros of the HT_Pert note (`\NOneCfourSolver`,
`\NOneCfourSolverDev`, `\NOneCfiveSolver`, `\NOneCfiveSolverDev`). The paper's `\HTpCfourOne` and `\HTpCfiveOne` come
from the exact sums instead (`code/lri_1d_c4_exact` row x4.c4, `code/lri_1d_c5_exact` row x5.c5).

| check id | quoted (macro) | value | records | command | tolerance / rule |
|---|---|---|---|---|---|
| rf.inputs | — | 46 recorded sha256 = shipped inputs and tables | DO, DA, F/run1, inputs | R | exact |
| rf.blind | (note text) | frozen hi = 44 forecast vs exact dC6..dC8 (46..72): max \|err\|/unc_typ = 0.099 (0.0986; 42 points) | DA/frozen_forecast_L46_72.json, DC | R | 2 sig. figures |
| rf.C4 | \NOneCfourSolver (note only) | 45.415–45.420: pre-registered A–F (Dconn_full) 45.41530..45.41889 (24 fits), floor+stat (dconn_w) median 45.419862, MI 45.41909 | RR, JS, MH | R | union of central values; 3 decimals, nearest (outward identical) |
| rf.C4dev | \NOneCfourSolverDev (note only) | 2e-4 (2.11e-4) | as rf.C4 | R | max \|end − C4\|/C4, 1 sig. fig. |
| rf.C5 | \NOneCfiveSolver (note only) | −731.36 to −730.97: freed tail (i) −731.3562..−731.0812 (18 fits), floor+stat (dconn_w) 16–84 −731.3336..−730.9651 | FL, JS | R | union, 2 decimals, **nearest** (outward would give −731.36 to −730.96) |
| rf.C5dev | \NOneCfiveSolverDev (note only) | 3e-4 (2.96e-4) | as rf.C5 | R | 1 sig. fig. |
| rf.C6 | \HTpCsixOne | 14,320–14,342: fixed A–F (unweighted dconn) 16–84 14332.61..14341.76, floor+stat (dconn_w) 14321.38..14329.43, MI 14320.33..14328.75 | JR, JS, MH, MF | R | union, integers, nearest (outward identical) |
| rf.C6dev | \HTpCsixOneDev | 8e-4 (7.93e-4) | as rf.C6 | R | 1 sig. fig. |
| rf.C7 | \HTpCsevenOne | −322,890 to −322,230: fixed A–F (unweighted dconn) −322884.30..−322574.43, floor+stat (dconn_w) −322572.60..−322233.55, MI widened by ±6 −322709.21..−322575.65 | JR, JS, MH, MF | R | union −322884.30..−322233.55, **outward** to tens |
| rf.C7dev | \HTpCsevenOneDev | 1e-3 (1.04e-3) | as rf.C7 | R | 1 sig. fig. |
| rf.C7w | — (sensitivity) | INFO: weighted fixed A–F (JR `C_low.dconn_w_hi118.fixed_AF`) in place of the unweighted one: C6 14332.80..14342.06, union still 14,320–14,342; C7 −322890.94..−322582.46, union −322,900 to −322,230 (outward) | JR, JS, MH, MF | R | INFO (not quoted) |
| rf.C8 | \HTpCeightOne | 8.0652e6 (8,065,157; n = 138 weighted fits) | JS (C8_calibrated) | R | 5 sig. figures |
| rf.C8dev | \HTpCeightOneDev | 7e-4 (6.69e-4) vs 8,059,766.72 | JS | R | 1 sig. fig. |
| rf.C8cal | \HTpCeightOneCalRange | INFO: stored estimator span 8.0636–8.0655 (16 estimators); the quoted 8.061–8.067 is the stage's judgement. Reconstruction from the stored components it names (estimators, FL/free selections, anchoring on C4..C7, hi = 70/80 selections, delta-free hi = 72 estimators): 8.0615–8.0669 | JS, JR | R | INFO (judgement; reconstruction printed, **outward** to 3 decimals: 8.061–8.067) |
| rf.C8uncal | \HTpCeightOneUncal | 8.045–8.073: union of the five prior-criterion family 16–84 ranges on the S1B weighted data (dconn_w) 8.0455–8.0729; also printed: unweighted and s46 8.046–8.072, run 1 8.047–8.072 (the value the macro held until 2026-10-14) | JS, J1 | R | 3 decimals, **nearest** |
| rf.paired | (note text) | C6 −0.01..−0.04; C7 +4..+19; C8 +17..+32 (fixed), −240..−490 (FL) | JR (D_paired) | R | as quoted |
| rf.noise | (caveat) | S10 noise rms 3.95e-10, 1.34e-8, 2.32e-7 (dC6..dC8) | DO, joint/code/data.py | R | 3 sig. figures |

Also (not quoted numbers): `make test` rebuilds the delta stage (DO, bitwise, else 1e-9 field-scaled), reruns the
model-independent `headline.py` and `final72.py` from the shipped intermediates (MH, MF, bitwise, else 1e-12
field-scaled) and, with python-flint, refits 12 joint-lens key fits (JS and `summary.json`, 1e-9 relative).
"Field-scaled" means relative to the largest |x| of the list that holds the number (or to the number itself), with no
absolute floor. The full refit (395,280 joint fits, 34 model-independent grids) is in REPRODUCE.

### `lri_d1_fullblock_tail_response`

Folder: `code/lri_d1_fullblock_tail_response/`.

#### results_map: lri_d1_fullblock_tail_response (d = 1, second Λ^(-1/2) channel)

**Scope.**
- One caveat sentence of the paper (main text, Hamiltonian truncation section, perturbative part, "Caveats"): "a
  second channel with the leading power Λ^(-1/2) enters at ε⁴". This is fact C6 of `pert_facts.md`.
- No macro of numbers.tex comes from this package, and no number of it is quoted in the paper.
- The HT_Pert note cites the same structure, and labels any coefficient it gives (2/(3√π), B) as unverified.

**Paths and commands.**
- Paths are relative to `HT_Pert/`. P = `code/lri_d1_fullblock_tail_response`, M = P`/docs/METHOD.md`,
  R = P`/results`.
- Command: `make -C code/lri_d1_fullblock_tail_response -f public.mk replay` (public/replay_fb.py; the row id is the
  first column). `replay-full` reruns all 13 response records instead of those with μ ≤ 16.
- Expected values: `quoted_lri_d1_fullblock_tail_response.json`, merged into `results/HT_1d/`.

| check id | quoted (macro) | value | records | command | tolerance/rule |
|---|---|---|---|---|---|
| fb.manifest | – | 108 files | P/MANIFEST.sha256 | replay | sha256; files in public/SCRUBBED.txt reported, not failed |
| fb.power | – (caveat: "leading power Λ^(-1/2)") | J channel Λ^(3α−2) → Λ^(-1/2) at ε = 0 (ε slope −3/2); φ⁶ channel Λ^(α−1) → Λ^(-1/2) (slope −1/2); (2−β)B3 = Λ^(3α−2)/[3Γ(3α)] | M Eqs. (2)–(3) (text checked verbatim) | replay | exact (sympy) |
| fb.onset | – (caveat: "enters at ε⁴") | S_J,0..3 = 0, S_J,4 > 0 | (a) J^P built from the formula of M Eq. (1) (and the normal-ordered form of code/response.py); (b) R/exact_full_L{2,4}_d8.json; (c) R/{dconn,raw}_full_L*_d8.json (13) | replay | (a) J^P on P ≤ 4 exactly 0 (both forms agree ≤ 1e-12); (b) exact rationals, S_J,4 = 4375/729, 18571/2592; (c) \|S_J,k≤3\| ≤ 1e-15, reruns ≤ 1e-12 scaled |
| fb.amplitude | – (not quoted; UNVERIFIED) | 1/[3Γ(3/2)] = 2/(3√π) = 0.376126389031837… | R/partial_assembly_example.json, R/dconn_{full,phi6}_L8_d8.json | replay | arithmetic 1e-35; record consistency 1e-14; rerun of code/assemble_response.py 1e-30 |
| fb.B | – (not quoted; role in C4 unverified) | B = 0.49138877353902566; Q = 1/81; A = 32(π−2)/(729π^(3/2)) | R/phase_overlap_asymptotics.json (rerun of code/mixing_asymptotics.py), M Eq. (6) text | replay | B against the closed form ≤ 1e-16 (abs) and repr(B) equal to the quoted 17 digits (passed with sympy 1.12 and 1.14); numeric triple equal to the record ≤ 1e-15 (rel); 38 topology weights exact |
| fb.annulus | – | "468 exact thresholds; 36 direct finite-annulus comparisons passed" | R/general_bath_annulus.json, R/annulus_validation.json, P/REPORT.md table | replay (rerun of tests/check_annulus.py) | its own assertions; 36 rows ≤ 1e-8 (rel); REPORT table to 9 decimals |
| fb.caveat | – | structure only | – | replay (INFO) | judgement: the sentence rests on fb.power and fb.onset |
| fb.unverified | – | J sign and normalisation "plausible" | REVIEWS.md | replay (INFO) | judgement: the review did not re-derive the K3 J coefficient |

Test stages (`make -f public.mk test`, public/run_tests_fb.py):
- manifest, and the verbatim tests/verify_manifest.py;
- check_annulus, mixing_asymptotics, check_finite_response;
- validate, on x86-64 only (80-bit long double), SKIP elsewhere.

##### Not replayed here, by design
- **The post hoc "J-informed" C4 misses** (−0.001 to −0.004), and the other fits of the 2026-10-07 review. They exist
  only in the unpublished review folder; the review itself calls them suggestive, and the paper does not quote them.
- **The bundle's large-μ phase shells (to μ = 262144) and the finite part C = 8.0942274117886863….** They are used
  only by `code/mixing_asymptotics.py` (convergence CSV), not by the caveat. `test` reruns the shell sums only through
  `tests/validate.py` on x86-64 (μ ≤ 256). The full regeneration commands are in REPRODUCE.
- **The ε⁶–ε⁸ response tables of REPORT.md.** They are low-space susceptibilities, not C6–C8 estimates (the package's
  own statement). replay-full reruns the full-J records; the φ⁶, phase and number records are rerun only by the
  package's own commands.

## d = 2: coefficients C2..C8 and the independent check

### `lri_d2_coeff_hpc`

Folder: `code/lri_d2_coeff_hpc/`.

#### d = 2 perturbative HT: every quoted number, its record, command and tolerance

Paper (final text, commit a6772872): Sec. 3.1 ("Around the generalized free field", `paper/sections/perturbation.tex`)
prints the d = 2 column of Table 2 (`tab:htpert`: C2 to C5 and their deviations δ; C6 to C8 "n.r.") and, in its
paragraph "Independent checks", `\HTpCfiveTwoDev` and `\HTpTwoLowDev`. The d = 2 macros printed in the paper are
`\HTpCtwoTwo`, `\HTpCtwoTwoDigits`, `\HTpCthreeTwo`, `\HTpCthreeTwoDev`, `\HTpCfourTwo`, `\HTpCfourTwoDev`, `\HTpCfiveTwo`,
`\HTpCfiveTwoDev` and `\HTpTwoLowDev`. The other d = 2 macros of `paper/numbers.tex` (`\HTpTwoLprod`, `\HTpTwoLfour`,
`\HTpTwoLfive`, `\HTpTwoImplAgree`, `\HTpTwoIdentThree`, `\HTpCfiveTwoLog`, `\HTnpDtwoCfourLog`) are not printed in the
paper; the HT_Pert note prints them under the same names and values. Note: Sec. 4 and Appendices A to C of the HT_Pert
note (Part III of the Supplemental Material), macros `\NTwo*` of `note/sections/d2/numbers_d2.tex`. The paper's earlier
tables of solver checks and descendant spacings are no longer in the paper; their content is in note Secs. 4.2 and
4.6 and Appendices A.2 and C.1. The cutoff L is the level cutoff of the codes (N ≤ L). ε = 2s − 2, Δφ = (2 − ε)/4.

Commands, run from `HT_Pert/code/<package>`:
- `P` = `make -f public.mk replay` in `lri_d2_coeff_hpc` (`public/replay_prod.py`, checks p2.prod.*);
- `R` = `make -f public.mk replay` in `lri_2d_coeff_independent_check` (`public/replay_p2.py`, all other p2.*);
- `F` = `make -f public.mk replay-full` there (reruns the shipped fit scripts; shows the shipped outputs are theirs);
- `T` = `make -f public.mk test` there (small-cutoff reruns of every code, t.*).
Each check prints PASS/FAIL, the recomputed value, the expected value and the tolerance. "n sig. digits" means the
recomputed value rounds to the quoted one. Status words follow the paper and the note.

##### Production records and code (lri_d2_coeff_hpc)
| Check | Paper / note | Quoted value | Recomputed from | Cmd | Tolerance | Status |
|---|---|---|---|---|---|---|
| p2.prod.records | (integrity) | 41 lri-coeff-v1 records | `data/HT_2d/prod/*/d8/*.json`: sha256 of canonical payload | P | exact | — |
| p2.prod.campaigns | (integrity) | 3 campaign manifests, self-hashed, source digest 550e9266… | `data/HT_2d/prod/*/campaign.json` | P | exact | — |
| p2.prod.source | (integrity) | solver source digest 550e9266… in every record | `code/lri_d2_coeff_hpc/src/lri_coeff/*.py, *.cpp` | P | exact | — |
| p2.prod.tables | (integrity) | coefficients.csv = records | `prod1_symmetry/`, `prod2_expanse/coefficients.csv` | P | exact | — |
| p2.prod.cited | cited by HT (`HT/data/HT_2d/pert_crosscheck`) | **`data/HT_2d/prod/prod1_symmetry/coefficients.csv` has sha256 d86743c1e2592ea2ed29d51680ad497970b851ef0d83a89c9e69cd98bb96bc6c**; `code/lri_d2_coeff_hpc/reference/lri_d2_perturbative_C8/results/coefficients_C0_C8.csv` has ee72158e2d9821f5aa330a09f8a094968083282078ff03a12b97067dad20b7bb | sha256 of the files | P | exact | — |
| p2.prod.lprod | `\HTpTwoLprod` (note) | 34 (raw and consistent L = 2..34; literal 2..14) | records | P | exact | finite-L |
| p2.prod.degree | (paper Table 2: C2..C8 computed, C6..C8 n.r. in d = 2) | eighth order | records | P | exact | — |
| p2.prod.validation | (note Sec. 4.2 context) | release validated on symmetry 571623 and Expanse 54765932 | receipts | P | receipts | — |

##### Independent implementations (note Sec. 4.2, App. A.2)
| Check | Paper / note | Quoted value | Recomputed from | Cmd | Tolerance | Status |
|---|---|---|---|---|---|---|
| p2.impl_agree | `\HTpTwoImplAgree` (note) | 4×10⁻¹³ (worst scaled difference 3.86e-13, 25 scheme/L pairs, C, r, g, E_p, vacua) | `rs_exact/results/*.json` vs production records | R | 1 sig. digit; value in [3.8, 3.9]e-13 | verified |
| p2.rs_lmax | `\NTwoRSLmax` | exact RS L = 0..18 | `rs_exact/results` | R | exact | — |
| p2.cauchy_vs_rs | `\NTwoCauchyAgree` | 5×10⁻⁴⁶ (4.76e-46, 15 cases) | `cauchy/results` vs `rs_exact/results` (mpmath, 60 digits) | R | 1 sig. digit | verified |
| p2.pkg_vs_cauchy | `\NTwoPkgCauchy` | 1.6×10⁻¹⁴ | production records vs `cauchy/results` | R | 2 sig. digits | verified |
| p2.cauchy_lmax | `\NTwoCauchyLmax` | L = 0..8 | `cauchy/results` | R | exact | — |
| p2.low_agree | `\NTwoLowAgree` | 4×10⁻¹⁴ (exact C2(L), C3(L) code vs package, L = 2..34, absolute) | `continuum/exact_C2_C3.csv` vs records | R | ≤ 4.5e-14, 1 sig. digit | verified |
| p2.c4_agree | `\NTwoCfourAgree` | 1.1×10⁻¹³ (large-L C4 code vs exact RS and package, relative) | recomputed from `c4_exact/results/c4_L2000.npz` (≤ 1.1e-13) + the recorded validation `c4_exact/validate_rs.txt` (= 1.1e-13) | R | bound + record | verified |
| p2.c5_agree | `\NTwoCfiveAgree` | 2.2×10⁻¹³ (large-L C2..C5 code vs package, L ≤ 34) | recomputed from `residual_log/large_L/results/c5_L300.npz` (≤ 2.2e-13) + `residual_log/results/eps5/validation_c5.txt` (= 2.2e-13) | R | bound + record | verified |
| p2.c5_opt_regress | `\NTwoOptRegress` | 7.3×10⁻¹⁶ per task (optimized vs production engine) | record `residual_log/large_L/results/regression_opt.txt` (65 task rows re-read; requirement 1e-12) | R | record | verified (cited check) |
| p2.c5_assembly | `\NTwoOptAssembly` | 7.6×10⁻¹³ (L = 300 assembly vs L ≤ 200 production, C5) | `c5_L300.npz` vs `results/eps5/c5_L200.npz` | R | 2 sig. digits | verified |
| p2.delta_rational | `\NTwoDeltaRational` | 4×10⁻¹⁶ (δ⁽³⁾ chain sums vs exact rationals, L = 2..16) | `tag3_L16000.npz` vs `results/tag/tag_L*_phi2_2_real.json` and the δ⁽³⁾ inputs of `ce_wc/out_wcs` | R | 1 sig. digit | verified |
| t.* | (code checks) | small-cutoff reruns = shipped outputs | every code | T | as printed | — |

##### Low orders
| Check | Paper / note | Quoted value | Recomputed from | Cmd | Tolerance | Status |
|---|---|---|---|---|---|---|
| p2.c2_digits | `\HTpCtwoTwo`, `\HTpCtwoTwoDigits` | 0.30806541358; = 4 log2/9 to 35 digits | closed form of C2(L) summed to ∞ (mpmath, 50 digits) | R | ≥ 35 digits | FINAL (numerical agreement, not a proof) |
| p2.c2_closed_form | (supports the above) | the closed form is the HT C2(L) | vs `continuum/exact_C2_C3.csv`, 49 L ≤ 600 | R | ≤ 1e-13 | — |
| p2.c3_limit | `\HTpCthreeTwo` | −0.8748500(1) | `continuum/exact_C2_C3.csv` (L ≤ 600), basis 1, l/L, 1/L, l/L², 1/L², l²/L², l/L³, 1/L³, Lmin 32/64/128 | R | every fit within 1e-7 | FINAL |
| p2.c3_dev | `\HTpCthreeTwoDev` | 1×10⁻⁸ (1.45e-8) | from the quoted value and exact C3 | R | 1 sig. digit | — |
| p2.c3_lmax, p2.c3_tail | `\NTwoCthreeLmax`, `\NTwoCthreeTail` | 600; ln L/L coefficient 0.70734 (= (9/2)·40/(81π)) | same fits (Lmin 64) | R | exact; 5 decimals | — |
| p2.r2_slope | note Sec. 4.4: r₂ ≃ 2L/(27π); `\NTwoRtwoSlope` | 0.0235785 = [r₂(2000) − r₂(1998)]/2 | `c4_exact/results/c4_L2000.npz` | R | 7 decimals; within 1e-6 of 2/(27π) | — |
| p2.low_dev | `\HTpTwoLowDev` | C2..C4 agree to better than 10⁻⁷ | p2.c2_digits, p2.c3_dev, p2.c4_dev | R | bound | — |

##### C4 (exact C4(L) to L = 2000)
| Check | Paper / note | Quoted value | Recomputed from | Cmd | Tolerance | Status |
|---|---|---|---|---|---|---|
| p2.c4_lfour | `\HTpTwoLfour` (note) | 2000 | `c4_exact/results/c4_L2000.npz` | R | exact | — |
| p2.c4W_limit | `\HTpCfourTwo` | 5.0488682(10) (median 5.04886823, 9 no-log fits) | C4^W = C4corr + off-diagonal + χ-line shifts (`c4_L2000.npz`, `residual_log/results/offdiag_L20000.npz`, `nm_L8000.npz`); towers T22, T22+l3/L, T23 × Lmin 200/300/400 | R | 7 decimals; half spread ≤ 1e-6 | FINAL |
| p2.c4_dev | `\HTpCfourTwoDev` | 5×10⁻⁸ (4.6e-8) | quoted value vs exact | R | 1 sig. digit | — |
| p2.c4W_spread, p2.c4W_nolog | `\NTwoCfourWFitSpread`, `\NTwoCfourWLogMax` | 6×10⁻⁷; free ln L coefficient ≤ 3.5×10⁻⁶ | same fits (+ ln L, Lmin 200/300) | R | 1–2 sig. digits | — |
| p2.c4W_table | (integrity) | `residual_log/C4W_by_L.csv` = the series | | R | ≤ 1e-13 | — |
| p2.c4_zmoff, p2.c4_chi | `\NTwoCfourZmOff`, `\NTwoCfourChi` | 5.0386139; 0.0102543 | same fits; `nm_L8000.npz` (Lmin 400/1000/2000) | R | 7 decimals | — |
| **p2.c4_log_consistent** | **`\HTnpDtwoCfourLog`** (note; in `paper/numbers.tex`, not printed); `\NTwoCfourConsB` | −0.027; −0.026563(42) = −365/(4374π) | `c4_L2000.npz` consistent scheme, stable set of `c4_exact/fits_c4.py` (log T22, log T22+l3/L × c2 free/fixed × Lmin 200/300/400; 12 fits) | R | 3 decimals (`\HTnpDtwoCfourLog`), 6 (`\NTwoCfourConsB`); within 5e-6 of −365/(4374π) | FINAL |
| p2.c4_log_zm, p2.c4_log_raw | `\NTwoCfourZmB`, `\NTwoCfourRawB` | −0.010480(42) = −8/(243π); −0.026381 = −725/(8748π) | same | R | 6 decimals | — |
| p2.c4_A_schemes | `\NTwoCfourConsA`, `ZmA`, `RawA` | 5.0026(5), 5.0213(5), 5.0021 | same | R | 4 decimals | — |
| p2.c4_kappa | `\NTwoKappa` (note Sec. 4.4) | 2.2073×10⁻⁴ | `c4_exact/results/windows_L20000.npz` (Lmin 2000) vs analytic 2.20729299645e-4 | R | 4 decimals of 1e4 κ | — |
| p2.c4_blind | `\NTwoBlindLogMax`, `\NTwoBlindNoLogMin` | 8.3×10⁻⁸ (models with ln L, largest miss over L = 1200..2000); 4.1×10⁻⁷ (models without, smallest miss at L = 2000; over the whole range they miss by as little as 1.9×10⁻⁹ at L = 1200) | predictions recorded (2026-10-08 19:44) from fits to L ≤ 1000 before the L = 2000 run finished (`c4_exact/fits/blind_predictions_L1200_2000.json`) vs `c4_L2000.npz` | R | 2 sig. digits | — |

##### C5 (exact raw C5(L) to L = 300; windows Wc and Wcs)
| Check | Paper / note | Quoted value | Recomputed from | Cmd | Tolerance | Status |
|---|---|---|---|---|---|---|
| p2.c5_lfive | `\HTpTwoLfive` (note) | 300 | `residual_log/large_L/results/c5_L300.npz` | R | exact | — |
| p2.c5_limit | `\HTpCfiveTwo`, `\NTwoCfiveMedian` | −38.835(13) (median −38.83544, half range 0.01277) | C5^Wcs = raw (`c5_L300.npz`) + Wc shift (`results/eps5/dC5_L1000_all.npz`) + δ⁽³⁾(L)·S(L) (`large_L/results/tag3_L16000.npz`, `results/legw/legw_L1000.npz`); 15 no-log fits, tail ln⁰⁻³L/L + ln⁰⁻ᵏ²L/L², k2 = 0..2, Lmin 30..100 | R | 3 decimals; median to 5e-6 | FINAL |
| p2.c5_dev | `\HTpCfiveTwoDev` | 5×10⁻⁵ (4.6e-5) | median vs exact | R | 1 sig. digit | — |
| p2.c5_logshift | `\HTpCfiveTwoLog` (note) | 0.1 (b = ∓0.01 moves the limit by +0.100 / −0.102) | refits of C5^Wcs − b ln L | R | 1 sig. digit | caveat: \|b\| ≲ 0.01 not excluded at L ≤ 300 |
| p2.c5_blind | `\NTwoBlindNoLog`, `\NTwoBlindFreeLog` | 4.3×10⁻⁶ (no ln L) vs 9.4×10⁻⁶ (free ln L); k1 = 2 towers prefer a log | fit L ≤ 200, predict 202..300 | R | 2 sig. digits | — |
| p2.c5_bdrift | `\NTwoBfreeTwoHundred`, `\NTwoBfreeThreeHundred` | −0.011 (Lmax 200) → +0.004 (Lmax 300) | free-log fits (15) | R | 3 decimals | — |
| p2.c5_bspread | `\NTwoBfitMin`, `\NTwoBfitMax` | −0.05 … +0.07 | same, Lmax 300 | R | 2 decimals | — |
| p2.c5_null | `\NTwoBnull` | +0.0005 (same estimator on C4^W, which has no ln L); limit 5.04868 | `c5_L300.npz` raw C4 + W shift | R | 1 sig. digit; 5 decimals | — |
| p2.c5_calibration, p2.c5_bdrift_agent | `\NTwoBbias` (note: bias of the estimator, about 0.004) | −0.0036, −0.0136, −0.0336 for injected β = 0, −0.01, −0.03; agent's 12-fit b −0.0134 / +0.0054 | `residual_log/C4W_by_L.csv`, `c5_L300.npz` (protocol of `large_L/c5_fits300.py`) | R | 4 decimals | — |
| p2.c5_wc, p2.c5_wcs_minus_wc | `\NTwoCfiveWc`, `\NTwoCfiveWcMedian` | −38.830(13) (−38.8297); Wcs − Wc ≈ δ∞S∞ = −0.0058 | same protocol without δ⁽³⁾S | R | 3 decimals; 1e-3 | — |
| p2.c5_W_linear | `\NTwoCfiveWLin` | −0.0019 L (scheme W: shift −0.002329 L plus raw +0.0004 L) | `dC5_L1000_all.npz` (protocol of `eps5/classes_c5.py`); raw's +0.0004(4) L from the profile fit at L ≤ 160 (record string in `residual_log/WINDOW_SPEC.md`, status after the exact ε⁵ test, item 1, checked by the replay; HT_Pert note App. B.3, Table d2:tab:c5lin) | R | 6 decimals (shift) | — |
| p2.delta_lmax, p2.delta_min | `\NTwoDeltaLmax`, `\NTwoDeltaMin`, `\NTwoDeltaMinL` | 16000; −0.0159046 at L = 34 | `tag3_L16000.npz` | R | exact; 7 decimals | — |
| p2.delta_limit | `\NTwoDeltaIdent` (note Sec. 4.5: "δ⁽³⁾ → −4/(81π)") | free-limit fits within 7×10⁻¹¹ of −4/(81π) | same, basis 1, l/L, 1/L, l/L², 1/L², Lmin 200..2000 (+ blind fit 200..4000) | R | bound | identified numerically, not proven |
| p2.delta_lnL | (note) | ln L/L coefficient −1/(54π) = −0.0058946; 1/L coefficient 0.01386 | limit fixed | R | 5e-7; 5 decimals | — |
| p2.S_limit, p2.delta_S, p2.shift_lmax | `\NTwoSinf`, `\NTwoDeltaS`, `\NTwoShiftLmax` | 0.367187 (no ln L); −0.005772; 1000 | `legw_L1000.npz` | R | 6 decimals | — |

##### Descendant identities (note Sec. 4.6, App. C) and ε⁴, C6
| Check | Paper / note | Quoted value | Recomputed from | Cmd | Tolerance | Status |
|---|---|---|---|---|---|---|
| p2.ident2_W | note Sec. 4.6, `[ε²]v_n` with window: 0; `\NTwoRtwoWcoef` | restored; R₂(χ₁₁) ≈ 0.0114/L | `complete_exact/results/descendant_W_L*.json` (exact) | R | 4 decimals; all five spacings decrease | FINAL |
| p2.ident2_cons | `\NTwoRtwoCons` | 0.0243 (consistent window, L = 16, constant) | `descendant_consistent_L16.json` | R | 4 decimals | — |
| p2.ident3_chi | `\HTpTwoIdentThree` (note); note Sec. 4.6, single-quantum states | at least 95 % of the ε³ violation removed at L ≤ 16 (min 97.1 % over a = 1..3, L = 14, 16) | Wcs (`ce_wc/out_wcs`) vs Wc (`ce_wc/out_local`), exact | R | ≥ 0.95 | FINAL at finite L; removed as L → ∞ (p2.delta_limit, p2.ident3_wc) |
| p2.ident3_wc | `\NTwoRthreeWcConst` | R₃^Wc(χ_aa)/(a w_aa) ≈ 0.063 (limit 16/(81π)) | `ce_wc/out_local` L = 16 | R | within 1e-3 | — |
| p2.ident3_L16 | `\NTwoRthreeWcsSixteen`, `\NTwoRthreeWcSixteen` | −1.6×10⁻⁴; 0.0156 | L = 16 | R | 2 sig. digits; 4 decimals | — |
| p2.ident3_phi2 | note Sec. 4.6, φ² descendants "not settled"; `\NTwoPhiDescTwo`, `\NTwoPhiDescFour` | −0.057, −0.059 at L = 16 | `ce_wc/out_wcs` | R | 3 decimals | not settled |
| p2.eps4_R4slope | `\NTwoRfourSlope` | R₄(χ₁₁) grows 0.028 per unit ln L (Wc = Wcs) | `ce_wc/out_wcs`, `out_local`, L = 8..16 | R | 3 decimals | — |
| p2.eps4_chiwindow | `\NTwoGapTwo`, `\NTwoGapThree`; note Sec. 4.6 and App. C.5, `[ε⁴]v_n` "window not yet known" | χ₂₂ / χ₃₃ gaps closed 95 % / 90 % at L = 14; invariances exact | reruns `residual_log/fits/parent_check_p5/verify_p5.py` on `ce_wc/out_wcs4x`, `out_wcs4c`, `results/tag` | R | nearest per cent | partial (Wcs4chi) |
| p2.c5_k1 | `\NTwoCfiveKfourShift`, `\NTwoCfiveKfourHalf`, `\NTwoCfiveKfourTab`; note Table d2:tab:k1 | Table k1 (no-log towers T(k1, 1..2), Lmin 40/60/80; hold-out fit ≤ 240 → 242..300, limits from L ≤ 300): C4^W errors 6.1e-4 … 6.5e-8, C5^Wcs errors 1.2e-2 … 5.7e-7, limit − exact +0.81, +0.16, +0.015, −0.003, +0.012 for k1 = 0..4; the 15 fits of Eq. C5tower with k1 = 4: median −38.8334 (+0.002 from k1 = 3), half range 0.050 (k1 = 3: 0.013); Table-k1 towers: k1 = 3 → 4 moves the limit by +0.015 | `c5_L300.npz`, `dC5_L1000_all.npz`, `tag3_L16000.npz`, `legw_L1000.npz` (protocol of `large_L/c5_fits300.py` sec. 1) | R | 2 sig. digits; 3–4 decimals | tail-model sensitivity, not in \HTpCfiveTwo |
| p2.c5_calibration15 | `\NTwoBcorr`; `\NTwoBbias` | the same calibration with the 15 fits of `refit_c5_300` reads −0.0038 (12 fits: −0.0036), so "about 0.004 low" holds for both sets; bias-corrected median b: +0.0078 (15 fits), +0.0090 (12 fits) | `residual_log/C4W_by_L.csv`, `c5_L300.npz` | R | 4 decimals | judgement input, not a bound |
| p2.c6_identity | (note App. C.5 text) | variant A and the proxy W_cs4 have the same eps^4 window form with different coefficients; their C6 values give S(L) of `legw_L1000.npz` to 7.6e-15 (L = 6..14); δ⁽³⁾S₁ = +0.0018 … +0.0025; C6^A − C6^Wcs = −0.0256, −0.0268 at L = 14, 16 | `ce_wc/out_wcs4c`, `ce_wc/out_wcs4` (shipped since 2026-10-16), `ce_wc/out_wcs`, `results/legw/legw_L1000.npz` | R | 1e-12; 4 decimals | — |
| p2.c6_L16 | `\NTwoCsixSixteen`, `\NTwoCsixStep`; paper Table 2, d = 2 C6..C8 "n.r." | C6(16) = 165.35 … 165.39 in every Wc-family scheme; +7.5 per step at L = 16 (continuum 362.366) | `ce_wc` outputs, L = 14, 16 | R | range; 1 decimal | not reproduced |

Not replayed: `\NTwoCsixLog` (+0.010 ln L, a prediction from the size of the ε⁴ window, no data) and `\NTwoBbound`,
`\NTwoLneeded` (judgements from p2.c5_bdrift / p2.c5_bspread / p2.c5_calibration). The integrity checks
p2.snapshot (snapshot sha256) and p2.lprod (records to L = 34 seen from this package) run first in R.

### `lri_2d_coeff_independent_check`

Folder: `code/lri_2d_coeff_independent_check/`.

_see the first section of this dimension (one text for the dimension)._

## d = 3: exact C2..C5(L) sums and the coefficients C2..C8

### `lri_3d_c4_exact`

Folder: `code/lri_3d_c4_exact/`.

#### d = 3 perturbative HT (exact sums): every quoted number -> record, command, tolerance

Package `HT_Pert/code/lri_3d_c4_exact` (git ref `d5afa4f`). Every row is a check of `make -f public.mk replay` (run
from `code/lri_3d_c4_exact`; `public/replay_exact3d.py`), which prints the table and exits 1 on any FAIL. The fit
summaries are regenerated by the package's own scripts from the shipped `results/` before the numbers are read.
Quoted numbers: the paper at its final commit `a6772872`, Table 2 (`tab:htpert`, Sec. 3.1), d = 3 column, frozen
in `HT_Pert/results/HT_3d/quoted_numbers.json`; the rest from the HT_Pert note (d = 3 section).
Continuum values (paper Table 1, `tab:pt`): C2(3) = (2 + 4 ln 2 - pi)/9, C3(3) = -0.353581520433, C4(3) = 1.22806354532762307997,
C5(3) = -5.85035142075132722922.

| Check | Quoted (paper macro) | Value | Records | Rule / tolerance |
|---|---|---|---|---|
| CUTOFFS | `\HTpThreeLfour` = 600, `\HTpThreeLfive` = 40, `\HTpThreeLwin` = 8000 (Sec. 3.1 text, Table 2 caption; `\HTpThreeLwin` only in the note) | 600, 40, 8000 | `results/c4_L600.npz`, `c5raw_all_L40.npz`, `windows_L8000.npz` | largest L of each |
| C2-3D | `\HTpCtwoThree` = 0.181221785405554, `\HTpCtwoThreeDigits` = 15 | limit - exact = -1.4e-16 | `results/windows_L8000.npz` -> `fits/fit_summary.txt` | fit to L <= 8000 (tower L^-3/2..L^-7/2) equals (2 + 4 ln 2 - pi)/9 to 15 significant digits |
| C3-3D | `\HTpCthreeThree` = -0.353581479(20), `\HTpCthreeThreeDev` = 1e-7 | mean of +5.73e-8, +1.68e-8, +4.94e-8 | `results/c4_L600.npz` -> `fits/fit_summary.txt` | mean and half-range of the fits with Lmin = 100, 200, 300 (L <= 600), PDG rounding; delta of the mean to 1 digit. The Lmin = 300 fit moves by about 1e-9 between platforms, so the central value is checked to 1/10 of its uncertainty |
| C4-3D | `\HTpCfourThree` = 1.228070(21), `\HTpCfourThreeDev` = 5e-6 | median +6.35e-6 over 12 windows; range -7.3e-6 .. +34.1e-6 with the blind fit | `results/c4_L600.npz`, `offdiag_L8000.npz`, `dchi_L1000.npz`, `windows_L8000.npz` -> `fits/fit_summary.txt` | complete window W; tower T4, windows Lmin 80..300 x Lmax 500, 600; value = C4(3) + median, uncertainty = half-range including the blind fit, PDG rounding; delta = median / C4(3) to 1 digit |
| C4-BLIND | (HT_Pert note, C4 extrapolation) | 1.6e-8 | same | tower T4 fitted to L <= 400 predicts 402..600 to better than 1e-7 |
| C4-NODIV | (note; the paper: "with the truncation artifact corrected") | sqrt(L): b <= 6.5e-8 | same | A fixed at C4(3), one free sqrt(L) term: |b| < 1e-7 for Lmin = 100, 200, 300 |
| C5-3D | `\HTpCfiveThree` = -6.0 +- 0.3, `\HTpCfiveThreeDev` = 3e-2 (provisional, Table 2 caption) | median -6.005; +-0.31; delta abs(-6.0/C5(3) - 1) = 0.0256 | `results/c5raw_all_L40.npz`, `dC5_L600.npz`, `eps5/legw_L400.npz`, `C4_by_L.csv` -> `fits/fits5_summary.txt` | window Wc, towers A and D over 8 fit windows each (L <= 32, 40): median; uncertainty = their largest C4^W miss with the same towers at L <= 40 (0.036) over C4^W's remaining correction at L = 40 (0.147), times C5^Wc(40) - C5(3) (1.28); 1 decimal; delta of the quoted central value to 1 digit. Blind fits L <= 28, 32 predict to <= 2e-3 |
| C5-LHALF | HT_Pert note: "A term in L^-1/2 ... would lower the limit by 0.5 to 1" | tower C: -0.54 .. -1.00 | same | Wc tower C (with L^-1/2) over 8 windows, 1 decimal |
| VAL-PKG-C4 | (independent-code check; note) | 2.7e-13 (C4), 6.2e-13 (all) | `results/c4_L600.npz`; `../lri_3d_hpc/results/reference_coefficients_L14.json`; `../../data/HT_3d/pert3d/results` | `validate_pkg.py`: C2, C3, C4, r, g, seed energies vs the package at every even L <= 20, raw and consistent (22 cases): <= 1e-12 |
| VAL-PKG-C5 | (note) | C5 2.2e-13, C4 5.9e-14; brute force 4.3e-13 | `results/c5_L20.npz`, `results/brute` | `eps5/validate5.py`: raw and consistent C2..C5 vs the package (L <= 20); W2, W3m, Wb, Wc, Zb vs the brute force on the package operators (L <= 14): <= 1e-12 |
| FITS-REGEN, FITS-QUOTED | the shipped `fits/*.txt` | identical on the platform that wrote them; quoted lines within tolerance elsewhere | `results/` | the package's scripts regenerate the summaries; byte identity is informational, the quoted lines must agree (C2 5e-16, C3 2e-9, T4 0.2e-6, blind 1e-7) |

`make -f public.mk test` recomputes the sums from scratch at small cutoffs (windows to L = 400, C2..C4 to 40, C2..C5 in
every scheme to 12, shifts, brute force) and compares them with the shipped results, the package and the brute force
(`public/REPRODUCE.md`).

### `lri_3d_hpc`

Folder: `code/lri_3d_hpc/`.

#### d = 3 perturbative HT: every quoted number -> record, command, tolerance

Package `HT_Pert/code/lri_3d_hpc` (git ref `7c8a67e`); records `R = HT_Pert/data/HT_3d/pert3d` (Expanse campaign
`pert3d`; sha256 in `HT_Pert/data/HT_3d/MANIFEST.sha256`; results, gates and crosscheck byte-identical, campaign.json
and the stage records scrubbed, `HT_Pert/data/HT_3d/SCRUBBED.txt`); table `HT_Pert/results/HT_3d/SUMMARY.md`.
Every row is a check of `make -f public.mk replay` (run from `code/lri_3d_hpc`; `public/replay_pert3d.py`), which
prints the table and exits 1 on any FAIL. Check ids match the note's reproduction table.

Status (2026-10-19, paper final at `a6772872`): the paper prints none of these numbers. Its d = 3 values (Table 2,
`tab:htpert`, Sec. 3.1) come from `code/lri_3d_c4_exact` (its own `public/results_map.md`). The ratios, the cutoffs
and the L = 14 gate below were printed in earlier drafts; their macros are still defined, unprinted, in the paper's
`numbers.tex`, and they are kept as checks of the records. The HT_Pert note (d = 3 section) quotes the cutoffs and
the L = 14 gate. C4-RATIO is still read by `HT/` (the finite-coupling note's 60 %).

Continuum values C_n(3) (the denominators of the ratios) are those of the paper's Table 1 (`tab:pt`) and `GFF/note/README.md`:
C2..C5 exact, C6..C8 the reported estimators (33.57542664131543, -220.35448047392794, 1602.6052229663408).

| Check | Quoted (macro) | Value | Records | Rule / tolerance |
|---|---|---|---|---|
| CUTOFFS | `\HTpThreeLmax` = 20; "L = 16, 18, 20" (HT_Pert note; not printed in the paper) | 16, 18, 20 | `R/results/L{16,18,20}/c{L}_{raw,consistent}.json` | the cutoffs of the shipped results |
| RATIO-2 | `\HTpRatioTwoThree` = 0.995 | 0.99495 | `R/results/L20/c20_consistent.json` (`result.C[2]`) | C2(20)/C2(3), consistent scheme, rounded to 3 decimals |
| RATIO-3 | `\HTpRatioThreeThree` = 0.933 | 0.93286 | same (`C[3]`) | same |
| RATIO-4 | `\HTpRatioFourThree` = 0.603 | 0.60258 | same (`C[4]`) | same |
| RATIO-5 | `\HTpRatioFiveThree` = 0.577 | 0.57711 | same (`C[5]`) | same |
| RATIO-6 | `\HTpRatioSixThree` = 0.507 | 0.50745 (allowance of C6(3): 0.5074-0.5075) | same (`C[6]`) | same, with the central C6(3) |
| RATIO-7 | `\HTpRatioSevenThree` = 0.414 | 0.41362 (0.4134-0.4139) | same (`C[7]`) | same, with the central C7(3) |
| RATIO-8 | `\HTpRatioEightThree` = 0.378 | 0.37804 (0.3771-0.3790) | same (`C[8]`) | same, with the central C8(3) |
| C4-RATIO | `\HTnpDthreeCfourRatio` = 60 % (HT folder; read from SUMMARY.md by `HT/code/lri_3d_window_hpc`) | 60.26 % | same (`C[4]` = 0.7400078407092003721) | C4(20)/C4(3) in percent to 2 decimals = 60.26 |
| GATE-L14 | `\HTpThreeGateL` = 14, `\HTpThreeGate` = about 1e-14 (HT_Pert note, d = 3 checks; not printed in the paper) | max 1.25e-14 (raw 2.3e-15) | `R/gates/L{16,18,20}/{raw,consistent}_c14.json`; reference `code/lri_3d_hpc/results/reference_coefficients_L14.json` | each production store solved at L = 14 against the original code's results: reference bound by sha256; scaled error over C, r, g, all seed energies and subcutoff vacua recomputed (equal to the stored value within 1e-17), <= 5e-13 (tolerance of the run); maximum rounds to 1e-14 |
| TABLE | `HT_Pert/results/HT_3d/SUMMARY.md` (C2..C8, L = 16, 18, 20, raw and consistent) | 6/6 rows | `R/results/L*/c*_*.json` | every row equals the stored strings of `result.C[2..8]` exactly |
| RESIDUAL | SUMMARY.md: recursion residuals <= 4e-19 | max 5.1e-19 | the 6 results | `execution.residual_gate.value` <= 1e-16 (the run's limit) |
| CROSSCHECK-L16 | (SUMMARY.md, campaign gate) recurrence vs stationary | 1.1e-17 raw, 4.1e-16 consistent | `R/crosscheck/L16/*` | comparison records passed, bound by sha256 to both results; recomputed scaled difference <= 1e-15 |
| CROSS-STORE | SUMMARY.md: reproducibility ~1e-14 | max 9.8e-15 | `R/results/L20/c{16,18}_*.json` vs `R/results/L{16,18}/` | the L20 store re-solved at L = 16, 18 against the L16, L18 stores: scaled difference <= 5e-13 |
| REC-MANIFEST | records as produced | 194 files | `HT_Pert/data/HT_3d/MANIFEST.sha256`, `SCRUBBED.txt` | every record's sha256, files listed in SCRUBBED.txt excepted (never a result, gate or crosscheck record); nothing missing or extra |
| REC-SRC | code at `7c8a67e` | 12 records | results and gates | `request.source_sha256` equals the sha256 of the 8 shipped `code/` files |
| REC-CHAIN | store -> gate -> solve -> result | 6/6 | `R/records/L*/{verify,gate,solve}`, `R/campaign.json` | store manifest sha256 equal across verify, gate, solve records and the result and gate requests; release fingerprint of the campaign; cutoff, order 8, scheme |

`make -f public.mk test` additionally rebuilds an L = 14 vertex store from scratch and solves cutoffs 0..14 (both
schemes, both strategies, 32 cases) against the same reference within 5e-13: the note's L = 14 check rerun on the
reader's machine (`public/REPRODUCE.md`).

Not quoted and not replayed: `\HTpThreeStates` (182,727,113 bath states at L = 20, marked "not used" in the paper's
numbers.tex; it is `execution.vertex_metadata.full_bath_states` of `R/results/L20/c20_consistent.json`).
