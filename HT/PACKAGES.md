# HT packages

What each package in `code/` contains and computes.

Assembled from the package authors' texts. Inside a package section, relative paths are relative to that package's folder `code/<package>/` unless they start with `HT/`. The values themselves are in `note/README.md` and the note.

- d = 1: dressed phi^4 Hamiltonian truncation: `lri_dressed_phi4_hpc`, `lri_dressed_phi4_hpc_analysis`, `lri_dressed_phi4_independent_check`
- d = 2: dressed-window Hamiltonian truncation: `lri_2d_window_hpc`, `lri_2d_window_indep`
- d = 3: dressed-window Hamiltonian truncation: `lri_3d_window_hpc`, `lri_3d_window_indep`

## d = 1: dressed phi^4 Hamiltonian truncation

### `lri_dressed_phi4_hpc`

Folder: `code/lri_dressed_phi4_hpc/`.

#### lri_dressed_phi4_hpc: the d = 1 finite-coupling HT solver

`HT/code/lri_dressed_phi4_hpc` is the solver behind every finite-coupling Hamiltonian-truncation number for the
one-dimensional long-range Ising model in the paper and the HT note. It ships at commit **33998bb**, the code the
production campaign `dens_v1` ran.

##### What it computes

- **Hamiltonian.** The phi^4 Hamiltonian of the long-range Ising chain in radial quantization (HT note, Sections
  "Model" and "Zero mode and bath"). The field is split into the zero mode q = a0 + a0^† and a bath of the other
  modes.
- **Zero mode.** Kept as `nz` states per parity, each a superposition of many zero-mode quanta (the level cutoff does
  not cap them). The full Hamiltonian, including the couplings L_j W_j of the zero mode to the bath, is diagonalized
  on the product of these states with the bath. The `nz` states are either the lowest eigenstates of the zero-mode
  part H_z = (Ds/4) p^2 + A q^2 + (g/12) q^4 or, with `--local-basis`, a frozen state-averaged ("density") basis.
- **Bath.** Truncated at total level N (`--bath-cut`), with no particle cap.
- **Tuning.** The two couplings (r, g) are tuned so that the sigma gap equals Ds and the phi^3 gap equals 1 − Ds.
  The output is Delta_eps, the first excited reflection-even, field-even gap.
- **Window correction.** `--window vacuum --window-mode consistent` adds the full-vacuum window correction
  D(N) = Ev(cut) − Ev(cut − N) to every bath state. Ev is solved as a scalar fixed point at every coupling (HT note,
  Section "Window correction"; `docs/WINDOW.md`).
- **Density basis.** `train-basis` builds the density basis from the reduced density matrix of a larger "teacher"
  zero-mode space (`docs/DENSITY_BASIS.md`).
- **HPC layer.** Node-packing launcher, cross-node leases and checkpoints for symmetry (`cluster/symmetry/`).

The package's own documentation ships verbatim: `README.md` (release notes of the received package and of the
symmetry/window revision), `INTEGRATION.md` (the density basis), `docs/ALGORITHM.md`, `docs/WINDOW.md`,
`docs/DENSITY_BASIS.md`, `docs/HPC.md` and `cluster/symmetry/README.md`.

##### Public targets (run from `HT/code/lri_dressed_phi4_hpc`)

| Command | What it does | Needs | Time |
|---|---|---|---|
| `make -f public.mk test` | The package's staged validation `scripts/validate_release.py` (see below) | Python 3.11, numpy 2.3.5, scipy 1.17.0, numba 0.65.1, pytest | about 2–3 min with THREADS=4, < 2 GB |
| `make -f public.mk replay` | Checks that this tree produced the shipped records (source and release fingerprints), then runs the package's own validator on all 881 shipped results | same | about 1 min, one core |
| `make -f public.mk smoke` | Reruns the production item N = 12, Ds = 0.2 (16 density states, consistent window) and compares it with its record to 1e-8. Basis artifacts are bound to the runtime that trained them, and the package refuses them on any other runtime. On a non-production runtime, smoke therefore first retrains the Ds = 0.2 basis with the production settings | same | 10 s on the production runtime; about 3.5 min (THREADS=4) otherwise |

