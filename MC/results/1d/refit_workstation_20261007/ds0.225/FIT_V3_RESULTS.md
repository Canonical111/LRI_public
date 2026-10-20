# FIT v3 results (production; x-windows; schedule 20260916, bootstrap 300, calibration 500)

Protocol: FIT_MODEL_V3.md §4 (decision table §4.6). Selection blind to Delta_epsilon; (beta_c, Delta_eps) for the windows frozen in pre.json.

## Delta_sigma = 0.225 (s = 0.55)

**Decision: CONDITIONAL (sigma_sys coverage absent)**

Quoted: Delta_epsilon = 0.47912 ± 0.00068 (stat) (sigma_sys unresolved)
from x0.35_second_Nmin16384_K2 degree 7 (chi2/dof 189.8/132); quotable 1; range [0.47911659515094096, 0.47911659515094096]

Equilibration (population rule): PASS — groups 70, hot/cold |z|>3: 0 (0.0%), half-chain |z|>3: 0 (0.0%)
Coverage guard: 54/54 configurations admissible

| configuration | d* | chi2/dof | Delta_eps | sigma_stat | quotable | reasons |
|---|---|---|---|---|---|---|
| x0.45_leading_Nmin4096_K1 | 6 | 32.95 | 0.46839 | — | no | chi2/dof 32.95 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.45_leading_Nmin4096_K2 | 6 | 31.38 | 0.47221 | — | no | chi2/dof 31.38 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.45_leading_Nmin8192_K1 | 6 | 16.83 | 0.46926 | — | no | chi2/dof 16.83 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.45_leading_Nmin8192_K2 | 6 | 16.29 | 0.47197 | — | no | chi2/dof 16.29 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.45_leading_Nmin16384_K1 | 6 | 6.16 | 0.47262 | — | no | chi2/dof 6.16 > 1.5; mean |pull| > 1.2 for ["Y''", 'U', "U'", "U''"] |
| x0.45_leading_Nmin16384_K2 | 6 | 6.20 | 0.47307 | — | no | chi2/dof 6.20 > 1.5; mean |pull| > 1.2 for ["Y''", 'U', "U'", "U''"] |
| x0.45_background_Nmin4096_K1 | 6 | 28.27 | 0.46743 | — | no | chi2/dof 28.27 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.45_background_Nmin4096_K2 | 6 | 9.27 | 0.48107 | — | no | chi2/dof 9.27 > 1.5; mean |pull| > 1.2 for ["Y'", "Y''", 'U', "U'", "U''"] |
| x0.45_background_Nmin8192_K1 | 7 | 13.10 | 0.46882 | — | no | chi2/dof 13.10 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.45_background_Nmin8192_K2 | 6 | 3.78 | 0.48117 | — | no | chi2/dof 3.78 > 1.5; mean |pull| > 1.2 for ["Y''", "U'", "U''"] |
| x0.45_background_Nmin16384_K1 | 6 | 4.95 | 0.47164 | — | no | chi2/dof 4.95 > 1.5; mean |pull| > 1.2 for ["Y''", 'U', "U'", "U''"] |
| x0.45_background_Nmin16384_K2 | 6 | 2.04 | 0.48278 | — | no | chi2/dof 2.04 > 1.5; mean |pull| > 1.2 for ["U''"] |
| x0.45_second_Nmin4096_K1 | 6 | 20.06 | 0.46733 | — | no | chi2/dof 20.06 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.45_second_Nmin4096_K2 | 6 | 3.95 | 0.47929 | — | no | chi2/dof 3.95 > 1.5; mean |pull| > 1.2 for ["Y''", "U'", "U''"] |
| x0.45_second_Nmin8192_K1 | 5 | 11.20 | 0.46932 | — | no | chi2/dof 11.20 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.45_second_Nmin8192_K2 | 7 | 2.01 | 0.47873 | — | no | chi2/dof 2.01 > 1.5; mean |pull| > 1.2 for ["Y''"] |
| x0.45_second_Nmin16384_K1 | 4 | 78.72 | 0.46759 | — | no | chi2/dof 78.72 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.45_second_Nmin16384_K2 | 6 | 1.57 | 0.47977 | — | no | chi2/dof 1.57 > 1.5 |
| x0.6_leading_Nmin4096_K1 | 7 | 39.13 | 0.46827 | — | no | chi2/dof 39.13 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.6_leading_Nmin4096_K2 | 6 | 39.97 | 0.47102 | — | no | chi2/dof 39.97 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.6_leading_Nmin8192_K1 | 7 | 17.68 | 0.47000 | — | no | chi2/dof 17.68 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.6_leading_Nmin8192_K2 | 3 | 491.09 | 0.50687 | — | no | chi2/dof 491.09 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.6_leading_Nmin16384_K1 | 7 | 8.88 | 0.47082 | — | no | chi2/dof 8.88 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.6_leading_Nmin16384_K2 | 3 | 471.01 | 0.49448 | — | no | chi2/dof 471.01 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.6_background_Nmin4096_K1 | 7 | 31.53 | 0.46795 | — | no | chi2/dof 31.53 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.6_background_Nmin4096_K2 | 6 | 14.81 | 0.47993 | — | no | chi2/dof 14.81 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.6_background_Nmin8192_K1 | 7 | 14.94 | 0.46944 | — | no | chi2/dof 14.94 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.6_background_Nmin8192_K2 | 3 | 451.73 | 0.49868 | — | no | chi2/dof 451.73 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.6_background_Nmin16384_K1 | 7 | 8.01 | 0.47080 | — | no | chi2/dof 8.01 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.6_background_Nmin16384_K2 | 3 | 432.38 | 0.49119 | — | no | chi2/dof 432.38 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.6_second_Nmin4096_K1 | 7 | 23.98 | 0.46678 | — | no | chi2/dof 23.98 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.6_second_Nmin4096_K2 | 3 | 538.67 | 0.47375 | — | no | chi2/dof 538.67 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.6_second_Nmin8192_K1 | 3 | 604.09 | 0.46236 | — | no | chi2/dof 604.09 > 1.5; flags: nonlinear parameter at search boundary; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.6_second_Nmin8192_K2 | 3 | 433.66 | 0.49939 | — | no | chi2/dof 433.66 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.6_second_Nmin16384_K1 | 3 | 559.83 | 0.46038 | — | no | chi2/dof 559.83 > 1.5; flags: nonlinear parameter at search boundary; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.6_second_Nmin16384_K2 | 3 | 430.41 | 0.49167 | — | no | chi2/dof 430.41 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.35_leading_Nmin4096_K1 | 7 | 17.45 | 0.46951 | — | no | chi2/dof 17.45 > 1.5; mean |pull| > 1.2 for ["Y'", "Y''", 'U', "U'", "U''"] |
| x0.35_leading_Nmin4096_K2 | 5 | 22.40 | 0.46852 | — | no | chi2/dof 22.40 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.35_leading_Nmin8192_K1 | 7 | 9.10 | 0.47029 | — | no | chi2/dof 9.10 > 1.5; mean |pull| > 1.2 for ["Y'", "Y''", 'U', "U'", "U''"] |
| x0.35_leading_Nmin8192_K2 | 7 | 9.16 | 0.46981 | — | no | chi2/dof 9.16 > 1.5; mean |pull| > 1.2 for ["Y'", "Y''", 'U', "U'", "U''"] |
| x0.35_leading_Nmin16384_K1 | 7 | 5.25 | 0.47159 | — | no | chi2/dof 5.25 > 1.5; mean |pull| > 1.2 for ["Y''", 'U', "U'", "U''"] |
| x0.35_leading_Nmin16384_K2 | 7 | 5.23 | 0.47319 | — | no | chi2/dof 5.23 > 1.5; mean |pull| > 1.2 for ["Y''", 'U', "U'", "U''"] |
| x0.35_background_Nmin4096_K1 | 5 | 16.13 | 0.46786 | — | no | chi2/dof 16.13 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.35_background_Nmin4096_K2 | 6 | 7.10 | 0.48289 | — | no | chi2/dof 7.10 > 1.5; mean |pull| > 1.2 for ["Y'", "Y''", 'U', "U'", "U''"] |
| x0.35_background_Nmin8192_K1 | 5 | 8.91 | 0.46984 | — | no | chi2/dof 8.91 > 1.5; mean |pull| > 1.2 for ["Y'", "Y''", 'U', "U'", "U''"] |
| x0.35_background_Nmin8192_K2 | 7 | 3.33 | 0.48135 | — | no | chi2/dof 3.33 > 1.5; mean |pull| > 1.2 for ["Y''", "U'", "U''"] |
| x0.35_background_Nmin16384_K1 | 7 | 4.27 | 0.47026 | — | no | chi2/dof 4.27 > 1.5; mean |pull| > 1.2 for ["Y''", 'U', "U'", "U''"] |
| x0.35_background_Nmin16384_K2 | 7 | 1.97 | 0.48238 | — | no | chi2/dof 1.97 > 1.5 |
| x0.35_second_Nmin4096_K1 | 3 | 161.27 | 0.46622 | — | no | chi2/dof 161.27 > 1.5; flags: nonlinear parameter at search boundary; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.35_second_Nmin4096_K2 | 6 | 2.22 | 0.47806 | — | no | chi2/dof 2.22 > 1.5; mean |pull| > 1.2 for ["Y''", "U''"] |
| x0.35_second_Nmin8192_K1 | 7 | 4.78 | 0.46751 | — | no | chi2/dof 4.78 > 1.5; mean |pull| > 1.2 for ["Y''", 'U', "U'", "U''"] |
| x0.35_second_Nmin8192_K2 | 6 | 1.72 | 0.47863 | — | no | chi2/dof 1.72 > 1.5 |
| x0.35_second_Nmin16384_K1 | 5 | 3.84 | 0.46972 | — | no | chi2/dof 3.84 > 1.5; mean |pull| > 1.2 for ['Y', "Y''", 'U', "U'", "U''"] |
| x0.35_second_Nmin16384_K2 | 7 | 1.44 | 0.47912 | 0.00068 | yes |  |

