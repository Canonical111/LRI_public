# Arbitrary-N continuum analysis of the 2D LRI C2 Hamiltonian records

Generation `20261015T000632Z_99019_1e66b9` (results are published as immutable generations under `generations/`; the file `CURRENT` names the current one, and the top-level files are copies of it).

Generated 2026-10-15T00:06:31.043867+00:00 by `code/continuum/continuum_driver.py run` (python 3.13.5, numpy 2.3.5, macOS-26.6.2-arm64-arm-64bit-Mach-O). Plan: `LRI_C2_expanse_loop/PLAN_ANALYSIS.md` rev 7 (sha256 f76af1bfb81f...). All selection rules are fixed in `continuum_analysis.RULES` and copied into every JSON output. No proposed closed form of C2 is an input, a prior or a selection criterion. All uncertainties are linear sums of systematic numerical diagnostics, **not rigorous bounds and not standard deviations**.

Files: `continuum_points.json` (every point, all M1-M4 diagnostics), `regulator_fits.json` (every deduplicated regulator fit with its admissibility), `C2_estimate.json` (per-order and joint results, error budget, outcome branch, rules, input hashes), `evidence/` (cluster job receipts, logs, legacy reproduction).

Approved deviations from the plan (operational; no rule changed): D1 — 2026-10-13, user-approved: A6-1 stages A and B run on symmetry instead of Expanse (evidence/DEVIATIONS_ANALYSIS.md).

## Result

Extraction coverage: **extraction coverage complete** (25 of 25 primary points have a direct full-coverage extraction comparison).

Outcome-table branch **4**: joint fit (orders consistent, joint fit validated).

- h0 = -3.413609 +- 0.003794
- **C2 = -4.06705 +- 0.00236** (C2 = -pi^2/(4 b0) + h0/b0^2, b0 = 1.268404308939143; dC2 = dh0/b0^2 = 0.62156 dh0)

| order | S_r | validation | h0_r | E_r | C2_r | dC2_r | status |
|---|---|---|---|---|---|---|---|
| 1 | preferred admissible | 30 distinct admissible fits | -3.414150 | 0.016186 | -4.06739 | 0.01006 | retained |
| 2 | preferred admissible | 29 distinct admissible fits | -3.412774 | 0.006705 | -4.06653 | 0.00417 | retained |
| 3 | preferred admissible | 26 distinct admissible fits | -3.412269 | 0.005563 | -4.06622 | 0.00346 | retained |

Order consistency (|h0_r - h0_r'| <= E_r + E_r'):

| orders | \|difference\| | E_r + E_r' | consistent |
|---|---|---|---|
| 1-2 | 1.376e-03 | 2.289e-02 | yes |
| 1-3 | 1.881e-03 | 2.175e-02 | yes |
| 2-3 | 5.045e-04 | 1.227e-02 | yes |

Envelope of the retained orders: [-3.430336, -3.397964] = -3.414150 +- 0.016186 in h0.

Joint fit (shared h0, each order with its S_r): h0 = -3.413609, accepted = yes, condition 2.42e+04, 22 distinct admissible joint variants of 84, eps_model,joint = 2.440e-03, E_joint = 3.794e-03; C2 = -4.06705 +- 0.00236.

| block (order) | points | terms | weighted | block dof | max \|res\| | limit | passed |
|---|---|---|---|---|---|---|---|
| 1 | 9 | 2,2log,3 | no | 5 | 1.689e-04 | 1.056e-03 | yes |
| 2 | 7 | 2,2log,3 | no | 3 | 1.600e-04 | 6.264e-04 | yes |
| 3 | 7 | 2,2log,3 | no | 3 | 2.043e-04 | 2.306e-04 | yes |

Superseded rev-4 result (evidence/rev4/, L1 extraction rule with inheritance): branch 4, h0 = -3.413609 +- 3.558, C2 = -4.06705 +- 2.211; E_r = 3.227 (r=1), 6.502 (r=2), 0.516 (r=3). The central values are unchanged by construction; only epsilon_grid changed.

## Caveats

- Limitation (M4d): a difference between two Cauchy grids measures extraction sensitivity. It does not bound an extraction error that both grids share.
- Extraction (M4d, rev 6/7): epsilon_grid = |v.s| + sum|v||rho| on each selected window (cubic smooth part with its measured sign, rough residual at worst-case signs), the maximum over the selected fits and over every full-coverage comparison of the point. Over the 28 full-coverage comparisons, max|rho| is 1.90e-11 to 1.93e-09 against max|delta| 7.98e-08 to 7.09e-05. The superseded rev-4 L1 sum|v||delta| on the same profiles is reported per point and in the budget (not in E).
- The M4d comparisons differ in size by check grid: radius_cost 4: max |delta_n| 1.76e-05 to 7.09e-05; radius_cost 4.5: max |delta_n| 7.98e-08 to 3.28e-06. A difference between two grids does not say which grid carries it; the variant grid (radius_cost 4.0) has a larger Cauchy radius and so more aliasing than the production grid (4.5).
- Partial overlaps reported but never used for epsilon_grid: k3_a0.2_N384_o4_r4.5_m4096_t2048_c800000_archived_archived vs k3_a0.2_N256_o5_r4_m4096_t2048_c200000_archived_archived (n <= 256 of 384: PARTIAL, reported only, never used for epsilon_grid, max |delta| 2.29e-06); k1_a0.1_N384_o4_r4.5_m4096_t2048_c800000_archived_archived vs k1_a0.1_N256_o5_r4_m4096_t2048_c200000_archived_archived (n <= 256 of 384: PARTIAL, reported only, never used for epsilon_grid, max |delta| 1.53e-06); k2_a0.125_N384_o4_r4.5_m4096_t2048_c800000_archived_archived vs k2_a0.125_N256_o5_r4_m4096_t2048_c200000_archived_archived (n <= 256 of 384: PARTIAL, reported only, never used for epsilon_grid, max |delta| 3.28e-06).
- Points below the lambda*N science minimum (flag only, M4c): (1, 0.125, N=256, lambda N=32.0), (1, 0.15, N=256, lambda N=38.4), (2, 0.175, N=256, lambda N=44.8), (3, 0.25, N=256, lambda N=64.0), (3, 0.5, N=128, lambda N=64.0).
- Legacy mode (A1), from the inspected receipt `results/continuum_2026-10/evidence/legacy_macos/legacy_reproduction.json` (sha256 46f9e32ab870...; platform macOS-26.6.2-arm64-arm-64bit-Mach-O, python 3.13.5, numpy 2.3.5): **PASSED**. Same-machine byte identity with the pristine 474487c run: 3 of 3 files; cross-platform category checks against the shipped reference passed: 3 of 3 files (largest value difference 2.161e-05, representative C2 4.505e-10, condition numbers 1.546e-02 relative); byte identity with the shipped reference: 0 of 3 files.

## Error budget (M8)

Each component is sum_i |w_i| eps_i through the influence row of the quoted fit (L1, worst-case signs). The "of which" lines under eps_prop split it by the parts of eps_spec = max(half-spread, prefix drift, cross-N) and are not additive; those under eps_grid give its smooth and rough parts (for rev-4 exceptions both are counted as 0 there). The rows "rev-4 L1 (superseded)" and "signed shift" are reported through the same weights and are NOT in E.

| component | order 1 (h0) | order 2 (h0) | order 3 (h0) | joint (h0) | joint (C2) |
|---|---|---|---|---|---|
| spectral, propagated (sum \|w\| eps_spec) | 6.107e-04 | 8.724e-04 | 4.904e-04 | 6.506e-04 | 4.044e-04 |
|   of which: spectral-model half-spread (breakdown, not additive) | 6.107e-04 | 6.905e-04 | 2.775e-04 | 5.838e-04 | 3.628e-04 |
|   of which: prefix drift \|h(N)-h(3N/4)\| (breakdown, not additive) | 1.663e-04 | 5.479e-04 | 4.244e-04 | 2.816e-04 | 1.750e-04 |
|   of which: cross-N (breakdown, not additive) | 4.148e-08 | 0.000e+00 | 0.000e+00 | 2.717e-08 | 1.689e-08 |
| mixed cutoff and mixed-model spread | 1.413e-04 | 1.021e-03 | 2.582e-04 | 3.440e-04 | 2.138e-04 |
| tail cutoff (2048 vs 8192) | 1.925e-09 | 8.629e-09 | 7.158e-09 | 4.043e-09 | 2.513e-09 |
| collapsed cutoff (400000 vs 800000) | 6.900e-05 | 1.858e-04 | 1.088e-04 | 9.913e-05 | 6.162e-05 |
| grid/coefficient extraction (M4d, rev 6/7: \|v.s\| + sum\|v\|\|rho\|) | 9.653e-05 | 2.385e-04 | 4.771e-05 | 1.203e-04 | 7.480e-05 |
|   of which: smooth part \|v.s\| (breakdown) | 5.168e-05 | 1.801e-04 | 1.303e-05 | 7.394e-05 | 4.596e-05 |
|   of which: rough part sum\|v\|\|rho\| (breakdown) | 4.484e-05 | 5.846e-05 | 3.468e-05 | 4.640e-05 | 2.884e-05 |
| rev-4 L1 sum\|v\|\|delta\| (superseded, not in E) | 2.700e+00 | 5.831e+00 | 2.888e-01 | 3.049e+00 | 1.895e+00 |
| signed shift \|sum v delta\| (reported, not in E) | 5.557e-05 | 1.808e-04 | 1.676e-05 | 7.713e-05 | 4.794e-05 |
| roundoff (M4e) | 1.157e-04 | 2.172e-04 | 1.364e-04 | 1.401e-04 | 8.706e-05 |
| regulator model | 1.515e-02 | 4.170e-03 | 4.522e-03 | 2.440e-03 | 1.516e-03 |
| **total E (linear sum)** | 1.619e-02 | 6.705e-03 | 5.563e-03 | 3.794e-03 | 2.358e-03 |

Share of the quoted E_joint by component: spectral, propagated (sum |w| eps_spec): 17.1%; mixed cutoff and mixed-model spread: 9.07%; tail cutoff (2048 vs 8192): 0.000107%; collapsed cutoff (400000 vs 800000): 2.61%; grid/coefficient extraction (M4d, rev 6/7: |v.s| + sum|v||rho|): 3.17%; roundoff (M4e): 3.69%; regulator model: 64.3%.

Share of E_1: eps_prop 3.77%, eps_mix 0.873%, eps_tailcut 1.19e-05%, eps_coll 0.426%, eps_grid 0.596%, eps_round 0.715%, eps_model 93.6%.
Share of E_2: eps_prop 13%, eps_mix 15.2%, eps_tailcut 0.000129%, eps_coll 2.77%, eps_grid 3.56%, eps_round 3.24%, eps_model 62.2%.
Share of E_3: eps_prop 8.82%, eps_mix 4.64%, eps_tailcut 0.000129%, eps_coll 1.96%, eps_grid 0.858%, eps_round 2.45%, eps_model 81.3%.

Order consistency: largest pairwise |h0_r - h0_r'| = 1.881e-03 (C2: 1.169e-03). Quoted: branch 4, E(h0) = 3.794e-03, E(C2) = 2.358e-03.

## Fixed-regulator points (PRIMARY pool, M5)

h is the median of the accepted selected M3 fits with aligned auxiliary inputs (mixed 16384, collapsed 800000, tail 8192). eps_spec = max(half-spread, |h(N)-h(3N/4)|, eps_cross).