**What `test` runs.** Six stages:

1. pytest: 104 tests.
2. Saved-seed regression.
3. `--window none` bit equality with the frozen baseline `reference/production_e637dfd`, the received code.
4. A calibration smoke run.
5. Window bit equality with `reference/production_e2ca07c`.
6. Density-basis validation.

The equality stages compare two runs on the same machine, so they hold on any CPU vendor. Receipt 570965 recorded
this validation on symmetry for the production install. It is in `HT/data/HT_1d/dens_v1/validation/570965/`.

The quoted numbers are not replayed here. `HT/code/lri_dressed_phi4_hpc_analysis` recomputes them from the shipped
records (`make -f public.mk replay` there).

##### Notes on shipped files

- **Verbatim tree.** The whole commit ships unchanged (157 files). The release fingerprint `io.release_fingerprint`
  hashes `src/`, `scripts/`, `cluster/symmetry/`, `tests/`, `reference/`, `inputs/`, `pyproject.toml` and
  `requirements-tested.txt`. The replay checks it against the records, so these files keep their original bytes,
  including site paths in `cluster/symmetry/env.sh`.
- **`MANIFEST.sha256`.** This is the checksum list of the package as originally received (e637dfd). It has been
  stale since the symmetry revision (157a2c6), so `scripts/verify_manifest.py` fails on this tree as it did in
  production. No target uses it. The binding is the release fingerprint.
- **`benchmarks/`.** Timing measurements of the received package, cited in `PERFORMANCE.md`. Not used by any target.
- **`inputs/`.** Coupling seeds of the received package, used by the saved-seed test.
- **Runtime binding of bases.**
  - `lri_dressed.local_basis` accepts a basis artifact only on the exact runtime that trained it: Python 3.11.4, numpy
    2.3.5, scipy 1.17.0, numba 0.65.1 for the shipped ones.
  - On another runtime, `python -m lri_dressed run --local-basis` stops with "Basis source/runtime differs from this
    release: regenerate and revalidate on the target runtime". This is by design.
  - Retrain with `train-basis`, using the settings stored in the artifact's config (as `public/smoke.py` does).
  - Tested on symmetry with Python 3.12.9 and numba 0.68.0: the retrained Ds = 0.2 basis reproduces the record to
    1e-15.

### `lri_dressed_phi4_hpc_analysis`

Folder: `code/lri_dressed_phi4_hpc_analysis/`.

#### lri_dressed_phi4_hpc_analysis: the d = 1 finite-coupling HT analysis

This folder holds the analysis that turns the d = 1 production records into the quoted numbers (paper: the HT column
of Table tab:num1 and the d = 1 comparison; HT note, "Results in one dimension"). The scripts and their inputs and outputs ship **verbatim** from
the production analysis folder. `public/` is added.