Cross-check: CROSS-CHECK UNAVAILABLE (fewer than 2 eligible series); distinct eligible series [] (duplicates removed: []); standalone: {'status': 'EXTRAPOLATION UNAVAILABLE (fewer than 2 distinct eligible series)'}
Crossing value: unavailable
Largest usable pairs: 131072-262144: Delta_eff(U) = 0.48135 ± 0.00153, Delta_eff(Y) = 0.44053 ± 0.00158 (300 valid draws; series xc0.45_star), 262144-524288: Delta_eff(U) = 0.48444 ± 0.00160, Delta_eff(Y) = 0.44639 ± 0.00165 (300 valid draws; series xc0.45_star)
- xc0.45_plus: Delta_inf 0.47801 omega' 0.20 chi2/dof 27.33/4 pairs [4096, 65536, 131072, 262144] — extrapolation chi2/dof 6.83 > 2.0
- xc0.45_star: Delta_inf 0.47765 omega' 0.20 chi2/dof 27.22/4 pairs [4096, 65536, 131072, 262144] — extrapolation chi2/dof 6.80 > 2.0
- xc0.6_star: Delta_inf 0.48119 omega' 0.20 chi2/dof 13.77/4 pairs [8192, 16384, 32768, 262144] — extrapolation chi2/dof 3.44 > 2.0
- xc0.6_plus: Delta_inf 0.48087 omega' 0.20 chi2/dof 14.55/4 pairs [8192, 16384, 32768, 262144] — extrapolation chi2/dof 3.64 > 2.0
Reblocking: block 2048: sigma_stat 0.00066 (ok); block 8192: sigma_stat 0.00064 (ok)

