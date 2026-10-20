# HT_Pert packages

What each package in `code/` contains and computes.

Assembled from the package authors' texts. Inside a package section, relative paths are relative to that package's folder `code/<package>/` unless they start with `HT_Pert/`. The values themselves are in `note/README.md` and the note.

- d = 1: exact C2..C5(Lambda) sums: `lri_1d_c4_exact`, `lri_1d_c5_exact`
- d = 1: thermal HT coefficients C2..C7 and the effective Hamiltonian: `lri_hpc_Hamitonian`, `lri_eh_hpc`
- d = 1: HT C8 and the complete-window coefficient flow: `lri_c8_hpc`, `lri_d1_full_coefficient_flow`, `lri_1d_dconn_refit`, `lri_d1_fullblock_tail_response`
- d = 2: coefficients C2..C8 and the independent check: `lri_d2_coeff_hpc`, `lri_2d_coeff_independent_check`
- d = 3: exact C2..C5(L) sums and the coefficients C2..C8: `lri_3d_c4_exact`, `lri_3d_hpc`

## d = 1: exact C2..C5(Lambda) sums

### `lri_1d_c4_exact`

Folder: `code/lri_1d_c4_exact/`.

#### lri_1d_c4_exact: exact finite-cutoff C4(Λ) of the d = 1 frozen-cutoff HT

The d = 1 perturbative Hamiltonian truncation (HT) with the frozen cutoff E^0 = ℓ + P/4 ≤ Λ gives the gap
Δ_ε(ε; Λ) = Σ C_n(Λ) ε^n. The HT solver reaches C4 only to Λ = 118 (`code/lri_hpc_Hamitonian`). This package
computes C4(Λ) exactly, with no truncated basis and no diagonalization, at every quarter cutoff up to Λ = 2000. It does
so by summing the fourth-order Rayleigh–Schrödinger expression over all intermediate-state patterns of the truncated
Hamiltonian.

**Method.**
- The zero mode is an oscillator with exact rational path amplitudes.
- The other modes enter through positive bundle series (V1 − 1)^n.
- Every four-vertex pattern is reduced to its even-parity density on the slice levels and summed in shells of the
  cutoff index m = max_s(4N_s + δ_s + n_s), which gives every quarter cutoff in one run.
- The tuning functionals (r, g, the gap) are applied as exact rational weights per key.
- The complete window D^conn of the paper (Eq. ht-Dconn) is added on the even grid:
  ΔC4 = fast(Λ) + shift4(Λ), with ΔR4 = H_odd(Λ−1)/2916 exactly.
- The method was ported from the d = 2 exact-C4 code (HT_Pert/code/lri_2d_coeff_independent_check).