| File | Role |
|---|---|
| `extrapolate.py` | The fit family, used by all analyses. `fits(series)` runs F1 = D + a N^-w, F2 = F1 + b N^-(w+1) and F3 = F1 + b N^-2w, each for N_min = 12, 14, …, 24. `summarize()` accepts a fit if rms < 3e-6, 0.2 < w < 4 and \|D − Delta(N_max)\| < 0.05, then returns the median, half-spread, min and max of the accepted fits. On import the script also redoes the earlier composite-series analysis of prod1–7 (`collected.json` → `extrapolation.json`). |
| `dens_v1.py` | The production extrapolation of the dens_v1 series (13 Ds, N = 12..40) with the stability rule (≥ 5 fits, median omega ≥ 0.45, half-spread ≤ 2e-3). Writes `dens_v1_extrapolation.json`. |
| `dens_v1_holdout.py` | The held-out-cutoff test: fits on N ≤ N_cut predict the held-out points. Writes `dens_v1_holdout.json`. |
| `dens_v1_rows.json` | The input rows: one per dens_v1 record, written by `campaigns/dump_dens_v1.py` on the cluster. |
| `collected.json`, `extrapolation.json` | The prod1–7 rows and their composite extrapolation. Needed because `extrapolate.py` runs that analysis on import. The paper does not quote them. |
| `nrg/ds13_final.json` | The earlier NRG table, which `dens_v1.py` prints for context. It is superseded: every quoted HT–NRG comparison uses `../../results/HT_1d/nrg_reference.json`, the NRG folder's final, re-analysed table. |
| `identities/` | 104 descendant-identity records: level-1 and level-2 spacings of sigma, the shadow (phi^3) and E, raw and window-corrected, at N = 16..28 for all 13 Ds. Each names its input prod record by sha256. |
| `indepcheck/production_reference.json` | The production values that the blind solver was compared against. |

##### Targets (run from `HT/code/lri_dressed_phi4_hpc_analysis`)

| Command | What | Time |
|---|---|---|
| `make -f public.mk test` | `public/selftest.py`: the shipped fit code recovers synthetic limits, the local exponent is constant on a power law, and the comparison rules behave | seconds |
| `make -f public.mk replay` | `public/replay_ht1d.py`, five steps below | about 1 min, one core |

What `replay` does:

1. Verifies all 1106 record envelopes.
2. Binds them to `../lri_dressed_phi4_hpc` through the source and release fingerprints.
3. Rebuilds `dens_v1_rows.json` from the records.
4. Reruns `dens_v1.py` and `dens_v1_holdout.py` unchanged in `.work/`, on the rebuilt rows.
5. Recomputes every number of `../../results/HT_1d/quoted_numbers.json` with its stated estimator.

It prints a PASS/FAIL table (in `.work/replay_ht1d.txt`) and exits 1 on any FAIL.

Python ≥ 3.10 with numpy and scipy. The fits use scipy's `curve_fit` from several starting exponents. The replay
compares refitted values with the shipped ones at 1e-7, far below every quoted digit. The quoted numbers themselves
are compared after rounding as quoted.

##### Added for the public release (`public/`)

- `replay_ht1d.py`: the replay.
- `make_tables_ht1d.py`: writes the published tables.
- `model_dependence_ht1d.py`: the model-dependence diagnostic.
  - It tries two alternative tail models of the window series: F4 with two free exponents, and a drifting local
    exponent.
  - It computes a fit-free bracket.
  - It extrapolates the raw prescription with the same fits.
  - It reports these shifts as measured and does not combine them into an error.
- `selftest.py`: the self-test of `make test`.

##### Estimators that are easy to get wrong

- **The quoted error is half the spread of the accepted fits**, a model spread. It is not a standard error.
- **Delta(N = 40)** is the record at the largest cutoff, not an extrapolation.
- **The local exponent** is omega_eff = −d ln(dDelta/d ln N)/d ln N. It is computed from slopes between successive
  cutoffs, taken four cutoff units apart, and labelled by the centre of the four cutoffs (N ≈ 15, 19, …, 35).
- **The Ds = 0.05 range** is the min and max of the accepted F1 and F2 fits. The lowest accepted F3 fit is quoted
  separately.
- **Model dependence** (0.075 ≤ Ds ≤ 0.2) is given as measured shifts: the largest tail-model shift and the raw
  minus window difference of the limits. They are not combined into an error, and the quoted errors stay fit spreads.
- **"no limit"** means that Delta(N) falls at N = 40 after a maximum, or that no fit is accepted. The table then
  quotes only Delta(N = 40).

### `lri_dressed_phi4_independent_check`

Folder: `code/lri_dressed_phi4_independent_check/`.

