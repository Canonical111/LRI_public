# FIT v3 results (production; x-windows; schedule 20260916, bootstrap 300, calibration 500)

Protocol: FIT_MODEL_V3.md §4 (decision table §4.6). Selection blind to Delta_epsilon; (beta_c, Delta_eps) for the windows frozen in pre.json.

## Delta_sigma = 0.15 (s = 0.7)

**Decision: CROSS-CHECK FAILED**

Quoted: Delta_epsilon = 0.49325 ± 0.00041 (stat) ± 0.00306 (sys; ratio to median sigma_stat 5.3)
from x0.35_background_Nmin4096_K2 degree 5 (chi2/dof 218.3/162); quotable 11; range [0.49034239602009333, 0.4964593548604985]

Equilibration (population rule): PASS — groups 70, hot/cold |z|>3: 0 (0.0%), half-chain |z|>3: 1 (0.2%)
Coverage guard: 54/54 configurations admissible

| configuration | d* | chi2/dof | Delta_eps | sigma_stat | quotable | reasons |
|---|---|---|---|---|---|---|
| x0.45_leading_Nmin4096_K1 | 4 | 9.56 | 0.49358 | — | no | chi2/dof 9.56 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.45_leading_Nmin4096_K2 | 7 | 3.22 | 0.49581 | — | no | chi2/dof 3.22 > 1.5; mean |pull| > 1.2 for ["Y'", "Y''", "U'"] |
| x0.45_leading_Nmin8192_K1 | 5 | 5.33 | 0.49227 | — | no | chi2/dof 5.33 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.45_leading_Nmin8192_K2 | 5 | 2.25 | 0.49510 | — | no | chi2/dof 2.25 > 1.5 |
| x0.45_leading_Nmin16384_K1 | 5 | 2.90 | 0.49149 | — | no | chi2/dof 2.90 > 1.5; mean |pull| > 1.2 for ['Y', "Y''", 'U', "U'", "U''"] |
| x0.45_leading_Nmin16384_K2 | 7 | 1.38 | 0.49567 | 0.00057 | yes |  |
| x0.45_background_Nmin4096_K1 | 4 | 9.22 | 0.49246 | — | no | chi2/dof 9.22 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.45_background_Nmin4096_K2 | 5 | 1.52 | 0.49255 | — | no | chi2/dof 1.52 > 1.5 |
| x0.45_background_Nmin8192_K1 | 5 | 5.11 | 0.49123 | — | no | chi2/dof 5.11 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.45_background_Nmin8192_K2 | 6 | 1.18 | 0.49227 | 0.00047 | yes |  |
| x0.45_background_Nmin16384_K1 | 5 | 2.67 | 0.49044 | — | no | chi2/dof 2.67 > 1.5; mean |pull| > 1.2 for ['Y', "Y''", 'U', "U'", "U''"] |
| x0.45_background_Nmin16384_K2 | 3 | 312.37 | 0.50888 | — | no | chi2/dof 312.37 > 1.5; flags: nonlinear parameter at search boundary; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.45_second_Nmin4096_K1 | 4 | 5.90 | 0.49392 | — | no | chi2/dof 5.90 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.45_second_Nmin4096_K2 | 6 | 1.01 | 0.49264 | 0.00045 | yes |  |
| x0.45_second_Nmin8192_K1 | 5 | 2.96 | 0.49239 | — | no | chi2/dof 2.96 > 1.5; mean |pull| > 1.2 for ['Y', "Y''", 'U', "U''"] |
| x0.45_second_Nmin8192_K2 | 3 | 377.49 | 0.55758 | — | no | chi2/dof 377.49 > 1.5; flags: nonlinear parameter at search boundary; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.45_second_Nmin16384_K1 | 5 | 1.50 | 0.49103 | — | no | chi2/dof 1.50 > 1.5 |
| x0.45_second_Nmin16384_K2 | 3 | 315.71 | 0.55623 | — | no | chi2/dof 315.71 > 1.5; flags: nonlinear parameter at search boundary; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.6_leading_Nmin4096_K1 | 6 | 13.61 | 0.48908 | — | no | chi2/dof 13.61 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.6_leading_Nmin4096_K2 | 6 | 5.05 | 0.49542 | — | no | chi2/dof 5.05 > 1.5; mean |pull| > 1.2 for ["Y'", "Y''", "U'", "U''"] |
| x0.6_leading_Nmin8192_K1 | 6 | 5.67 | 0.49219 | — | no | chi2/dof 5.67 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.6_leading_Nmin8192_K2 | 6 | 2.20 | 0.49575 | — | no | chi2/dof 2.20 > 1.5; mean |pull| > 1.2 for ["Y''"] |
| x0.6_leading_Nmin16384_K1 | 6 | 3.26 | 0.49113 | — | no | chi2/dof 3.26 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.6_leading_Nmin16384_K2 | 3 | 640.51 | 0.51478 | — | no | chi2/dof 640.51 > 1.5; flags: nonlinear parameter at search boundary; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.6_background_Nmin4096_K1 | 6 | 12.12 | 0.48760 | — | no | chi2/dof 12.12 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.6_background_Nmin4096_K2 | 7 | 1.62 | 0.49212 | — | no | chi2/dof 1.62 > 1.5; mean |pull| > 1.2 for ["Y''"] |
| x0.6_background_Nmin8192_K1 | 6 | 5.40 | 0.49163 | — | no | chi2/dof 5.40 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.6_background_Nmin8192_K2 | 3 | 625.86 | 0.51225 | — | no | chi2/dof 625.86 > 1.5; flags: nonlinear parameter at search boundary; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.6_background_Nmin16384_K1 | 6 | 3.06 | 0.49103 | — | no | chi2/dof 3.06 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.6_background_Nmin16384_K2 | 3 | 601.45 | 0.55984 | — | no | chi2/dof 601.45 > 1.5; flags: nonlinear parameter at search boundary; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.6_second_Nmin4096_K1 | 6 | 7.46 | 0.48834 | — | no | chi2/dof 7.46 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.6_second_Nmin4096_K2 | 3 | 692.31 | 0.56410 | — | no | chi2/dof 692.31 > 1.5; flags: nonlinear parameter at search boundary; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.6_second_Nmin8192_K1 | 6 | 2.96 | 0.49255 | — | no | chi2/dof 2.96 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U''"] |
| x0.6_second_Nmin8192_K2 | 3 | 586.48 | 0.57024 | — | no | chi2/dof 586.48 > 1.5; flags: nonlinear parameter at search boundary; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.6_second_Nmin16384_K1 | 6 | 1.64 | 0.49188 | — | no | chi2/dof 1.64 > 1.5 |
| x0.6_second_Nmin16384_K2 | 3 | 586.03 | 0.56135 | — | no | chi2/dof 586.03 > 1.5; flags: nonlinear parameter at search boundary; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.35_leading_Nmin4096_K1 | 4 | 6.91 | 0.49212 | — | no | chi2/dof 6.91 > 1.5; mean |pull| > 1.2 for ['Y', "Y''", 'U', "U'", "U''"] |
| x0.35_leading_Nmin4096_K2 | 5 | 3.06 | 0.49747 | — | no | chi2/dof 3.06 > 1.5; mean |pull| > 1.2 for ["Y'", "Y''", "U'"] |
| x0.35_leading_Nmin8192_K1 | 5 | 3.79 | 0.49091 | — | no | chi2/dof 3.79 > 1.5; mean |pull| > 1.2 for ['Y', "Y''", 'U', "U'", "U''"] |
| x0.35_leading_Nmin8192_K2 | 5 | 1.84 | 0.49667 | — | no | chi2/dof 1.84 > 1.5; mean |pull| > 1.2 for ["Y''"] |
| x0.35_leading_Nmin16384_K1 | 5 | 2.44 | 0.49065 | — | no | chi2/dof 2.44 > 1.5; mean |pull| > 1.2 for ["Y''", 'U', "U''"] |
| x0.35_leading_Nmin16384_K2 | 5 | 1.42 | 0.49646 | 0.00071 | yes |  |
| x0.35_background_Nmin4096_K1 | 4 | 6.48 | 0.49014 | — | no | chi2/dof 6.48 > 1.5; mean |pull| > 1.2 for ['Y', "Y''", 'U', "U'", "U''"] |
| x0.35_background_Nmin4096_K2 | 5 | 1.35 | 0.49325 | 0.00041 | yes |  |
| x0.35_background_Nmin8192_K1 | 5 | 3.55 | 0.48909 | — | no | chi2/dof 3.55 > 1.5; mean |pull| > 1.2 for ['Y', "Y''", 'U', "U'", "U''"] |
| x0.35_background_Nmin8192_K2 | 5 | 1.13 | 0.49320 | 0.00056 | yes |  |
| x0.35_background_Nmin16384_K1 | 5 | 2.27 | 0.48903 | — | no | chi2/dof 2.27 > 1.5; mean |pull| > 1.2 for ["Y''", "U'"] |
| x0.35_background_Nmin16384_K2 | 5 | 1.03 | 0.49317 | 0.00077 | yes |  |
| x0.35_second_Nmin4096_K1 | 4 | 4.73 | 0.49025 | — | no | chi2/dof 4.73 > 1.5; mean |pull| > 1.2 for ['Y', "Y''", 'U', "U''"] |
| x0.35_second_Nmin4096_K2 | 5 | 0.98 | 0.49301 | 0.00053 | yes |  |
| x0.35_second_Nmin8192_K1 | 5 | 2.34 | 0.49000 | — | no | chi2/dof 2.34 > 1.5; mean |pull| > 1.2 for ['Y', "U''"] |
| x0.35_second_Nmin8192_K2 | 5 | 0.95 | 0.49376 | 0.00082 | yes |  |
| x0.35_second_Nmin16384_K1 | 5 | 1.36 | 0.49034 | 0.00104 | yes |  |
| x0.35_second_Nmin16384_K2 | 5 | 0.92 | 0.49323 | 0.00101 | yes |  |

