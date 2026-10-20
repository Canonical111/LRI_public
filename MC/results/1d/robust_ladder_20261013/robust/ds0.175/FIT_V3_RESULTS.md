# FIT v3 results (production; x-windows; schedule 20260916, bootstrap 300, calibration 500)

Protocol: FIT_MODEL_V3.md §4 (decision table §4.6). Selection blind to Delta_epsilon; (beta_c, Delta_eps) for the windows frozen in pre.json.

## Delta_sigma = 0.175 (s = 0.65)

**Decision: CROSS-CHECK FAILED**

Quoted: Delta_epsilon = 0.48460 ± 0.00035 (stat) ± 0.00115 (sys; ratio to median sigma_stat 2.1)
from x0.45_second_Nmin4096_K2 degree 6 (chi2/dof 220.2/182); quotable 13; range [0.4822987236383077, 0.4845993642634777]

Equilibration (population rule): PASS — groups 70, hot/cold |z|>3: 0 (0.0%), half-chain |z|>3: 3 (0.5%)
Coverage guard: 54/54 configurations admissible

| configuration | d* | chi2/dof | Delta_eps | sigma_stat | quotable | reasons |
|---|---|---|---|---|---|---|
| x0.45_leading_Nmin4096_K1 | 5 | 16.97 | 0.47827 | — | no | chi2/dof 16.97 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.45_leading_Nmin4096_K2 | 5 | 9.01 | 0.48863 | — | no | chi2/dof 9.01 > 1.5; mean |pull| > 1.2 for ["Y'", "Y''", 'U', "U''"] |
| x0.45_leading_Nmin8192_K1 | 5 | 8.25 | 0.47733 | — | no | chi2/dof 8.25 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.45_leading_Nmin8192_K2 | 5 | 4.83 | 0.48568 | — | no | chi2/dof 4.83 > 1.5; mean |pull| > 1.2 for ["Y''", "U''"] |
| x0.45_leading_Nmin16384_K1 | 5 | 4.08 | 0.47704 | — | no | chi2/dof 4.08 > 1.5; mean |pull| > 1.2 for ['Y', "Y''", 'U', "U'"] |
| x0.45_leading_Nmin16384_K2 | 5 | 2.79 | 0.48287 | — | no | chi2/dof 2.79 > 1.5 |
| x0.45_background_Nmin4096_K1 | 5 | 15.67 | 0.47691 | — | no | chi2/dof 15.67 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.45_background_Nmin4096_K2 | 5 | 2.13 | 0.48515 | — | no | chi2/dof 2.13 > 1.5; mean |pull| > 1.2 for ["U''"] |
| x0.45_background_Nmin8192_K1 | 5 | 7.56 | 0.47698 | — | no | chi2/dof 7.56 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.45_background_Nmin8192_K2 | 6 | 1.40 | 0.48453 | 0.00040 | yes |  |
| x0.45_background_Nmin16384_K1 | 5 | 3.65 | 0.47716 | — | no | chi2/dof 3.65 > 1.5; mean |pull| > 1.2 for ['Y', "Y''", 'U', "U'"] |
| x0.45_background_Nmin16384_K2 | 6 | 1.04 | 0.48394 | 0.00055 | yes |  |
| x0.45_second_Nmin4096_K1 | 5 | 9.75 | 0.47833 | — | no | chi2/dof 9.75 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.45_second_Nmin4096_K2 | 6 | 1.21 | 0.48460 | 0.00035 | yes |  |
| x0.45_second_Nmin8192_K1 | 5 | 4.22 | 0.47833 | — | no | chi2/dof 4.22 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.45_second_Nmin8192_K2 | 6 | 1.07 | 0.48399 | 0.00045 | yes |  |
| x0.45_second_Nmin16384_K1 | 5 | 2.09 | 0.47806 | — | no | chi2/dof 2.09 > 1.5; mean |pull| > 1.2 for ["Y''", "U''"] |
| x0.45_second_Nmin16384_K2 | 6 | 0.92 | 0.48328 | 0.00066 | yes |  |
| x0.6_leading_Nmin4096_K1 | 6 | 18.48 | 0.47685 | — | no | chi2/dof 18.48 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.6_leading_Nmin4096_K2 | 6 | 10.88 | 0.48660 | — | no | chi2/dof 10.88 > 1.5; mean |pull| > 1.2 for ["Y'", "Y''", 'U', "U''"] |
| x0.6_leading_Nmin8192_K1 | 6 | 8.42 | 0.47839 | — | no | chi2/dof 8.42 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.6_leading_Nmin8192_K2 | 6 | 4.76 | 0.48651 | — | no | chi2/dof 4.76 > 1.5; mean |pull| > 1.2 for ["Y''", "U''"] |
| x0.6_leading_Nmin16384_K1 | 7 | 4.13 | 0.47809 | — | no | chi2/dof 4.13 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'"] |
| x0.6_leading_Nmin16384_K2 | 7 | 2.55 | 0.48420 | — | no | chi2/dof 2.55 > 1.5 |
| x0.6_background_Nmin4096_K1 | 6 | 16.25 | 0.47632 | — | no | chi2/dof 16.25 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.6_background_Nmin4096_K2 | 6 | 2.38 | 0.48502 | — | no | chi2/dof 2.38 > 1.5; mean |pull| > 1.2 for ["Y''"] |
| x0.6_background_Nmin8192_K1 | 6 | 7.76 | 0.47817 | — | no | chi2/dof 7.76 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.6_background_Nmin8192_K2 | 7 | 1.49 | 0.48452 | 0.00037 | yes |  |
| x0.6_background_Nmin16384_K1 | 7 | 3.90 | 0.47813 | — | no | chi2/dof 3.90 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'"] |
| x0.6_background_Nmin16384_K2 | 3 | 506.64 | 0.51272 | — | no | chi2/dof 506.64 > 1.5; flags: nonlinear parameter at search boundary; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.6_second_Nmin4096_K1 | 6 | 10.81 | 0.47632 | — | no | chi2/dof 10.81 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.6_second_Nmin4096_K2 | 6 | 1.45 | 0.48450 | 0.00029 | yes |  |
| x0.6_second_Nmin8192_K1 | 6 | 4.40 | 0.47986 | — | no | chi2/dof 4.40 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.6_second_Nmin8192_K2 | 3 | 486.29 | 0.53660 | — | no | chi2/dof 486.29 > 1.5; flags: nonlinear parameter at search boundary; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.6_second_Nmin16384_K1 | 7 | 2.19 | 0.47939 | — | no | chi2/dof 2.19 > 1.5; mean |pull| > 1.2 for ['Y', "Y''"] |
| x0.6_second_Nmin16384_K2 | 7 | 0.95 | 0.48350 | 0.00058 | yes |  |
| x0.35_leading_Nmin4096_K1 | 5 | 9.60 | 0.47728 | — | no | chi2/dof 9.60 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.35_leading_Nmin4096_K2 | 5 | 7.04 | 0.48984 | — | no | chi2/dof 7.04 > 1.5; mean |pull| > 1.2 for ["Y'", "Y''", "U''"] |
| x0.35_leading_Nmin8192_K1 | 5 | 4.89 | 0.47720 | — | no | chi2/dof 4.89 > 1.5; mean |pull| > 1.2 for ['Y', "Y''", 'U', "U'", "U''"] |
| x0.35_leading_Nmin8192_K2 | 5 | 3.88 | 0.48644 | — | no | chi2/dof 3.88 > 1.5; mean |pull| > 1.2 for ["Y''"] |
| x0.35_leading_Nmin16384_K1 | 5 | 2.75 | 0.47728 | — | no | chi2/dof 2.75 > 1.5; mean |pull| > 1.2 for ["Y''", 'U'] |
| x0.35_leading_Nmin16384_K2 | 5 | 2.42 | 0.48284 | — | no | chi2/dof 2.42 > 1.5 |
| x0.35_background_Nmin4096_K1 | 5 | 7.83 | 0.47443 | — | no | chi2/dof 7.83 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.35_background_Nmin4096_K2 | 5 | 1.81 | 0.48527 | — | no | chi2/dof 1.81 > 1.5; mean |pull| > 1.2 for ["Y''"] |
| x0.35_background_Nmin8192_K1 | 5 | 4.08 | 0.47571 | — | no | chi2/dof 4.08 > 1.5; mean |pull| > 1.2 for ['Y', "Y''", 'U', "U'", "U''"] |
| x0.35_background_Nmin8192_K2 | 5 | 1.29 | 0.48451 | 0.00050 | yes |  |
| x0.35_background_Nmin16384_K1 | 5 | 2.30 | 0.47628 | — | no | chi2/dof 2.30 > 1.5; mean |pull| > 1.2 for ["Y''"] |
| x0.35_background_Nmin16384_K2 | 6 | 1.02 | 0.48353 | 0.00070 | yes |  |
| x0.35_second_Nmin4096_K1 | 5 | 5.21 | 0.47424 | — | no | chi2/dof 5.21 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.35_second_Nmin4096_K2 | 6 | 1.05 | 0.48366 | 0.00054 | yes |  |
| x0.35_second_Nmin8192_K1 | 5 | 2.59 | 0.47603 | — | no | chi2/dof 2.59 > 1.5; mean |pull| > 1.2 for ["Y''", "U''"] |
| x0.35_second_Nmin8192_K2 | 6 | 0.94 | 0.48325 | 0.00065 | yes |  |
| x0.35_second_Nmin16384_K1 | 5 | 1.51 | 0.47703 | — | no | chi2/dof 1.51 > 1.5 |
| x0.35_second_Nmin16384_K2 | 6 | 0.87 | 0.48230 | 0.00087 | yes |  |

