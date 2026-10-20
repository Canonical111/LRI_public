# N = 24 valley scan, Δσ = 0.125 and 0.126 (2026-10-10)

**Question.** Do the two tuning conditions have a root at bath cutoff N = 24 for Δσ ≤ 0.126? There, the production
Newton solve stalled, and so did restarts from an extrapolated seed and with a finite-difference Jacobian.

**Method** (`HT/code/lri_2d_window_hpc/public/scan_valley.py`). The code is release afe69ab = 889a968 +
`public/afe69ab.diff`; the scan calls only `DensitySolver.spectrum`, which is unchanged between the two. Settings and
bases are those of production (nz = 16; bases `inputs/x0.125/L6_z24.json` and `inputs/x0.126/teacher_L6_x0.126.json` of
`HT/data/HT_2d/prod1`). The tuning conditions are f1 = E_σ − E_v − Δσ and f2 = E_χ − E_v − (2 − Δσ). For each θ0, a
secant in θ1 solves f2 = 0 to |f2| ≤ 1e-9 (4–5 evaluations at N = 24), and f1 is recorded there. A sign change of f1 along
f2 = 0 would bracket a root. The runs used Expanse shared nodes: 12 jobs of 64 cores and 64 GB, 3.2–4.9 h each, about
3.0k core-hours.

**Files.** `prod_x<Δσ>_L24_t<θ0>.json`. Each row is one evaluation (θ, f1, f2, the three lowest even and odd energies,
seconds). The last row (`summary: true`) gives θ1 on f2 = 0 and f1 there. f1 and f2 can be recomputed from the energies
(f1 = E_odd[0] − E_even[0] − Δσ, f2 = E_odd[1] − E_even[0] − (2 − Δσ)), and the replay checks this.

| θ0 | 12.5 | 13.25 | best* | 14.3 | 14.8 | 15.5 | minimum (quartic fit) |
|---|---|---|---|---|---|---|---|
| f1, Δσ = 0.125 | 6.124e-3 | 3.618e-3 | 2.701e-3 | 2.803e-3 | 3.682e-3 | 6.529e-3 | 2.686e-3 at θ0 ≈ 14.03 |
| f1, Δσ = 0.126 | 5.107e-3 | 2.550e-3 | 1.604e-3 | 1.651e-3 | 2.482e-3 | 5.250e-3 | 1.556e-3 at θ0 ≈ 14.06 |

\*best = the best point of the stalled Newton solves: θ0 = 13.934717… (0.125) and 13.883939… (0.126). The first
evaluation there reproduces their residual, max(|f1|, |f2|) = 2.93e-3 and 1.99e-3.

**Result.**
- f1 > 0 everywhere on f2 = 0. It has an interior minimum and rises steeply on both sides.
- So there is no root at N = 24 for Δσ = 0.125 or 0.126 on the branch continued from N ≤ 22. The margin, 1.6–2.7e-3,
  is about 10^4 times the nz truncation (≤ 5e-7).
- The minimum falls by 1.13e-3 per 0.001 in Δσ. At a saddle-node it is linear in the parameter, so the N = 24 fold
  sits at **Δσ ≈ 0.1274**. This is an estimate from two values of Δσ.
- Above the fold, roots exist: Δσ = 0.135 converged at N = 24.
- The d = 2 data at Δσ = 0.125 and 0.126 therefore end at N = 22.

Replay: `make -f public.mk replay` in `HT/code/lri_2d_window_hpc` (checks d2.valley.*, d2.no_root, d2.fold).
