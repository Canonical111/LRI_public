# HT/results/HT_1d: finite-coupling HT results in one dimension

| File | Content |
|---|---|
| `quoted_numbers.json` | every quoted d = 1 finite-coupling number: value as quoted, estimator ("rule"), comparison ("compare"); checked by `code/lri_dressed_phi4_hpc_analysis` (`make -f public.mk replay`) |
| `delta_eps_table.md` | Delta_eps at N = 40 and extrapolated, with status words, for the 13 values of Ds |
| `identity_violations.md` | level-1 descendant violations at N = 16..28, raw and with the window |
| `holdout_and_local_exponent.md` | held-out-cutoff fits and the local exponent omega_eff(N) |
| `nrg_reference.json` | byte copy of the NRG folder's final table (NRG/results/ds13_final.json, re-analysed 2026-10-13); used for every HT-NRG comparison |
| `model_dependence.md`, `model_dependence.json` | tail-model and prescription (raw vs window) dependence of the limits at 0.075 <= Ds <= 0.2, as measured shifts (`public/model_dependence_ht1d.py`, computed in the production analysis environment; the replay checks the shipped rows exactly and a refit within 2e-4) |
| `note_tables/` | the same tables as rows for the HT note |

The tables are written by `code/lri_dressed_phi4_hpc_analysis/public/make_tables_ht1d.py` from the shipped analysis
outputs and identity records; the replay regenerates them byte for byte. Errors are half-spreads of accepted fits
(model spreads, not confidence intervals). Status words (final, one-sided, unstable, no limit) are part of the results.
