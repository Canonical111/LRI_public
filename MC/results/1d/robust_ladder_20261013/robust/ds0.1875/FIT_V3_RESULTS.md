# FIT v3 results (production; x-windows; schedule 20260916, bootstrap 300, calibration 500)

Protocol: FIT_MODEL_V3.md §4 (decision table §4.6). Selection blind to Delta_epsilon; (beta_c, Delta_eps) for the windows frozen in pre.json.

## Delta_sigma = 0.1875 (s = 0.625)

**Decision: CROSS-CHECK UNAVAILABLE**

Quoted: Delta_epsilon = 0.48263 ± 0.00030 (stat) ± 0.00063 (sys; ratio to median sigma_stat 1.3)
from x0.45_second_Nmin4096_K2 degree 5 (chi2/dof 268.6/190); quotable 10; range [0.4820639741622713, 0.4833215032413779]

Equilibration (population rule): PASS — groups 70, hot/cold |z|>3: 0 (0.0%), half-chain |z|>3: 1 (0.2%)
Coverage guard: 54/54 configurations admissible

| configuration | d* | chi2/dof | Delta_eps | sigma_stat | quotable | reasons |
|---|---|---|---|---|---|---|
| x0.45_leading_Nmin4096_K1 | 5 | 21.16 | 0.47423 | — | no | chi2/dof 21.16 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.45_leading_Nmin4096_K2 | 5 | 13.94 | 0.48456 | — | no | chi2/dof 13.94 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.45_leading_Nmin8192_K1 | 5 | 10.14 | 0.47452 | — | no | chi2/dof 10.14 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.45_leading_Nmin8192_K2 | 5 | 7.34 | 0.48181 | — | no | chi2/dof 7.34 > 1.5; mean |pull| > 1.2 for ['Y', "Y''", 'U', "U''"] |
| x0.45_leading_Nmin16384_K1 | 5 | 4.81 | 0.47533 | — | no | chi2/dof 4.81 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.45_leading_Nmin16384_K2 | 6 | 3.42 | 0.48224 | — | no | chi2/dof 3.42 > 1.5; mean |pull| > 1.2 for ["Y''"] |
| x0.45_background_Nmin4096_K1 | 5 | 19.20 | 0.47304 | — | no | chi2/dof 19.20 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.45_background_Nmin4096_K2 | 5 | 3.02 | 0.48340 | — | no | chi2/dof 3.02 > 1.5; mean |pull| > 1.2 for ["Y''", "U''"] |
| x0.45_background_Nmin8192_K1 | 5 | 9.06 | 0.47402 | — | no | chi2/dof 9.06 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.45_background_Nmin8192_K2 | 5 | 1.62 | 0.48301 | — | no | chi2/dof 1.62 > 1.5 |
| x0.45_background_Nmin16384_K1 | 5 | 4.31 | 0.47525 | — | no | chi2/dof 4.31 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.45_background_Nmin16384_K2 | 5 | 1.26 | 0.48282 | 0.00049 | yes |  |
| x0.45_second_Nmin4096_K1 | 5 | 12.70 | 0.47434 | — | no | chi2/dof 12.70 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.45_second_Nmin4096_K2 | 5 | 1.41 | 0.48263 | 0.00030 | yes |  |
| x0.45_second_Nmin8192_K1 | 5 | 5.65 | 0.47518 | — | no | chi2/dof 5.65 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.45_second_Nmin8192_K2 | 5 | 1.14 | 0.48238 | 0.00036 | yes |  |
| x0.45_second_Nmin16384_K1 | 3 | 480.47 | 0.45672 | — | no | chi2/dof 480.47 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.45_second_Nmin16384_K2 | 5 | 1.06 | 0.48210 | 0.00054 | yes |  |
| x0.6_leading_Nmin4096_K1 | 7 | 23.16 | 0.47275 | — | no | chi2/dof 23.16 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.6_leading_Nmin4096_K2 | 6 | 18.19 | 0.48101 | — | no | chi2/dof 18.19 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.6_leading_Nmin8192_K1 | 6 | 10.76 | 0.47499 | — | no | chi2/dof 10.76 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.6_leading_Nmin8192_K2 | 6 | 7.28 | 0.48262 | — | no | chi2/dof 7.28 > 1.5; mean |pull| > 1.2 for ['Y', "Y''", 'U', "U''"] |
| x0.6_leading_Nmin16384_K1 | 7 | 4.84 | 0.47512 | — | no | chi2/dof 4.84 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.6_leading_Nmin16384_K2 | 7 | 3.62 | 0.48024 | — | no | chi2/dof 3.62 > 1.5; mean |pull| > 1.2 for ["Y''"] |
| x0.6_background_Nmin4096_K1 | 7 | 20.29 | 0.47261 | — | no | chi2/dof 20.29 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.6_background_Nmin4096_K2 | 7 | 3.46 | 0.48262 | — | no | chi2/dof 3.46 > 1.5; mean |pull| > 1.2 for ["Y''", "U''"] |
| x0.6_background_Nmin8192_K1 | 7 | 9.47 | 0.47393 | — | no | chi2/dof 9.47 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.6_background_Nmin8192_K2 | 7 | 1.70 | 0.48299 | — | no | chi2/dof 1.70 > 1.5 |
| x0.6_background_Nmin16384_K1 | 7 | 4.51 | 0.47512 | — | no | chi2/dof 4.51 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.6_background_Nmin16384_K2 | 3 | 377.45 | 0.50405 | — | no | chi2/dof 377.45 > 1.5; flags: nonlinear parameter at search boundary; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.6_second_Nmin4096_K1 | 7 | 13.89 | 0.47249 | — | no | chi2/dof 13.89 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.6_second_Nmin4096_K2 | 7 | 1.89 | 0.48187 | — | no | chi2/dof 1.89 > 1.5 |
| x0.6_second_Nmin8192_K1 | 7 | 6.14 | 0.47504 | — | no | chi2/dof 6.14 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.6_second_Nmin8192_K2 | 7 | 1.25 | 0.48234 | 0.00038 | yes |  |
| x0.6_second_Nmin16384_K1 | 7 | 2.95 | 0.47581 | — | no | chi2/dof 2.95 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.6_second_Nmin16384_K2 | 7 | 1.10 | 0.48217 | 0.00048 | yes |  |
| x0.35_leading_Nmin4096_K1 | 5 | 13.23 | 0.47403 | — | no | chi2/dof 13.23 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.35_leading_Nmin4096_K2 | 5 | 11.11 | 0.48501 | — | no | chi2/dof 11.11 > 1.5; mean |pull| > 1.2 for ['Y', "Y''", 'U', "U''"] |
| x0.35_leading_Nmin8192_K1 | 5 | 6.89 | 0.47498 | — | no | chi2/dof 6.89 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.35_leading_Nmin8192_K2 | 5 | 6.21 | 0.48134 | — | no | chi2/dof 6.21 > 1.5; mean |pull| > 1.2 for ["Y''", 'U', "U'"] |
| x0.35_leading_Nmin16384_K1 | 5 | 3.09 | 0.47618 | — | no | chi2/dof 3.09 > 1.5; mean |pull| > 1.2 for ['Y', "Y''", 'U'] |
| x0.35_leading_Nmin16384_K2 | 5 | 2.34 | 0.48414 | — | no | chi2/dof 2.34 > 1.5 |
| x0.35_background_Nmin4096_K1 | 5 | 10.69 | 0.47178 | — | no | chi2/dof 10.69 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.35_background_Nmin4096_K2 | 5 | 2.60 | 0.48387 | — | no | chi2/dof 2.60 > 1.5; mean |pull| > 1.2 for ["Y''", "U''"] |
| x0.35_background_Nmin8192_K1 | 5 | 5.54 | 0.47351 | — | no | chi2/dof 5.54 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.35_background_Nmin8192_K2 | 5 | 1.54 | 0.48386 | — | no | chi2/dof 1.54 > 1.5 |
| x0.35_background_Nmin16384_K1 | 5 | 2.86 | 0.47596 | — | no | chi2/dof 2.86 > 1.5; mean |pull| > 1.2 for ['Y', "Y''", 'U'] |
| x0.35_background_Nmin16384_K2 | 5 | 1.20 | 0.48332 | 0.00072 | yes |  |
| x0.35_second_Nmin4096_K1 | 5 | 7.22 | 0.47138 | — | no | chi2/dof 7.22 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.35_second_Nmin4096_K2 | 5 | 1.28 | 0.48206 | 0.00045 | yes |  |
| x0.35_second_Nmin8192_K1 | 5 | 3.72 | 0.47357 | — | no | chi2/dof 3.72 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.35_second_Nmin8192_K2 | 5 | 1.14 | 0.48253 | 0.00058 | yes |  |
| x0.35_second_Nmin16384_K1 | 5 | 1.93 | 0.47749 | — | no | chi2/dof 1.93 > 1.5; mean |pull| > 1.2 for ["U''"] |
| x0.35_second_Nmin16384_K2 | 5 | 1.06 | 0.48256 | 0.00079 | yes |  |

