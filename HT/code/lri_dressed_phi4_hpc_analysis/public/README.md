# lri_dressed_phi4_hpc_analysis: the d = 1 finite-coupling HT analysis

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

## Targets (run from `HT/code/lri_dressed_phi4_hpc_analysis`)

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

## Added for the public release (`public/`)

- `replay_ht1d.py`: the replay.
- `make_tables_ht1d.py`: writes the published tables.
- `model_dependence_ht1d.py`: the model-dependence diagnostic.
  - It tries two alternative tail models of the window series: F4 with two free exponents, and a drifting local
    exponent.
  - It computes a fit-free bracket.
  - It extrapolates the raw prescription with the same fits.
  - It reports these shifts as measured and does not combine them into an error.
- `selftest.py`: the self-test of `make test`.

## Estimators that are easy to get wrong

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
