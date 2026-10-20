# FIT v3 results (production; x-windows; schedule 20260916, bootstrap 300, calibration 500)

Protocol: FIT_MODEL_V3.md §4 (decision table §4.6). Selection blind to Delta_epsilon; (beta_c, Delta_eps) for the windows frozen in pre.json.

## Delta_sigma = 0.2 (s = 0.6)

**Decision: CONDITIONAL (sigma_sys coverage absent)**

Quoted: Delta_epsilon = 0.48160 ± 0.00054 (stat) (sigma_sys unresolved)
from x0.45_second_Nmin16384_K2 degree 5 (chi2/dof 224.2/154); quotable 2; range [0.4813141162143974, 0.4816032134438406]

Equilibration (population rule): PASS — groups 70, hot/cold |z|>3: 0 (0.0%), half-chain |z|>3: 3 (0.5%)
Coverage guard: 54/54 configurations admissible

| configuration | d* | chi2/dof | Delta_eps | sigma_stat | quotable | reasons |
|---|---|---|---|---|---|---|
| x0.45_leading_Nmin4096_K1 | 5 | 24.36 | 0.47104 | — | no | chi2/dof 24.36 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.45_leading_Nmin4096_K2 | 6 | 17.26 | 0.47911 | — | no | chi2/dof 17.26 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.45_leading_Nmin8192_K1 | 5 | 13.07 | 0.47157 | — | no | chi2/dof 13.07 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.45_leading_Nmin8192_K2 | 6 | 10.18 | 0.47707 | — | no | chi2/dof 10.18 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.45_leading_Nmin16384_K1 | 5 | 6.82 | 0.47229 | — | no | chi2/dof 6.82 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.45_leading_Nmin16384_K2 | 5 | 5.35 | 0.47784 | — | no | chi2/dof 5.35 > 1.5; mean |pull| > 1.2 for ["Y'", "Y''", 'U', "U'", "U''"] |
| x0.45_background_Nmin4096_K1 | 5 | 22.14 | 0.46998 | — | no | chi2/dof 22.14 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.45_background_Nmin4096_K2 | 5 | 4.76 | 0.48165 | — | no | chi2/dof 4.76 > 1.5; mean |pull| > 1.2 for ["Y''", "U'", "U''"] |
| x0.45_background_Nmin8192_K1 | 5 | 11.90 | 0.47108 | — | no | chi2/dof 11.90 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.45_background_Nmin8192_K2 | 5 | 2.60 | 0.48192 | — | no | chi2/dof 2.60 > 1.5; mean |pull| > 1.2 for ["Y''", "U''"] |
| x0.45_background_Nmin16384_K1 | 5 | 6.45 | 0.47232 | — | no | chi2/dof 6.45 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.45_background_Nmin16384_K2 | 5 | 1.72 | 0.48236 | — | no | chi2/dof 1.72 > 1.5 |
| x0.45_second_Nmin4096_K1 | 5 | 15.78 | 0.47127 | — | no | chi2/dof 15.78 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.45_second_Nmin4096_K2 | 5 | 2.48 | 0.48081 | — | no | chi2/dof 2.48 > 1.5; mean |pull| > 1.2 for ["Y''", "U''"] |
| x0.45_second_Nmin8192_K1 | 5 | 8.45 | 0.47202 | — | no | chi2/dof 8.45 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.45_second_Nmin8192_K2 | 5 | 1.82 | 0.48146 | — | no | chi2/dof 1.82 > 1.5; mean |pull| > 1.2 for ["U''"] |
| x0.45_second_Nmin16384_K1 | 3 | 544.77 | 0.45005 | — | no | chi2/dof 544.77 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.45_second_Nmin16384_K2 | 5 | 1.46 | 0.48160 | 0.00054 | yes |  |
| x0.6_leading_Nmin4096_K1 | 5 | 27.88 | 0.47094 | — | no | chi2/dof 27.88 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.6_leading_Nmin4096_K2 | 5 | 23.27 | 0.47732 | — | no | chi2/dof 23.27 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.6_leading_Nmin8192_K1 | 5 | 14.05 | 0.47240 | — | no | chi2/dof 14.05 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.6_leading_Nmin8192_K2 | 5 | 11.14 | 0.47860 | — | no | chi2/dof 11.14 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.6_leading_Nmin16384_K1 | 5 | 7.77 | 0.47305 | — | no | chi2/dof 7.77 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.6_leading_Nmin16384_K2 | 5 | 5.96 | 0.47843 | — | no | chi2/dof 5.96 > 1.5; mean |pull| > 1.2 for ["Y'", "Y''", 'U', "U'", "U''"] |
| x0.6_background_Nmin4096_K1 | 5 | 24.92 | 0.47069 | — | no | chi2/dof 24.92 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.6_background_Nmin4096_K2 | 7 | 5.73 | 0.48093 | — | no | chi2/dof 5.73 > 1.5; mean |pull| > 1.2 for ["Y''", "U'", "U''"] |
| x0.6_background_Nmin8192_K1 | 5 | 13.03 | 0.47208 | — | no | chi2/dof 13.03 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.6_background_Nmin8192_K2 | 7 | 2.72 | 0.48195 | — | no | chi2/dof 2.72 > 1.5; mean |pull| > 1.2 for ["Y''", "U''"] |
| x0.6_background_Nmin16384_K1 | 5 | 7.46 | 0.47308 | — | no | chi2/dof 7.46 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.6_background_Nmin16384_K2 | 3 | 355.68 | 0.50136 | — | no | chi2/dof 355.68 > 1.5; flags: nonlinear parameter at search boundary; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.6_second_Nmin4096_K1 | 5 | 18.87 | 0.47029 | — | no | chi2/dof 18.87 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.6_second_Nmin4096_K2 | 7 | 3.37 | 0.48011 | — | no | chi2/dof 3.37 > 1.5; mean |pull| > 1.2 for ["Y''", "U'", "U''"] |
| x0.6_second_Nmin8192_K1 | 3 | 767.66 | 0.45583 | — | no | chi2/dof 767.66 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.6_second_Nmin8192_K2 | 3 | 374.45 | 0.51511 | — | no | chi2/dof 374.45 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.6_second_Nmin16384_K1 | 3 | 716.61 | 0.45725 | — | no | chi2/dof 716.61 > 1.5; flags: nonlinear parameter at search boundary; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.6_second_Nmin16384_K2 | 3 | 350.85 | 0.50605 | — | no | chi2/dof 350.85 > 1.5; flags: nonlinear parameter at search boundary; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.35_leading_Nmin4096_K1 | 5 | 14.85 | 0.47080 | — | no | chi2/dof 14.85 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.35_leading_Nmin4096_K2 | 5 | 14.55 | 0.47466 | — | no | chi2/dof 14.55 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.35_leading_Nmin8192_K1 | 5 | 8.60 | 0.47214 | — | no | chi2/dof 8.60 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.35_leading_Nmin8192_K2 | 5 | 8.47 | 0.47491 | — | no | chi2/dof 8.47 > 1.5; mean |pull| > 1.2 for ["Y'", "Y''", 'U', "U'", "U''"] |
| x0.35_leading_Nmin16384_K1 | 5 | 4.10 | 0.47308 | — | no | chi2/dof 4.10 > 1.5; mean |pull| > 1.2 for ["Y''", 'U', "U'", "U''"] |
| x0.35_leading_Nmin16384_K2 | 5 | 3.47 | 0.48068 | — | no | chi2/dof 3.47 > 1.5; mean |pull| > 1.2 for ["Y''", "U'"] |
| x0.35_background_Nmin4096_K1 | 5 | 11.81 | 0.46868 | — | no | chi2/dof 11.81 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.35_background_Nmin4096_K2 | 5 | 3.86 | 0.48271 | — | no | chi2/dof 3.86 > 1.5; mean |pull| > 1.2 for ["Y''", "U''"] |
| x0.35_background_Nmin8192_K1 | 5 | 6.99 | 0.47071 | — | no | chi2/dof 6.99 > 1.5; mean |pull| > 1.2 for ["Y'", "Y''", 'U', "U'", "U''"] |
| x0.35_background_Nmin8192_K2 | 5 | 2.30 | 0.48344 | — | no | chi2/dof 2.30 > 1.5; mean |pull| > 1.2 for ["Y''", "U''"] |
| x0.35_background_Nmin16384_K1 | 5 | 3.82 | 0.47256 | — | no | chi2/dof 3.82 > 1.5; mean |pull| > 1.2 for ["Y''", "U'", "U''"] |
| x0.35_background_Nmin16384_K2 | 5 | 1.71 | 0.48342 | — | no | chi2/dof 1.71 > 1.5; mean |pull| > 1.2 for ["U''"] |
| x0.35_second_Nmin4096_K1 | 5 | 8.29 | 0.46816 | — | no | chi2/dof 8.29 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.35_second_Nmin4096_K2 | 5 | 1.97 | 0.47998 | — | no | chi2/dof 1.97 > 1.5; mean |pull| > 1.2 for ["U''"] |
| x0.35_second_Nmin8192_K1 | 5 | 5.14 | 0.47017 | — | no | chi2/dof 5.14 > 1.5; mean |pull| > 1.2 for ['Y', "Y''", 'U', "U'", "U''"] |
| x0.35_second_Nmin8192_K2 | 5 | 1.70 | 0.48120 | — | no | chi2/dof 1.70 > 1.5 |
| x0.35_second_Nmin16384_K1 | 5 | 2.67 | 0.47348 | — | no | chi2/dof 2.67 > 1.5; mean |pull| > 1.2 for ["U'", "U''"] |
| x0.35_second_Nmin16384_K2 | 5 | 1.48 | 0.48131 | 0.00081 | yes |  |