**Validation (A1–A6 of the package's PLAN.md).**
- A1/A2: exact rationals at small cutoffs, to 2e-14.
- A3: brute-force Rayleigh–Schrödinger on explicit bases, 945 comparisons, to 8e-13.
- A4: the HT solver's raw and thermal C4 at Λ ≤ 118, |ΔC4| ≤ 1.4e-12.
- A5: the window pieces against the reconciled window table, 4e-16.
- A6: overlap between runs, ≤ 3.3e-13.

**Results.**
- **C2 and C3 of the paper** (Table htpert, d = 1). The exact C2(Λ), C3(Λ) at even Λ ≤ 2000 are fitted by a rule fixed
  before any fit was run (`public/c2c3_rule.py`, symmetry job 574918): free intercept; for C2 the bases Λ^{-j/2} with
  j ≤ 6 and j ≤ 8; for C3 the bases L1 and L1 + {Λ^{-2} log Λ, Λ^{-5/2}}; lo = 100, 200, 400. The quoted value is the
  median of the 6 fits ± their half-range. Result: C2 = 0.657131263984(10) (δ = 4e-12) and C3 = −3.7198563(10)
  (δ = 2e-8). This replaced the earlier values on 2026-10-14 by the author's decision; those had been the closest of
  20 fits to the exact value at Λ ≤ 98. The same rule at Λ ≤ 118 gives C2 = 0.65713127(4) and C3 = −3.71984(8).
- C4^Dconn(1000) = 37.8351012026 and C4^Dconn(2000) = 39.4111422825; the limit is C4 = 45.42488010356.
- Blind protocol: fits frozen from Λ ≤ 1000 before the Λ = 2000 run existed predict C4^Dconn(2000) to 4.0e-10. The fit
  basis is L2: Λ^{-1/2} log^{0..2}, Λ^{-1} log^{0..2}, Λ^{-3/2} log^{0,1}, Λ^{-2}.
- The frozen L2 intercept (lo 200) is 45.42494, and the refit on all data to 2000 gives 45.424924 (lo 200). Both
  deviate from C4 by about 5e-5 (1e-6 relative).
- The Λ^{-1/2} log² Λ coefficient is about −1.71.

##### Layout in the public tree
- `code/lri_1d_c4_exact/`: the package at commit fa23479; its production code equals the production snapshot
  (sha256 a8b57b2e… over 38 files, checked by `replay`). It adds:
  - `public.mk`, `public/`;
  - `fits/frozen/`: the blind records;
  - `fits/blind_check_L1000_to_2000.txt`;
  - `fits/explore/`: the refit.
- `data/HT_1d/exact_c4/a8b57b2e8475/`: the four production results `c4_1d_L{200,400,1000,2000}.npz` with their gate
  records `gates_L*.txt` (3.2 MB).

##### Targets (run from `HT_Pert/code/lri_1d_c4_exact`)
| Command | What | Time |
|---|---|---|
| `make -f public.mk test` | fast unit tests, A1/A2, A3 to cut4 = 48 | about 10 s |
| `make -f public.mk replay` | `public/replay_c4.py`, rows x4.* (see `results_map.md`), including the C2/C3 rule rerun | a few minutes (mpmath fits) |
| `make -f public.mk replay-quick` | the same without refits (the C2/C3 rows read the record of job 574918) | seconds |
| `make -f public.mk smoke` | production path at Λmax = 40 vs the shipped L200 result, ≤ 1e-12 | about 1 min |

### `lri_1d_c5_exact`

Folder: `code/lri_1d_c5_exact/`.

#### lri_1d_c5_exact: exact finite-cutoff C5(Λ) of the d = 1 frozen-cutoff HT

This package extends `../lri_1d_c4_exact` to fifth order: exact C5(Λ) at every quarter cutoff to Λ = 500, with the
complete window D^conn on the even grid. The HT solver reaches C5 only to Λ = 118.

**Method.**
- The fifth-order Rayleigh–Schrödinger assembly is generated by `rs5.py`, the d = 2 generator, vendored verbatim. It
  has 221 terms and 89 canonical chains, with two to five vertices.
- Vertices carry ε-Taylor coefficients, distributed over the bundles by Leibniz' rule, with two-ended ε-jets of the
  line series.
- Empty slices factorize.
- The five-vertex densities use a middle-split streaming kernel (`lib5/kernel5.py`, BLAS-bound, about 0.12 N⁵
  multiply-adds).
- Window at ε⁵: ΔC5 = T1 + T2 + T3 + T4 − 2·fast + 2C2(3A4 − B4) − B5/3, with ΔR5 in closed form and a
  cancellation-free engine form that agree to 1e-15.

**Validation.**
- A1/A2: exact rationals.
- A3: brute-force RS to cut4 = 128, with order-5 floor 1 (logged deviation: float64 roundoff of a few 1e-12 at
  cut4 = 4).
- A4: the HT solver's C5 at Λ ≤ 118, |ΔC5| ≤ 1e-11.
- A5: the window pieces against the reconciled window table, gated against the exact identity on its A4/B4 (logged
  deviation: the table's rows4 column carries about 6e-12 fit noise).
- A6:
  - the jets against mpmath to 1e-13;
  - densities against the dense reference;
  - orders 2–4 against lri_1d_c4_exact to 1e-12;
  - overlaps between rungs ≤ 5.7e-12 (the data noise floor is about 1e-11).

**Results.**
- C5^Dconn(400) = −506.619063805112 and C5^Dconn(500) = −519.770442010804, against C5 = −731.1394766 (29 % of the
  tail left at Λ = 500).
- ΔC5 = C5^Dconn − C5^raw tends to a constant ≈ 0.72.
- **Blind protocol.** Fits frozen from Λ ≤ 320 predict Λ ≤ 400 to 1e-9 (L2) and Λ ≤ 500 to 1.5e-8. Fits frozen from
  Λ ≤ 400 predict 400 < Λ ≤ 500 to ≤ 3e-9.
- **Free intercepts.** −730.85 (L2, biased) and −731.08 to −731.13 (M3, with log³), i.e. ±0.3.
- **With the intercept fixed to C5**, the M3 basis fits at the noise floor. Its log³ coefficient is c13 ≈ 1.95–2.04,
  which equals −(7/2)/3 times the C4 log² coefficient.
- **Constrained extrapolation** (log³ fixed by the exponentiated tail; `fits/constrained_c5.py`): −731.147, −731.140
  and −731.136 for the three best-conditioned fits.
- **Cited checks** (`fits/explore/constrained_L500/xchk/`): a blind re-implementation of the constrained fit gives
  −731.13 ± 0.10, and a theory check derives c_n(top) = a2(−7/2)^{n−2}/(n−2)! with a2 = −40/(81√π).

##### Layout in the public tree
- `code/lri_1d_c5_exact/`: the package at commit 9ff34dc. Its production code equals the production snapshot
  (sha256 040d92b3… over 53 files, checked by `replay`). Later commits add only `fits/` records and analysis scripts.
  The package also carries `public.mk` and `public/`.
- `data/HT_1d/exact_c5/040d92b3bd1d/`: the six production results `c5_1d_L{80,160,240,320,400,500}.npz` with their
  gate records (2.7 MB).
- Also needed:
  - `../lri_1d_c4_exact`, for the regression test;
  - `data/HT_1d/exact_c4`, the reference of the A6e gate and the input of the constrained fit.

##### Targets (run from `HT_Pert/code/lri_1d_c5_exact`)
| Command | What | Time |
|---|---|---|
| `make -f public.mk test` | fast unit tests (`public/run_tests_c5.py`), A1/A2, A3 to cut4 = 32, window closed forms to Λ = 400 | about 2 min, 4 cores |
| `make -f public.mk replay` | `public/replay_c5.py`, rows x5.* | about 5 min on a 64-core node |
| `make -f public.mk replay-quick` | the same without the mpmath refits | seconds |
| `make -f public.mk smoke` | production path at Λmax = 24 vs the shipped L80 result, ≤ 1e-11 | about 10 min, 16 cores |
| `make -f public.mk fetch-data` | downloads the raw per-fit results of the blind re-implementation (one archive, 28 MB, 71 MB unpacked) from the Zenodo data record (DOI 10.5281/zenodo.23466766), with sha256 checks (DATA); not needed by test or replay | download time; seconds |

## d = 1: thermal HT coefficients C2..C7 and the effective Hamiltonian

### `lri_hpc_Hamitonian`

Folder: `code/lri_hpc_Hamitonian/`.

#### lri_hpc_Hamitonian: d = 1 frozen-cutoff perturbative HT, solver, Expanse records and analysis

The d = 1 perturbative Hamiltonian truncation (HT) keeps the Fock states with free energy E⁰ = N + P/4 ≤ Λ (frozen
cutoff), tunes the couplings r(ε), g(ε) order by order with the two exact relations Δ_φ = (1−ε)/4 and
Δ_{φ³} = 1 − Δ_φ, and expands the thermal gap as Δ_ε(ε; Λ) = Σ C_n(Λ) εⁿ. This package holds:

- **the solver** `lri_hpc/` (lri_hpc 1.0.0; Numba float64, exact ranked Fock basis, formal-jet Rayleigh–Schrödinger
  recursion through ε³ and Rayleigh-quotient components through ε⁷). Written by OpenAI GPT-6 astra (via ChatGPT) and
  supplied by the author as `lri_hpc_optimized.zip` (with `reference/`, `tests/`, `benchmarks/`); reviewed, gated and
  given the Expanse layer by Claude Code (`PROVENANCE_lri_hpc_Hamitonian.md`). Source fingerprint c0c30783db5dd9a1…
  (sha256 over the sorted `lri_hpc/*.py` names and bytes); every production record carries it;
- **the Expanse production** of 2026-09-29..10-01 (records in `data/HT_1d/thermal_expanse/`): thermal C0..C7 at every
  even Λ = 52..118, φ⁶-gap degree 5 at Λ = 52..160 and degree 3 at Λ = 136..832 (608 not run); about 1180 core-hours
  on SDSC Expanse (2 TB nodes for thermal Λ ≥ ~96);
- **the supplied Λ ≤ 50 data** and the original joint φ⁶/C7 analysis in `analysis_original/` (written by OpenAI GPT-6
  astra (via ChatGPT), supplied by the author as `lri_phi6_joint_C7_results.zip`);
- **the perturbative analysis** in `analysis/`:
  - `extended/`: the joint tail model (frozen model code of `analysis_original`), fits on all data, the pre-registered
    protocol generator `write_updated_results.py` and its output `UPDATED_RESULTS.md`, the exploratory lower-edge study;
  - `identity_checks/`: descendant identities through ε⁴, the closed-form top-level sums (`top_a.jsonl`) and the
    top-level shift limit 0.0186910, the cutoff-placement test at Λ = L + ¼, ½, ¾, 1¼ (two engines A and B plus a
    reconciler and two challenge workflows);
  - `eps5_window/`: the complete vacuum window D^conn through ε⁵ (engines A and B, exact rationals, the independent
    engine `challenge-num/ht5.py`), the table `reconcile/dC_reconciled.json` (ΔC4, ΔC5 at every even Λ = 2..128 and at 136, 144, 152), the
    corrected refits `reconcile/refit_rc.json` and `challenge-theory/freelead2.json`, and the ε⁵ identities;
  - `eh_review/physics-impact/{d5_all,d7_all}.json`: the isolated g²D shifts per cutoff made with `lri_eh`
    (`code/lri_eh_hpc`) through `gen_deltas.py`; the rest of that review folder is not shipped.

The numbers it backs are quoted in the HT_Pert note, under the paper's macro names (`numbers.tex`, `\HTp…`) or the
note-only macros (`\NOne…`), and listed in `results_map.md`: reach and size (`\HTpLamThermal` 118, `\HTpStatesMax`
3.5×10⁹, `\HTpRawFracFour` 67, `\HTpRawFracSeven` 44), the window (`\HTpWinCfour` 0.080, `\HTpWinCfive` 0.71,
`\HTpWinCfourInf` 0.0803), the extrapolations (`\HTpRawOffsetFour` 0.19, `\HTpOmegaThree` 556, `\HTpOmegaThreeEff`
380–430), the protocol verdict "unresolved", the checks (`\HTpEngineAgree` 10⁻¹¹, `\HTpIdentThree` 0.003,
`\HTpIdentFour` 96–100, `\HTpIdentFive` 0.1–0.2, the cutoff-placement test, W/54 at ε²) and the C2 tail amplitude
−40/(81√π). The solver-fit C4 and C5 are note-only since 2026-10-14: the bases A–F part of `\NOneCfourSolver`
(45.415–45.420), `\NOneCfivePre` (2×10⁻³) and the freed-tail part of `\NOneCfiveSolver` (−731.36 to −730.97). The
paper's d = 1 HT C4 and C5 (`\HTpCfourOne` 45.4249(9), `\HTpCfiveOne` −731.13(10)) come from the exact sums of
`code/lri_1d_c4_exact` and `code/lri_1d_c5_exact`, not from this package.

**Every extrapolation beyond C3 in this package is post hoc** (windows and bases chosen after the solver data were
seen); the pre-registered protocol ended **unresolved**. These status words are part of the result. (The exact-sum
extrapolations of `code/lri_1d_c4_exact` and `code/lri_1d_c5_exact` have their own rules and status.)

##### Layout in the public tree
- **`code/lri_hpc_Hamitonian/`** (773 files with the overlay, 11.9 MB): the repository at commit c55d134 (`git archive`, so untracked files
  never ship), without the duplicate zip, the review folders `analysis/stress_test/` and `analysis/eh_review/` (except
  `physics-impact/{d5_all.json, d7_all.json, gen_deltas.py, dc4_exact.json}`), the raw workflow journals and summaries,
  run logs and superseded engine-B runs (`entries_lri_hpc_Hamitonian.json`, `not_exported`). `public.mk` and `public/`
  are added.
- **`data/HT_1d/thermal_expanse/`** (112 files, 269 KB): `thermal_d7/` (34), `phi6_d5/` (44), `phi6_d3/` (33) and
  `campaign/plan.json`.
- Shared with other HT_Pert packages at fixed paths (byte-identical; replay row `a1.code` checks the sha256 that other
  records bind): `analysis/eps5_window/reconcile/{dC_reconciled.json, dC_reconciled.csv, refit_rc.json}`,
  `analysis/eps5_window/challenge-theory/freelead2.json`, `analysis/eh_review/physics-impact/{d5_all,d7_all}.json`,
  `analysis/extended/{thermal_new.json, C7_extension.json, prior_c7/C7_completed_runs.json}`,
  `analysis/eps5_window/B/{top5.jsonl, exact5_c*.json}`, `analysis/eps5_window/reconcile/exactL2/exact5_c*.json`.
- **Needs** `code/lri_eh_hpc` (sibling): `lri_eh/exact.py` gives K, and `lri_eh` is imported by the re-pointed analysis.

##### Targets (run from `HT_Pert/code/lri_hpc_Hamitonian`)
| Command | What | Time |
|---|---|---|
| `make -f public.mk test` | identity check, engine smokes, `tests/run_all.py` (11 scripts) on a copy, validation regression V | 2.5 min, 4 cores |
| `make -f public.mk replay` | `public/replay_hpcham.py`, rows `a1.*` (`results_map.md`): 16 analysis scripts rerun on a re-pointed copy, every quoted number recomputed | 25 s |
| `make -f public.mk smoke` | production items thermal d7 Λ = 52, 60, φ⁶ d5 52, d3 136 rerun and compared with their records (bitwise on symmetry) | 1.5 min, < 5 GB |
| `make -f public.mk replay-full` | top-level sums at 108 cutoffs and the independent engine at Λ = 6..28 regenerated; shift4 limit and engine agreement recomputed | 30 min, 8 threads |

**Re-pointing.** About 50 analysis scripts were run in an agent session's temporary directory and still name its
absolute paths (`<TMP>/scratchpad/{eps5, identity, eh_review}`, `<PROJECT>/lri_hpc_Hamitonian/...`,
`<PROJECT>/lri_eh_hpc/lri_eh`) and an unarchived `pkg/` copy. `public/repoint.py` copies `analysis/`,
`analysis_original/` and `lri_hpc/` to `.work/tree/`, rewrites those prefixes in the copy (original or scrubbed token
form), puts `lri_hpc` and `lri_eh` on `PYTHONPATH`, and, with numpy ≥ 2.4 only, replaces one `float()` of a one-element
array in `identity_checks/reconcile/refit_corrected.py` (line 38) by `.item()` of the same array (identical value). The
shipped files are never modified. The mapping is the one of the HT note's appendix "Temporary paths".

Generic Slurm templates with placeholders: `public/slurm/item.sbatch` (one production item; it lists the measured RSS
and time per cutoff) and `public/slurm/acceptance.sbatch` (test, replay, smoke of this package and `code/lri_eh_hpc`).

**New public scripts** (the analysis printed these numbers only into workflow summaries that are not shipped):
`public/omega3_eff.py` (ω₃,eff of the free-exponent and E+zh fits, JSON), `public/engine_agree.py` (engine B full
basis vs pipeline, and the independent engine vs the reconciled table), `public/count_states.py` (independent count
of the frozen-cutoff basis).

### `lri_eh_hpc`

Folder: `code/lri_eh_hpc/`.

#### lri_eh_hpc: the isolated g²D vacuum-window add-on (lri_eh 0.2.0) of the d = 1 HT

In the d = 1 frozen-cutoff HT (`code/lri_hpc_Hamitonian`) a disconnected vacuum bubble inside a basis state only sees
the energy budget left by the other quanta. Its leading part is the diagonal operator g(ε)² D(ε),
D_i(ε) = −1/6 Σ_{m even, m+1 ≤ Λ < m+1+E⁰_i} (2−2ε)_m / (m! (m+1−ε)). This package computes the effect of that one
term on the thermal coefficients, with both gaps retuned, by an exact perturbative response (no difference of two
seventh-order spectra), and evaluates its fourth-order part in closed form. It is **not** the complete window D^conn
of the paper; the complete window is built in `code/lri_hpc_Hamitonian/analysis` (identity checks and ε⁵ window), which
uses this package for its g²D part.

What the HT_Pert results take from it:
- `lri_eh/exact.py`: the exact isolated shift ΔC4(g²D)(Λ) = 485/8748 + Σ_{n even} [v_n A(n) + B(n)] (exact rationals,
  and a float version `fast`), and its finite part **K = 0.0616119308426799**
  (`renormalized_constant`, mpmath at 60 digits), with ΔC4(g²D) ≈ log Λ/17496 + K − 16/(2187√(πΛ)) − 1/(243Λ).
  K enters `\HTpWinCfourInf` = K + 0.0186910 = 0.0803 (row `a1.win4inf` of `code/lri_hpc_Hamitonian`).
- the solver `lri_eh.numerics.compute`: it made the g²D tables
  `code/lri_hpc_Hamitonian/analysis/eh_review/physics-impact/d5_all.json` (degree 5, Λ = 4..118) and `d7_all.json`
  (degree 7, Λ = 4..90), the g²D input of the complete window table `dC_reconciled.json` and of every corrected refit.
- `code/lri_1d_c4_exact` vendors `lri_eh/exact.py` verbatim as `vendor/exact_fast.py`.

**Provenance:** written by OpenAI GPT-6 astra (via ChatGPT), supplied by the author as
`lri_effective_hamiltonian_campaign_update.zip` (sha256 3a480805…); used and reviewed by Claude Code
(`PROVENANCE_lri_eh_hpc.md`, `REVIEWS.md`).

**Scope (the package's own words):** the isolated correction keeps the log Λ/17496 term; the connected and folded
matching terms are missing, so it is not a physical effective Hamiltonian and not a continuum extrapolation.

##### Layout in the public tree
- **`code/lri_eh_hpc/`** (103 files + `public.mk` and 4 files in `public/`, 108 files, 0.39 MB): the unmodified folder (not a git repository),
  without `__pycache__/` and `.DS_Store`. `MANIFEST_SHA256.json` binds 102 files; `BUILD_INFO.json` binds the source
  fingerprint 2e2e8ca8… (sha256 over `lri_eh/**/*.py`) and the supplier's sealed validation receipt
  `benchmarks/validation_local.json` (payload sha256 648fa9fb…).
- Cross-folder input: `../lri_hpc_Hamitonian/analysis/eh_review/physics-impact/{d5_all.json, d7_all.json,
  gen_deltas.py, dc4_exact.json}` (rows SKIP without it).

##### Targets (run from `HT_Pert/code/lri_eh_hpc`)
| Command | What | Time |
|---|---|---|
| `make -f public.mk test` | manifest (102 files), `scripts/verify_package.py`, and `scripts/validate_release.py` on a copy (pytest, 32 tests; gated degree-7 smoke at cutoff 20; sealed receipt) | about 35 s, 4 cores |
| `make -f public.mk replay` | `public/replay_eh.py`, rows `a1.eh.*` (`results_map.md`): integrity, K, exact ΔC4 vs the g²D tables, supplier benchmark | about 3 s |
| `make -f public.mk smoke` | g²D tables regenerated at small cutoffs (degree 5 Λ = 4..20, degree 7 Λ = 4..12) and compared | about 15 s |
| `make -f public.mk replay-full` | the whole g²D tables regenerated (degree 5 Λ = 4..118, degree 7 Λ = 4..90) and compared | 12 min, 8 threads |

## d = 1: HT C8 and the complete-window coefficient flow

### `lri_c8_hpc`

Folder: `code/lri_c8_hpc/`.

#### lri_c8_hpc: eighth-order coefficients of the d = 1 frozen-cutoff HT, Λ = 52..92

The d = 1 perturbative Hamiltonian truncation (HT) with the frozen cutoff E⁰ = N + P/4 ≤ Λ gives the gap
Δ_ε(ε; Λ) = Σ C_n(Λ) εⁿ at each even cutoff. The thermal solver (`code/lri_hpc_Hamitonian`) reaches C7 at Λ ≤ 118.
This package computes C0..C8 at every even Λ = 52..92 for two prescriptions:
- **raw**: the truncated Hamiltonian as it stands;
- **vacuum_only**: raw plus the isolated g²D vacuum term only. This is not the complete window D^conn of the HT_Pert
  note.

**Where the numbers are quoted.** The HT_Pert note quotes the reach **Λ = 92 for C8** (`\HTpLamCeight`, numbers.tex)
and carries this package's rows in its reproduction table. The campaign facts, its validation and the C8 data table are
as printed in the LRI HT note (`LRI_HT_note`). The paper's HT section was removed from main.tex on 2026-10-14. Until the
author decides where it goes, cite the HT_Pert note, with the macro name and the row ids of this package (`c8.reach`
etc.), as the place these numbers are quoted. The C8 extrapolations (`\HTpCeightOne` and its ranges) are
fits to these data and live in `code/lri_1d_dconn_refit`. Every C8 fit reads its data through
`data/HT_1d/c8/extrapolation/data.json`, which ships here.

**Method.**
- The method is the original eighth-order solver: formal-jet Rayleigh–Schrödinger recursion with coupling tuning
  through ε⁸. It keeps the same caps on the full support, P ≤ 19 and Q ≤ 16.
- The solver here is a performance rewrite of that code. It stores wavefunctions only through order three, in a
  P ≤ 15, Q ≤ 12 core.
- It recovers the eighth-order effect of the fourth-order wavefunction exactly, through a scalar free-resolvent
  quadratic form on the full support. The extra states therefore still enter the residual explicitly.
- Arithmetic is float64, with fastmath off.
- See `docs/ALGORITHM.md` of the package. The coefficients are the same as the original's; nothing physical is added.

**Production on symmetry defq** (Xeon Gold 6148, Python 3.11.4, numpy 1.24.3, numba 0.57.0):
- validation job 569659;
- production array 569698, campaign 654fb90d19a573c1: 42 items (21 cutoffs × 2 prescriptions), one exclusive node
  per item;
- every lane ran once and was accepted with exit 0;
- 8605.5 s of solver time in total; peak RSS 107 GiB (Λ = 88, stored backend).

**Results.**
- C8^raw(92) = 2883374.2546683108 and C8^vac(92) = 2883433.2067096015.
- Every output satisfies: shell residual ≤ 1.6e-14, low-order residual ≤ 7.9e-13, tuning residual ≤ 1.95e-9.
- The original solver agrees with the rewrite at Λ = 60 (validation receipt) to max |ΔC| = 2.0e-8 (raw) and 7.5e-9
  (vacuum_only). On the cluster that is the only direct comparison with the original solver beyond Λ = 50.
- For Λ = 52..92 the evidence is the internal gates plus one cross-check: raw C0..C7 agree with the separate thermal
  campaign of `lri_hpc_Hamitonian` (same `lri_hpc` core; different driver, cluster and runs) to 6.1e-14 relative over
  all 46 common cutoffs Λ = 2..92 (2.1e-14 for Λ = 52..92 alone).
  - The shared core: `src/lri_c8/_core/{basis,cache,kernels,operators,parallel}.py` are byte-identical to `lri_hpc/`
    of `lri_hpc_Hamitonian`, and `_core/solver.py` (whose helpers the C8 engine calls) is its baseline version; see
    `PROVENANCE_lri_c8_hpc.md`.
  - So the cross-check tests the eighth-order driver, the assembly and the runs (for Λ = 52..92: symmetry vs Expanse).
    It does not test the Fock-space and operator construction, which both codes share.

##### Layout in the public tree
- **`code/lri_c8_hpc/`**: the package at commit 529f208, all 165 tracked files.
  - The source digest of `src/lri_c8` is dd811aca…. It is recorded in every record, so nothing may be added under
    `src/`.
  - `public.mk` and `public/` are added.
  - `inputs/` holds the 38 original runs (Λ ≤ 50) of the supplied archive.
  - `reference/` holds the original solver.
- **`data/HT_1d/c8/`** (92 files, 1.2 MB):
  - `c8_L52-92/accepted/`: the 42 outputs;
  - `c8_L52-92/journals/654fb90d19a573c1/`: the 42 lane journals;
  - `c8_L52-92/submissions.txt`;
  - `campaigns/c8_L52-92.json`;
  - `exports/`: the two flat exports and their provenance sidecars;
  - `validation/receipt_dd811aca899543c4.json`;
  - `extrapolation/data.json`: sha256 ccc77dfa…, the C8 extrapolation input, shared with other packages.

##### Targets (run from `HT_Pert/code/lri_c8_hpc`)
Times are for the default `THREADS=4` on one exclusive node: Intel Xeon Gold 6148 (symmetry defq, job 575032) and AMD
EPYC 7543 (symmetry amdq, job 575138). Peak memory from job 575138.

| Command | What | Time |
|---|---|---|
| `make -f public.mk test` | manifest (164 files, `public/SCRUBBED.txt` honoured); pytest (74 tests, Numba threading layer pinned) and the 38-point saved-grid replay on a copy in `.work/tree` | 6 min Intel (4 min on the production stack), 4.4 min AMD; 1.2 GiB |
| `make -f public.mk replay` | `public/replay_c8.py`, rows `c8.*` (see `results_map.md`); standard library only | about 1 s |
| `make -f public.mk smoke` | production item Λ = 52, raw and vacuum_only, rerun and compared with the shipped outputs (bitwise on both tested stacks and on both CPUs) | 1.2 min Intel, 0.9 min AMD; 1.6 GiB |
| `make -f public.mk replay-full` | export rerun (byte-identical exports and sidecars) and the original-solver comparison at Λ = 60 | 13 min Intel, 9 min AMD; 8.6 GiB |

A production rerun needs a working copy with a rehashed manifest: `public/rehash_manifest.py` (REPRODUCE, section 5,
step 0).

The `c8.datajson` row rebuilds `data.json` with `public/build_data_json.py`. It reads the thermal records of
`code/lri_hpc_Hamitonian/analysis/extended/` (make variable `THERMAL`). When they are absent, the row checks only the
raw and vacuum_only tables and reports SKIP.

### `lri_d1_full_coefficient_flow`

Folder: `code/lri_d1_full_coefficient_flow/`.

#### lri_d1_full_coefficient_flow: complete-window coefficients C0..C8 of the d = 1 HT to Λ = 72 (S10)

The d = 1 perturbative Hamiltonian truncation (HT) with the frozen cutoff E0 = N + P/4 ≤ Λ (docs/METHOD.md) gives the
gap Δ_ε(ε; Λ) = 1/2 − ε/6 + Σ_{n≥2} C_n(Λ) ε^n. The complete vacuum-window correction D^conn of the HT_Pert note
restores, once per disconnected vacuum bubble, the bubbles that the cutoff removes from excited states but keeps in the
vacuum. The exact window shifts ΔC4, ΔC5 are known in closed form (code/lri_hpc_Hamitonian). This package, called S10
in the notes, computes the full D^conn coefficients C0..C8 numerically at every even cutoff, so the window is exact through
ε^8 up to the largest computed cutoff, Λ = 72 (`\HTpWinLamEight`).

**Method** (docs/METHOD.md).
- The coefficients come from an exact half-order Rayleigh quotient of the truncated Hamiltonian, with "ragged"
  storage of the sub-cutoff vacuum problems (each state carries the vacuum bubbles of energy up to Λ − E_s).
- Float64 wave coefficients and sparse operations, with some scalar sums accumulated in long double. No amplitude is
  pruned; a state guard (`--max-states`) stops a run before it outgrows memory.
- `tests/exact_stationarity.py` checks the quotient order in exact Fraction arithmetic;
  `tests/independent_coefficients.py` compares fresh runs at L ≤ 28 with the vendored ordinary and exact-Fraction
  references (scaled error < 1e-10).

**Two layers.**
- The supplied archive (lri_1d_full_coefficient_cutoff_flow.zip, OpenAI GPT-6 astra via ChatGPT, supplied by the
  author; its `vendor/` and `inputs/` come from three earlier archives by the same model, see PROVENANCE): the engine,
  the archive records at L = 2..44 (`results/new_coefficients/`), forecasts frozen from older data, and exploratory
  leading-polynomial probes. Its README states that the analytic large-Λ leading polynomials
  of C6, C7, C8 are **not** completed.
- The symmetry extension (Claude Code, 2026-10-08, approved by Codex in round 4): cutoffs above 44 on exclusive
  180 GB defq nodes. It adds a state-guard option, exclusive output locks, atomic writes, a provenance block,
  `code/compare_archive.py`, the production gate `code/check_validation.py`, `slurm/` and `SYMMETRY_EXTENSION.md`.
  **The numerics are unchanged**: bitwise identical to the baseline at L = 8, 16, 20, and the archive records
  reproduced to ≤ 1e-12. The production gate (validation job 571525) reproduced the archived L = 40, 42, 44
  records to 5.3e-15 in C.

**Results** (data/HT_1d/s10_production, symmetry, 2026-10-08; quoted in the HT_Pert note under the macros named here).
- Complete D^conn C0..C8 at L = 46, 48, ..., 72. At L = 72: 109,373,212 states, 11.7 h and 117 GiB on one node.
- The window shifts dC_k = C_k^Dconn − C_k^raw at L = 72 are dC6 = +1.1717361, dC7 = −1.828185 and dC8 = −8.5641
  (`dconn_minus_raw_L46_72.csv`, last row).
- They reproduce the exact ε^4 and ε^5 windows of `dC_reconciled.json` at L = 46..72 to 4.3e-13 (dC4) and
  2.0e-11 (dC5) (`\HTpSTenMatch`). C0..C3 are unchanged by the window to 1.1e-13.
- The S10 values at L = 46..72 carry a small numerical noise, about 1e-13 relative (rms 3.95e-10, 1.34e-8, 2.32e-7
  on dC6, dC7, dC8). It is handled in the refits (code/lri_1d_dconn_refit, row rf.noise).
- Beyond L = 72 the refits continue dC6..dC8 with the delta-v1 model, validated blind on L = 46..72
  (code/lri_1d_dconn_refit, row rf.blind).

##### Layout in the public tree
- `code/lri_d1_full_coefficient_flow/`: the s10_extend repository at commit fec60a2 (86 files, 1.3 MB), verbatim,
  plus `public.mk` and `public/`:
  - `public/verify_manifest_public.py`: MANIFEST.sha256 check that honours `public/SCRUBBED.txt`;
  - `public/run_tests_s10.py`: the package's tests on a run-time copy;
  - `public/fresh_s10.py`: fresh small runs and the validation rerun;
  - `public/make_dconn_minus_raw.py`: regenerates the L = 46..72 dC table (no script had been kept);
  - `public/replay_s10.py`: the replay.
- `data/HT_1d/s10_production/`: the 14 production records `dconn_L<L>_d8.json` and `dconn_minus_raw_L46_72.csv`
  (420 KB).

##### Targets (run from `HT_Pert/code/lri_d1_full_coefficient_flow`)
| Command | What | Time |
|---|---|---|
| `make -f public.mk test` | manifest; tests/run_all.py on a copy (results compared order-insensitively, 1e-12); fresh Dconn run L = 2..24 vs the archive (rtol 1e-10) | about 2 min, one core |
| `make -f public.mk replay` | `public/replay_s10.py`, rows s10.* (see `results_map.md`) | seconds |
| `make -f public.mk smoke` | the production gate's validation: Dconn L = 40, 42, 44 and raw L = 44 vs the archive (rtol 1e-10) | 10–13 min, one core, 2.4 GiB |

### `lri_1d_dconn_refit`

Folder: `code/lri_1d_dconn_refit/`.

#### lri_1d_dconn_refit: d = 1 large-Λ limits of C4..C8 with the complete window (refits "S1B", 2026-10-08/09)

The frozen-cutoff HT coefficients C_n(Λ) converge slowly. Their large-Λ limits are extracted by tail fits on the
**fully corrected** sequences C_n^corr(Λ) = C_n^raw(Λ) + dC_n(Λ), where dC_n is the complete vacuum-window shift D^conn
(defined in the HT_Pert note). This package holds the code and outputs of the refits whose C4..C8 values the HT_Pert
note quotes:
- C6..C8 under `\HTpCsixOne` … `\HTpCeightOneUncal`;
- the solver-fit C4 and C5 ranges under the note-only macros `\NOneCfourSolver`, `\NOneCfourSolverDev`,
  `\NOneCfiveSolver` and `\NOneCfiveSolverDev`. The paper's C4 and C5 (`\HTpCfourOne`, `\HTpCfiveOne`) come from the
  exact sums instead (`code/lri_1d_c4_exact` row x4.c4, `code/lri_1d_c5_exact` row x5.c5).

The refits ran on 2026-10-08/09, after the S10 cluster run made dC6..dC8 exact to Λ = 72.

**Inputs** (all shipped elsewhere in HT_Pert, read by sha256-checked path):
- raw C0..C7 (thermal HT, every even Λ ≤ 118) and raw C8 (Λ ≤ 92): `data/HT_1d/c8/extrapolation/data.json`, with the
  g²D tables `d5_all.json` and `d7_all.json` of `code/lri_hpc_Hamitonian`;
- exact dC4, dC5 at every Λ: `dC_reconciled.json/.csv` of `code/lri_hpc_Hamitonian`;
- exact dC6..dC8: the S10 archive at Λ ≤ 44 (`code/lri_d1_full_coefficient_flow/results/whole_model_coefficients.csv`)
  and the S10 production at Λ = 46..72 (`data/HT_1d/s10_production/dconn_minus_raw_L46_72.csv`).

**Four stages** (Claude Code subagents of one workflow; no Codex review):
1. **Delta model** (`delta/`). It continues dC6..dC8 beyond Λ = 72 with the delta-v1 rule: an ensemble of fits to dC_k
   on the exact points (91, 77 and 80 kept fits of 116 for k = 6, 7, 8). Each modelled point carries an envelope
   (`dC_unc`) and a typical size (`dC_unc_typ`).
   - dC6, dC7 are modelled at Λ = 74..118 and dC8 at 74..92.
   - Smooth centrals: floor-mean (the joint lens's primary) and floor-level medoid (the model-independent lens's
     primary), in the derived tables `delta_v1_hi72_*_corrected.json`.
   - **Blind check:** the same rule, frozen on Λ ≤ 44 before the production data existed (2026-10-08 08:35,
     self-hashed record), predicts the exact dC6..dC8 at Λ = 46..72 within 0.099 of its typical uncertainty
     (row rf.blind).
2. **Joint lens** (`joint/`). A linked joint tail model for orders 4..8, fitted by 256-bit python-flint least squares.
   - The scan covers 7 lower edges, 18 tail bases, 4 tail modes (fixed gap ω, free ω, freed leading tail FL/FL5),
     3 shifts and 3 gap inputs, on five datasets (raw, dconn, dconn_s46, dconn_old, dconn_w). That is 186,624 o8 and
     129,600 o7 fits for the unweighted datasets, plus 46,656 and 32,400 weighted ones.
   - In dconn_w (the weighted dataset) the S10 rows at Λ = 46..72 are down-weighted by their noise (row rf.noise).
   - The quoted values use these datasets:
     - fixed A–F components of C6 and C7: the **unweighted** dataset dconn (`r72_summary.json`
       `C_low.dconn_hi118.fixed_AF`);
     - floor+stat ensembles of C4..C7 and the calibrated C8: the weighted dataset dconn_w (`summary_dconn_w.json`);
     - the MI components: the model-independent lens (stage 3; primary run2_fmedoid, on the floor-level medoid
       table).
   - With the weighted fixed A–F the C7 union would round outward to −322,900 instead of −322,890 (row rf.C7w, INFO;
     C6 is unchanged).
   - C8 is calibrated post hoc: fits are selected on |C6/C6^ref − 1| ≤ 1e-4 and |C7 + 322550| ≤ 82.
3. **Model-independent lens** (`model-independent/`): 50-digit e-subtracted least squares on a grid of tail sets, with
   held-out calibration rules (mpmath).
4. **Verifier** (`verify/`): an independent re-implementation (own loader, 320-bit arb least squares, own continuation
   and fitters). Verdict "Mostly confirmed, with adjustments" (REVIEWS.md).

**Results** (rows rf.*, `results_map.md`). All windows (lower and upper fit edges) are post hoc. "fixed A–F" is the
unweighted dataset dconn, "floor+stat" the weighted dataset dconn_w, "MI" the model-independent lens.
- **C4** (solver fits, HT_Pert note only) = 45.415–45.420 (`\NOneCfourSolver`), relative miss ≤ 2e-4
  (`\NOneCfourSolverDev`): union of the central values of the pre-registered bases A–F (lo = 40–70), the floor+stat
  ensemble (45.41986) and the model-independent lens (45.41909), rounded to 3 decimals (nearest; outward gives the
  same). All lie below the exact 45.42488.
- **C5** (solver fits, HT_Pert note only) = −731.36 to −730.97 (`\NOneCfiveSolver`), ≤ 3e-4 (`\NOneCfiveSolverDev`):
  union of the freed-leading-tail fits (misses −0.22 to +0.06) and the floor+stat 16–84 range, −731.3562..−730.9651,
  rounded to 2 decimals **nearest** (outward would give −730.96 at the upper end).
- **C6** = 14,320–14,342 (`\HTpCsixOne`), ≤ 8e-4: union of fixed A–F (16–84), the floor+stat ensemble (16–84) and the
  model-independent variants, rounded to integers (nearest; outward identical). No robust C6 deficit.
- **C7** = −322,890 to −322,230 (`\HTpCsevenOne`), ≤ 1e-3: the same union (model-independent range widened by ±6),
  −322884.30..−322233.55, rounded **outward** to tens.
- **C8** = 8.0652 × 10⁶ (`\HTpCeightOne`; 8,065,157), calibrated on C6 and C7 (post hoc). It differs from the
  diagrammatic 8,059,767 by 7e-4 (`\HTpCeightOneDev`). The 16 calibrated estimators span 8.0636–8.0655 × 10⁶.
  - The "realistic calibrated range" 8.061–8.067 × 10⁶ (`\HTpCeightOneCalRange`) is a judgement of the stage (spread
    over estimator, family, anchoring and window choices), not a stored number.
  - Without calibration the tail family sets C8: 8.045–8.073 × 10⁶ (`\HTpCeightOneUncal`): the union of the five
    families' 16–84 ranges on the S1B weighted data, rounded to 3 decimals (nearest; row rf.C8uncal). Until 2026-10-14
    the macro held 8.047–8.072, the run-1 value; the author updated it to the cited refit.
- **Window effects at orders 6–8 are not the bottleneck.** Making dC6..dC8 exact at Λ = 46..72 moves identical fits by
  C6 −0.01 to −0.04, C7 +4 to +19, and C8 +17 to +32 (fixed ω) or −240 to −490 (FL) (row rf.paired). The order-8
  tail-family spread and the post hoc calibration dominate.
- **Caveat: S10 noise.** The S10 values at Λ = 46..72 carry about 1e-13 relative noise (rms about the smooth curve
  3.95e-10, 1.34e-8, 2.32e-7 for dC6, dC7, dC8; row rf.noise). It biases selection-based fits; the verifier prefers the
  noise-free (s46) model-independent C8 8,065,419 over its primary 8,064,938.

##### Layout in the public tree
- `code/lri_1d_dconn_refit/`: a keep_only subset of the archived stage folder (not a git repository), verbatim.
  - `delta/`: code, lens adapters (`lens_compat/`), the hi = 72 outputs and validation, and the run-1 outputs it
    compares with (`archived_out_delta_v1/`).
  - `joint/`: code, the symmetry sharedq scripts, the r72 summaries and analysis texts, and the run-1 summary.
  - `model-independent/`: code and every summary output, without logs.
  - `verify/`: code and its small outputs.
  - `run1/joint/out/variants_full.json`: the one run-1 table that is still an input.
  - plus `public.mk` and `public/` (`repoint.py`, `test_refit.py`, `refit_keyfits.py`, `replay_refit.py`).
- The stage scripts name their inputs by absolute paths of the authors' machine and cluster. `public/repoint.py`
  makes a re-pointed run-time copy; the shipped files are never edited.

##### Targets (run from `HT_Pert/code/lri_1d_dconn_refit`)
| Command | What | Time |
|---|---|---|
| `make -f public.mk test` | delta stage rebuilt on a re-pointed copy and compared with the shipped outputs (bitwise, else 1e-9 field-scaled); the model-independent post-processing rerun from its shipped intermediates (bitwise, else 1e-12 field-scaled); with `FLINT_PY=<python with python-flint>`, 12 joint-lens key fits refitted (1e-9 relative) | about 3 min, one core |
| `make -f public.mk replay` | `public/replay_refit.py`, rows rf.* | seconds |
| `make -f public.mk fetch-data` | downloads the raw joint scans (97.5 MB) and the model-independent outputs git leaves out (one archive, 319 MB, 1.77 GB unpacked) from the Zenodo data record (DOI 10.5281/zenodo.23466766), with sha256 checks (DATA) | download time; about 1 min to check and unpack |

### `lri_d1_fullblock_tail_response`

Folder: `code/lri_d1_fullblock_tail_response/`.

#### lri_d1_fullblock_tail_response: the second Λ^(-1/2) channel of the d = 1 HT cutoff tail (cited check)

The paper quotes no number from this package. It is the cited check behind one caveat of the Hamiltonian truncation
section: the leading cutoff tail of C_n(Λ) is not a single φ⁶ channel, because "a second channel with the leading
power Λ^(-1/2) enters at ε⁴". The fact sheet lists this as fact C6.

The package is a research bundle written by OpenAI GPT-6 astra, delivered on 2026-10-07. It ships verbatim. Its
`README.md`, `REPORT.md` and `docs/METHOD.md` are the authors' own description. Its own scope statements stand:
- it publishes no physical C6, C7 or C8 tail coefficient;
- its auxiliary low cutoff μ is not the outer cutoff Λ.

##### What the caveat uses (docs/METHOD.md)

Conventions: ε = 2s − 1, α = (1 − ε)/2. The frozen-cutoff regulator is the one of the HT solver.

- **Eqs. (1)–(2): the kernel.** The leading three-line high-energy kernel K3, for arbitrary fixed low bath states,
  contains the regulator-phase operator J_ν^bath = J_ν^P − {N, M}/2.
- **Eq. (3): the outer matching.** It has two channels:
  δΔ_E = −Λ^(α−1) S_Φ6 / [18(1−α)Γ(α)] + Λ^(3α−2) S_J / [3Γ(3α)] + …,
  where S_O is the low-space susceptibility of the retuned gap to a source η g² O.
  - At ε = 0 both powers are Λ^(-1/2).
  - Their ε slopes differ: −1/2 for the φ⁶ channel and −3/2 for the J channel.
  - The J prefactor at ε = 0 is 1/[3Γ(3/2)] = 2/(3√π).
- **Sec. 5 and Eq. (5): the onset.** J^P annihilates every state with P ≤ 4, so S_J starts at ε⁴. The shipped response
  records confirm that the full S_J, number part −{N, M}/2 included, vanishes through ε³.
- **Eq. (6): the logarithms.** The ε⁴ phase response grows as A√μ + (log μ)²/81 + B log μ + C in the low cutoff μ, with
  B = [41 + 42π + 12γ_E + 24 log 2 + 48 log(1+√2)]/486 = 0.49138877353902566.

**Status of the coefficients.**
- The power and the onset are what the paper uses. The replay recomputes both (rows fb.power, fb.onset).
- **The J coefficient is UNVERIFIED.** The review of 2026-10-07 (`REVIEWS.md`) rated its sign and normalisation only
  "plausible" and did not re-derive the K3 J coefficient. So the amplitude 2/(3√π) and any use of B in a C4 tail are
  unverified. The replay checks their arithmetic and the package's internal consistency, nothing more (rows
  fb.amplitude and fb.B).
- The finite-annulus test (fb.annulus) compares Eq. (2) with the package's own direct sums. It does not check the
  derivation of those sums from the Hamiltonian.

##### What is in the package
| Path | Content |
|---|---|
| `docs/METHOD.md` | Derivation: Eqs. (1)–(7) |
| `README.md`, `REPORT.md` | Scope and summary by the package authors |
| `code/response.py` | Taylor engine: low-space responses through ε⁸ (raw and Dconn) |
| `code/exact_response.py` | Exact-rational small-space check |
| `code/annulus.py` | Finite-annulus test of Eq. (2) |
| `code/phase_response_shell.py` | Phase-response convolutions to μ = 262144 (x86-64 80-bit long double) |
| `code/phase_finite_part.py` | Finite part C of Eq. (6) |
| `code/mixing_asymptotics.py` | A, 1/81 and B of Eq. (6) |
| `code/assemble_response.py` | Partial two-vertex assembly, labelled "not a physical Cn prediction" |
| `code/analyze.py`, `code/plot.py`, `code/write_report.py` | Tables, figures, REPORT |
| `vendor/window_jets.py` | Upstream basis helper, verbatim |
| `tests/` | The package's own checks |
| `results/` | 56 response and control records, 8 exact-rational records, shells, finite parts, validations |
| `figures/` | Figures of the package |
| `inputs/PROVENANCE.json` | Hashes of the upstream archives |
| `MANIFEST.sha256` | sha256 of the other 108 files |

##### Layout in the public tree
- **`code/lri_d1_fullblock_tail_response/`**: the 109 files of the bundle (850,370 bytes), byte-identical to the members
  of the supplied zip.
- The overlay adds `public.mk` and `public/`:
  - `fb_common.py`: copy and manifest helpers;
  - `run_tests_fb.py`: the test target;
  - `replay_fb.py`: the replay.
- **No data or results folder.** Every record the targets read is inside the package and bound by `MANIFEST.sha256`.

##### Targets (run from `HT_Pert/code/lri_d1_fullblock_tail_response`)
| Command | What | Time |
|---|---|---|
| `make -f public.mk test` | Manifest (also the verbatim `tests/verify_manifest.py`); on a copy: `check_annulus.py`, `mixing_asymptotics.py`, `check_finite_response.py`, and `validate.py` on x86-64 only (SKIP elsewhere) | seconds |
| `make -f public.mk replay` | `public/replay_fb.py`, rows fb.* (`results_map.md`) | about 15 s (13 s on Intel Xeon 6148) |
| `make -f public.mk replay-full` | The same, with float reruns of all 13 full-J response records | about 3.5 min, one core (209 s on Intel Xeon 6148) |
| `make -f public.mk clean` | Removes `.work/` | |

All runs happen on a copy under `.work/`, because the package's scripts rewrite `results/`. Add `.work/` to
`.gitignore`.

## d = 2: coefficients C2..C8 and the independent check

### `lri_d2_coeff_hpc`

Folder: `code/lri_d2_coeff_hpc/`.

#### lri_d2_coeff_hpc: d = 2 eighth-order coefficient solver (production)

The ε-expansion coefficients C0..C8 of Δ_ε(L) of the d = 2 long-range Ising Hamiltonian truncation at fixed level cutoff
L, by direct Taylor tuning in exact-order float arithmetic (80-bit long double reductions): GFF on the circle,
x = 1/2 − ε/4, M = ⟨:φ²:⟩, V = ⟨:φ⁴:⟩/12, J = 0 reflection-even sectors, primaries tuned so that E1 − E0 = x and
E3 − E0 = 2 − x, Δ_ε = E2 − E0. Three window prescriptions of the delivered package: raw, consistent (vacuum window
D_L(ℓ) = E_v(L) − E_v(L − ℓ)) and literal. `docs/METHOD.md` describes the graph/moment reorganization; the original
reference package with its exact-Fraction oracle is `reference/lri_d2_perturbative_C8/`.

**What is used from here:** the finite-cutoff tables C0..C8(L), L = 2..34 (raw and consistent; `\HTpTwoLprod`
= 34 in the HT_Pert note), checked by the independent solvers (HT_Pert note Sec. 4.2, `\HTpTwoImplAgree`); the
consistent-scheme table also feeds the finite-coupling cross-check `HT/data/HT_2d/pert_crosscheck`. The continuum values
of the paper (Sec. 3.1, Table 2) come from `../lri_2d_coeff_independent_check` (exact large-L sums with the complete
window), because the package's windows do not converge in d = 2 beyond ε³. C6..C8 are not reproduced in d = 2 (paper
Table 2, "n.r.").

##### Layout (public tree)
| Path | Contents |
|---|---|
| `HT_Pert/code/lri_d2_coeff_hpc/` | the package at commit f847d38 (verbatim) + `public.mk`, `public/`, `REVIEWS.md` |
| `…/src/lri_coeff/` | the solver (unchanged since the delivery; source digest 550e9266…) |
| `…/cluster/`, `scripts/`, `docs/CLUSTER.md` | the Expanse/symmetry layer that ran the production (release tar, validation receipt gate, one job per task) |
| `…/tests/` | the suite (61 tests) |
| `…/reference/lri_d2_perturbative_C8/` | delivered reference package: code, exact oracle, `results/coefficients_C0_C8.csv` (L ≤ 20; cited by HT) |
| `HT_Pert/data/HT_2d/prod/` | the 41 production records (lri-coeff-v1, self-hashed), campaign manifests, tables, validation receipts |

##### Targets (`make -f public.mk <target>`, from `HT_Pert/code/lri_d2_coeff_hpc`)
`verify-manifest`, `test` (≈ 2 min), `smoke` (L = 6 rerun vs the shipped records, ≈ 1 min), `replay` (seconds),
`fetch-data` (nothing hosted). The native backend needs x86-64 Linux with 80-bit long double and a C++17/OpenMP
compiler; arm64 macOS cannot run it.

### `lri_2d_coeff_independent_check`

Folder: `code/lri_2d_coeff_independent_check/`.

#### lri_2d_coeff_independent_check: the d = 2 perturbative HT coefficients, checked and extended

This folder is the independent check of the d = 2 coefficient solver (`../lri_d2_coeff_hpc`) and the work that
followed it: exact finite-cutoff coefficients C2(L)..C5(L) at large cutoff, the window corrections that make C4 and
C5 converge to the continuum, and the descendant identities that test those windows without continuum input. Every
d = 2 perturbative-HT number of the paper and of the d = 2 section of the HT_Pert note is recomputed from the files
here (and from the production records in `../../data/HT_2d/prod`) by `make -f public.mk replay`.

It is a **snapshot** (2026-10-14) of a working tree that was never a git repository. `public/SNAPSHOT.sha256` lists
every shipped file with its sha256 as exported; `make -f public.mk verify-snapshot` checks it. The files of the
snapshot are verbatim, including the READMEs of the subfolders, which carry dated status lines from the time they were
written; this README and `REVIEWS.md` are the current description, and the derivations are in Appendices A to C of the HT_Pert note (`../../note/`). Where they
differ, the replay (`public/replay_p2.py`) and the HT_Pert note are authoritative.

##### The model and conventions
`SPEC.md`: GFF on the unit circle, x = Δφ = 1/2 − ε/4, mode weights (x)_a(x)_b/(a! b!), M = ⟨:φ²:⟩, V = ⟨:φ⁴:⟩/12,
level cutoff N ≤ L (the paper's L), J = 0 reflection-even sectors, tuning E1 − E0 = x and E3 − E0 = 2 − x,
Δ_ε = E2 − E0 = Σ C_n ε^n, ε = 2s − 2. Continuum values: `continuum/reference_values.csv` (C2..C5 exact,
C6..C8 numerical, from the condensed note).

##### Layout (what each part is for)
| folder | content | used for |
|---|---|---|
| `rs_exact/` | clean-room Rayleigh–Schrödinger solver in exact rationals (Fraction reference + multi-modular), L = 0..18, raw/consistent/literal schemes; `results/*.json` | `\HTpTwoImplAgree` (vs the production records), check of every other code |
| `cauchy/` | clean-room non-perturbative solver: truncated H at complex ε on a circle (256-bit), Cauchy integrals, L = 0..8; `results/*.json` | agreement with rs_exact (5e-46) and the package (1.6e-14) |
| `compare_with_package.*`, `compare_three_way.*` | the original comparison scripts and outputs (absolute base path inside; `public/replay_p2.py` redoes both with relative paths) | HT_Pert note Sec. 4.2, App. A.2 |
| `continuum/` | exact C2(L), C3(L) code (`exact_low_orders.py`), its table to L = 600, asymptotics (`asymptotics_C2_C3.*`) | `\HTpCtwoTwo` (35 digits), `\HTpCthreeTwo`, κ |
| `c4_exact/` | exact fourth-order cutoff sums: C4(L) to L = 2000 in the raw, consistent and zero-mode schemes (`results/c4_L2000.npz`), exact window shifts to L = 20000, fits, the blind L = 2000 test, validations against rs_exact, the package and zeromode_exact | `\HTpTwoLfour`, `\HTnpDtwoCfourLog`, the C4 scheme table of the note |
| `zeromode_exact/` | exact-rational solver of the zero-mode window scheme, L ≤ 18 | validation of `c4_exact` |
| `complete_exact/` | exact-rational solver of the complete window W through ε⁸ (L ≤ 16) and the descendant channels | ε² descendant identities (`[ε²]v_n`, HT_Pert note Sec. 4.6) |
| `residual_log/` | the derived complete ε² window (zero-mode Bloch + χ-line mass window) at large L (`offdiag_window.py`, `nm_window.py`, `C4W_by_L.csv`), the window specification `WINDOW_SPEC.md`, exact C5(L) (`eps5/` engine; `large_L/lib` = the same engine as run, `large_L/lib_opt` = the optimized engine), the ε⁵ window shifts (`results/eps5/dC5_L1000_all.npz`), the leg response S(L) (`results/legw`), the ε³ external-line window δ⁽³⁾(L) to L = 16000 (`large_L/tagchan.py`, `large_L/results/tag3_L16000.npz`), the exact all-order window solver `ce_wc/` (schemes Wc, Wcs, Wcs4X; L ≤ 16), the parent checks `fits/parent_check_*` | `\HTpCfourTwo`, `\HTpCfiveTwo` (+Dev, Log), `\HTpTwoLfive`, `\HTpTwoIdentThree`, the C5 and ε³/ε⁴ numbers of the note |
| `public/` | replay, tests, snapshot list, Slurm templates (new files, not part of the snapshot) | |

##### Results in brief (each is a replay check, `results_map.md` of the HT_Pert d = 2 entries)
- The production solver is correct for the model as defined: exact-rational RS agrees on every C_n, r_n, g_n, E_p and
  vacuum coefficient (25 scheme/cutoff pairs) to 3.9e-13; the Cauchy solver agrees with RS to 5e-46.
- C2(∞) = 4 log 2/9 to 35 digits; C3(∞) = −0.8748500(1) (exact −0.87485001265).
- C4: every scheme of the package diverges (raw linearly, κ = 2.2073e-4; consistent and zero-mode like ln L, with
  coefficients −365/(4374π) and −8/(243π)). With the derived complete window W, C4(L) has no ln L and
  C4(∞) = 5.0488682(10) (exact 5.04886843).
- C5: with nested windows referred to the outer cutoff (Wc) and the ε³ external-line window (Wcs; δ⁽³⁾ → −4/(81π)),
  exact C5(L) to L = 300 extrapolates to −38.835(13) (exact −38.8336459). A residual b ln L with |b| ≲ 0.01 is not
  excluded at L ≤ 300; it would move C5 by about 0.1.
- Descendant identities: W restores them at ε²; Wcs removes at least 95 % of the ε³ violation of single-quantum
  descendants at L ≤ 16 (all of it as L → ∞); the ε³ identities of the φ² descendants are not settled at L ≤ 16; the
  ε⁴ window is only partly known (Wcs4chi). C6..C8 are not reproduced in d = 2.

##### How to run
See `REPRODUCE` of the HT_Pert d = 2 entries; in short (from this folder):
```
make -f public.mk replay        # every p2.* check, seconds (numpy, mpmath)
make -f public.mk replay-full   # rerun the shipped fit scripts on a scratch copy, compare outputs (~1 min)
make -f public.mk test          # small-cutoff reruns of every code vs the shipped outputs (~2-3 min; numba, scipy, python-flint)
```
Several codes import siblings by relative path (`residual_log/eps5` and `large_L/lib*` take `RS_EXACT_DIR`, default
`../../rs_exact`, which from `large_L/lib*` must be set explicitly: `RS_EXACT_DIR=<this folder>/rs_exact`). Scripts that
read the production records expect them at `../results/<campaign>/d8` relative to this folder (the source layout); in
the public tree they are at `../../data/HT_2d/prod/<campaign>/d8`.

## d = 3: exact C2..C5(L) sums and the coefficients C2..C8

### `lri_3d_c4_exact`

Folder: `code/lri_3d_c4_exact/`.

#### lri_3d_c4_exact: exact finite-cutoff sums of the d = 3 perturbative Hamiltonian truncation

This package computes the coefficients C_n(L), n = 2..5, of the thermal gap of the d = 3 long-range Ising fixed point
in the level-cutoff Hamiltonian truncation exactly, as sums over intermediate states (diagram sums with exact
partial-wave reductions on S^2 and exact zero-mode projections), for every even cutoff L up to L = 600 (C2..C4) and
L = 40 (C5), with the window corrections to L = 8000. The model is that of the production package `lri_3d_hpc` (same
Hamiltonian, cutoff and tuning); at L <= 20 the two agree to about 1e-13.

    Delta_E(eps; L) = 3/2 - eps/6 + sum_{n>=2} C_n(L) eps^n,   eps = 2s - 3,   Delta_phi = (3 - eps)/4.

The paper quotes, in d = 3 (Table 2, `tab:htpert`, Sec. 3.1; final commit `a6772872`), the extrapolated limits:

| | value | delta = abs(C^HT/C - 1) | from |
|---|---|---|---|
| C2(3) | 0.181221785405554 | 15 digits | fit to L <= 8000 |
| C3(3) | -0.353581479(20) | 1e-7 | fits to L <= 600, three windows |
| C4(3) | 1.228070(21) | 5e-6 | complete window W, tower T4, 12 fit windows to L <= 600 |
| C5(3) | -6.0 +- 0.3 (provisional, so marked in the caption) | 3e-2 | window Wc, L <= 40 |

The complete window W (vacuum window, full zero-mode window including the zero-mode-number-changing part, and the
chi-attached sunset window) was derived in d = 2 and is applied unchanged; without it, the truncation diverges at
order eps^4 (uncorrected like L^2, with the vacuum window alone like L and sqrt(L) ln L). Fit forms and windows were
chosen after the data were seen, with the continuum values known; the chi window is used in its leading-order linear
form, which is not derived for d = 3. `results_map.md` lists every number with its check and tolerance.

##### Quick start

```
make -f public.mk replay     # every quoted number from the shipped exact sums (numpy; about 2 s)
make -f public.mk test       # recompute the sums at small L and compare (1-3.5 min on one node)
```

`replay` reruns the package's own analysis scripts (`fits_c4.py`, `eps5/fits5.py`, `eps5/t3.py`) on the shipped
results, recomputes each quoted number with its rule and repeats the validation against `../lri_3d_hpc` and its
campaign records (`../../data/HT_3d/pert3d/results`). `test` recomputes the sums from scratch at small cutoffs.

##### What is where

| Path | Contents |
|---|---|
| `c4lib3d.py`, `c4_compute3d.py`, `c4_run3d.py` | the C2..C4 engine: mode tables, partial-wave bundle sums, exact zero-mode projections, assembly, production driver |
| `windows3d.py`, `offdiag3d.py`, `dchi3d.py` | the window shifts (vacuum, zero-mode diagonal and off-diagonal, chi-attached sunset), cancellation-free, to L = 8000 |
| `eps5/` | the eps^5 engine (`engine.py`; model-independent modules ported from the d = 2 package), production `prod5.py`, shifts `delta5.py`, leg response `legw3d.py`, brute force on the package operators `brute3d_*.py`, validation, analysis `fits5.py`, `t3.py` |
| `fitlib3d.py`, `fits_c4.py`, `fits/` | asymptotic fits; `fits/fit_summary.txt` (C2..C4), `fits/fits5_summary.txt` (C5), `fits/t3_summary.txt` (descendant identity) |
| `results/` | the production results (npz: C_n, r, g, energies, window shifts per L; json: brute force), regression logs |
| `brute_zm.py`, `validate_pkg.py` | brute force with the package's reference solver; comparison with the package |
| `C4_by_L.csv` | C2, C3, C4 in every scheme at every even L <= 600 |
| `README.md` | the package's own README (derivation, validation, results, cost); Sec. 7 is the eps^5 part |
| `public.mk`, `public/` | public targets and documents |

References in the verbatim files to `../../lri_2d_coeff_expanse/...` (for example `README.md` Sec. 2.1 and the
docstring of `eps5/engine.py`) point to the d = 2 counterpart, shipped here as
`HT_Pert/code/lri_2d_coeff_independent_check`.

The package ships at git commit `d5afa4f`. The memory-profiling scripts and the job-log tails are not shipped
(`public/PROVENANCE.md`).

### `lri_3d_hpc`

Folder: `code/lri_3d_hpc/`.

#### lri_3d_hpc: perturbative Hamiltonian truncation in d = 3 (C_2 to C_8 at finite level cutoff L)

This package computes the finite-cutoff coefficients C_n(L), n = 2..8, of the thermal gap of the long-range Ising
fixed point in d = 3 from the truncated Hamiltonian, by Rayleigh-Schroedinger perturbation theory on formal power
series (no Feynman graphs, nothing fitted):

    Delta_E(eps; L) = 3/2 - eps/6 + sum_{n>=2} C_n(L) eps^n,   eps = 2s - 3,   Delta_phi = x = (3 - eps)/4.

The model is the generalized free field on S^2 (modes (n, l, m), level 2n + l), H = H0 + r M + g V with
M = int dOmega :phi^2:/(4 pi), V = int dOmega :phi^4:/(48 pi); the bath (nonzero modes) is cut at
N_b = sum (2n + l) <= L, the zero mode (the local oscillator) is not truncated. r and g are tuned order by order to
the exact dimensions of phi and phi^3. Two prescriptions: `raw` (no window) and `consistent` (the vacuum window
D_L(l) = E_v(L) - E_v(L - l), the only window this package implements).

Since 2026-10-14 the paper's d = 3 values come from the exact finite-cutoff sums of `../lri_3d_c4_exact`, which use
the complete window of d = 2. This package's finite-cutoff results remain part of the release:
- they are the independent code against which the exact sums are validated: C2..C5, r, g and the seed energies agree
  at every even L <= 20, to 3e-13 or better;
- `HT/code/lri_3d_window_hpc` reads C4(20) of the consistent scheme from `HT_Pert/results/HT_3d/SUMMARY.md` (60 % of
  C4(3));
- the HT_Pert note shows them as a table.
An earlier draft of the paper quoted the ratios C_n(20)/C_n (0.995, 0.933, 0.603, 0.577, 0.507, 0.414, 0.378) and
the L = 14 agreement with the original code (about 1e-14); `make replay` still recomputes them (`results_map.md`).
The exact sums show that the consistent scheme diverges from order eps^4 on, so these values are finite-cutoff
quantities, not continuum estimates beyond C3.

##### Quick start

```
make -f public.mk replay     # every quoted number from the shipped records (standard-library Python, ~1 s)
make -f public.mk test       # the package's checks + an L14 store built from scratch vs the original code
make -f public.mk smoke      # the shipped L4 fixture against the original code at 1e-16 (seconds)
```

`replay` reads `../../data/HT_3d/pert3d` (the production records, byte-identical) and `../../results/HT_3d/SUMMARY.md`.
`test` needs Linux x86-64 (80-bit long double), a C++17 compiler with OpenMP and Python 3.12 with numpy, scipy,
numba, threadpoolctl (`public/requirements.txt`); see `public/REPRODUCE.md` for the measured runtimes.

##### What is where

| Path | Contents |
|---|---|
| `code/` | the optimized solver: Taylor vertices, stationary energy series, native C++/OpenMP kernels, MPI backend, vertex store |
| `reference/`, `vendor/ht3d/` | the original implementation and its SO(3) basis machinery, unchanged (the "original code" of the note's L = 14 check) |
| `results/reference_coefficients_L14.json` | the original code's results for every even L = 0..14, both schemes, C_0..C_8, r, g and all energy series |
| `fixtures/vertices_L4/` | a small vertex store for the smoke test |
| `tests/` | the package's checks (run by `public/run_tests.py`) |
| `hpc/` | generic Slurm examples of the supplied package |
| `cluster/` | the Expanse/symmetry layer that ran the production campaign (`cluster/RUNBOOK.md`): staged releases, validation receipts, stage runner, submit wrapper |
| `docs/` | `NUMERICS.md` (exact stationary reformulation, precision contract), `VERTEX_CONSTRUCTION.md`, `PERFORMANCE.md` |
| `benchmarks/`, `results/*.json` | the supplier's measurements and validation records (not used by the public targets) |
| `README.md`, `RELEASE_MANIFEST.json` | the package's own README and file manifest (sha256 of every file; checked by `make test`) |
| `public.mk`, `public/` | public targets and documents (this README, `REPRODUCE.md`, `PROVENANCE.md`, `REVIEWS.md`, `results_map.md`) |

The package's own files ship unchanged at git commit `7c8a67e`, the release the production campaign ran. In
`cluster/RUNBOOK.md` the authors' cluster paths are replaced by placeholders (`public/SCRUBBED.txt`).