#### lri_dressed_phi4_independent_check: blind re-implementation of the d = 1 finite-coupling HT

This is a separately written solver for the same model as `../lri_dressed_phi4_hpc`. A Claude Code subagent wrote it
on 2026-10-08 from the definition of the model. It was not allowed to read the production code, results or analysis:
it read only the "Definition" section of the window documentation and the "Hamiltonian" section of the algorithm
notes, and derived H itself from the GFF radial quantization (`DERIVATION.md`). The Supplementary Material
names it among the independent recomputations (opening section "AI agents and reproducibility"); its numbers are in
the HT note, Section "Independent checks".

**Own method.**

- The zero mode is on a sinc-DVR grid instead of an oscillator basis.
- It builds its own bath Fock space.
- It implements literal and consistent windows.
- It runs Newton tuning continued from weak coupling.
- Every point is verified on 1.5× finer and 1.5× wider grids.

**Result.**

- **Production comparison.** 38 points: raw and consistent at Ds = 0.249, 0.2, 0.1, 0.05, 0.025 and 0.01 with
  N = 12, 16, 20, plus literal at Ds = 0.2 and 0.1 with N = 12. Delta_eps agrees with production to ≤ 1.3e-9 where
  production used nz 48 (or Ds ≥ 0.2), and to ≤ 4.8e-9 where it used nz 24/32. The latter gap is production's
  zero-mode truncation.
- **Weak coupling.** Delta_eps = 1/2 − eps/6 + C2(N) eps^2 is reproduced, with C2(N) equal to the exact rational
  formula to ≤ 3e-7 for N = 0..16.

The check verifies that production solves the stated model. It says nothing about the model's continuum limit.

##### Targets (run from `HT/code/lri_dressed_phi4_independent_check`)

| Command | What | Time |
|---|---|---|
| `make -f public.mk test` | `tests/test_indep_ht.py`, 64 unit checks | a few minutes, one core |
| `make -f public.mk replay` | `public/replay_indep.py`, four steps below | about 10 s |
| `make -f public.mk smoke` | Reruns one point (Ds = 0.2, N = 12, raw) and compares it to 1e-10 | 1–2 min |

What `replay` does:

1. Rebuilds `results/indep_results.json` from `results/raw_runs/` with the shipped `analyze.py`.
2. Rebuilds the production reference from `../../data/HT_1d`.
3. Recomputes the agreement: 1.3e-9 and 4.8e-9, giving the 5e-9 quoted in the paper.
4. Recomputes the C2(N) check: ≤ 3e-7.

**Files.**

- `indep_ht.py`: the solver.
- `analyze.py`: merges the per-task outputs and runs the C2 fits.
- `make_tasks.py`, `tasks/`: the run inputs.
- `slurm/`: job scripts (site values replaced by placeholders).
- `retune_check.py`: full retuning on altered grids.
- `REPORT.md`: the subagent's report, with the host's comparison.
- `results/`.

Production cost: about 3 h on one symmetry node (jobs 571688 and 571710).

## d = 2: dressed-window Hamiltonian truncation

### `lri_2d_window_hpc`

Folder: `code/lri_2d_window_hpc/`.

#### lri_2d_window_hpc: d = 2 finite-coupling Hamiltonian truncation (dressed zero mode, vacuum window)

The long-range Ising model in d = 2 on the circle, as the generalized free field φ with Δσ = Δ_φ plus
r :φ²: + (g/12) :φ⁴:, truncated in the bath level N. The zero mode is kept in a density-optimized basis of nz states
per parity (each a superposition of many zero-mode quanta), and the full Hamiltonian, its couplings to the bath
included, is diagonalized on the product of this basis with the bath states of level ≤ N. This basis is a truncation
whose convergence is checked: nz = 12, 16 and 20 agree to 5.2e-7 (checks d2.nz.*). Every bath state gets the vacuum
window shift D(ℓ) = E_v(N) − E_v(N − ℓ) (consistent mode). The
two couplings are tuned so that the lowest odd gaps equal Δσ and 2 − Δσ; the output is the lowest even gap Δ_E(N).
The physics is in `docs/ORIGINAL_METHOD.md` and in the HT note (Sec. "d = 2").

