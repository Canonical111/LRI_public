# FIT v3 results (production; x-windows; schedule 20260916, bootstrap 300, calibration 500)

Protocol: FIT_MODEL_V3.md §4 (decision table §4.6). Selection blind to Delta_epsilon; (beta_c, Delta_eps) for the windows frozen in pre.json.

## Delta_sigma = 0.1625 (s = 0.675)

**Decision: ACCEPTED**

Quoted: Delta_epsilon = 0.48761 ± 0.00058 (stat) ± 0.00024 (sys; ratio to median sigma_stat 0.5)
from x0.35_second_Nmin4096_K2 degree 5 (chi2/dof 197.8/166); quotable 6; range [0.48720584427527125, 0.4876958123218533]

Equilibration (population rule): PASS — groups 70, hot/cold |z|>3: 0 (0.0%), half-chain |z|>3: 4 (0.7%)
Coverage guard: 54/54 configurations admissible

| configuration | d* | chi2/dof | Delta_eps | sigma_stat | quotable | reasons |
|---|---|---|---|---|---|---|
| x0.45_leading_Nmin4096_K1 | 5 | 13.58 | 0.48507 | — | no | chi2/dof 13.58 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.45_leading_Nmin4096_K2 | 5 | 5.81 | 0.49195 | — | no | chi2/dof 5.81 > 1.5; mean |pull| > 1.2 for ["Y'", "Y''", "U'", "U''"] |
| x0.45_leading_Nmin8192_K1 | 5 | 6.95 | 0.48356 | — | no | chi2/dof 6.95 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.45_leading_Nmin8192_K2 | 5 | 3.77 | 0.49012 | — | no | chi2/dof 3.77 > 1.5; mean |pull| > 1.2 for ["Y''"] |
| x0.45_leading_Nmin16384_K1 | 5 | 3.72 | 0.48290 | — | no | chi2/dof 3.72 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.45_leading_Nmin16384_K2 | 3 | 320.40 | 0.51046 | — | no | chi2/dof 320.40 > 1.5; flags: nonlinear parameter at search boundary; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.45_background_Nmin4096_K1 | 5 | 12.75 | 0.48448 | — | no | chi2/dof 12.75 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.45_background_Nmin4096_K2 | 6 | 1.91 | 0.48810 | — | no | chi2/dof 1.91 > 1.5 |
| x0.45_background_Nmin8192_K1 | 5 | 6.22 | 0.48289 | — | no | chi2/dof 6.22 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.45_background_Nmin8192_K2 | 6 | 1.26 | 0.48746 | 0.00044 | yes |  |
| x0.45_background_Nmin16384_K1 | 3 | 423.32 | 0.44556 | — | no | chi2/dof 423.32 > 1.5; flags: nonlinear parameter at search boundary; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.45_background_Nmin16384_K2 | 3 | 311.55 | 0.53712 | — | no | chi2/dof 311.55 > 1.5; flags: nonlinear parameter at search boundary; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.45_second_Nmin4096_K1 | 5 | 7.90 | 0.48477 | — | no | chi2/dof 7.90 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.45_second_Nmin4096_K2 | 6 | 1.28 | 0.48770 | 0.00042 | yes |  |
| x0.45_second_Nmin8192_K1 | 3 | 477.38 | 0.44847 | — | no | chi2/dof 477.38 > 1.5; flags: nonlinear parameter at search boundary; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.45_second_Nmin8192_K2 | 6 | 1.14 | 0.48721 | 0.00048 | yes |  |
| x0.45_second_Nmin16384_K1 | 3 | 427.19 | 0.44250 | — | no | chi2/dof 427.19 > 1.5; flags: nonlinear parameter at search boundary; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.45_second_Nmin16384_K2 | 3 | 298.37 | 0.54123 | — | no | chi2/dof 298.37 > 1.5; flags: nonlinear parameter at search boundary; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.6_leading_Nmin4096_K1 | 6 | 15.93 | 0.48171 | — | no | chi2/dof 15.93 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.6_leading_Nmin4096_K2 | 6 | 7.47 | 0.49049 | — | no | chi2/dof 7.47 > 1.5; mean |pull| > 1.2 for ["Y'", "Y''", "U'", "U''"] |
| x0.6_leading_Nmin8192_K1 | 6 | 7.13 | 0.48377 | — | no | chi2/dof 7.13 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.6_leading_Nmin8192_K2 | 6 | 3.62 | 0.49030 | — | no | chi2/dof 3.62 > 1.5; mean |pull| > 1.2 for ["Y''"] |
| x0.6_leading_Nmin16384_K1 | 7 | 3.59 | 0.48300 | — | no | chi2/dof 3.59 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.6_leading_Nmin16384_K2 | 3 | 672.21 | 0.52104 | — | no | chi2/dof 672.21 > 1.5; flags: nonlinear parameter at search boundary; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.6_background_Nmin4096_K1 | 6 | 14.15 | 0.48080 | — | no | chi2/dof 14.15 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.6_background_Nmin4096_K2 | 6 | 2.00 | 0.48777 | — | no | chi2/dof 2.00 > 1.5 |
| x0.6_background_Nmin8192_K1 | 3 | 926.39 | 0.48665 | — | no | chi2/dof 926.39 > 1.5; flags: nonlinear parameter at search boundary; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.6_background_Nmin8192_K2 | 3 | 647.96 | 0.56575 | — | no | chi2/dof 647.96 > 1.5; flags: nonlinear parameter at search boundary; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.6_background_Nmin16384_K1 | 3 | 895.22 | 0.49896 | — | no | chi2/dof 895.22 > 1.5; flags: nonlinear parameter at search boundary; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.6_background_Nmin16384_K2 | 3 | 612.76 | 0.55850 | — | no | chi2/dof 612.76 > 1.5; flags: nonlinear parameter at search boundary; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.6_second_Nmin4096_K1 | 6 | 8.63 | 0.48113 | — | no | chi2/dof 8.63 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.6_second_Nmin4096_K2 | 6 | 1.42 | 0.48729 | 0.00029 | yes |  |
| x0.6_second_Nmin8192_K1 | 3 | 931.84 | 0.48829 | — | no | chi2/dof 931.84 > 1.5; flags: nonlinear parameter at search boundary; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.6_second_Nmin8192_K2 | 3 | 588.71 | 0.56262 | — | no | chi2/dof 588.71 > 1.5; flags: nonlinear parameter at search boundary; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.6_second_Nmin16384_K1 | 3 | 901.82 | 0.50193 | — | no | chi2/dof 901.82 > 1.5; flags: nonlinear parameter at search boundary; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.6_second_Nmin16384_K2 | 3 | 599.35 | 0.55964 | — | no | chi2/dof 599.35 > 1.5; flags: nonlinear parameter at search boundary; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.35_leading_Nmin4096_K1 | 5 | 8.75 | 0.48391 | — | no | chi2/dof 8.75 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.35_leading_Nmin4096_K2 | 5 | 4.73 | 0.49331 | — | no | chi2/dof 4.73 > 1.5; mean |pull| > 1.2 for ["Y'", "Y''", "U'", "U''"] |
| x0.35_leading_Nmin8192_K1 | 5 | 4.61 | 0.48369 | — | no | chi2/dof 4.61 > 1.5; mean |pull| > 1.2 for ['Y', "Y''", 'U', "U'", "U''"] |
| x0.35_leading_Nmin8192_K2 | 5 | 3.02 | 0.49188 | — | no | chi2/dof 3.02 > 1.5; mean |pull| > 1.2 for ["Y'", "Y''"] |
| x0.35_leading_Nmin16384_K1 | 5 | 2.53 | 0.48460 | — | no | chi2/dof 2.53 > 1.5; mean |pull| > 1.2 for ["Y''", 'U', "U'"] |
| x0.35_leading_Nmin16384_K2 | 3 | 261.79 | 0.50834 | — | no | chi2/dof 261.79 > 1.5; flags: nonlinear parameter at search boundary; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.35_background_Nmin4096_K1 | 5 | 7.60 | 0.48178 | — | no | chi2/dof 7.60 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.35_background_Nmin4096_K2 | 5 | 1.67 | 0.48851 | — | no | chi2/dof 1.67 > 1.5 |
| x0.35_background_Nmin8192_K1 | 5 | 3.83 | 0.48153 | — | no | chi2/dof 3.83 > 1.5; mean |pull| > 1.2 for ["Y''", 'U', "U'"] |
| x0.35_background_Nmin8192_K2 | 3 | 293.40 | 0.50327 | — | no | chi2/dof 293.40 > 1.5; flags: nonlinear parameter at search boundary; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.35_background_Nmin16384_K1 | 5 | 2.30 | 0.48613 | — | no | chi2/dof 2.30 > 1.5; mean |pull| > 1.2 for ["Y''", "U'"] |
| x0.35_background_Nmin16384_K2 | 3 | 257.76 | 0.52243 | — | no | chi2/dof 257.76 > 1.5; flags: nonlinear parameter at search boundary; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.35_second_Nmin4096_K1 | 5 | 4.94 | 0.48099 | — | no | chi2/dof 4.94 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.35_second_Nmin4096_K2 | 5 | 1.19 | 0.48761 | 0.00058 | yes |  |
| x0.35_second_Nmin8192_K1 | 5 | 2.49 | 0.48205 | — | no | chi2/dof 2.49 > 1.5; mean |pull| > 1.2 for ["Y''", "U''"] |
| x0.35_second_Nmin8192_K2 | 5 | 1.16 | 0.48734 | 0.00067 | yes |  |
| x0.35_second_Nmin16384_K1 | 5 | 1.66 | 0.48604 | — | no | chi2/dof 1.66 > 1.5; mean |pull| > 1.2 for ["Y''"] |
| x0.35_second_Nmin16384_K2 | 3 | 259.01 | 0.49690 | — | no | chi2/dof 259.01 > 1.5; flags: nonlinear parameter at search boundary; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |

Cross-check: pass; distinct eligible series ['xc0.45_star', 'xc0.45_plus', 'xc0.6_star', 'xc0.6_plus'] (duplicates removed: []); standalone: {'status': 'ok', 'Delta_inf': 0.4873226569958256, 'sigma_inf': 0.0007536440912191966, 'model_spread': 0.0011070877191454165, 'omega_profile_half_range': 0.0018598941031963134, 'Delta_omega_prime': 0.00296698182234173, 'omega_range': [0.25, 0.31], 'common_valid': 300}
Crossing value: Delta_inf = 0.48732 ± 0.00075 (sigma_inf) ± 0.00297 (Delta_omega') from ['xc0.45_star', 'xc0.45_plus', 'xc0.6_star', 'xc0.6_plus']
Largest usable pairs: 131072-262144: Delta_eff(U) = 0.48749 ± 0.00120, Delta_eff(Y) = 0.47458 ± 0.00114 (300 valid draws; series xc0.45_star), 262144-524288: Delta_eff(U) = 0.48890 ± 0.00138, Delta_eff(Y) = 0.47707 ± 0.00133 (300 valid draws; series xc0.45_star)
- xc0.45_star: Delta_inf 0.48723 omega' 0.30 chi2/dof 1.63/4 pairs [1024, 65536, 131072, 262144] — eligible
- xc0.45_plus: Delta_inf 0.48742 omega' 0.30 chi2/dof 2.09/4 pairs [1024, 65536, 131072, 262144] — eligible
- xc0.6_star: Delta_inf 0.48529 omega' 0.31 chi2/dof 1.69/4 pairs [2048, 32768, 65536, 131072] — eligible
- xc0.6_plus: Delta_inf 0.48750 omega' 0.25 chi2/dof 2.18/4 pairs [32768, 65536, 131072, 262144] — eligible
Reblocking: block 2048: sigma_stat 0.00053 (ok); block 8192: sigma_stat 0.00053 (ok)