Cross-check: CROSS-CHECK FAILED (|difference| > 2 sigma_D); distinct eligible series ['xc0.45_plus', 'xc0.45_star'] (duplicates removed: []); standalone: {'status': 'ok', 'Delta_inf': 0.49182520361735904, 'sigma_inf': 0.0007116149960485763, 'model_spread': 0.00023626350403949115, 'omega_profile_half_range': 0.0004609181177378241, 'Delta_omega_prime': 0.0006971816217773152, 'omega_range': [0.31, 0.32], 'common_valid': 300}
Crossing value: Delta_inf = 0.49183 ± 0.00071 (sigma_inf) ± 0.00070 (Delta_omega') from ['xc0.45_plus', 'xc0.45_star']
Largest usable pairs: 131072-262144: Delta_eff(U) = 0.49421 ± 0.00132, Delta_eff(Y) = 0.48188 ± 0.00117 (300 valid draws; series xc0.45_star), 262144-524288: Delta_eff(U) = 0.49300 ± 0.00137, Delta_eff(Y) = 0.48370 ± 0.00127 (300 valid draws; series xc0.45_star)
- xc0.6_plus:  — only 0 usable doubling pairs
- xc0.6_star:  — only 0 usable doubling pairs
- xc0.45_plus: Delta_inf 0.49206 omega' 0.31 chi2/dof 3.05/4 pairs [2048, 65536, 131072, 262144] — eligible
- xc0.45_star: Delta_inf 0.49159 omega' 0.32 chi2/dof 3.50/4 pairs [2048, 65536, 131072, 262144] — eligible
Reblocking: block 2048: sigma_stat 0.00044 (ok); block 8192: sigma_stat 0.00042 (ok)