Cross-check: CROSS-CHECK UNAVAILABLE (fewer than 2 eligible series); distinct eligible series [] (duplicates removed: []); standalone: {'status': 'EXTRAPOLATION UNAVAILABLE (fewer than 2 distinct eligible series)'}
Crossing value: unavailable
Largest usable pairs: 131072-262144: Delta_eff(U) = 0.48660 ± 0.00137, Delta_eff(Y) = 0.45871 ± 0.00131 (300 valid draws; series xc0.45_star), 262144-524288: Delta_eff(U) = 0.48189 ± 0.00146, Delta_eff(Y) = 0.45699 ± 0.00147 (300 valid draws; series xc0.45_star)
- xc0.45_star: Delta_inf 0.48585 omega' 0.20 chi2/dof 11.97/4 pairs [8192, 65536, 131072, 262144] — extrapolation chi2/dof 2.99 > 2.0
- xc0.6_star: Delta_inf 0.48048 omega' 0.23 chi2/dof 21.76/4 pairs [2048, 4096, 8192, 262144] — extrapolation chi2/dof 5.44 > 2.0
- xc0.6_plus: Delta_inf 0.47973 omega' 0.20 chi2/dof 4.99/4 pairs [8192, 16384, 32768, 262144] — omega' at grid bound or not unique
- xc0.45_plus: Delta_inf 0.48653 omega' 0.20 chi2/dof 11.35/4 pairs [8192, 65536, 131072, 262144] — extrapolation chi2/dof 2.84 > 2.0
Reblocking: block 2048: sigma_stat 0.00052 (ok); block 8192: sigma_stat 0.00059 (ok)

