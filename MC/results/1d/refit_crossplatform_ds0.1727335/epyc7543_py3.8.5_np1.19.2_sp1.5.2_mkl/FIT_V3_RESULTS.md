# FIT v3 results (production; x-windows; schedule 20260916, bootstrap 300, calibration 500)

Protocol: FIT_MODEL_V3.md §4 (decision table §4.6). Selection blind to Delta_epsilon; (beta_c, Delta_eps) for the windows frozen in pre.json.

## Delta_sigma = 0.1727335 (s = 0.654533)

**Decision: CONDITIONAL (sigma_sys coverage absent)**

Quoted: Delta_epsilon = 0.48368 ± 0.00052 (stat) (sigma_sys unresolved)
from x0.35_second_Nmin4096_K2 degree 5 (chi2/dof 185.1/160); quotable 3; range [0.48329334117712164, 0.484853014226842]

Equilibration (population rule): PASS — groups 70, hot/cold |z|>3: 0 (0.0%), half-chain |z|>3: 0 (0.0%)
Coverage guard: 54/54 configurations admissible

| configuration | d* | chi2/dof | Delta_eps | sigma_stat | quotable | reasons |
|---|---|---|---|---|---|---|
| x0.45_leading_Nmin4096_K1 | 5 | 16.33 | 0.47924 | — | no | chi2/dof 16.33 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.45_leading_Nmin4096_K2 | 5 | 8.59 | 0.48869 | — | no | chi2/dof 8.59 > 1.5; mean |pull| > 1.2 for ["Y'", "Y''", 'U', "U'", "U''"] |
| x0.45_leading_Nmin8192_K1 | 5 | 7.93 | 0.47832 | — | no | chi2/dof 7.93 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.45_leading_Nmin8192_K2 | 5 | 4.75 | 0.48585 | — | no | chi2/dof 4.75 > 1.5; mean |pull| > 1.2 for ["Y''", "U''"] |
| x0.45_leading_Nmin16384_K1 | 5 | 4.05 | 0.47723 | — | no | chi2/dof 4.05 > 1.5; mean |pull| > 1.2 for ['Y', "Y''", 'U', "U'", "U''"] |
| x0.45_leading_Nmin16384_K2 | 3 | 369.30 | 0.50805 | — | no | chi2/dof 369.30 > 1.5; flags: nonlinear parameter at search boundary; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.45_background_Nmin4096_K1 | 5 | 15.03 | 0.47811 | — | no | chi2/dof 15.03 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.45_background_Nmin4096_K2 | 6 | 2.07 | 0.48528 | — | no | chi2/dof 2.07 > 1.5 |
| x0.45_background_Nmin8192_K1 | 5 | 7.34 | 0.47791 | — | no | chi2/dof 7.34 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.45_background_Nmin8192_K2 | 3 | 384.43 | 0.50032 | — | no | chi2/dof 384.43 > 1.5; flags: nonlinear parameter at search boundary; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.45_background_Nmin16384_K1 | 3 | 584.80 | 0.45238 | — | no | chi2/dof 584.80 > 1.5; flags: nonlinear parameter at search boundary; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.45_background_Nmin16384_K2 | 3 | 355.48 | 0.49613 | — | no | chi2/dof 355.48 > 1.5; flags: nonlinear parameter at search boundary; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.45_second_Nmin4096_K1 | 5 | 9.65 | 0.47946 | — | no | chi2/dof 9.65 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.45_second_Nmin4096_K2 | 6 | 1.29 | 0.48485 | 0.00036 | yes |  |
| x0.45_second_Nmin8192_K1 | 6 | 4.27 | 0.47993 | — | no | chi2/dof 4.27 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.45_second_Nmin8192_K2 | 3 | 368.68 | 0.54129 | — | no | chi2/dof 368.68 > 1.5; flags: nonlinear parameter at search boundary; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.45_second_Nmin16384_K1 | 3 | 594.15 | 0.45285 | — | no | chi2/dof 594.15 > 1.5; flags: nonlinear parameter at search boundary; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.45_second_Nmin16384_K2 | 3 | 345.74 | 0.53161 | — | no | chi2/dof 345.74 > 1.5; flags: nonlinear parameter at search boundary; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.6_leading_Nmin4096_K1 | 6 | 17.64 | 0.47750 | — | no | chi2/dof 17.64 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.6_leading_Nmin4096_K2 | 6 | 10.65 | 0.48659 | — | no | chi2/dof 10.65 > 1.5; mean |pull| > 1.2 for ["Y'", "Y''", 'U', "U''"] |
| x0.6_leading_Nmin8192_K1 | 6 | 8.14 | 0.47961 | — | no | chi2/dof 8.14 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.6_leading_Nmin8192_K2 | 3 | 554.32 | 0.51113 | — | no | chi2/dof 554.32 > 1.5; flags: nonlinear parameter at search boundary; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.6_leading_Nmin16384_K1 | 7 | 4.14 | 0.47869 | — | no | chi2/dof 4.14 > 1.5; mean |pull| > 1.2 for ['Y', "Y''", 'U', "U'", "U''"] |
| x0.6_leading_Nmin16384_K2 | 3 | 508.23 | 0.50654 | — | no | chi2/dof 508.23 > 1.5; flags: nonlinear parameter at search boundary; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.6_background_Nmin4096_K1 | 6 | 15.33 | 0.47702 | — | no | chi2/dof 15.33 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.6_background_Nmin4096_K2 | 7 | 2.48 | 0.48481 | — | no | chi2/dof 2.48 > 1.5 |
| x0.6_background_Nmin8192_K1 | 6 | 7.44 | 0.47931 | — | no | chi2/dof 7.44 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.6_background_Nmin8192_K2 | 3 | 507.32 | 0.50088 | — | no | chi2/dof 507.32 > 1.5; flags: nonlinear parameter at search boundary; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.6_background_Nmin16384_K1 | 7 | 3.80 | 0.47858 | — | no | chi2/dof 3.80 > 1.5; mean |pull| > 1.2 for ['Y', "Y''", 'U', "U'", "U''"] |
| x0.6_background_Nmin16384_K2 | 3 | 508.84 | 0.51485 | — | no | chi2/dof 508.84 > 1.5; flags: nonlinear parameter at search boundary; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.6_second_Nmin4096_K1 | 6 | 10.21 | 0.47711 | — | no | chi2/dof 10.21 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.6_second_Nmin4096_K2 | 7 | 1.55 | 0.48427 | — | no | chi2/dof 1.55 > 1.5 |
| x0.6_second_Nmin8192_K1 | 6 | 4.45 | 0.48087 | — | no | chi2/dof 4.45 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.6_second_Nmin8192_K2 | 3 | 487.56 | 0.53849 | — | no | chi2/dof 487.56 > 1.5; flags: nonlinear parameter at search boundary; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.6_second_Nmin16384_K1 | 7 | 2.55 | 0.48015 | — | no | chi2/dof 2.55 > 1.5; mean |pull| > 1.2 for ['Y', "Y''", 'U', "U''"] |
| x0.6_second_Nmin16384_K2 | 3 | 483.46 | 0.52806 | — | no | chi2/dof 483.46 > 1.5; flags: nonlinear parameter at search boundary; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.35_leading_Nmin4096_K1 | 5 | 9.64 | 0.47797 | — | no | chi2/dof 9.64 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.35_leading_Nmin4096_K2 | 5 | 7.31 | 0.48953 | — | no | chi2/dof 7.31 > 1.5; mean |pull| > 1.2 for ["Y'", "Y''", "U'", "U''"] |
| x0.35_leading_Nmin8192_K1 | 5 | 4.90 | 0.47818 | — | no | chi2/dof 4.90 > 1.5; mean |pull| > 1.2 for ['Y', "Y''", 'U', "U'", "U''"] |
| x0.35_leading_Nmin8192_K2 | 5 | 4.11 | 0.48620 | — | no | chi2/dof 4.11 > 1.5; mean |pull| > 1.2 for ["Y''"] |
| x0.35_leading_Nmin16384_K1 | 5 | 2.91 | 0.47777 | — | no | chi2/dof 2.91 > 1.5; mean |pull| > 1.2 for ["Y''", 'U', "U'", "U''"] |
| x0.35_leading_Nmin16384_K2 | 3 | 277.73 | 0.50738 | — | no | chi2/dof 277.73 > 1.5; flags: nonlinear parameter at search boundary; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.35_background_Nmin4096_K1 | 5 | 7.53 | 0.47517 | — | no | chi2/dof 7.53 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.35_background_Nmin4096_K2 | 5 | 1.76 | 0.48503 | — | no | chi2/dof 1.76 > 1.5 |
| x0.35_background_Nmin8192_K1 | 5 | 3.83 | 0.47634 | — | no | chi2/dof 3.83 > 1.5; mean |pull| > 1.2 for ["Y''", 'U', "U'", "U''"] |
| x0.35_background_Nmin8192_K2 | 5 | 1.39 | 0.48431 | 0.00057 | no | structured residuals |
| x0.35_background_Nmin16384_K1 | 5 | 2.39 | 0.47657 | — | no | chi2/dof 2.39 > 1.5; mean |pull| > 1.2 for ["Y''", "U''"] |
| x0.35_background_Nmin16384_K2 | 3 | 277.41 | 0.52611 | — | no | chi2/dof 277.41 > 1.5; flags: nonlinear parameter at search boundary; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.35_second_Nmin4096_K1 | 5 | 5.22 | 0.47457 | — | no | chi2/dof 5.22 > 1.5; mean |pull| > 1.2 for ['Y', "Y''", 'U', "U'", "U''"] |
| x0.35_second_Nmin4096_K2 | 5 | 1.16 | 0.48368 | 0.00052 | yes |  |
| x0.35_second_Nmin8192_K1 | 5 | 2.60 | 0.47643 | — | no | chi2/dof 2.60 > 1.5; mean |pull| > 1.2 for ['Y', "Y''", 'U', "U''"] |
| x0.35_second_Nmin8192_K2 | 5 | 1.10 | 0.48329 | 0.00067 | yes |  |
| x0.35_second_Nmin16384_K1 | 5 | 1.89 | 0.47747 | — | no | chi2/dof 1.89 > 1.5; mean |pull| > 1.2 for ["U''"] |
| x0.35_second_Nmin16384_K2 | 3 | 263.90 | 0.53055 | — | no | chi2/dof 263.90 > 1.5; flags: nonlinear parameter at search boundary; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |

Cross-check: pass; distinct eligible series ['xc0.45_plus', 'xc0.45_star', 'xc0.6_plus', 'xc0.6_star'] (duplicates removed: []); standalone: {'status': 'ok', 'Delta_inf': 0.48354875765589433, 'sigma_inf': 0.0006237441299328517, 'model_spread': 0.0004175233581187876, 'omega_profile_half_range': 0.0004175233581187876, 'Delta_omega_prime': 0.0008350467162375752, 'omega_range': [0.27, 0.28], 'common_valid': 300}
Crossing value: Delta_inf = 0.48355 ± 0.00062 (sigma_inf) ± 0.00084 (Delta_omega') from ['xc0.45_plus', 'xc0.45_star', 'xc0.6_plus', 'xc0.6_star']
Largest usable pairs: 131072-262144: Delta_eff(U) = 0.48349 ± 0.00133, Delta_eff(Y) = 0.46732 ± 0.00137 (300 valid draws; series xc0.45_star), 262144-524288: Delta_eff(U) = 0.48516 ± 0.00139, Delta_eff(Y) = 0.47148 ± 0.00128 (300 valid draws; series xc0.45_star)
- xc0.45_plus: Delta_inf 0.48314 omega' 0.28 chi2/dof 2.42/4 pairs [1024, 65536, 131072, 262144] — eligible
- xc0.45_star: Delta_inf 0.48318 omega' 0.28 chi2/dof 2.34/4 pairs [1024, 65536, 131072, 262144] — eligible
- xc0.6_plus: Delta_inf 0.48397 omega' 0.27 chi2/dof 2.24/4 pairs [2048, 65536, 131072, 262144] — eligible
- xc0.6_star: Delta_inf 0.48391 omega' 0.27 chi2/dof 2.11/4 pairs [2048, 65536, 131072, 262144] — eligible
Reblocking: block 2048: sigma_stat 0.00054 (ok); block 8192: sigma_stat 0.00054 (ok)