| r | lambda | N | lambda N | h(lambda) | half-spread | prefix d34 | eps_cross | eps_spec | eps_mix | eps_coll | eps_grid | eps_round | eps_tailcut | fits acc. |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 0.05 | 1024 | 51.2 | -3.489852540 | 1.972e-04 | 4.170e-05 | - | 1.972e-04 | 4.594e-05 | 3.392e-05 | 4.739e-05 | 5.096e-05 | 9.928e-10 | 8/8 |
| 1 | 0.0625 | 1024 | 64.0 | -3.517417833 | 3.031e-05 | 3.574e-06 | - | 3.031e-05 | 3.463e-05 | 1.470e-05 | 1.977e-05 | 1.867e-05 | 3.014e-10 | 8/8 |
| 1 | 0.075 | 768 | 57.6 | -3.545337213 | 3.881e-05 | 6.375e-06 | - | 3.881e-05 | 2.196e-05 | 7.425e-06 | 6.149e-06 | 1.427e-05 | 1.738e-10 | 8/8 |
| 1 | 0.0875 | 768 | 67.2 | -3.572773395 | 1.003e-05 | 4.353e-07 | - | 1.003e-05 | 3.833e-05 | 4.169e-06 | 2.197e-06 | 7.330e-06 | 7.922e-11 | 8/8 |
| 1 | 0.1 | 768 | 76.8 | -3.599025521 | 2.803e-06 | 3.772e-07 | 6.043e-08 | 2.803e-06 | 2.155e-05 | 2.529e-06 | 1.599e-06 | 4.277e-06 | 3.652e-11 | 8/8 |
| 1 | 0.125 | 256 | 32.0 | -3.645695922 | 3.521e-04 | 1.329e-04 | - | 3.521e-04 | 1.437e-05 | 1.097e-06 | 5.681e-06 | 1.773e-05 | 1.049e-10 | 8/8 |
| 1 | 0.15 | 256 | 38.4 | -3.681585771 | 8.773e-05 | 2.126e-05 | - | 8.773e-05 | 5.405e-07 | 5.545e-07 | 2.185e-06 | 6.380e-06 | 2.284e-12 | 8/8 |
| 1 | 0.2 | 256 | 51.2 | -3.710096387 | 7.857e-06 | 6.826e-07 | - | 7.857e-06 | 1.560e-06 | 1.889e-07 | 7.950e-07 | 1.469e-06 | 1.189e-12 | 8/8 |
| 1 | 0.25 | 256 | 64.0 | -3.669024229 | 9.117e-07 | 3.391e-07 | - | 9.117e-07 | 1.196e-06 | 8.182e-08 | 2.357e-07 | 5.258e-07 | 2.082e-12 | 8/8 |
| 2 | 0.0625 | 1024 | 64.0 | -3.437960431 | 2.088e-04 | 1.030e-04 | - | 2.088e-04 | 3.216e-04 | 5.507e-05 | 7.448e-05 | 5.792e-05 | 2.700e-09 | 8/8 |
| 2 | 0.075 | 1024 | 76.8 | -3.450360197 | 4.694e-05 | 1.232e-05 | - | 4.694e-05 | 1.333e-04 | 2.780e-05 | 4.428e-05 | 2.719e-05 | 1.004e-09 | 8/8 |
| 2 | 0.1 | 768 | 76.8 | -3.482445342 | 2.162e-05 | 4.921e-06 | - | 2.162e-05 | 2.657e-05 | 9.459e-06 | 4.308e-06 | 1.319e-05 | 3.347e-10 | 8/8 |
| 2 | 0.125 | 768 | 96.0 | -3.524103987 | 1.779e-06 | 1.724e-06 | - | 1.779e-06 | 1.569e-05 | 4.100e-06 | 2.212e-06 | 5.716e-06 | 1.002e-10 | 8/8 |
| 2 | 0.15 | 768 | 115.2 | -3.574877309 | 7.383e-07 | 1.271e-06 | - | 1.271e-06 | 9.844e-06 | 2.071e-06 | 1.307e-06 | 3.068e-06 | 3.925e-11 | 8/8 |
| 2 | 0.175 | 256 | 44.8 | -3.634122296 | 4.406e-05 | 1.467e-04 | - | 1.467e-04 | 1.380e-05 | 1.164e-06 | 3.502e-06 | 9.440e-06 | 1.358e-10 | 8/8 |
| 2 | 0.25 | 256 | 64.0 | -3.855379305 | 1.996e-06 | 4.962e-06 | - | 4.962e-06 | 1.159e-05 | 3.071e-07 | 1.044e-06 | 1.705e-06 | 1.174e-11 | 8/8 |
| 2 | 0.35 | 256 | 89.6 | -4.217203431 | 6.669e-07 | 1.009e-06 | - | 1.009e-06 | 4.650e-06 | 8.777e-08 | 2.309e-07 | 4.428e-07 | 2.394e-12 | 8/8 |
| 3 | 0.1 | 768 | 76.8 | -3.429964009 | 1.767e-05 | 7.686e-05 | - | 7.686e-05 | 4.923e-05 | 2.495e-05 | 8.970e-06 | 2.861e-05 | 1.772e-09 | 8/8 |
| 3 | 0.125 | 768 | 96.0 | -3.444268952 | 1.164e-06 | 2.189e-06 | - | 2.189e-06 | 1.820e-04 | 1.081e-05 | 4.564e-06 | 1.229e-05 | 7.319e-10 | 8/8 |
| 3 | 0.15 | 768 | 115.2 | -3.463304521 | 2.818e-06 | 3.475e-06 | - | 3.475e-06 | 1.978e-05 | 5.456e-06 | 2.985e-06 | 6.562e-06 | 1.928e-10 | 8/8 |
| 3 | 0.175 | 768 | 134.4 | -3.487350826 | 2.335e-06 | 3.045e-06 | - | 3.045e-06 | 7.631e-06 | 3.062e-06 | 1.450e-06 | 4.007e-06 | 8.274e-11 | 8/8 |
| 3 | 0.2 | 384 | 76.8 | -3.516638047 | 1.971e-05 | 1.256e-05 | - | 1.971e-05 | 5.440e-06 | 1.856e-06 | 2.495e-06 | 4.975e-06 | 1.210e-10 | 8/8 |
| 3 | 0.25 | 256 | 64.0 | -3.591600566 | 7.609e-05 | 5.216e-05 | - | 7.609e-05 | 4.105e-06 | 8.049e-07 | 1.966e-06 | 3.816e-06 | 7.100e-11 | 8/8 |
| 3 | 0.35 | 256 | 89.6 | -3.809690200 | 5.421e-06 | 2.380e-06 | - | 5.421e-06 | 3.723e-06 | 2.288e-07 | 5.812e-07 | 9.762e-07 | 1.102e-11 | 8/8 |
| 3 | 0.5 | 128 | 64.0 | -4.302528694 | 2.888e-05 | 6.580e-06 | - | 2.888e-05 | 5.012e-07 | 6.066e-08 | 3.038e-07 | 6.591e-07 | 5.694e-12 | 8/8 |

Flags:

- (1, 0.125, N=256): lambda*N = 32 below the order-1 minimum 50
- (1, 0.15, N=256): lambda*N = 38.4 below the order-1 minimum 50
- (2, 0.175, N=256): lambda*N = 44.8 below the order-2 minimum 60
- (3, 0.25, N=256): lambda*N = 64 below the order-3 minimum 75
- (3, 0.5, N=128): lambda*N = 64 below the order-3 minimum 75

Replaced by M5 (kept as cross-N checks):

- (1, 0.075): N=384 -> N=768
- (1, 0.1): N=512 -> N=768
- (1, 0.1): N=384 -> N=768
- (1, 0.1): N=256 -> N=768
- (2, 0.125): N=384 -> N=768
- (2, 0.125): N=256 -> N=768
- (3, 0.2): N=256 -> N=384

## Auxiliary-cutoff alignment of archived points (M1, M2, M2b)

| r | lambda | N | h (recorded inputs) | h (aligned) | t x d(mixed) | mixed 4096->16384 | collapsed ->800000 | tail 2048->8192 | total |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 0.125 | 256 | -3.645699250 | -3.645695922 | -1.458e-06 | -1.458e-06 | 4.787e-06 | -5.407e-11 | 3.328e-06 |
| 1 | 0.15 | 256 | -3.681587707 | -3.681585771 | -4.831e-07 | -4.831e-07 | 2.420e-06 | -1.557e-11 | 1.936e-06 |
| 1 | 0.2 | 256 | -3.710097056 | -3.710096387 | -1.555e-07 | -1.555e-07 | 8.242e-07 | -1.698e-12 | 6.687e-07 |
| 1 | 0.25 | 256 | -3.669024551 | -3.669024229 | -3.489e-08 | -3.489e-08 | 3.571e-07 | -3.547e-12 | 3.222e-07 |
| 2 | 0.175 | 256 | -3.634126203 | -3.634122296 | -1.171e-06 | -1.171e-06 | 5.078e-06 | -1.358e-10 | 3.907e-06 |
| 2 | 0.25 | 256 | -3.855380315 | -3.855379305 | -3.294e-07 | -3.294e-07 | 1.340e-06 | -1.339e-11 | 1.011e-06 |
| 2 | 0.35 | 256 | -4.217203774 | -4.217203431 | -4.049e-08 | -4.049e-08 | 3.830e-07 | -2.371e-12 | 3.425e-07 |
| 3 | 0.2 | 384 | -3.516634050 | -3.516638047 | -3.997e-06 | -3.997e-06 | 0.000e+00 | -1.210e-10 | -3.997e-06 |
| 3 | 0.25 | 256 | -3.591602573 | -3.591600566 | -1.505e-06 | -1.505e-06 | 3.512e-06 | -6.942e-11 | 2.007e-06 |
| 3 | 0.35 | 256 | -3.809689370 | -3.809690200 | -1.829e-06 | -1.829e-06 | 9.983e-07 | -1.117e-11 | -8.303e-07 |
| 3 | 0.5 | 128 | -4.302528662 | -4.302528694 | -2.967e-07 | -2.967e-07 | 2.647e-07 | -6.796e-12 | -3.202e-08 |

