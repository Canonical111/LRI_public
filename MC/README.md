# Monte Carlo: Δε of the long-range Ising model in d = 1, 2, 3

This folder holds the cluster Monte Carlo (MC) part of the paper: the code, the merged production records, the expected outputs, and a
self-contained note (`note/lri_mc_note.pdf`) that explains the method and every result. Read the note for the physics. Read
`REPRODUCE.md` to rerun anything.

## What is computed

The model is the ferromagnetic Ising model on a periodic hypercubic lattice of side L, with couplings
J(r) = Σ_images |r + L n|^−(d+s). On the long-range line the spin dimension is exact, Δσ = (d − s)/2. The quantity computed is the
dimension Δε of the leading Z2-even scalar, with 1/ν = d − Δε, as a function of Δσ.

- **Simulation:** the Fukui–Todo cluster algorithm, whose cost per sweep is O(N) for long-range couplings. The number of kept bond events
  gives exact temperature derivatives and exact reweighting.
- **Observables:** the scaled susceptibility Y = L^(d−s)⟨m²⟩, the Binder ratio U4 (also U6 and U8), and their exact derivatives.
- **d = 1:** a global finite-size-scaling fit of Y, U and their derivatives, cross-checked by extrapolating U-crossings. N = 2^10 … 2^19,
  20 couplings.
- **d = 2, 3:** effective dimensions at the U4 crossing of size-doubling pairs, extrapolated with one correction power.
  d = 2 uses L = 64 … 1024 and d = 3 uses L = 8 … 128, 8 couplings each.

Each coupling receives one label from a fixed decision table (note §4). Only ACCEPTED and ACCEPTED (σ_sys-dominated) mean that a value
passed the protocol. When and how the rules were fixed, and what data had been seen at that time, is in note §5 and
`protocols/PROTOCOL_HISTORY.md`.

## Results and status

| | result | limitations |
|---|---|---|
| d = 1 | 9 of 20 couplings pass, with σ_stat = (2.0–5.5) × 10⁻⁴ and σ_sys = (0.8–9.6) × 10⁻³. E.g. Δε(0.05) = 0.61987(55)(220). All 9 are within 0.0032 of the eight-loop resummed ε expansion. | See limitations 1–4 below. |
| d = 2 | **No infinite-size value.** Finite-size Δ_eff(U4, 512→1024) = 0.958–0.977 at all eight couplings, σ ≈ 0.002. These agree with the resummed expansion to 0.002 for s = 1.2–1.4. | The two CONDITIONAL single-series values at s = 1.05 and 1.1 lie 0.05–0.065 below the expansion. Do not use them as infinite-size estimates. |
| d = 3 | One value passes: Δε(s = 1.6) = 1.47314 ± 0.00118 (stat) ± 0.00230 (sys). It is consistent with the expansion (1.4721). | Accepted only under amendment P1, adopted after the data were evaluated; the last P1 code fixes are uninspected. Near the short-range end the extrapolations are 0.022–0.033 above the expansion. |

Notation: in v(a)(b), a is σ_stat and b is σ_sys, in units of the last digits.

Known limitations. They apply to every file in this folder.
1. **σ_sys is a model-family half-range, not a standard deviation.** Never add it to σ_stat in quadrature. An independent audit found the 1D
   values at Δσ = 0.025, 0.175 and 0.225 sensitive to the size cut or the correction model, and those at 0.1, 0.1375 and 0.1727335 stable
   (note §6.4).
2. **Two 1D labels depend on the platform.** Rerunning the fits elsewhere reproduces all 17 quoted values to ≤ 10⁻⁸. The labels differ at
   Δσ = 0.1625 (CONDITIONAL ↔ ACCEPTED) and 0.1727335 (ACCEPTED ↔ CONDITIONAL). The cause is a fragile step of the degree ladder
   (note §6.4.1). A sensitivity study with a robust ladder is in note §6.4.2.
3. **The 1D fits lie above the crossing extrapolations by a common +0.0010(3).** The cross-check failures at Δσ = 0.15 and 0.175 pass on a
   finer exponent grid. The quoted fits at Δσ = 0.1 and 0.125 have χ² probabilities ≈ 5 × 10⁻⁵ (note §6.4).
4. **The 1D rules were not all fixed before the data.** The protocol was rewritten after 8 000 of the 10 240 chains had been analysed, and
   its fit windows come from fits of those chains. Two gates were replaced after couplings had failed them, and four of the nine accepted
   labels (0.025, 0.05, 0.0875, 0.125) depend on that. The rule of the N0 diagnostic, which released the last campaign, was amended twice
   after its data had been seen (note §5).
5. **3D s = 1.6:** the U4–Y cross-check has little power there, and the label rests on amendment P1 (note §7.2, §9).

Open items: 2D L = 2048 and 3D L = 256 at selected couplings; a reviewed amendment of the 1D ladder rule; a broader 1D model family;
inspection of the last P1 code fixes (note §11).

## Cost

