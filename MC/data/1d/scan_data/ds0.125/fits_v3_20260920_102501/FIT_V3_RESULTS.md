# FIT v3 results (production; x-windows; schedule 20260916, bootstrap 300, calibration 500)

Protocol: FIT_MODEL_V3.md §4 (decision table §4.6). Selection blind to Delta_epsilon; (beta_c, Delta_eps) for the windows frozen in pre.json.

## Delta_sigma = 0.125 (s = 0.75)

**Decision: ACCEPTED**

Quoted: Delta_epsilon = 0.50710 ± 0.00035 (stat) ± 0.00193 (sys; ratio to median sigma_stat 2.3)
from x0.35_background_Nmin4096_K2 degree 5 (chi2/dof 249.3/168); quotable 9; range [0.5060335791069525, 0.5098852297824404]

Equilibration (population rule): PASS — groups 70, hot/cold |z|>3: 1 (1.4%), half-chain |z|>3: 1 (0.2%)
Coverage guard: 54/54 configurations admissible

| configuration | d* | chi2/dof | Delta_eps | sigma_stat | quotable | reasons |
|---|---|---|---|---|---|---|
| x0.45_leading_Nmin4096_K1 | 5 | 3.84 | 0.51033 | — | no | chi2/dof 3.84 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", "U'", "U''"] |
| x0.45_leading_Nmin4096_K2 | 5 | 2.03 | 0.50959 | — | no | chi2/dof 2.03 > 1.5; mean |pull| > 1.2 for ["U'"] |
| x0.45_leading_Nmin8192_K1 | 5 | 2.85 | 0.50951 | — | no | chi2/dof 2.85 > 1.5; mean |pull| > 1.2 for ["Y'", "Y''", "U'", "U''"] |
| x0.45_leading_Nmin8192_K2 | 5 | 1.70 | 0.50868 | — | no | chi2/dof 1.70 > 1.5 |
| x0.45_leading_Nmin16384_K1 | 5 | 1.87 | 0.50880 | — | no | chi2/dof 1.87 > 1.5 |
| x0.45_leading_Nmin16384_K2 | 3 | 131.46 | 0.56380 | — | no | chi2/dof 131.46 > 1.5; flags: nonlinear parameter at search boundary; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.45_background_Nmin4096_K1 | 3 | 166.69 | 0.52576 | — | no | chi2/dof 166.69 > 1.5; flags: nonlinear parameter at search boundary; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.45_background_Nmin4096_K2 | 3 | 154.06 | 0.55051 | — | no | chi2/dof 154.06 > 1.5; flags: nonlinear parameter at search boundary; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.45_background_Nmin8192_K1 | 3 | 161.48 | 0.52687 | — | no | chi2/dof 161.48 > 1.5; flags: nonlinear parameter at search boundary; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.45_background_Nmin8192_K2 | 3 | 135.50 | 0.55882 | — | no | chi2/dof 135.50 > 1.5; flags: nonlinear parameter at search boundary; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.45_background_Nmin16384_K1 | 3 | 157.87 | 0.52834 | — | no | chi2/dof 157.87 > 1.5; flags: nonlinear parameter at search boundary; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.45_background_Nmin16384_K2 | 3 | 111.88 | 0.56515 | — | no | chi2/dof 111.88 > 1.5; flags: nonlinear parameter at search boundary; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.45_second_Nmin4096_K1 | 3 | 166.41 | 0.52744 | — | no | chi2/dof 166.41 > 1.5; flags: nonlinear parameter at search boundary; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.45_second_Nmin4096_K2 | 3 | 153.44 | 0.55133 | — | no | chi2/dof 153.44 > 1.5; flags: nonlinear parameter at search boundary; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.45_second_Nmin8192_K1 | 3 | 164.78 | 0.52713 | — | no | chi2/dof 164.78 > 1.5; flags: nonlinear parameter at search boundary; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.45_second_Nmin8192_K2 | 3 | 135.53 | 0.55912 | — | no | chi2/dof 135.53 > 1.5; flags: nonlinear parameter at search boundary; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.45_second_Nmin16384_K1 | 5 | 1.40 | 0.50989 | 0.00084 | yes |  |
| x0.45_second_Nmin16384_K2 | 3 | 110.16 | 0.56491 | — | no | chi2/dof 110.16 > 1.5; flags: nonlinear parameter at search boundary; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.6_leading_Nmin4096_K1 | 6 | 6.67 | 0.50956 | — | no | chi2/dof 6.67 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.6_leading_Nmin4096_K2 | 6 | 2.33 | 0.50944 | — | no | chi2/dof 2.33 > 1.5; mean |pull| > 1.2 for ["U'"] |
| x0.6_leading_Nmin8192_K1 | 5 | 2.79 | 0.51009 | — | no | chi2/dof 2.79 > 1.5; mean |pull| > 1.2 for ["Y'", "Y''", "U'", "U''"] |
| x0.6_leading_Nmin8192_K2 | 3 | 298.30 | 0.57265 | — | no | chi2/dof 298.30 > 1.5; flags: nonlinear parameter at search boundary; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.6_leading_Nmin16384_K1 | 3 | 308.72 | 0.55286 | — | no | chi2/dof 308.72 > 1.5; flags: nonlinear parameter at search boundary; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.6_leading_Nmin16384_K2 | 3 | 249.13 | 0.58481 | — | no | chi2/dof 249.13 > 1.5; flags: nonlinear parameter at search boundary; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.6_background_Nmin4096_K1 | 6 | 6.57 | 0.50842 | — | no | chi2/dof 6.57 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.6_background_Nmin4096_K2 | 3 | 316.91 | 0.56851 | — | no | chi2/dof 316.91 > 1.5; flags: nonlinear parameter at search boundary; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.6_background_Nmin8192_K1 | 3 | 295.57 | 0.55509 | — | no | chi2/dof 295.57 > 1.5; flags: nonlinear parameter at search boundary; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.6_background_Nmin8192_K2 | 3 | 257.85 | 0.57715 | — | no | chi2/dof 257.85 > 1.5; flags: nonlinear parameter at search boundary; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.6_background_Nmin16384_K1 | 3 | 301.55 | 0.56144 | — | no | chi2/dof 301.55 > 1.5; flags: nonlinear parameter at search boundary; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.6_background_Nmin16384_K2 | 3 | 223.57 | 0.58316 | — | no | chi2/dof 223.57 > 1.5; flags: nonlinear parameter at search boundary; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.6_second_Nmin4096_K1 | 6 | 4.88 | 0.51007 | — | no | chi2/dof 4.88 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.6_second_Nmin4096_K2 | 6 | 1.29 | 0.50687 | 0.00031 | yes |  |
| x0.6_second_Nmin8192_K1 | 3 | 296.55 | 0.55606 | — | no | chi2/dof 296.55 > 1.5; flags: nonlinear parameter at search boundary; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.6_second_Nmin8192_K2 | 3 | 258.35 | 0.57899 | — | no | chi2/dof 258.35 > 1.5; flags: nonlinear parameter at search boundary; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.6_second_Nmin16384_K1 | 3 | 304.47 | 0.56197 | — | no | chi2/dof 304.47 > 1.5; flags: nonlinear parameter at search boundary; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.6_second_Nmin16384_K2 | 3 | 222.87 | 0.58527 | — | no | chi2/dof 222.87 > 1.5; flags: nonlinear parameter at search boundary; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.35_leading_Nmin4096_K1 | 7 | 2.91 | 0.50976 | — | no | chi2/dof 2.91 > 1.5; mean |pull| > 1.2 for ["Y'", "Y''", "U'", "U''"] |
| x0.35_leading_Nmin4096_K2 | 5 | 2.08 | 0.50957 | — | no | chi2/dof 2.08 > 1.5; mean |pull| > 1.2 for ["U'"] |
| x0.35_leading_Nmin8192_K1 | 5 | 2.38 | 0.50855 | — | no | chi2/dof 2.38 > 1.5; mean |pull| > 1.2 for ["Y''", "U''"] |
| x0.35_leading_Nmin8192_K2 | 5 | 1.62 | 0.50910 | — | no | chi2/dof 1.62 > 1.5 |
| x0.35_leading_Nmin16384_K1 | 5 | 1.64 | 0.50798 | — | no | chi2/dof 1.64 > 1.5 |
| x0.35_leading_Nmin16384_K2 | 4 | 1.51 | 0.50840 | — | no | chi2/dof 1.51 > 1.5 |
| x0.35_background_Nmin4096_K1 | 7 | 2.82 | 0.50855 | — | no | chi2/dof 2.82 > 1.5; mean |pull| > 1.2 for ["Y'", "Y''", "U'", "U''"] |
| x0.35_background_Nmin4096_K2 | 5 | 1.48 | 0.50710 | 0.00035 | yes |  |
| x0.35_background_Nmin8192_K1 | 5 | 2.38 | 0.50750 | — | no | chi2/dof 2.38 > 1.5; mean |pull| > 1.2 for ["Y''", "U''"] |
| x0.35_background_Nmin8192_K2 | 5 | 1.41 | 0.50662 | 0.00057 | yes |  |
| x0.35_background_Nmin16384_K1 | 5 | 1.63 | 0.50665 | — | no | chi2/dof 1.63 > 1.5 |
| x0.35_background_Nmin16384_K2 | 5 | 1.35 | 0.50603 | 0.00091 | yes |  |
| x0.35_second_Nmin4096_K1 | 5 | 2.94 | 0.51301 | — | no | chi2/dof 2.94 > 1.5; mean |pull| > 1.2 for ['Y', "Y''", 'U', "U''"] |
| x0.35_second_Nmin4096_K2 | 5 | 1.30 | 0.50745 | 0.00048 | yes |  |
| x0.35_second_Nmin8192_K1 | 5 | 1.97 | 0.51083 | — | no | chi2/dof 1.97 > 1.5; mean |pull| > 1.2 for ["Y''"] |
| x0.35_second_Nmin8192_K2 | 5 | 1.32 | 0.50836 | 0.00127 | yes |  |
| x0.35_second_Nmin16384_K1 | 5 | 1.35 | 0.50861 | 0.00133 | yes |  |
| x0.35_second_Nmin16384_K2 | 5 | 1.28 | 0.50795 | 0.00148 | yes |  |