| r | lambda | t | mixed limit (16384) | mixed half-spread | \|prefix - full\| | A_face (8192) | A(2048)-A(8192) | Xdisc(800k)-Xdisc(400k) | A(800k)-A(400k) |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 0.05 | 39.290 | -8199.774019751 | 1.169e-06 | 5.459e-07 | -307113 | 1.785e-03 | 3.392e-05 | 1.414e-08 |
| 1 | 0.0625 | 31.430 | -6544.714153116 | 1.102e-06 | 9.071e-08 | -133103 | 5.173e-04 | 1.470e-05 | 1.513e-09 |
| 1 | 0.075 | 26.189 | -5441.238073428 | 8.387e-07 | 5.789e-08 | -67234 | 1.883e-04 | 7.425e-06 | 7.713e-10 |
| 1 | 0.0875 | 22.445 | -4652.951805880 | 1.708e-06 | 7.186e-08 | -37747.1 | 8.023e-05 | 4.169e-06 | 0.000e+00 |
| 1 | 0.1 | 19.637 | -4061.658398975 | 1.098e-06 | 1.486e-08 | -22896.2 | 3.833e-05 | 2.529e-06 | -3.638e-12 |
| 1 | 0.125 | 15.704 | -3233.656416399 | 9.150e-07 | 2.690e-08 | -9931.94 | 1.117e-05 | 1.097e-06 | 1.146e-10 |
| 1 | 0.15 | 13.082 | -2681.439674123 | 4.131e-08 | 8.099e-10 | -5020.15 | 4.079e-06 | 5.545e-07 | -2.819e-11 |
| 1 | 0.2 | 9.802 | -1990.674760707 | 1.591e-07 | 1.229e-09 | -1710.15 | 8.329e-07 | 1.889e-07 | 1.955e-11 |
| 1 | 0.25 | 7.831 | -1575.678816675 | 1.527e-07 | 7.446e-10 | -740.86 | 2.429e-07 | 8.183e-08 | 4.206e-12 |
| 2 | 0.0625 | 52.991 | -11084.582181049 | 6.070e-06 | 7.590e-07 | -498682 | 4.734e-03 | 5.507e-05 | 1.147e-08 |
| 2 | 0.075 | 44.158 | -9224.752118756 | 3.019e-06 | 6.422e-07 | -251754 | 1.720e-03 | 2.780e-05 | 0.000e+00 |
| 2 | 0.1 | 33.116 | -6899.856905709 | 8.024e-07 | 9.267e-08 | -85643.9 | 3.491e-04 | 9.459e-06 | -1.004e-09 |
| 2 | 0.125 | 26.491 | -5504.803987106 | 5.922e-07 | 4.646e-08 | -37121.8 | 1.015e-04 | 4.100e-06 | 1.892e-10 |
| 2 | 0.15 | 22.073 | -4574.670987463 | 4.460e-07 | 1.750e-08 | -18756.5 | 3.706e-05 | 2.071e-06 | 2.183e-10 |
| 2 | 0.175 | 18.917 | -3910.205248574 | 7.293e-07 | 1.542e-08 | -10535.6 | 1.581e-05 | 1.164e-06 | 1.201e-10 |
| 2 | 0.25 | 13.235 | -2713.799200502 | 8.759e-07 | 2.720e-08 | -2779.84 | 2.207e-06 | 3.071e-07 | -1.592e-11 |
| 2 | 0.35 | 9.444 | -1915.549148378 | 4.923e-07 | 1.374e-08 | -794.338 | 3.444e-07 | 8.777e-08 | 2.160e-12 |
| 3 | 0.1 | 47.442 | -9916.169833626 | 1.038e-06 | 3.176e-07 | -225933 | 1.716e-03 | 2.495e-05 | 5.151e-09 |
| 3 | 0.125 | 37.952 | -7918.034135192 | 4.796e-06 | 2.953e-07 | -97862.2 | 4.984e-04 | 1.081e-05 | -4.133e-09 |
| 3 | 0.15 | 31.625 | -6585.881629566 | 6.255e-07 | 2.115e-08 | -49404 | 1.817e-04 | 5.456e-06 | -5.675e-10 |
| 3 | 0.175 | 27.106 | -5634.290837849 | 2.815e-07 | 3.823e-08 | -27721.9 | 7.750e-05 | 3.062e-06 | 3.201e-10 |
| 3 | 0.2 | 23.716 | -4920.550964229 | 2.294e-07 | 6.079e-08 | -16807.6 | 3.705e-05 | 1.856e-06 | 1.965e-10 |
| 3 | 0.25 | 18.969 | -3921.202143153 | 2.164e-07 | 1.268e-08 | -7286.79 | 1.081e-05 | 8.049e-07 | 0.000e+00 |
| 3 | 0.35 | 13.543 | -2778.760828644 | 2.749e-07 | 1.705e-08 | -2070.49 | 1.687e-06 | 2.288e-07 | -1.182e-11 |
| 3 | 0.5 | 9.471 | -1921.330199160 | 5.292e-08 | 1.350e-09 | -548.478 | 2.355e-07 | 6.066e-08 | -1.592e-12 |

## Spectral validation (M4)

### Prefix test (M4a): h at N' = N/2, 2N/3, 3N/4, N

| r | lambda | N | N'1 | N'2 | N'3 | N'4 | drift (max-min) | \|h(N)-h(3N/4)\| |
|---|---|---|---|---|---|---|---|---|
| 1 | 0.05 | 1024 | 512: -3.489183893 | 683: -3.489757762 | 768: -3.489810840 | 1024: -3.489852540 | 6.686e-04 | 4.170e-05 |
| 1 | 0.0625 | 1024 | 512: -3.517326671 | 683: -3.517405068 | 768: -3.517414260 | 1024: -3.517417833 | 9.116e-05 | 3.574e-06 |
| 1 | 0.075 | 768 | 384: -3.545214619 | 512: -3.545322423 | 576: -3.545330838 | 768: -3.545337213 | 1.226e-04 | 6.375e-06 |
| 1 | 0.0875 | 768 | 384: -3.572745635 | 512: -3.572770541 | 576: -3.572772960 | 768: -3.572773395 | 2.776e-05 | 4.353e-07 |
| 1 | 0.1 | 768 | 384: -3.599018765 | 512: -3.599025808 | 576: -3.599025898 | 768: -3.599025521 | 7.133e-06 | 3.772e-07 |
| 1 | 0.125 | 256 | 128: -3.636896205 | 171: -3.644905890 | 192: -3.645563068 | 256: -3.645695922 | 8.800e-03 | 1.329e-04 |
| 1 | 0.15 | 256 | 128: -3.680644498 | 171: -3.681529633 | 192: -3.681564508 | 256: -3.681585771 | 9.413e-04 | 2.126e-05 |
| 1 | 0.2 | 256 | 128: -3.710068999 | 171: -3.710093606 | 192: -3.710095705 | 256: -3.710096387 | 2.739e-05 | 6.826e-07 |
| 1 | 0.25 | 256 | 128: -3.669022428 | 171: -3.669024494 | 192: -3.669024568 | 256: -3.669024229 | 2.140e-06 | 3.391e-07 |
| 2 | 0.0625 | 1024 | 512: -3.435344373 | 683: -3.437328802 | 768: -3.437857425 | 1024: -3.437960431 | 2.616e-03 | 1.030e-04 |
| 2 | 0.075 | 1024 | 512: -3.449407146 | 683: -3.450320404 | 768: -3.450347873 | 1024: -3.450360197 | 9.531e-04 | 1.232e-05 |
| 2 | 0.1 | 768 | 384: -3.482014398 | 512: -3.482428110 | 576: -3.482440421 | 768: -3.482445342 | 4.309e-04 | 4.921e-06 |
| 2 | 0.125 | 768 | 384: -3.524068859 | 512: -3.524105846 | 576: -3.524105711 | 768: -3.524103987 | 3.699e-05 | 1.724e-06 |
| 2 | 0.15 | 768 | 384: -3.574879574 | 512: -3.574879186 | 576: -3.574878581 | 768: -3.574877309 | 2.265e-06 | 1.271e-06 |
| 2 | 0.175 | 256 | 128: -3.648011633 | 171: -3.633652436 | 192: -3.633975631 | 256: -3.634122296 | 1.436e-02 | 1.467e-04 |
| 2 | 0.25 | 256 | 128: -3.855254529 | 171: -3.855371834 | 192: -3.855374343 | 256: -3.855379305 | 1.248e-04 | 4.962e-06 |
| 2 | 0.35 | 256 | 128: -4.217203715 | 171: -4.217204707 | 192: -4.217204441 | 256: -4.217203431 | 1.276e-06 | 1.009e-06 |
| 3 | 0.1 | 768 | 384: -3.426724177 | 512: -3.429711336 | 576: -3.429887151 | 768: -3.429964009 | 3.240e-03 | 7.686e-05 |
| 3 | 0.125 | 768 | 384: -3.443988055 | 512: -3.444253803 | 576: -3.444266763 | 768: -3.444268952 | 2.809e-04 | 2.189e-06 |
| 3 | 0.15 | 768 | 384: -3.463278826 | 512: -3.463308323 | 576: -3.463307996 | 768: -3.463304521 | 2.950e-05 | 3.475e-06 |
| 3 | 0.175 | 768 | 384: -3.487355012 | 512: -3.487355288 | 576: -3.487353871 | 768: -3.487350826 | 4.462e-06 | 3.045e-06 |
| 3 | 0.2 | 384 | 192: -3.515899716 | 256: -3.516590029 | 288: -3.516625484 | 384: -3.516638047 | 7.383e-04 | 1.256e-05 |
| 3 | 0.25 | 256 | 128: -3.589205004 | 171: -3.591435411 | 192: -3.591548407 | 256: -3.591600566 | 2.396e-03 | 5.216e-05 |
| 3 | 0.35 | 256 | 128: -3.809648427 | 171: -3.809692049 | 192: -3.809692581 | 256: -3.809690200 | 4.415e-05 | 2.380e-06 |
| 3 | 0.5 | 128 | 64: -4.302083635 | 85: -4.302495392 | 96: -4.302522114 | 128: -4.302528694 | 4.451e-04 | 6.580e-06 |

### Cross-N (M4b), aligned auxiliary inputs

| r | lambda | N primary | N other | pool | lambda N | meets min | h other | \|diff\| | enters eps_cross | config differences |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 0.05 | 1024 | 1024 | diagnostic | 51.2 | yes | -3.489825439 | 2.710e-05 | no | radius_cost |
| 1 | 0.0625 | 1024 | 1024 | diagnostic | 64.0 | yes | -3.517403885 | 1.395e-05 | no | radius_cost,site |
| 1 | 0.075 | 768 | 1024 | diagnostic | 76.8 | yes | -3.545337796 | 5.834e-07 | no | N,site |
| 1 | 0.075 | 768 | 384 | primary | 28.8 | no | -3.545214715 | 1.225e-04 | no | N,mixed_cutoff,tail_cutoff,sources,site |
| 1 | 0.0875 | 768 | 1024 | diagnostic | 89.6 | yes | -3.572772995 | 4.001e-07 | no | N |
| 1 | 0.1 | 768 | 1024 | diagnostic | 102.4 | yes | -3.599025254 | 2.672e-07 | no | N |
| 1 | 0.1 | 768 | 512 | primary | 51.2 | yes | -3.599025582 | 6.043e-08 | yes | N,site |
| 1 | 0.1 | 768 | 384 | primary | 38.4 | no | -3.599017713 | 7.808e-06 | no | N,mixed_cutoff,tail_cutoff,sources,site |
| 1 | 0.1 | 768 | 256 | primary | 25.6 | no | -3.598877704 | 1.478e-04 | no | N,oversample,radius_cost,mixed_cutoff,tail_cutoff,collapsed_cutoff,sources,site |
| 1 | 0.125 | 256 | 512 | diagnostic | 64.0 | yes | -3.645712092 | 1.617e-05 | no | N,oversample,radius_cost,mixed_cutoff,tail_cutoff,collapsed_cutoff,sources,site |
| 1 | 0.15 | 256 | 512 | diagnostic | 76.8 | yes | -3.681587239 | 1.468e-06 | no | N,oversample,radius_cost,mixed_cutoff,tail_cutoff,collapsed_cutoff,sources,site |
| 1 | 0.2 | 256 | 512 | diagnostic | 102.4 | yes | -3.710095532 | 8.559e-07 | no | N,oversample,radius_cost,mixed_cutoff,tail_cutoff,collapsed_cutoff,sources,site |
| 1 | 0.25 | 256 | 512 | diagnostic | 128.0 | yes | -3.669023779 | 4.495e-07 | no | N,oversample,radius_cost,mixed_cutoff,tail_cutoff,collapsed_cutoff,sources,site |
| 2 | 0.0625 | 1024 | 1024 | diagnostic | 64.0 | yes | -3.437901305 | 5.913e-05 | no | radius_cost |
| 2 | 0.075 | 1024 | 1024 | diagnostic | 76.8 | yes | -3.450324964 | 3.523e-05 | no | radius_cost,site |
| 2 | 0.1 | 768 | 1024 | diagnostic | 102.4 | yes | -3.482443912 | 1.430e-06 | no | N,site |
| 2 | 0.125 | 768 | 1024 | diagnostic | 128.0 | yes | -3.524103159 | 8.280e-07 | no | N |
| 2 | 0.125 | 768 | 384 | primary | 48.0 | no | -3.524067407 | 3.658e-05 | no | N,mixed_cutoff,tail_cutoff,sources,site |
| 2 | 0.125 | 768 | 256 | primary | 32.0 | no | -3.523505498 | 5.985e-04 | no | N,oversample,radius_cost,mixed_cutoff,tail_cutoff,collapsed_cutoff,sources,site |
| 2 | 0.15 | 768 | 1024 | diagnostic | 153.6 | yes | -3.574876572 | 7.377e-07 | no | N |
| 2 | 0.175 | 256 | 512 | diagnostic | 89.6 | yes | -3.634161688 | 3.939e-05 | no | N,oversample,radius_cost,mixed_cutoff,tail_cutoff,collapsed_cutoff,sources,site |
| 2 | 0.25 | 256 | 512 | diagnostic | 128.0 | yes | -3.855376820 | 2.485e-06 | no | N,oversample,radius_cost,mixed_cutoff,tail_cutoff,collapsed_cutoff,sources,site |
| 2 | 0.35 | 256 | 512 | diagnostic | 179.2 | yes | -4.217202442 | 9.890e-07 | no | N,oversample,radius_cost,mixed_cutoff,tail_cutoff,collapsed_cutoff,sources,site |
| 3 | 0.1 | 768 | 1024 | diagnostic | 102.4 | yes | -3.429978008 | 1.400e-05 | no | N,site |
| 3 | 0.125 | 768 | 1024 | diagnostic | 128.0 | yes | -3.444265538 | 3.414e-06 | no | N |
| 3 | 0.15 | 768 | 1024 | diagnostic | 153.6 | yes | -3.463302160 | 2.361e-06 | no | N |
| 3 | 0.175 | 768 | 1024 | diagnostic | 179.2 | yes | -3.487349606 | 1.220e-06 | no | N |
| 3 | 0.2 | 384 | 512 | diagnostic | 102.4 | yes | -3.516635350 | 2.697e-06 | no | N,mixed_cutoff,tail_cutoff,sources,site |
| 3 | 0.2 | 384 | 256 | primary | 51.2 | no | -3.516592005 | 4.604e-05 | no | N,oversample,radius_cost,collapsed_cutoff |
| 3 | 0.25 | 256 | 512 | diagnostic | 128.0 | yes | -3.591595404 | 5.162e-06 | no | N,oversample,radius_cost,mixed_cutoff,tail_cutoff,collapsed_cutoff,sources,site |
| 3 | 0.35 | 256 | 512 | diagnostic | 179.2 | yes | -3.809687103 | 3.097e-06 | no | N,oversample,radius_cost,mixed_cutoff,tail_cutoff,collapsed_cutoff,sources,site |
| 3 | 0.5 | 128 | 512 | diagnostic | 256.0 | yes | -4.302524407 | 4.287e-06 | no | N,oversample,radius_cost,mixed_cutoff,tail_cutoff,collapsed_cutoff,sources,site |