**What the paper uses from here (all finite-N, no continuum limit):** the largest cutoff N = 24 and the value Δ_E at it
for 13 values of Δσ (N = 22 at Δσ = 0.125, 0.126), in Fig. fig:cmp2d3d (left panel, green squares; Sec. Results,
"Nonperturbative results") and Table tab:num2 (Appendix "Numerical results", five decimals), and the N = 24 valley scan
behind the caption's statement that there is no solution at Δσ = 0.125, 0.126. The HT note gives the full Δ_E(N),
N = 8 … 24, its finite-N behaviour and the fold near Δσ ≈ 0.1274. `results_map.md` lists every number.

##### Layout (public tree)
| Path | Contents |
|---|---|
| `HT/code/lri_2d_window_hpc/` | the package at commit 889a968 (verbatim) + `public.mk`, `public/`, `REVIEWS.md` |
| `…/code/ht2d/`, `code/hpc_run.py` | the solver and the one-point driver that wrote every record |
| `…/cluster/expanse/` | the campaign layer that ran prod1 (spec freeze, chains, continuation, collect.py) |
| `…/reference/`, `upstream/`, `tests/` | the package's reference port, earlier implementation and test suite |
| `…/public/scan_valley.py` | the N = 24 valley scan (verbatim; ran on afe69ab = 889a968 + `public/afe69ab.diff`) |
| `HT/data/HT_2d/prod1/` | the frozen campaign spec, its inputs (bases, seeds) and the 348 records `chains/<chain>/L<N>_z<nz>.json` |
| `HT/results/HT_2d/prod1/` | points.csv, nested.csv, descendants.csv, flags.txt (collect.py) and largest_N.csv |
| `HT/results/HT_2d/valley_N24/` | the 12 valley-scan outputs |
| `HT/data/HT_2d/pert_crosscheck/` | consistent-scheme C0..C8(N) at N = 8 … 24 (from the perturbative package) |

##### Targets
`make -f public.mk test | smoke | replay` (see REPRODUCE). Records are self-hashed (`record_sha256` over canonical JSON)
and bind the source hash of `code/` and `inputs/`; they ship byte-identical and keep the original machine paths.

### `lri_2d_window_indep`

Folder: `code/lri_2d_window_indep/`.

#### lri_2d_window_indep: an independent solver for the d = 2 finite-coupling HT model

A second implementation of the d = 2 dressed-window truncation, written from the method description
(`HT/code/lri_2d_window_hpc/docs/ORIGINAL_METHOD.md`, sections 1–5), without importing, copying or reading the
production code while writing it, and run against the production records. It is **not blind**: it was written by the
Claude Code session that had ported the production package to Expanse (and fixed its HF-01 fixed-point fallback), so the
author of the check knew the production design. Its independence rests on the different numerics below. It verifies that
the production code computes the stated model; it says nothing about the continuum limit.

Deliberately different numerical choices (header of `indep_ht2d.py`): bath vertices from explicit annihilation amplitudes
on a dictionary Fock representation; reflection-even states as explicit symmetric combinations; the zero mode in the
eigenbasis of the bare local Hamiltonian h_z, truncated to K states per parity (production: a density-optimized basis of
nz states); window fixed points by Newton on λ_min(H(s)) − s; tuning by finite-difference Newton.