Cross-check: CROSS-CHECK FAILED (|difference| > 2 sigma_D); distinct eligible series ['xc0.6_star', 'xc0.6_plus'] (duplicates removed: []); standalone: {'status': 'ok', 'Delta_inf': 0.48304478839178505, 'sigma_inf': 0.0008094196590147096, 'model_spread': 5.218024355047035e-06, 'omega_profile_half_range': 5.218024355047035e-06, 'Delta_omega_prime': 1.043604871009407e-05, 'omega_range': [0.27, 0.27], 'common_valid': 300}
Crossing value: Delta_inf = 0.48304 ± 0.00081 (sigma_inf) ± 0.00001 (Delta_omega') from ['xc0.6_star', 'xc0.6_plus']
Largest usable pairs: 131072-262144: Delta_eff(U) = 0.48390 ± 0.00137, Delta_eff(Y) = 0.46681 ± 0.00131 (300 valid draws; series xc0.45_star), 262144-524288: Delta_eff(U) = 0.48514 ± 0.00144, Delta_eff(Y) = 0.46999 ± 0.00133 (300 valid draws; series xc0.45_star)
- xc0.45_star:  — only 0 usable doubling pairs
- xc0.45_plus:  — only 0 usable doubling pairs
- xc0.6_star: Delta_inf 0.48304 omega' 0.27 chi2/dof 0.78/4 pairs [2048, 65536, 131072, 262144] — eligible
- xc0.6_plus: Delta_inf 0.48305 omega' 0.27 chi2/dof 0.72/4 pairs [2048, 65536, 131072, 262144] — eligible
Reblocking: block 2048: sigma_stat 0.00036 (ok); block 8192: sigma_stat 0.00034 (ok)