### Extraction (M4d) and roundoff (M4e)

Per primary point (rev 6/7): the A5-1 epsilon_grid (in E) and, NOT in E, the superseded rev-4 L1 sum|v||delta|, the plain signed shift |sum v delta| and max_W|rho|, each the maximum over the accepted selected fits and the full-coverage comparisons. eps_round keeps its L1 form (rounding errors have random signs).

| r | lambda | N | status | comparisons | max\|delta\| (first) | signed \|v.delta\| | max\|rho\| | smooth \|v.s\| | rough sum\|v\|\|rho\| | eps_grid (A5-1, in E) | rev-4 L1 (superseded, not in E) | eps_round |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 0.05 | 1024 | measured | 1 | 3.299e-05 | 2.825e-05 | 1.737e-09 | 2.596e-05 | 2.143e-05 | 4.739e-05 | 1.448e+00 | 5.096e-05 |
| 1 | 0.0625 | 1024 | measured | 1 | 1.760e-05 | 1.401e-05 | 6.885e-10 | 1.386e-05 | 5.906e-06 | 1.977e-05 | 4.428e-01 | 1.867e-05 |
| 1 | 0.075 | 768 | measured | 1 | 5.459e-07 | 1.042e-06 | 5.152e-10 | 4.550e-07 | 5.694e-06 | 6.149e-06 | 1.786e-02 | 1.427e-05 |
| 1 | 0.0875 | 768 | measured | 1 | 3.543e-07 | 4.196e-07 | 2.631e-10 | 2.775e-07 | 1.920e-06 | 2.197e-06 | 8.119e-03 | 7.330e-06 |
| 1 | 0.1 | 768 | measured | 1 | 2.435e-07 | 1.946e-07 | 2.323e-10 | 1.783e-07 | 1.421e-06 | 1.599e-06 | 4.264e-03 | 4.277e-06 |
| 1 | 0.125 | 256 | measured | 1 | 5.765e-07 | 4.864e-07 | 7.014e-11 | 4.567e-07 | 5.225e-06 | 5.681e-06 | 1.108e-01 | 1.773e-05 |
| 1 | 0.15 | 256 | measured | 1 | 3.439e-07 | 4.813e-07 | 5.890e-11 | 2.576e-07 | 1.927e-06 | 2.185e-06 | 3.452e-02 | 6.380e-06 |
| 1 | 0.2 | 256 | measured | 1 | 1.515e-07 | 1.256e-07 | 4.376e-11 | 1.241e-07 | 6.709e-07 | 7.950e-07 | 6.347e-03 | 1.469e-06 |
| 1 | 0.25 | 256 | measured | 1 | 7.982e-08 | 6.924e-08 | 1.898e-11 | 6.464e-08 | 1.711e-07 | 2.357e-07 | 1.908e-03 | 5.258e-07 |
| 2 | 0.0625 | 1024 | measured | 1 | 7.089e-05 | 5.959e-05 | 1.929e-09 | 5.950e-05 | 1.498e-05 | 7.448e-05 | 1.990e+00 | 5.792e-05 |
| 2 | 0.075 | 1024 | measured | 1 | 4.242e-05 | 3.552e-05 | 1.286e-09 | 3.555e-05 | 8.726e-06 | 4.428e-05 | 8.039e-01 | 2.719e-05 |
| 2 | 0.1 | 768 | measured | 1 | 9.800e-07 | 1.131e-06 | 6.163e-10 | 8.180e-07 | 3.490e-06 | 4.308e-06 | 1.892e-02 | 1.319e-05 |
| 2 | 0.125 | 768 | measured | 1 | 5.242e-07 | 4.724e-07 | 4.159e-10 | 4.931e-07 | 1.719e-06 | 2.212e-06 | 6.855e-03 | 5.716e-06 |
| 2 | 0.15 | 768 | measured | 1 | 3.138e-07 | 2.712e-07 | 2.900e-10 | 2.632e-07 | 1.044e-06 | 1.307e-06 | 3.176e-03 | 3.068e-06 |
| 2 | 0.175 | 256 | measured | 1 | 9.015e-07 | 7.530e-07 | 1.153e-10 | 7.344e-07 | 2.768e-06 | 3.502e-06 | 6.418e-02 | 9.440e-06 |
| 2 | 0.25 | 256 | measured | 1 | 3.283e-07 | 2.827e-07 | 7.329e-11 | 2.760e-07 | 7.682e-07 | 1.044e-06 | 8.714e-03 | 1.705e-06 |
| 2 | 0.35 | 256 | measured | 1 | 1.256e-07 | 1.030e-07 | 3.666e-11 | 1.015e-07 | 1.294e-07 | 2.309e-07 | 1.733e-03 | 4.428e-07 |
| 3 | 0.1 | 768 | measured | 1 | 2.558e-06 | 3.257e-06 | 1.094e-09 | 2.335e-06 | 6.635e-06 | 8.970e-06 | 5.279e-02 | 2.861e-05 |
| 3 | 0.125 | 768 | measured | 1 | 1.370e-06 | 1.357e-06 | 8.898e-10 | 1.172e-06 | 3.393e-06 | 4.564e-06 | 1.891e-02 | 1.229e-05 |
| 3 | 0.15 | 768 | measured | 1 | 8.205e-07 | 7.132e-07 | 7.929e-10 | 6.861e-07 | 2.299e-06 | 2.985e-06 | 8.697e-03 | 6.562e-06 |
| 3 | 0.175 | 768 | measured | 1 | 5.321e-07 | 5.590e-07 | 3.329e-10 | 4.729e-07 | 9.774e-07 | 1.450e-06 | 4.687e-03 | 4.007e-06 |
| 3 | 0.2 | 384 | measured | 1 | 6.697e-07 | 6.953e-07 | 2.532e-10 | 6.077e-07 | 1.887e-06 | 2.495e-06 | 1.364e-02 | 4.975e-06 |
| 3 | 0.25 | 256 | measured | 1 | 8.631e-07 | 8.050e-07 | 1.237e-10 | 7.487e-07 | 1.217e-06 | 1.966e-06 | 2.477e-02 | 3.816e-06 |
| 3 | 0.35 | 256 | measured | 1 | 3.326e-07 | 2.871e-07 | 6.001e-11 | 2.802e-07 | 3.010e-07 | 5.812e-07 | 4.839e-03 | 9.762e-07 |
| 3 | 0.5 | 128 | measured | 1 | 9.677e-08 | 8.716e-08 | 2.218e-11 | 8.346e-08 | 2.204e-07 | 3.038e-07 | 2.693e-03 | 6.591e-07 |

All comparisons (the last three columns are illustrative and in no budget: mean signed delta over the last quarter, the largest |sum v delta|, and the change of the median when the check chain replaces the primary chain):

