# c2_cylinder_d2: c_2 in d = 2 from the truncated cylinder Hamiltonian

Near s_* = 7/4 the two-dimensional long-range Ising model is the short-range Ising CFT coupled to a generalized free
field chi of dimension 15/8 - delta. Here delta = (7/4 - s)/2 and Delta_epsilon = 1 + c_2 delta^2 + O(delta^3).
This package computes c_2 numerically, without the closed form.

- Fourth-order Rayleigh-Schroedinger perturbation theory on the cylinder at delta = 0, in the Ising CFT x GFF basis,
  gives the coefficient h(lambda) at finite regulator lambda (orders r = 1, 2, 3) and coefficient-box cutoff N.
  Then C2 = -pi^2/(4 b0) + h0/b0^2, with b0 = 9 pi^4/(4 Gamma(1/4)^4) and h0 = lim h(lambda) as lambda -> 0.
- Each point (r, lambda) is extrapolated in N (fractional windows {5N/8, 3N/4} of the partial sums, N <= 1024). The
  error components of each point are kept separately: the spectral model, the mixed, collapsed and tail cutoffs, the
  grid extraction and roundoff.
- The extrapolation lambda -> 0 uses pre-declared regulator models with an admissibility rule. Each order gets a fit,
  and a joint fit shares h0 across the three orders. A pre-declared outcome table chooses the quoted estimator.
- Result (outcome branch 4, the joint fit, with all 25 points measured for extraction):
  **C2 = -4.0670498 +- 0.0023580** (h0 = -3.4136088 +- 0.0037937).
  - The error is a linear sum of systematic diagnostics, 64 % of it the choice of regulator model. It is not a
    standard deviation.
  - The per-order values are -4.06739, -4.06653 and -4.06622.
  - The closed form is -4.0662701481: the result is 1.9e-4 from it in relative terms, or 0.33 of the error.

Paper:
- `\SRtwoCtwoHT` = -4.0670(24) (Sec. "Near the short-range end", d = 2, and Table `tab:htpert`) and
  `\SRtwoCtwoHTDev` = 2x10^-4 (Table `tab:htpert`); `\SRtwoCtwoHTNmax` = 1024 is defined but not
  printed (an INFO row of the replay);
- the C^SR_2(2) (c_2) row of Table `tab:htpert` and its caption (the footnote (f) of the 2026-10-14 paper was folded into the caption and the text).

Status:
- The analysis plan (rev 7) was approved by Codex.
- Codex inspected the code twice. The second round's hardening fixes are uninspected; they changed no number.
- Deviation D1 was approved by the author.

| Path | What |
|---|---|
| `code/hamiltonian/` | the solver of the supplied study (coefficient grids, fourth-order partial sums, local counterterms, leading tails); its 29 modules define the science-source identity of every record |
| `code/continuum/` | the arbitrary-N continuum analysis: `continuum_driver.py` (run, check, sync, legacy), `continuum_analysis.py` (rules M1-M8), `continuum_records.py` (verified record pools), `continuum_report.py`, `continuum_legacy.py` (legacy mode A1), `aux_inputs.py` + `aux_job.sbatch` (auxiliary-input job), `test_continuum.py` |
| `cluster/` | production launch layer for SDSC Expanse and symmetry (`sitekit/`, site profiles, plans, tests) |
| `outputs/` | the 16 production records, 25 extraction-check records, the auxiliary-input job and the three merged indexes |
| `data/hamiltonian/` | the 17 archived records of the supplied study and their references |
| `results/continuum_2026-10/` | `CURRENT` -> `generations/20261015T000632Z_99019_1e66b9/` (`C2_estimate.json`, `continuum_points.json`, `regulator_fits.json`, `REPORT.md`); the evidence the driver reads |
| (not shipped) `note/lri_c2_progress.tex`, `.pdf` | the supplied study's note (12 October 2026) is not shipped since 16 October 2026 (one note per direction; listed in `public/NOT_EXPORTED.txt`). Its method is the SRI note, Appendix F; the continuum analysis is the SRI note, Sec. 3.8, and `results/continuum_2026-10/REPORT.md` |
| `README.md`, `MANIFEST.sha256`, `provenance/` | the repository's own README, checksum list (verbatim) and revision notes |
| `public.mk`, `public/` | public targets: `test`, `replay`, `replay-full` |

The repository README describes the whole repository; the public export ships a subset. Commands of that README for
parts that are not shipped (`certify`, `formula-checks`, `original-study`, `legacy-checks`, `scripts/verify_manifest.py`)
do not run here: use `public/verify_manifest_public.py`, and the sibling package `c2_closed_d2` for the closed form.

Caveats:
- The result is not a rigorous enclosure.
- The regulator extrapolation dominates the error: the spread of the admissible joint models is 1.5e-3 of the
  2.4e-3 in C2.
- The error rule was revised (rev 4 -> rev 7) after the first result was seen; the central value did not change.
- The extraction comparisons measure the sensitivity to the Cauchy grid; they do not bound an error that both grids
  share.