| File | Role |
|---|---|
| `indep_ht2d.py` | the solver (numpy/scipy only) |
| `test_indep.py` | self-tests: two-point weights vs closed form, vertices vs brute force in the full Fock space (N = 5), reflection projector, dense vs Lanczos |
| `run_check.py` | the task list and driver: fixed-coupling spectra at the production θ, and re-tuning from shifted seeds |
| `summarize.py`, `compare.py` | the tables used during the check |
| `ht2d_indep.sbatch`, `ht2d_indep_followup.sbatch` | the two symmetry jobs (571680: 143 tasks; 571811: 12 tasks) |
| `public/replay_indep.py` | recomputes every agreement figure from the shipped outputs |

Outputs: `HT/results/HT_2d/independent_check/out_sym/<task>.json` (155). Each embeds the production values it was compared
with and the production `record_sha256`; the replay checks that binding against `HT/data/HT_2d/prod1/chains`.

**Quoted:** 1.4e-12 (Δ_E, every Δσ, N = 12 and 16, K ≥ 32) and 4.4e-10 (N = 22, Δσ = 0.125, K = 32; 4.0e-10 at 0.126).
At K = 24 the independent zero-mode basis is not converged at strong coupling (6e-9 at N = 16, 2.4e-7 at N = 20,
Δσ = 0.125); those rows test the truncation of the check, not the production code.

## d = 3: dressed-window Hamiltonian truncation

### `lri_3d_window_hpc`

Folder: `code/lri_3d_window_hpc/`.

#### lri_3d_window_hpc: d = 3 Hamiltonian truncation at finite coupling

The production code behind every d = 3 finite-coupling Hamiltonian-truncation (HT) number of the paper and the HT note: the dressed
zero-mode truncation on the sphere S² × ℝ with the vacuum window correction, tuned to Δσ = Ds and Δφ³ = 3 − Ds, solved
at even bath cutoffs N = 8, …, 20 for 15 values 0.518149 ≤ Ds ≤ 0.7499. The cutoff is called L in the code and in
the record names. The method is in the HT note (`HT/note`), Secs. 2–6 and 9.

The package ships **verbatim at git ref `b330ee7`**, the last commit used in production; this folder (`public/`) and
`public.mk` are the only additions. The package's own `README.md`, `EXPANSE.md`, `FIX_L18_L20.md`, `REPORT_L18_L20.md`
and `PERFORMANCE.md` describe its history: the 0.2.0rc1 performance candidate, the 0.2.1rc1 projector repair that made
N = 18 and 20 possible, and the Expanse site layer in `cluster/expanse/`. The numerical source (`code/` and
`inputs/prior_3d_points.json`, hashed by `ht3d.hpc.source_hash()`, d27a3bc2…) is the same in every commit that
produced a record: 33ef4f3 (N ≤ 18), ccd055a (N = 20 at Ds = 0.6) and b330ee7 (the other N = 20 points). Those
commits differ only in `cluster/expanse/` and its tests.

##### What is where

| path | content |
|---|---|
| `code/ht3d/` | the solver: bath graph and SO(3) projector (`basis.py`), vertices (`rotational_vertices.py`, `block_vertices.py`), product operator (`operators.py`), zero-mode problem (`local.py`), density basis (`density.py`), window (`window.py`), tuning (`solver.py`), point driver and record format (`hpc.py`), immutable cache (`cache.py`) |
| `cluster/expanse/` | the Expanse layer that ran production: frozen campaigns (`campaign.py`), lanes and recovery (`lanes.py`, `child.py`, `lane.sbatch`), validation receipt (`receipt.py`, `validate.sbatch`), setup and cache probes (`probe.py`, `setup_probe.sbatch`) |
| `tests/` | pytest suite (158 tests at b330ee7) and the five validators the receipt runs |
| `reference/` | earlier code kept as oracles (`baseline/`, `d3original/`, `performance_0_2_0/`) |
| `MANIFEST.sha256` | sha256 of 646 files, checked by `tests/verify_manifest.py` |
| `public/` | `run_tests.py` (test), `replay_ht3d.py` (replay), `bp_x07.py` (Borel–Padé value at Ds = 0.7), `smoke_points.py` (smoke), `slurm/` templates, this README, `REPRODUCE.md`, `PROVENANCE.md`, `REVIEWS.md` |

