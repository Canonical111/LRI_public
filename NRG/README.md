# NRG: thermal dimension of the d = 1 long-range Ising model from bosonic NRG

This folder computes Δ_ε, the scaling dimension of the energy operator of the one-dimensional long-range Ising model,
at 13 values of Δσ = (1 − s)/2. The critical point is realised as the quantum critical point of the sub-ohmic
spin–boson model and solved with a bosonic numerical renormalization group (NRG). The exponent y_t = 1 − Δ_ε comes from
the exact derivative of the truncated NRG map with respect to the bath coupling. The study is d = 1 only.

The write-up is **`note/lri_nrg_1d_note.pdf`** (source `note/lri_nrg_1d_note.tex`). It is self-contained: physics,
method, estimator, error budget, code and validation, production, results, checks, limitations and reproduction.

## Result

Δ_ε at Λ = 3, K = 128 kept states per parity sector and n_b = 16 oscillator levels. The total error is in parentheses
(note §4, PDG rounding): the chain-depth error, the spread over K/n_b and the discretization error, added linearly. The
discretization error is the spread over Λ = 2–4 or, at 8 of the 10 final points, the larger allowance for the one K
doubling at Λ = 2.5. It is an error scale, not a standard deviation. Source: `results/ds13_final.json`.

| Δσ | s | Δ_ε | status | external test |
|---|---|---|---|---|
| 0.249 | 0.502 | [0.5080] | not converged in chain depth | ε series 0.499344 |
| 0.24 | 0.52 | [0.4989] | not converged in chain depth | ε series 0.49422 |
| 0.225 | 0.55 | [0.4897] | not converged in chain depth | ε series 0.48808 |
| 0.2 | 0.60 | 0.4830(7) | final, extrapolated | ε series 0.48292, spread 9e-3 |
| 0.175 | 0.65 | 0.48390(35) | final, extrapolated | MC label: cross-check failed (not used) |
| 0.15 | 0.70 | 0.49111(11) | final | MC label: cross-check failed (not used) |
| 0.125 | 0.75 | 0.50567(5) | final | MC label: accepted |
| 0.1 | 0.80 | 0.529608(33) | final | MC label: accepted |
| 0.075 | 0.85 | 0.566260(30) | final | MC label: accepted |
| 0.05 | 0.90 | 0.622115(27) | final | MC label: accepted |
| 0.025 | 0.95 | 0.713422(29) | final | MC label: accepted |
| 0.01 | 0.98 | 0.80975(5) | final | s → 1 expansion only |
| 0.001 | 0.998 | 0.93742(11) | final | s → 1 expansion only |

- **Estimator** (`code/analysis/estimator.py`, note §3.7). The value is the *settled window*: the window of the
  derivative fit where the critical flow is closest to its fixed point. Fits that include the departure from the fixed
  point (`code/analysis/crosscheck.py`, cross-check only) reproduce the plateau values to 3e-6. Where the window values around it are flat
  (plateau drift ≤ 5e-5, here 0.001 ≤ Δσ ≤ 0.15), that is the value. Where they are still drifting (0.175, 0.2), the
  local exponent is extrapolated along the RG time.
- **[bracketed]: not converged in chain depth.** Near s = 1/2 the correction exponent ω ≈ ε vanishes. Within the depth
  that double precision allows, the flow does not reach its fixed point, and the settled values lie +8.7e-3, +4.7e-3
  and +1.6e-3 above the ε expansion. The values are shown as computed, carry no error and are **not used in any
  comparison**. The label is not an outcome of the estimator: the author assigned it after the comparison with the
  series (note §3.7). At 0.225 the estimator alone would extrapolate, to 0.487529 with a depth error of 2.1e-3.
- **Estimator history.** Values published before 13 October 2026 used the midpoint of the quality range. That midpoint
  sits on the transient before the plateau and is superseded. The old values and the reason are in note App. E.

Checks (note §8):
- **Second implementation.** A separate Claude agent wrote a second solver from a physics-only specification, with no
  access log. It reproduces:
  - the chain coefficients to rounding (better than 1e-15);
  - the critical couplings bitwise, or to 7.2e-14;
  - Δ_E to 3.1e-7, window by window, in all 316 windows where its finite differences are reliable. These cover 228 of the
    296 production quality windows; the check does not test the estimator.