| record | kind | compared with | coverage | max\|delta\| | max\|rho\| | eps_grid (A5-1) | rev-4 L1 | const. shift (illus.) | max signed fit shift (illus.) | median shift (illus.) |
|---|---|---|---|---|---|---|---|---|---|---|
| k1_a0.05_N1024_o4_r4.5_m16384_t8192_c800000_eebafa82d841_expanse | M4d extraction-check record | k1_a0.05_N1024_o4_r4_m16384_t8192_c800000_eebafa82d841_expanse | n <= 1024 (complete) | 3.299e-05 | 1.737e-09 | 4.739e-05 | 1.448e+00 | -2.617e-05 | 2.825e-05 | -2.710e-05 |
| k1_a0.0625_N1024_o4_r4.5_m16384_t8192_c800000_eebafa82d841_expanse | M4d extraction-check record | k1_a0.0625_N1024_o4_r4_m16384_t8192_c800000_eebafa82d841_symmetry | n <= 1024 (complete) | 1.760e-05 | 6.885e-10 | 1.977e-05 | 4.428e-01 | -1.390e-05 | 1.401e-05 | -1.395e-05 |
| k1_a0.075_N768_o4_r4.5_m16384_t8192_c800000_eebafa82d841_symmetry | M4d extraction-check record | k1_a0.075_N1024_o4_r4.5_m16384_t8192_c800000_eebafa82d841_expanse | n <= 768 (complete) | 5.459e-07 | 5.152e-10 | 6.149e-06 | 1.786e-02 | 4.407e-07 | 1.042e-06 | 7.434e-07 |
| k1_a0.0875_N768_o4_r4.5_m16384_t8192_c800000_eebafa82d841_symmetry | M4d extraction-check record | k1_a0.0875_N1024_o4_r4.5_m16384_t8192_c800000_eebafa82d841_symmetry | n <= 768 (complete) | 3.543e-07 | 2.631e-10 | 2.197e-06 | 8.119e-03 | 2.849e-07 | 4.196e-07 | 3.519e-07 |
| k1_a0.125_N256_o5_r4_m4096_t2048_c200000_archived_archived | M4d extraction-check record | k1_a0.125_N512_o4_r4.5_m16384_t8192_c800000_eebafa82d841_symmetry | n <= 256 (complete) | 5.765e-07 | 7.014e-11 | 5.681e-06 | 1.108e-01 | -4.578e-07 | 4.864e-07 | -4.135e-07 |
| k1_a0.15_N256_o5_r4_m4096_t2048_c200000_archived_archived | M4d extraction-check record | k1_a0.15_N512_o4_r4.5_m16384_t8192_c800000_eebafa82d841_symmetry | n <= 256 (complete) | 3.439e-07 | 5.890e-11 | 2.185e-06 | 3.452e-02 | -2.720e-07 | 4.813e-07 | -3.687e-07 |
| k1_a0.1_N256_o5_r4_m4096_t2048_c200000_archived_archived | archived overlap (N=256 grid vs N=384 grid) | k1_a0.1_N384_o4_r4.5_m4096_t2048_c800000_archived_archived | n <= 256 (complete) | 1.526e-06 | 1.209e-10 | 2.527e-05 | 7.266e-01 | -1.228e-06 | 1.818e-06 | -8.467e-07 |
| k1_a0.1_N384_o4_r4.5_m4096_t2048_c800000_archived_archived | archived overlap (N=384 grid vs N=256 grid) | k1_a0.1_N256_o5_r4_m4096_t2048_c200000_archived_archived | n <= 256 of 384: PARTIAL, reported only, never used for epsilon_grid | 1.526e-06 | - | not used | - | - | - | - |
| k1_a0.1_N768_o4_r4.5_m16384_t8192_c800000_eebafa82d841_symmetry | M4d extraction-check record | k1_a0.1_N1024_o4_r4.5_m16384_t8192_c800000_eebafa82d841_symmetry | n <= 768 (complete) | 2.435e-07 | 2.323e-10 | 1.599e-06 | 4.264e-03 | 1.951e-07 | 1.946e-07 | 1.837e-07 |
| k1_a0.25_N256_o5_r4_m4096_t2048_c200000_archived_archived | M4d extraction-check record | k1_a0.25_N512_o4_r4.5_m16384_t8192_c800000_eebafa82d841_symmetry | n <= 256 (complete) | 7.982e-08 | 1.898e-11 | 2.357e-07 | 1.908e-03 | -6.231e-08 | 6.924e-08 | -4.652e-08 |
| k1_a0.2_N256_o5_r4_m4096_t2048_c200000_archived_archived | M4d extraction-check record | k1_a0.2_N512_o4_r4.5_m16384_t8192_c800000_eebafa82d841_symmetry | n <= 256 (complete) | 1.515e-07 | 4.376e-11 | 7.950e-07 | 6.347e-03 | -1.190e-07 | 1.256e-07 | -8.985e-08 |
| k2_a0.0625_N1024_o4_r4.5_m16384_t8192_c800000_eebafa82d841_expanse | M4d extraction-check record | k2_a0.0625_N1024_o4_r4_m16384_t8192_c800000_eebafa82d841_expanse | n <= 1024 (complete) | 7.089e-05 | 1.929e-09 | 7.448e-05 | 1.990e+00 | -5.966e-05 | 5.959e-05 | -5.913e-05 |
| k2_a0.075_N1024_o4_r4.5_m16384_t8192_c800000_eebafa82d841_expanse | M4d extraction-check record | k2_a0.075_N1024_o4_r4_m16384_t8192_c800000_eebafa82d841_symmetry | n <= 1024 (complete) | 4.242e-05 | 1.286e-09 | 4.428e-05 | 8.039e-01 | -3.555e-05 | 3.552e-05 | -3.523e-05 |
| k2_a0.125_N256_o5_r4_m4096_t2048_c200000_archived_archived | archived overlap (N=256 grid vs N=384 grid) | k2_a0.125_N384_o4_r4.5_m4096_t2048_c800000_archived_archived | n <= 256 (complete) | 3.284e-06 | 2.501e-10 | 2.493e-05 | 7.931e-01 | -2.797e-06 | 3.102e-06 | -2.113e-06 |
| k2_a0.125_N384_o4_r4.5_m4096_t2048_c800000_archived_archived | archived overlap (N=384 grid vs N=256 grid) | k2_a0.125_N256_o5_r4_m4096_t2048_c200000_archived_archived | n <= 256 of 384: PARTIAL, reported only, never used for epsilon_grid | 3.284e-06 | - | not used | - | - | - | - |
| k2_a0.125_N768_o4_r4.5_m16384_t8192_c800000_eebafa82d841_symmetry | M4d extraction-check record | k2_a0.125_N1024_o4_r4.5_m16384_t8192_c800000_eebafa82d841_symmetry | n <= 768 (complete) | 5.242e-07 | 4.159e-10 | 2.212e-06 | 6.855e-03 | 4.457e-07 | 4.724e-07 | 3.464e-07 |
| k2_a0.15_N768_o4_r4.5_m16384_t8192_c800000_eebafa82d841_symmetry | M4d extraction-check record | k2_a0.15_N1024_o4_r4.5_m16384_t8192_c800000_eebafa82d841_symmetry | n <= 768 (complete) | 3.138e-07 | 2.900e-10 | 1.307e-06 | 3.176e-03 | 2.653e-07 | 2.712e-07 | 2.710e-07 |
| k2_a0.175_N256_o5_r4_m4096_t2048_c200000_archived_archived | M4d extraction-check record | k2_a0.175_N512_o4_r4.5_m16384_t8192_c800000_eebafa82d841_symmetry | n <= 256 (complete) | 9.015e-07 | 1.153e-10 | 3.502e-06 | 6.418e-02 | -7.539e-07 | 7.530e-07 | -7.363e-07 |
| k2_a0.1_N768_o4_r4.5_m16384_t8192_c800000_eebafa82d841_symmetry | M4d extraction-check record | k2_a0.1_N1024_o4_r4.5_m16384_t8192_c800000_eebafa82d841_expanse | n <= 768 (complete) | 9.800e-07 | 6.163e-10 | 4.308e-06 | 1.892e-02 | 8.389e-07 | 1.131e-06 | 9.700e-07 |
| k2_a0.25_N256_o5_r4_m4096_t2048_c200000_archived_archived | M4d extraction-check record | k2_a0.25_N512_o4_r4.5_m16384_t8192_c800000_eebafa82d841_symmetry | n <= 256 (complete) | 3.283e-07 | 7.329e-11 | 1.044e-06 | 8.714e-03 | -2.719e-07 | 2.827e-07 | -2.117e-07 |
| k2_a0.35_N256_o5_r4_m4096_t2048_c200000_archived_archived | M4d extraction-check record | k2_a0.35_N512_o4_r4.5_m16384_t8192_c800000_eebafa82d841_symmetry | n <= 256 (complete) | 1.256e-07 | 3.666e-11 | 2.309e-07 | 1.733e-03 | -1.030e-07 | 1.030e-07 | -1.016e-07 |
| k3_a0.125_N768_o4_r4.5_m16384_t8192_c800000_eebafa82d841_symmetry | M4d extraction-check record | k3_a0.125_N1024_o4_r4.5_m16384_t8192_c800000_eebafa82d841_symmetry | n <= 768 (complete) | 1.370e-06 | 8.898e-10 | 4.564e-06 | 1.891e-02 | 1.204e-06 | 1.357e-06 | 1.200e-06 |
| k3_a0.15_N768_o4_r4.5_m16384_t8192_c800000_eebafa82d841_symmetry | M4d extraction-check record | k3_a0.15_N1024_o4_r4.5_m16384_t8192_c800000_eebafa82d841_symmetry | n <= 768 (complete) | 8.205e-07 | 7.929e-10 | 2.985e-06 | 8.697e-03 | 7.164e-07 | 7.132e-07 | 7.046e-07 |
| k3_a0.175_N768_o4_r4.5_m16384_t8192_c800000_eebafa82d841_symmetry | M4d extraction-check record | k3_a0.175_N1024_o4_r4.5_m16384_t8192_c800000_eebafa82d841_symmetry | n <= 768 (complete) | 5.321e-07 | 3.329e-10 | 1.450e-06 | 4.687e-03 | 4.622e-07 | 5.590e-07 | 4.652e-07 |
| k3_a0.1_N768_o4_r4.5_m16384_t8192_c800000_eebafa82d841_symmetry | M4d extraction-check record | k3_a0.1_N1024_o4_r4.5_m16384_t8192_c800000_eebafa82d841_expanse | n <= 768 (complete) | 2.558e-06 | 1.094e-09 | 8.970e-06 | 5.279e-02 | 2.265e-06 | 3.257e-06 | 2.280e-06 |
| k3_a0.25_N256_o5_r4_m4096_t2048_c200000_archived_archived | M4d extraction-check record | k3_a0.25_N512_o4_r4.5_m16384_t8192_c800000_eebafa82d841_symmetry | n <= 256 (complete) | 8.631e-07 | 1.237e-10 | 1.966e-06 | 2.477e-02 | -7.363e-07 | 8.050e-07 | -7.767e-07 |
| k3_a0.2_N256_o5_r4_m4096_t2048_c200000_archived_archived | archived overlap (N=256 grid vs N=384 grid) | k3_a0.2_N384_o4_r4.5_m4096_t2048_c800000_archived_archived | n <= 256 (complete) | 2.291e-06 | 1.944e-10 | 5.512e-06 | 1.221e-01 | -1.984e-06 | 2.127e-06 | -1.976e-06 |
| k3_a0.2_N384_o4_r4.5_m4096_t2048_c800000_archived_archived | M4d extraction-check record | k3_a0.2_N512_o4_r4.5_m16384_t8192_c800000_eebafa82d841_symmetry | n <= 384 (complete) | 6.697e-07 | 2.532e-10 | 2.495e-06 | 1.364e-02 | 5.934e-07 | 6.953e-07 | 6.420e-07 |
| k3_a0.2_N384_o4_r4.5_m4096_t2048_c800000_archived_archived | archived overlap (N=384 grid vs N=256 grid) | k3_a0.2_N256_o5_r4_m4096_t2048_c200000_archived_archived | n <= 256 of 384: PARTIAL, reported only, never used for epsilon_grid | 2.291e-06 | - | not used | - | - | - | - |
| k3_a0.35_N256_o5_r4_m4096_t2048_c200000_archived_archived | M4d extraction-check record | k3_a0.35_N512_o4_r4.5_m16384_t8192_c800000_eebafa82d841_symmetry | n <= 256 (complete) | 3.326e-07 | 6.001e-11 | 5.812e-07 | 4.839e-03 | -2.811e-07 | 2.871e-07 | -2.709e-07 |
| k3_a0.5_N128_o5_r4_m4096_t2048_c200000_archived_archived | M4d extraction-check record | k3_a0.5_N512_o4_r4.5_m16384_t8192_c800000_eebafa82d841_symmetry | n <= 128 (complete) | 9.677e-08 | 2.218e-11 | 3.038e-07 | 2.693e-03 | -7.997e-08 | 8.716e-08 | -6.366e-08 |

### Cross-site replicas (A3)

Records of the same configuration and sources on several sites are one replica (Expanse representative); the differences are raw partial sums (max over n) and the sidecar finite-cutoff h.

| record | representative site | replica site | max \|raw chain difference\| | finite-cutoff h difference |
|---|---|---|---|---|
| k1_a0.1_N512_o4_r4.5_m16384_t8192_c800000_eebafa82d841_expanse | expanse | symmetry | 6.912e-11 | -1.004e-09 |

### Records reported alongside (never estimates)