Cross-check: CROSS-CHECK UNAVAILABLE (fewer than 2 eligible series); distinct eligible series [] (duplicates removed: []); standalone: {'status': 'EXTRAPOLATION UNAVAILABLE (fewer than 2 distinct eligible series)'}
Crossing value: unavailable
Largest usable pairs: 131072-262144: Delta_eff(U) = 0.48462 ± 0.00140, Delta_eff(Y) = 0.46454 ± 0.00132 (300 valid draws; series xc0.45_star), 262144-524288: Delta_eff(U) = 0.48030 ± 0.00142, Delta_eff(Y) = 0.46246 ± 0.00143 (300 valid draws; series xc0.45_star)
- xc0.45_star: Delta_inf 0.48077 omega' 0.26 chi2/dof 10.08/4 pairs [8192, 65536, 131072, 262144] — extrapolation chi2/dof 2.52 > 2.0
- xc0.45_plus: Delta_inf 0.48174 omega' 0.25 chi2/dof 10.55/4 pairs [8192, 65536, 131072, 262144] — extrapolation chi2/dof 2.64 > 2.0
- xc0.6_star: Delta_inf 0.48115 omega' 0.28 chi2/dof 10.49/4 pairs [32768, 65536, 131072, 262144] — extrapolation chi2/dof 2.62 > 2.0
- xc0.6_plus: Delta_inf 0.48081 omega' 0.29 chi2/dof 10.41/4 pairs [32768, 65536, 131072, 262144] — extrapolation chi2/dof 2.60 > 2.0
Reblocking: block 2048: sigma_stat 0.00032 (ok); block 8192: sigma_stat 0.00031 (ok)