- **Monte Carlo** (the project's own study, `../MC`). There are five common points where the Monte Carlo value is
  ACCEPTED.
  - At four of them NRG lies within σ_stat + σ_sys + δ_tot.
  - At Δσ = 0.1 the difference is 1.08 times that sum.
  - NRG lies below the Monte Carlo fits at five consecutive points; only the Monte Carlo σ_sys reconciles the two.
  - The differences reach 14 Monte Carlo statistical errors. The sum σ_stat + σ_sys + δ_tot mixes a standard deviation,
    a fit-model half-range and an error scale, so it is a scale, not a test of statistical consistency.
  - The Monte Carlo crossing extrapolations agree with NRG within 1.05 σ_∞ at the five accepted points (1.06 at all
    seven common points, including the two that are not used).
  - The two CROSS-CHECK FAILED points are not infinite-size values and are not used as references.
- **s → 1.** The values reproduce the strong–weak dual expansion Δ_ε = 1 + Σ C^SR_n(1) Δσ^(n/2) (C^SR_1, C^SR_2 from
  Benedetti, Lauria, Mazáč and van Vliet, 2025/2026; C^SR_3 to C^SR_8 from the accompanying paper) through C^SR_5. At
  Δσ = 0.01 the difference shrinks from 4.7e-3 to 5.3e-5, the size of δ_tot, as C^SR_3 to C^SR_5 are added (note §7.5).

## Layout

| path | content |
|---|---|
| `note/` | the note: TeX source, PDF, generated `tables/` and `figures/` |
| `code/lri_spin_boson_hpc/` | the solver package `lri_spin` (commit `af9b1dc` minus files not needed here; see `PROVENANCE.md`), its 85 tests, the reference solver of the original study, and the cluster tools used in production |
| `code/campaigns/` | generators of the item lists in `inputs/items/` |
| `code/analysis/` | analysis: `summarize.py` (verify records), `estimator.py` (settled value, plateau test, extrapolation), `build_tables.py`, `make_figures.py`, `note_numbers.py`, `check_figures.py`; `collect_records.py` (cluster) |
| `inputs/` | item lists, the frozen manifests that were submitted, the validation receipt, the environment record |
| `data/` | the 197 result records, the lane logs and the job accounting; see `data/DATA.md` |
| `results/` | `ds13_final.json` / `ds13_final_table.md` (final table with all error components, fits and the superseded midpoint budget), `lambda_study.json` |
| `independent_check/` | the second implementation: `SPEC.md`, `indep_nrg.py`, `selftest.py`, `run_config.py`, `NOTES.md`, outputs `out/c1–c8.json` |
| `independent_check_compare/` | `compare.py`, `trusted_windows.py` and their outputs: second implementation against production |
| `method_comparison/` | `compare_methods.py` and its outputs: NRG against the Monte Carlo study and the ε series |
| `verify/` | `verify.py`, `expected.json`, `quoted_numbers.json` (the paper's NRG numbers), `smoke_check.py`, `smoke_expected.json` |
| `slurm/` | job templates with placeholders for other clusters |
| `REPRODUCE.md` | the reproduction steps, costs and checks, and the decisions you must not make |
| `results_map.md` | every NRG number the paper prints: its record, the command that recomputes it, its tolerance |
| `REVIEWS.md`, `PROVENANCE.md` | who wrote and reviewed what; what was changed for this release |

The solver package's own `README.md` and `docs/SYMMETRY.md` refer to files that were removed for this release
(`slurm/`, `docs/ALGORITHM.md`, `PERFORMANCE.md`, `review/`). They are hash-listed and were left unchanged. Use
`slurm/` here and note §3 instead.

## Quick start

```sh
python -m pip install -r requirements.txt
make test     # ~75 s: 85 solver tests, code checksums, 38 self-tests of the second implementation
make replay   # ~20-30 s: verify all records, recompute every result, table, number and figure of the note and every
              # NRG number of the paper (results_map.md), compare
make smoke    # ~15 s: one small critical search with both solvers against verify/smoke_expected.json
make note     # compile the note (pdflatex)
```

`make replay` also reads the Monte Carlo table of this repository, `../MC/data/1d/scan_data/FIT_V3_SCAN.json`. If you
copied only `NRG/`, point to it with `make replay MCSCAN=<path>`. Times are for one core of a recent laptop. The
extrapolations are least-squares fits, and some checks recompute numbers with the platform's libm, so replay compares
with tolerances, not byte for byte (`REPRODUCE.md` §6). Tested range: Python 3.10–3.12, NumPy 1.24–2.3, SciPy 1.11–1.17,
macOS arm64 and Linux x86-64.

Production took 178 thread-hours, or about 15 node-hours of whole 64-core nodes, on a Slurm cluster. It is described
in `REPRODUCE.md` §5.

## Who wrote what

- **Solver.** GPT-6 astra (OpenAI, via ChatGPT) wrote the reference solver and the optimized package.
- **Port and production.** Claude Code (Anthropic) ported the package to the cluster, ran production and wrote the
  analysis and the note. OpenAI Codex reviewed the cluster port, not the numerics or the analysis.
- **Reviews.** Claude Opus 5.5 agents reviewed the analysis and the note in two rounds (13 October 2026), and an
  independent reader reviewed the note's text on 15 October. This version follows them; the changes after the second
  round and after the reading have not been reviewed again.

Details: `PROVENANCE.md`, `REVIEWS.md`.