| record | role | lambda N | meets min | h (aligned aux) | half-spread |
|---|---|---|---|---|---|
| k1_a0.1_N256_o5_r4_m4096_t2048_c200000_archived_archived | lower-N PRIMARY record (M4b check only) | 25.6 | no | -3.598877704 | 1.885e-03 |
| k2_a0.125_N256_o5_r4_m4096_t2048_c200000_archived_archived | lower-N PRIMARY record (M4b check only) | 32.0 | no | -3.523505498 | 5.849e-03 |
| k3_a0.2_N256_o5_r4_m4096_t2048_c200000_archived_archived | lower-N PRIMARY record (M4b check only) | 51.2 | no | -3.516592005 | 7.808e-04 |
| k1_a0.075_N384_o4_r4.5_m4096_t2048_c800000_archived_archived | lower-N PRIMARY record (M4b check only) | 28.8 | no | -3.545214715 | 1.926e-03 |
| k1_a0.1_N384_o4_r4.5_m4096_t2048_c800000_archived_archived | lower-N PRIMARY record (M4b check only) | 38.4 | no | -3.599017713 | 2.255e-04 |
| k2_a0.125_N384_o4_r4.5_m4096_t2048_c800000_archived_archived | lower-N PRIMARY record (M4b check only) | 48.0 | no | -3.524067407 | 1.036e-04 |
| k1_a0.1_N512_o4_r4.5_m16384_t8192_c800000_eebafa82d841_expanse | lower-N PRIMARY record (M4b check only) | 51.2 | yes | -3.599025582 | 4.151e-05 |
| k1_a0.05_N1024_o4_r4_m16384_t8192_c800000_eebafa82d841_expanse | DIAGNOSTIC (M4d; never an estimate) | 51.2 | yes | -3.489825439 | 1.972e-04 |
| k2_a0.0625_N1024_o4_r4_m16384_t8192_c800000_eebafa82d841_expanse | DIAGNOSTIC (M4d; never an estimate) | 64.0 | yes | -3.437901305 | 2.088e-04 |
| k1_a0.075_N1024_o4_r4.5_m16384_t8192_c800000_eebafa82d841_expanse | DIAGNOSTIC (M4d; never an estimate) | 76.8 | yes | -3.545337796 | 5.863e-06 |
| k2_a0.1_N1024_o4_r4.5_m16384_t8192_c800000_eebafa82d841_expanse | DIAGNOSTIC (M4d; never an estimate) | 102.4 | yes | -3.482443912 | 2.333e-06 |
| k3_a0.1_N1024_o4_r4.5_m16384_t8192_c800000_eebafa82d841_expanse | DIAGNOSTIC (M4d; never an estimate) | 102.4 | yes | -3.429978008 | 5.117e-06 |
| k1_a0.0625_N1024_o4_r4_m16384_t8192_c800000_eebafa82d841_symmetry | DIAGNOSTIC (M4d; never an estimate) | 64.0 | yes | -3.517403885 | 3.031e-05 |
| k2_a0.075_N1024_o4_r4_m16384_t8192_c800000_eebafa82d841_symmetry | DIAGNOSTIC (M4d; never an estimate) | 76.8 | yes | -3.450324964 | 4.695e-05 |
| k1_a0.0875_N1024_o4_r4.5_m16384_t8192_c800000_eebafa82d841_symmetry | DIAGNOSTIC (M4d; never an estimate) | 89.6 | yes | -3.572772995 | 1.171e-06 |
| k1_a0.1_N1024_o4_r4.5_m16384_t8192_c800000_eebafa82d841_symmetry | DIAGNOSTIC (M4d; never an estimate) | 102.4 | yes | -3.599025254 | 1.560e-07 |
| k2_a0.125_N1024_o4_r4.5_m16384_t8192_c800000_eebafa82d841_symmetry | DIAGNOSTIC (M4d; never an estimate) | 128.0 | yes | -3.524103159 | 7.500e-07 |
| k2_a0.15_N1024_o4_r4.5_m16384_t8192_c800000_eebafa82d841_symmetry | DIAGNOSTIC (M4d; never an estimate) | 153.6 | yes | -3.574876572 | 6.151e-07 |
| k3_a0.125_N1024_o4_r4.5_m16384_t8192_c800000_eebafa82d841_symmetry | DIAGNOSTIC (M4d; never an estimate) | 128.0 | yes | -3.444265538 | 2.814e-06 |
| k3_a0.15_N1024_o4_r4.5_m16384_t8192_c800000_eebafa82d841_symmetry | DIAGNOSTIC (M4d; never an estimate) | 153.6 | yes | -3.463302160 | 1.938e-06 |
| k3_a0.175_N1024_o4_r4.5_m16384_t8192_c800000_eebafa82d841_symmetry | DIAGNOSTIC (M4d; never an estimate) | 179.2 | yes | -3.487349606 | 1.133e-06 |
| k1_a0.125_N512_o4_r4.5_m16384_t8192_c800000_eebafa82d841_symmetry | DIAGNOSTIC (M4d; never an estimate) | 64.0 | yes | -3.645712092 | 5.805e-06 |
| k1_a0.15_N512_o4_r4.5_m16384_t8192_c800000_eebafa82d841_symmetry | DIAGNOSTIC (M4d; never an estimate) | 76.8 | yes | -3.681587239 | 8.951e-07 |
| k1_a0.2_N512_o4_r4.5_m16384_t8192_c800000_eebafa82d841_symmetry | DIAGNOSTIC (M4d; never an estimate) | 102.4 | yes | -3.710095532 | 1.049e-07 |
| k1_a0.25_N512_o4_r4.5_m16384_t8192_c800000_eebafa82d841_symmetry | DIAGNOSTIC (M4d; never an estimate) | 128.0 | yes | -3.669023779 | 7.110e-08 |
| k2_a0.175_N512_o4_r4.5_m16384_t8192_c800000_eebafa82d841_symmetry | DIAGNOSTIC (M4d; never an estimate) | 89.6 | yes | -3.634161688 | 7.545e-07 |
| k2_a0.25_N512_o4_r4.5_m16384_t8192_c800000_eebafa82d841_symmetry | DIAGNOSTIC (M4d; never an estimate) | 128.0 | yes | -3.855376820 | 4.571e-07 |
| k2_a0.35_N512_o4_r4.5_m16384_t8192_c800000_eebafa82d841_symmetry | DIAGNOSTIC (M4d; never an estimate) | 179.2 | yes | -4.217202442 | 1.272e-07 |
| k3_a0.2_N512_o4_r4.5_m16384_t8192_c800000_eebafa82d841_symmetry | DIAGNOSTIC (M4d; never an estimate) | 102.4 | yes | -3.516635350 | 4.044e-06 |
| k3_a0.25_N512_o4_r4.5_m16384_t8192_c800000_eebafa82d841_symmetry | DIAGNOSTIC (M4d; never an estimate) | 128.0 | yes | -3.591595404 | 1.935e-06 |
| k3_a0.35_N512_o4_r4.5_m16384_t8192_c800000_eebafa82d841_symmetry | DIAGNOSTIC (M4d; never an estimate) | 179.2 | yes | -3.809687103 | 4.999e-07 |
| k3_a0.5_N512_o4_r4.5_m16384_t8192_c800000_eebafa82d841_symmetry | DIAGNOSTIC (M4d; never an estimate) | 256.0 | yes | -4.302524407 | 1.026e-07 |

## Regulator limit per order (M6)

### Order 1: preferred admissible; 30 distinct admissible fits

S_1: terms {2,2log,3}, unweighted, windows ['all', 'lam<=0.25'], lambdas [0.05, 0.0625, 0.075, 0.0875, 0.1, 0.125, 0.15, 0.2, 0.25], h0 = -3.414150, dof 5, max |res| 5.21e-05 (limit 1.06e-03), condition 1.33e+04; eps_model = 1.515e-02.

| terms | wt | windows | pts | dof | h0 | max \|res\| | limit | cond | status | role |
|---|---|---|---|---|---|---|---|---|---|---|
| 2,2log | u | drop1/lam<=0.2 | 8 | 5 | -3.418939 | 8.077e-04 | 1.056e-03 | 9.4e+02 | ADMISSIBLE |  |
| 2,2log | u | drop2/lam<=0.15 | 7 | 4 | -3.416957 | 2.890e-04 | 1.056e-03 | 2.2e+03 | ADMISSIBLE |  |
| 2,2log | w | drop2/lam<=0.15 | 7 | 4 | -3.417624 | 5.737e-04 | 1.056e-03 | 1.6e+04 | ADMISSIBLE |  |
| 2,2log,3 | u | all/lam<=0.25 | 9 | 5 | -3.414150 | 5.209e-05 | 1.056e-03 | 1.3e+04 | ADMISSIBLE | S_r |
| 2,2log,3 | w | all/lam<=0.25 | 9 | 5 | -3.414183 | 9.178e-05 | 1.056e-03 | 9.5e+04 | ADMISSIBLE |  |
| 2,2log,4 | u | all/lam<=0.25 | 9 | 5 | -3.415759 | 1.316e-04 | 1.056e-03 | 1.5e+04 | ADMISSIBLE |  |
| 2,2log,4 | w | all/lam<=0.25 | 9 | 5 | -3.416100 | 2.986e-04 | 1.056e-03 | 1e+05 | ADMISSIBLE |  |
| 2,2log,3 | u | drop1/lam<=0.2 | 8 | 4 | -3.414321 | 1.636e-05 | 1.056e-03 | 3.1e+04 | ADMISSIBLE |  |
| 2,2log,3 | w | drop1/lam<=0.2 | 8 | 4 | -3.414416 | 4.879e-05 | 1.056e-03 | 2.6e+05 | ADMISSIBLE |  |
| 2,2log,4 | u | drop1/lam<=0.2 | 8 | 4 | -3.415257 | 5.579e-05 | 1.056e-03 | 4.3e+04 | ADMISSIBLE |  |
| 2,2log,4 | w | drop1/lam<=0.2 | 8 | 4 | -3.415477 | 1.537e-04 | 1.056e-03 | 3.7e+05 | ADMISSIBLE |  |
| 2,3,4 | u | drop1/lam<=0.2 | 8 | 4 | -3.429303 | 6.674e-04 | 1.056e-03 | 1e+05 | ADMISSIBLE |  |
| 2,2log,3 | u | drop2/lam<=0.15 | 7 | 3 | -3.414164 | 1.018e-05 | 1.056e-03 | 9.1e+04 | ADMISSIBLE |  |
| 2,2log,3 | w | drop2/lam<=0.15 | 7 | 3 | -3.414310 | 3.312e-05 | 1.056e-03 | 5.9e+05 | ADMISSIBLE |  |
| 2,2log,4 | u | drop2/lam<=0.15 | 7 | 3 | -3.414819 | 2.429e-05 | 1.056e-03 | 1.6e+05 | ADMISSIBLE |  |
| 2,2log,4 | w | drop2/lam<=0.15 | 7 | 3 | -3.414989 | 6.581e-05 | 1.056e-03 | 1e+06 | ADMISSIBLE |  |
| 2,3,4 | u | drop2/lam<=0.15 | 7 | 3 | -3.425830 | 2.612e-04 | 1.056e-03 | 3.4e+05 | ADMISSIBLE |  |
| 2,3,4 | w | drop2/lam<=0.15 | 7 | 3 | -3.426692 | 6.314e-04 | 1.056e-03 | 2.3e+06 | ADMISSIBLE |  |
| 2,2log,3,4 | u | all/lam<=0.25 | 9 | 4 | -3.414433 | 2.559e-05 | 1.056e-03 | 2.3e+05 | ADMISSIBLE |  |
| 2,2log,3,4 | w | all/lam<=0.25 | 9 | 4 | -3.414536 | 5.646e-05 | 1.056e-03 | 4.9e+06 | ADMISSIBLE |  |
| 2,2log,3,3log (sens.) | u | all/lam<=0.25 | 9 | 4 | -3.414493 | 2.818e-05 | 1.056e-03 | 1.7e+05 | ADMISSIBLE |  |
| 2,2log,3,3log (sens.) | w | all/lam<=0.25 | 9 | 4 | -3.414601 | 5.789e-05 | 1.056e-03 | 3.6e+06 | ADMISSIBLE |  |
| 2,2log,3,4 | u | drop1/lam<=0.2 | 8 | 3 | -3.413961 | 5.741e-06 | 1.056e-03 | 8.8e+05 | ADMISSIBLE |  |
| 2,2log,3,4 | w | drop1/lam<=0.2 | 8 | 3 | -3.414186 | 2.683e-05 | 1.056e-03 | 5.7e+06 | ADMISSIBLE |  |
| 2,2log,3,3log (sens.) | u | drop1/lam<=0.2 | 8 | 3 | -3.413854 | 4.778e-06 | 1.056e-03 | 5.3e+05 | ADMISSIBLE |  |
| 2,2log,3,3log (sens.) | w | drop1/lam<=0.2 | 8 | 3 | -3.414113 | 2.486e-05 | 1.056e-03 | 3.5e+06 | ADMISSIBLE |  |
| 2,2log,3,4 | u | drop2/lam<=0.15 | 7 | 2 | -3.413854 | 3.595e-06 | 1.056e-03 | 3.1e+06 | ADMISSIBLE |  |
| 2,2log,3,4 | w | drop2/lam<=0.15 | 7 | 2 | -3.413807 | 2.110e-05 | 1.056e-03 | 5e+07 | ADMISSIBLE |  |
| 2,2log,3,3log (sens.) | u | drop2/lam<=0.15 | 7 | 2 | -3.413757 | 3.246e-06 | 1.056e-03 | 1.6e+06 | ADMISSIBLE |  |
| 2,2log,3,3log (sens.) | w | drop2/lam<=0.15 | 7 | 2 | -3.413668 | 1.915e-05 | 1.056e-03 | 2.4e+07 | ADMISSIBLE |  |
| 2,2log | u | all/lam<=0.25 | 9 | 6 | -3.421706 | 2.336e-03 | 1.056e-03 | 5.3e+02 | residual |  |
| 2,2log | w | all/lam<=0.25 | 9 | 6 | -3.429064 | 6.512e-03 | 1.056e-03 | 2.7e+03 | residual |  |
| 2,3 | u | all/lam<=0.25 | 9 | 6 | -3.459719 | 1.235e-02 | 1.056e-03 | 1.5e+03 | residual |  |
| 2,3 | w | all/lam<=0.25 | 9 | 6 | -3.488107 | 3.255e-02 | 1.056e-03 | 6.8e+03 | residual |  |
| 2,2log | w | drop1/lam<=0.2 | 8 | 5 | -3.419105 | 1.286e-03 | 1.056e-03 | 3.8e+03 | residual |  |
| 2,3 | u | drop1/lam<=0.2 | 8 | 5 | -3.448380 | 5.545e-03 | 1.056e-03 | 2.8e+03 | residual |  |
| 2,3 | w | drop1/lam<=0.2 | 8 | 5 | -3.449368 | 9.496e-03 | 1.056e-03 | 1.3e+04 | residual |  |
| 2,3 | u | drop2/lam<=0.15 | 7 | 4 | -3.438380 | 2.367e-03 | 1.056e-03 | 7.6e+03 | residual |  |
| 2,3 | w | drop2/lam<=0.15 | 7 | 4 | -3.442820 | 4.799e-03 | 1.056e-03 | 4.8e+04 | residual |  |
| 2,3,4 | u | all/lam<=0.25 | 9 | 5 | -3.434999 | 1.938e-03 | 1.056e-03 | 3.5e+04 | residual |  |
| 2,3,4 | w | all/lam<=0.25 | 9 | 5 | -3.437635 | 3.689e-03 | 1.056e-03 | 2.7e+05 | residual |  |
| 2,3,4 | w | drop1/lam<=0.2 | 8 | 4 | -3.431404 | 1.783e-03 | 1.056e-03 | 8.3e+05 | residual |  |