Cross-check: pass; distinct eligible series ['xc0.45_star', 'xc0.45_plus', 'xc0.6_star', 'xc0.6_plus'] (duplicates removed: []); standalone: {'status': 'ok', 'Delta_inf': 0.5064032140215231, 'sigma_inf': 0.0017232580770349948, 'model_spread': 0.001529910003329693, 'omega_profile_half_range': 0.0023869694181429257, 'Delta_omega_prime': 0.003916879421472619, 'omega_range': [0.33, 0.36], 'common_valid': 300}
Crossing value: Delta_inf = 0.50640 ± 0.00172 (sigma_inf) ± 0.00392 (Delta_omega') from ['xc0.45_star', 'xc0.45_plus', 'xc0.6_star', 'xc0.6_plus']
Largest usable pairs: 131072-262144: Delta_eff(U) = 0.50585 ± 0.00118, Delta_eff(Y) = 0.50027 ± 0.00103 (300 valid draws; series xc0.45_plus), 262144-524288: Delta_eff(U) = 0.50841 ± 0.00127, Delta_eff(Y) = 0.50198 ± 0.00116 (300 valid draws; series xc0.45_star)
- xc0.45_star: Delta_inf 0.50669 omega' 0.35 chi2/dof 3.87/4 pairs [8192, 16384, 32768, 262144] — eligible
- xc0.45_plus: Delta_inf 0.50457 omega' 0.36 chi2/dof 6.59/4 pairs [32768, 65536, 131072, 262144] — eligible
- xc0.6_star: Delta_inf 0.50763 omega' 0.33 chi2/dof 6.28/4 pairs [32768, 65536, 131072, 262144] — eligible
- xc0.6_plus: Delta_inf 0.50612 omega' 0.36 chi2/dof 6.02/4 pairs [32768, 65536, 131072, 262144] — eligible
Reblocking: block 2048: sigma_stat 0.00036 (ok); block 8192: sigma_stat 0.00034 (ok)