Records: `../../data/HT_3d/campaigns/` (105 window records and their teachers, with each campaign's frozen
`manifest.json`). Published outputs: `../../results/HT_3d/` (`finite_L_table.csv`).

##### Targets

```
make -f public.mk test        # manifest + pytest + validators (~4 min, 4 cores)
make -f public.mk replay      # every quoted number from the records, PASS/FAIL table (~5 s, any OS)
make -f public.mk smoke       # re-solve four N = 8, 10 production points from the shipped inputs (~2 min)
make -f public.mk fetch-data  # nothing is hosted; prints how the N = 20 static cache is rebuilt
```

`public/REPRODUCE.md` gives the production rerun. `../lri_3d_window_indep` is the separately written solver that checks
this one (HT note, d = 3 checks).

##### Requirements

`requirements.txt` (package) and `public/requirements.txt` (exact production versions: Python 3.11.9, numpy 2.3.5,
scipy 1.17.0, numba 0.65.1, llvmlite 0.47.0). Replay needs only numpy and scipy.

### `lri_3d_window_indep`

Folder: `code/lri_3d_window_indep/`.

#### lri_3d_window_indep: a separately written solver for the d = 3 window HT

A clean-room re-implementation of the finite model that `../lri_3d_window_hpc` solves: the dressed zero-mode
truncation on S² × ℝ with the vacuum window. It was written from the method description only, without reading or
importing the production code. It checks that the production code computes the stated model (HT note, d = 3
checks: 2×10⁻¹¹ at N ≤ 12, macro `\HTnpDthreeIndep`). It does not test whether the model's limit is the CFT.

Deliberately different choices from the production code:
- a complex Condon–Shortley Y_lm Fock space with all magnetic sectors;
- the J = 0 bath space from the null space of the Casimir J₋J₊ (dense eigh per species block), not an SVD null space;
- scalar vertices ⟨:χᵏ:⟩ evaluated at a generic sphere point and checked at a second one;
- the zero mode in a plain number-state basis, truncated to its K lowest local eigenstates (no trained density basis);
- window fixed points by bracketed Brent root finding;
- tuning by `scipy.optimize.root`.

##### Files (as they ran; verbatim)

| file | role |
|---|---|
| `indep_ht3d.py` | the solver: modes, Fock space, J = 0 projection, vertices, local basis, window, `Model.solve`, `Model.tune` |
| `indep_spin.py` | J = 1, 2 sectors (descendant diagnostics) |
| `run_compare.py` | one comparison: production (r, g) at K = 16 and 24, then independent tuning from a start displaced by 2% |
| `t_fixed.py`, `t_spin.py` | the session's quick checks at fixed couplings (scalar, J = 1, 2); a third, `t_basic.py`, is not shipped (it read a local file by an absolute path), and `public/test_indep.py` runs its checks |
| `indep_extract.json` | the production values (r, g, ΔE, gaps, window energies) of 181 records, extracted on 2026-10-08; replay checks every value it uses against the shipped records |
| `results/cmp_L*_*.json` | the 23 comparisons quoted (N = 8, 10, 12; window and raw) |
| `tasks.txt`, `*.sbatch` | the Expanse job list and job scripts that produced them |
| `public/` | `test_indep.py`, `replay_indep.py`, `INDEPENDENT_CHECK.md` (the full report), `slurm/` template |

##### Targets

```
make -f public.mk test      # structural checks + one fixed-coupling production point (~1 min, 1 core)
make -f public.mk replay    # the quoted agreement from the 23 comparison records (~1 s)
make -f public.mk rerun L=10 X=0.6 MODE=window   # one comparison from scratch (minutes to hours, see public.mk)
```

Requirements: Python ≥ 3.10, numpy, scipy ≥ 1.15 (`public/requirements.txt`).