### Order 2: preferred admissible; 29 distinct admissible fits

S_2: terms {2,2log,3}, unweighted, windows ['drop1', 'lam<=0.25'], lambdas [0.0625, 0.075, 0.1, 0.125, 0.15, 0.175, 0.25], h0 = -3.412774, dof 3, max |res| 3.22e-05 (limit 6.26e-04), condition 1.88e+04; eps_model = 4.170e-03.

| terms | wt | windows | pts | dof | h0 | max \|res\| | limit | cond | status | role |
|---|---|---|---|---|---|---|---|---|---|---|
| 2,2log | u | drop2/lam<=0.2 | 6 | 3 | -3.408875 | 2.750e-04 | 6.264e-04 | 1.6e+03 | ADMISSIBLE |  |
| 2,3 | u | drop2/lam<=0.2 | 6 | 3 | -3.408900 | 2.584e-04 | 6.264e-04 | 4.8e+03 | ADMISSIBLE |  |
| 2,2log | u | lam<=0.15 | 5 | 2 | -3.409783 | 1.098e-04 | 6.264e-04 | 2.6e+03 | ADMISSIBLE |  |
| 2,2log | w | lam<=0.15 | 5 | 2 | -3.408603 | 4.519e-04 | 6.264e-04 | 2e+04 | ADMISSIBLE |  |
| 2,3 | u | lam<=0.15 | 5 | 2 | -3.409494 | 1.152e-04 | 6.264e-04 | 8.5e+03 | ADMISSIBLE |  |
| 2,3 | w | lam<=0.15 | 5 | 2 | -3.408607 | 4.598e-04 | 6.264e-04 | 6.5e+04 | ADMISSIBLE |  |
| 2,2log,3 | u | all | 8 | 4 | -3.413616 | 1.413e-04 | 6.264e-04 | 5e+03 | ADMISSIBLE |  |
| 2,2log,4 | u | all | 8 | 4 | -3.410443 | 1.749e-04 | 6.264e-04 | 4e+03 | ADMISSIBLE |  |
| 2,3,4 | u | all | 8 | 4 | -3.409300 | 2.723e-04 | 6.264e-04 | 1e+04 | ADMISSIBLE |  |
| 2,2log,3 | u | drop1/lam<=0.25 | 7 | 3 | -3.412774 | 3.216e-05 | 6.264e-04 | 1.9e+04 | ADMISSIBLE | S_r |
| 2,2log,3 | w | drop1/lam<=0.25 | 7 | 3 | -3.413094 | 1.107e-04 | 6.264e-04 | 1.7e+05 | ADMISSIBLE |  |
| 2,2log,4 | u | drop1/lam<=0.25 | 7 | 3 | -3.411310 | 3.744e-05 | 6.264e-04 | 2.1e+04 | ADMISSIBLE |  |
| 2,2log,4 | w | drop1/lam<=0.25 | 7 | 3 | -3.411291 | 8.822e-05 | 6.264e-04 | 1.9e+05 | ADMISSIBLE |  |
| 2,3,4 | u | drop1/lam<=0.25 | 7 | 3 | -3.410268 | 6.993e-05 | 6.264e-04 | 5e+04 | ADMISSIBLE |  |
| 2,3,4 | w | drop1/lam<=0.25 | 7 | 3 | -3.410084 | 1.587e-04 | 6.264e-04 | 4.8e+05 | ADMISSIBLE |  |
| 2,2log,3 | u | drop2/lam<=0.2 | 6 | 2 | -3.412480 | 2.124e-05 | 6.264e-04 | 6.5e+04 | ADMISSIBLE |  |
| 2,2log,3 | w | drop2/lam<=0.2 | 6 | 2 | -3.412710 | 6.356e-05 | 6.264e-04 | 1.5e+06 | ADMISSIBLE |  |
| 2,2log,4 | u | drop2/lam<=0.2 | 6 | 2 | -3.411639 | 6.672e-06 | 6.264e-04 | 9.3e+04 | ADMISSIBLE |  |
| 2,2log,4 | w | drop2/lam<=0.2 | 6 | 2 | -3.411709 | 1.468e-05 | 6.264e-04 | 2.1e+06 | ADMISSIBLE |  |
| 2,3,4 | u | drop2/lam<=0.2 | 6 | 2 | -3.410745 | 1.397e-05 | 6.264e-04 | 2e+05 | ADMISSIBLE |  |
| 2,3,4 | w | drop2/lam<=0.2 | 6 | 2 | -3.410652 | 8.189e-05 | 6.264e-04 | 4.5e+06 | ADMISSIBLE |  |
| 2,2log,3,4 | u | all | 8 | 3 | -3.412230 | 1.744e-05 | 6.264e-04 | 9.4e+04 | ADMISSIBLE |  |
| 2,2log,3,4 | w | all | 8 | 3 | -3.412551 | 6.244e-05 | 6.264e-04 | 9.4e+05 | ADMISSIBLE |  |
| 2,2log,3,3log (sens.) | u | all | 8 | 3 | -3.411888 | 1.200e-05 | 6.264e-04 | 8.9e+04 | ADMISSIBLE |  |
| 2,2log,3,3log (sens.) | w | all | 8 | 3 | -3.412198 | 4.398e-05 | 6.264e-04 | 9.2e+05 | ADMISSIBLE |  |
| 2,2log,3,4 | u | drop1/lam<=0.25 | 7 | 2 | -3.412109 | 1.410e-05 | 6.264e-04 | 5e+05 | ADMISSIBLE |  |
| 2,2log,3,4 | w | drop1/lam<=0.25 | 7 | 2 | -3.412265 | 3.986e-05 | 6.264e-04 | 1e+07 | ADMISSIBLE |  |
| 2,2log,3,3log (sens.) | u | drop1/lam<=0.25 | 7 | 2 | -3.411905 | 1.238e-05 | 6.264e-04 | 3.7e+05 | ADMISSIBLE |  |
| 2,2log,3,3log (sens.) | w | drop1/lam<=0.25 | 7 | 2 | -3.412052 | 3.598e-05 | 6.264e-04 | 7.4e+06 | ADMISSIBLE |  |
| 2,2log | u | all | 8 | 5 | -3.397635 | 6.135e-03 | 6.264e-04 | 2.1e+02 | residual |  |
| 2,2log | w | all | 8 | 5 | -3.385018 | 1.307e-02 | 6.264e-04 | 6.5e+02 | residual |  |
| 2,3 | u | all | 8 | 5 | -3.403622 | 3.311e-03 | 6.264e-04 | 5.3e+02 | residual |  |
| 2,3 | w | all | 8 | 5 | -3.397883 | 7.223e-03 | 6.264e-04 | 1.6e+03 | residual |  |
| 2,2log | u | drop1/lam<=0.25 | 7 | 4 | -3.405586 | 1.129e-03 | 6.264e-04 | 5e+02 | residual |  |
| 2,2log | w | drop1/lam<=0.25 | 7 | 4 | -3.399939 | 4.389e-03 | 6.264e-04 | 1.4e+03 | residual |  |
| 2,3 | u | drop1/lam<=0.25 | 7 | 4 | -3.407204 | 8.009e-04 | 6.264e-04 | 1.4e+03 | residual |  |
| 2,3 | w | drop1/lam<=0.25 | 7 | 4 | -3.404048 | 2.989e-03 | 6.264e-04 | 3.6e+03 | residual |  |
| 2,2log | w | drop2/lam<=0.2 | 6 | 3 | -3.408543 | 7.361e-04 | 6.264e-04 | 2e+04 | residual |  |
| 2,3 | w | drop2/lam<=0.2 | 6 | 3 | -3.408551 | 7.222e-04 | 6.264e-04 | 6.5e+04 | residual |  |
| 2,2log,3 | w | all | 8 | 4 | -3.414798 | 6.913e-04 | 6.264e-04 | 1.9e+04 | residual |  |
| 2,2log,4 | w | all | 8 | 4 | -3.408894 | 9.629e-04 | 6.264e-04 | 1.4e+04 | residual |  |
| 2,3,4 | w | all | 8 | 4 | -3.407559 | 1.340e-03 | 6.264e-04 | 3.5e+04 | residual |  |
| 2,2log,3 | u | lam<=0.15 | 5 | 1 | -3.412153 | 1.028e-05 | 6.264e-04 | 1.4e+05 | dof < 2 |  |
| 2,2log,3 | w | lam<=0.15 | 5 | 1 | -3.412514 | 4.058e-05 | 6.264e-04 | 1.8e+06 | dof < 2 |  |
| 2,2log,4 | u | lam<=0.15 | 5 | 1 | -3.411611 | 5.473e-06 | 6.264e-04 | 2.2e+05 | dof < 2 |  |
| 2,2log,4 | w | lam<=0.15 | 5 | 1 | -3.411752 | 1.995e-05 | 6.264e-04 | 2.8e+06 | dof < 2 |  |
| 2,3,4 | u | lam<=0.15 | 5 | 1 | -3.410881 | 1.375e-06 | 6.264e-04 | 4.8e+05 | dof < 2 |  |
| 2,3,4 | w | lam<=0.15 | 5 | 1 | -3.410858 | 4.606e-06 | 6.264e-04 | 6.3e+06 | dof < 2 |  |
| 2,2log,3,4 | u | drop2/lam<=0.2 | 6 | 1 | -3.411443 | 4.027e-06 | 6.264e-04 | 2e+06 | dof < 2 |  |
| 2,2log,3,4 | w | drop2/lam<=0.2 | 6 | 1 | -3.411879 | 2.258e-05 | 6.264e-04 | 2.9e+07 | dof < 2 |  |
| 2,2log,3,3log (sens.) | u | drop2/lam<=0.2 | 6 | 1 | -3.411123 | 3.190e-06 | 6.264e-04 | 1.2e+06 | dof < 2 |  |
| 2,2log,3,3log (sens.) | w | drop2/lam<=0.2 | 6 | 1 | -3.411577 | 1.889e-05 | 6.264e-04 | 1.9e+07 | dof < 2 |  |
| 2,2log,3,4 | u | lam<=0.15 | 5 | 0 | -3.411025 | 3.997e-15 | 6.264e-04 | 5.5e+06 | dof < 2 |  |
| 2,2log,3,4 | w | lam<=0.15 | 5 | 0 | -3.411025 | 1.230e-13 | 6.264e-04 | 1.8e+08 | dof < 2, condition |  |
| 2,2log,3,3log (sens.) | u | lam<=0.15 | 5 | 0 | -3.410697 | 1.776e-15 | 6.264e-04 | 3e+06 | dof < 2 |  |
| 2,2log,3,3log (sens.) | w | lam<=0.15 | 5 | 0 | -3.410697 | 1.230e-13 | 6.264e-04 | 9.6e+07 | dof < 2 |  |

