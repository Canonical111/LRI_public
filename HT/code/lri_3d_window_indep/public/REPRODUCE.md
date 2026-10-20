# Reproducing the d = 3 independent-solver check

From `HT/code/lri_3d_window_indep`:

1. **Replay (seconds).** `make -f public.mk replay` recomputes from the 23 shipped comparison records:
   - INDEP-TUNED: max |ΔE(indep, tuned) − ΔE(production)| = 1.89e-11, quoted as 2e-11;
   - INDEP-FIXED: ≤ 1.7e-12 at the production couplings, K = 16;
   - INDEP-RESID: every independent tuning converged to ≤ 1e-12;
   - INDEP-PKG: the production values each comparison used equal the shipped production records in
     `HT/data/HT_3d/campaigns` and `indep_extract.json`. The raw-scheme comparisons use the `raw_L10` side-step
     records, which are shipped for this reason.
2. **Test (about 10 s; passed on symmetry, AMD and Intel, 2026-10-13).** `make -f public.mk test`:
   - the Gegenbauer identity behind the mode weights;
   - the J = 0 state counts 3, 10, 33, 110 at N = 2, 4, 6, 8, equal to those of the perturbative package;
   - rotation invariance of the vertices;
   - the free spectrum;
   - one production point at fixed couplings (N = 8, Ds = 0.7) to 1e-10.
3. **Rerun.** Each comparison is one `run_compare.py` call; `tasks.txt` lists the Expanse array (N, scheme, Ds).
   - The first runs of three L12 tunings (Ds = 0.7499, 0.55, 0.518149) started 8% + 0.01 away from the production
     couplings and failed with NaN in the local diagonalisation.
   - They were rerun with the 2% multiplicative start that `run_compare.py` now uses, in jobs 54771132, 54771237
     and 54772616.
   - Wall time per comparison, from the records' `seconds` (Expanse `shared`, 4–8 cores, 16–24 GB requested):
     - N = 8 window: 0.7–3.3 min;
     - N = 10: 0.5–0.8 min raw, 2.4–3.4 min window;
     - N = 12 window: 6–8 min setup, 9 min to 3.1 h in all.