Slurm core-hours from 2026-09-03 to 2026-10-13, including development and repeated runs:
- d = 1: 9.8 × 10⁴;
- d = 2, 3: 8.4 × 10⁴.

Replaying every published number from `data/` takes minutes on a workstation (`make replay`). REPRODUCE.md §5 gives the production rates
and layouts.

## Layout

```
README.md, REPRODUCE.md   this file; the reproduction steps, for agents and people
PROVENANCE.md, REVIEWS.md where the records came from; summary of the independent reviews
RE-PINNED.json            original and published SHA-256 of the 25 records scrubbed after the results
Makefile                  test, replay, smoke, fetch-data, note, clean, verify and the specialist targets (make help)
requirements.txt          Python packages with version floors
note/                     lri_mc_note.tex, lri_mc_note.pdf (self-contained; pdflatex, 3 passes)
protocols/                FIT_MODEL_V3 rev 14, FIT_MODEL_2D, FIT_MODEL_3D (rev 7, plus the approved rev 5 and the diff),
                          AMENDMENT_PROFILED_SIGMA (+ .sha256), IMPLEMENTATION_P1, PROTOCOL_HISTORY.md
code/
  1d/                     1D engines (src/, src_1d/), campaign tools (prepare*.py/.sh, submit.py, run_task.py), analysis (analyze.py,
                          merge_summaries.py, …), fit pipeline (select_model_v3.py, select_model.py, fit_fss.py, quotients.py),
                          scan_v3_report.py, tests/
  1d_report_tools/        1D table rows and figures
  2d3d_engine/            2D/3D sampler, pack_histograms.py, multihist.py (reweighting), precision_analysis.py, tests; reference engine
  2d/, 3d/                evaluate_2d.py, evaluate_3d.py (frozen rule and amendment P1; hash-bound), make_plan.py
  reanalysis_p1/          calibrate_p1.py and the 56 tests of amendment P1 (hash-bound); reanalyse.py, the tests' reference implementation
  oned_xcheck/            the 1D cross-check study (note Table 8)
  package_tools/          assemble_workspace.py, compare_outputs.py, make_note_tables.py, index_prefix.py, refit_1d_point.sh
data/                     DATA.md and the merged production records:
                          1d/scan_data/  per coupling: the selected fit run, snapshot manifests, completion evidence, registry
                          2d/prod, 3d/prod  analysis records at blocks 1000/2000/4000, campaign manifests, histogram indices,
                                         the pinned production evaluations; temperature-centre tables; 3d/preflight (gate records)
                          reference/     theory (eight-loop resummation) and literature values, used only for comparison
results/                  expected outputs: P1 evaluations, the P1 calibration (an input of eval-p1), 1D tables and figures and
                          their input records, the cross-platform refits, the robust-ladder study (with its modified fitter) and
                          the cross-check study
slurm/                    submission templates with placeholders (slurm/README.md)
```

**Hidden workspace.** The evaluators bind themselves and the protocols by SHA-256 and find their inputs relative to the layout they ran in.
Every target therefore runs inside `.work/` (git-ignored), which `make` builds in that layout. The code is copied byte-identically and the
data are linked. Outputs go to `.work/reproduced/`.

**Records.** The production records are released byte-identical, because their SHA-256 bindings are part of the evidence that nothing
changed after the results. They name the cluster paths, user and compute nodes on which they were written; the code never resolves those
paths. Exception: 25 records that named a personal machine were scrubbed after the results (host labels, a home directory and file names
only; no number changed) and re-pinned. `RE-PINNED.json` lists their original and published SHA-256, and `make verify` maps one to the
other. Files in `code/1d` are unchanged; only those needed for tests, replay or a production rerun are released (PROVENANCE.md).

**Not in git.** `make fetch-data` downloads the first two from the project's Zenodo data record,
[doi:10.5281/zenodo.23466766](https://doi.org/10.5281/zenodo.23466766), and checks them against the SHA-256 in
`data/HOSTED.json` (data/DATA.md):
- needed by `refit1d`: the 1D block archives (1.43 GB) and merged summaries (25 MB) of the selected snapshots, `MC__1d_refit_inputs.tar.gz`;
- for inspection only: the per-degree fits (140 MB), `MC__1d_fits_per_degree.tar.gz`;
- needed only to regenerate the records: the raw data (1D 0.655 TB; 2D and 3D trees, 257.5 GiB and 237.2 GiB). They are not hosted; they
  are available from the author on request.

## Licence and citation

Licence: the code is under the MIT licence (`LICENSE` at the top of the repository) and everything else under CC BY 4.0
(`LICENSE-CC-BY-4.0.txt`), as stated in the repository's README. The exception in this folder is the delivered 2D/3D engine,
`code/2d3d_engine/`, which keeps its own MIT licence ("Copyright (c) 2026 Contributors", `delivery_LICENSE`). Citation: the accompanying
article (see `CITATION.cff`). Who wrote which code is stated in `PROVENANCE.md`.