### Order 3: preferred admissible; 26 distinct admissible fits

S_3: terms {2,2log,3}, unweighted, windows ['drop1', 'lam<=0.35'], lambdas [0.1, 0.125, 0.15, 0.175, 0.2, 0.25, 0.35], h0 = -3.412269, dof 3, max |res| 3.30e-05 (limit 2.31e-04), condition 8.05e+03; eps_model = 4.522e-03.

| terms | wt | windows | pts | dof | h0 | max \|res\| | limit | cond | status | role |
|---|---|---|---|---|---|---|---|---|---|---|
| 2,2log | u | drop1/lam<=0.35 | 7 | 4 | -3.411035 | 1.839e-04 | 2.306e-04 | 2.5e+02 | ADMISSIBLE |  |
| 2,2log | u | drop2/lam<=0.25 | 6 | 3 | -3.411609 | 6.212e-06 | 2.306e-04 | 7e+02 | ADMISSIBLE |  |
| 2,2log | w | drop2/lam<=0.25 | 6 | 3 | -3.411674 | 2.492e-05 | 2.306e-04 | 4.5e+03 | ADMISSIBLE |  |
| 2,2log | u | lam<=0.2 | 5 | 2 | -3.411630 | 6.182e-06 | 2.306e-04 | 1.7e+03 | ADMISSIBLE |  |
| 2,2log | w | lam<=0.2 | 5 | 2 | -3.411688 | 1.956e-05 | 2.306e-04 | 5.6e+03 | ADMISSIBLE |  |
| 2,3 | u | lam<=0.2 | 5 | 2 | -3.407747 | 8.897e-05 | 2.306e-04 | 4.5e+03 | ADMISSIBLE |  |
| 2,2log,4 | u | all | 8 | 4 | -3.413212 | 2.220e-04 | 2.306e-04 | 1.2e+03 | ADMISSIBLE |  |
| 2,2log,3 | u | drop1/lam<=0.35 | 7 | 3 | -3.412269 | 3.304e-05 | 2.306e-04 | 8e+03 | ADMISSIBLE | S_r |
| 2,2log,3 | w | drop1/lam<=0.35 | 7 | 3 | -3.412130 | 1.369e-04 | 2.306e-04 | 4.6e+04 | ADMISSIBLE |  |
| 2,2log,4 | u | drop1/lam<=0.35 | 7 | 3 | -3.412024 | 2.572e-05 | 2.306e-04 | 6e+03 | ADMISSIBLE |  |
| 2,2log,4 | w | drop1/lam<=0.35 | 7 | 3 | -3.411957 | 1.122e-04 | 2.306e-04 | 3.7e+04 | ADMISSIBLE |  |
| 2,3,4 | u | drop1/lam<=0.35 | 7 | 3 | -3.408663 | 6.241e-05 | 2.306e-04 | 1.5e+04 | ADMISSIBLE |  |
| 2,2log,3 | u | drop2/lam<=0.25 | 6 | 2 | -3.411637 | 5.874e-06 | 2.306e-04 | 3e+04 | ADMISSIBLE |  |
| 2,2log,3 | w | drop2/lam<=0.25 | 6 | 2 | -3.411715 | 2.046e-05 | 2.306e-04 | 1.5e+05 | ADMISSIBLE |  |
| 2,2log,4 | u | drop2/lam<=0.25 | 6 | 2 | -3.411635 | 5.976e-06 | 2.306e-04 | 2.9e+04 | ADMISSIBLE |  |
| 2,2log,4 | w | drop2/lam<=0.25 | 6 | 2 | -3.411707 | 2.038e-05 | 2.306e-04 | 1.4e+05 | ADMISSIBLE |  |
| 2,3,4 | u | drop2/lam<=0.25 | 6 | 2 | -3.409306 | 1.703e-05 | 2.306e-04 | 6.6e+04 | ADMISSIBLE |  |
| 2,3,4 | w | drop2/lam<=0.25 | 6 | 2 | -3.409087 | 6.291e-05 | 2.306e-04 | 2.8e+05 | ADMISSIBLE |  |
| 2,2log,3,4 | u | all | 8 | 3 | -3.410703 | 1.035e-05 | 2.306e-04 | 3.5e+04 | ADMISSIBLE |  |
| 2,2log,3,4 | w | all | 8 | 3 | -3.410767 | 3.095e-05 | 2.306e-04 | 1.7e+05 | ADMISSIBLE |  |
| 2,2log,3,3log (sens.) | u | all | 8 | 3 | -3.409729 | 2.107e-05 | 2.306e-04 | 4.6e+04 | ADMISSIBLE |  |
| 2,2log,3,3log (sens.) | w | all | 8 | 3 | -3.409870 | 6.827e-05 | 2.306e-04 | 2.2e+05 | ADMISSIBLE |  |
| 2,2log,3,4 | u | drop1/lam<=0.35 | 7 | 2 | -3.411043 | 8.707e-07 | 2.306e-04 | 1.9e+05 | ADMISSIBLE |  |
| 2,2log,3,4 | w | drop1/lam<=0.35 | 7 | 2 | -3.410978 | 3.158e-06 | 2.306e-04 | 1.2e+06 | ADMISSIBLE |  |
| 2,2log,3,3log (sens.) | u | drop1/lam<=0.35 | 7 | 2 | -3.410708 | 1.009e-06 | 2.306e-04 | 2e+05 | ADMISSIBLE |  |
| 2,2log,3,3log (sens.) | w | drop1/lam<=0.35 | 7 | 2 | -3.410579 | 8.653e-06 | 2.306e-04 | 1.3e+06 | ADMISSIBLE |  |
| 2,2log | u | all | 8 | 5 | -3.406897 | 2.249e-03 | 2.306e-04 | 95 | residual |  |
| 2,2log | w | all | 8 | 5 | -3.408149 | 8.037e-03 | 2.306e-04 | 2.8e+02 | residual |  |
| 2,3 | u | all | 8 | 5 | -3.398019 | 3.999e-03 | 2.306e-04 | 2e+02 | residual |  |
| 2,3 | w | all | 8 | 5 | -3.398969 | 1.398e-02 | 2.306e-04 | 5.6e+02 | residual |  |
| 2,2log | w | drop1/lam<=0.35 | 7 | 4 | -3.411294 | 3.693e-04 | 2.306e-04 | 4.2e+02 | residual |  |
| 2,3 | u | drop1/lam<=0.35 | 7 | 4 | -3.404217 | 9.861e-04 | 2.306e-04 | 5.9e+02 | residual |  |
| 2,3 | w | drop1/lam<=0.35 | 7 | 4 | -3.404968 | 2.114e-03 | 2.306e-04 | 1.1e+03 | residual |  |
| 2,3 | u | drop2/lam<=0.25 | 6 | 3 | -3.406666 | 2.455e-04 | 2.306e-04 | 1.8e+03 | residual |  |
| 2,3 | w | drop2/lam<=0.25 | 6 | 3 | -3.406770 | 1.236e-03 | 2.306e-04 | 1.1e+04 | residual |  |
| 2,3 | w | lam<=0.2 | 5 | 2 | -3.407278 | 2.478e-04 | 2.306e-04 | 1.4e+04 | residual |  |
| 2,2log,3 | u | all | 8 | 4 | -3.414613 | 3.543e-04 | 2.306e-04 | 2.1e+03 | residual |  |
| 2,2log,3 | w | all | 8 | 4 | -3.414570 | 5.496e-04 | 2.306e-04 | 3.6e+03 | residual |  |
| 2,2log,4 | w | all | 8 | 4 | -3.413149 | 3.549e-04 | 2.306e-04 | 2.1e+03 | residual |  |
| 2,3,4 | u | all | 8 | 4 | -3.407709 | 2.327e-04 | 2.306e-04 | 3.2e+03 | residual |  |
| 2,3,4 | w | all | 8 | 4 | -3.407710 | 3.830e-04 | 2.306e-04 | 5e+03 | residual |  |
| 2,3,4 | w | drop1/lam<=0.35 | 7 | 3 | -3.408713 | 2.608e-04 | 2.306e-04 | 8.8e+04 | residual |  |
| 2,2log,3 | u | lam<=0.2 | 5 | 1 | -3.411405 | 9.851e-07 | 2.306e-04 | 8.8e+04 | dof < 2 |  |
| 2,2log,3 | w | lam<=0.2 | 5 | 1 | -3.411515 | 9.184e-06 | 2.306e-04 | 3.5e+05 | dof < 2 |  |
| 2,2log,4 | u | lam<=0.2 | 5 | 1 | -3.411460 | 1.180e-06 | 2.306e-04 | 9.7e+04 | dof < 2 |  |
| 2,2log,4 | w | lam<=0.2 | 5 | 1 | -3.411564 | 1.044e-05 | 2.306e-04 | 3.5e+05 | dof < 2 |  |
| 2,3,4 | u | lam<=0.2 | 5 | 1 | -3.409600 | 5.483e-06 | 2.306e-04 | 2.1e+05 | dof < 2 |  |
| 2,3,4 | w | lam<=0.2 | 5 | 1 | -3.409268 | 4.561e-05 | 2.306e-04 | 7.3e+05 | dof < 2 |  |
| 2,2log,3,4 | u | drop2/lam<=0.25 | 6 | 1 | -3.410991 | 5.183e-07 | 2.306e-04 | 9.7e+05 | dof < 2 |  |
| 2,2log,3,4 | w | drop2/lam<=0.25 | 6 | 1 | -3.410891 | 5.422e-06 | 2.306e-04 | 4.9e+06 | dof < 2 |  |
| 2,2log,3,3log (sens.) | u | drop2/lam<=0.25 | 6 | 1 | -3.410792 | 6.792e-07 | 2.306e-04 | 8.8e+05 | dof < 2 |  |
| 2,2log,3,3log (sens.) | w | drop2/lam<=0.25 | 6 | 1 | -3.410646 | 7.000e-06 | 2.306e-04 | 4.6e+06 | dof < 2 |  |
| 2,2log,3,4 | u | lam<=0.2 | 5 | 0 | -3.411134 | 8.882e-16 | 2.306e-04 | 3.9e+06 | dof < 2 |  |
| 2,2log,3,4 | w | lam<=0.2 | 5 | 0 | -3.411134 | 5.773e-15 | 2.306e-04 | 1.2e+07 | dof < 2 |  |
| 2,2log,3,3log (sens.) | u | lam<=0.2 | 5 | 0 | -3.411043 | 1.776e-15 | 2.306e-04 | 3.2e+06 | dof < 2 |  |
| 2,2log,3,3log (sens.) | w | lam<=0.2 | 5 | 0 | -3.411043 | 7.994e-15 | 2.306e-04 | 1e+07 | dof < 2 |  |

## Comparison with earlier numbers (made after the computation)

Computed after every estimate was fixed; the historical numbers are not inputs.

| order | new C2_r | new dC2_r | historical C2 (representative fit) | difference | difference / dC2_r |
|---|---|---|---|---|---|
| 1 | -4.06739 | 0.01006 | -4.06694 | -0.00045 | -0.04 |
| 2 | -4.06653 | 0.00417 | -4.06800 | +0.00147 | +0.35 |
| 3 | -4.06622 | 0.00346 | -4.07127 | +0.00505 | +1.46 |

Earlier reviewers: C2 = -4.067 +- 0.004. This analysis: C2 = -4.06705 +- 0.00236 (difference -0.00005).

