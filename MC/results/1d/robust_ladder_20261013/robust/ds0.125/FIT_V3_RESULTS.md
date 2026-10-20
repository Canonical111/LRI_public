# FIT v3 results (production; x-windows; schedule 20260916, bootstrap 300, calibration 500)

Protocol: FIT_MODEL_V3.md §4 (decision table §4.6). Selection blind to Delta_epsilon; (beta_c, Delta_eps) for the windows frozen in pre.json.

## Delta_sigma = 0.125 (s = 0.75)

**Decision: ACCEPTED (sigma_sys-dominated)**

Quoted: Delta_epsilon = 0.50712 ± 0.00032 (stat) ± 0.00221 (sys; ratio to median sigma_stat 3.6)
from x0.45_background_Nmin4096_K2 degree 5 (chi2/dof 280.7/198); quotable 18; range [0.5059643562350281, 0.5103845429136002]

Equilibration (population rule): PASS — groups 70, hot/cold |z|>3: 1 (1.4%), half-chain |z|>3: 1 (0.2%)
Coverage guard: 54/54 configurations admissible

| configuration | d* | chi2/dof | Delta_eps | sigma_stat | quotable | reasons |
|---|---|---|---|---|---|---|
| x0.45_leading_Nmin4096_K1 | 5 | 3.84 | 0.51033 | — | no | chi2/dof 3.84 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", "U'", "U''"] |
| x0.45_leading_Nmin4096_K2 | 5 | 2.03 | 0.50959 | — | no | chi2/dof 2.03 > 1.5; mean |pull| > 1.2 for ["U'"] |
| x0.45_leading_Nmin8192_K1 | 5 | 2.85 | 0.50951 | — | no | chi2/dof 2.85 > 1.5; mean |pull| > 1.2 for ["Y'", "Y''", "U'", "U''"] |
| x0.45_leading_Nmin8192_K2 | 5 | 1.70 | 0.50868 | — | no | chi2/dof 1.70 > 1.5 |
| x0.45_leading_Nmin16384_K1 | 5 | 1.87 | 0.50880 | — | no | chi2/dof 1.87 > 1.5 |
| x0.45_leading_Nmin16384_K2 | 5 | 1.46 | 0.50810 | 0.00053 | yes |  |
| x0.45_background_Nmin4096_K1 | 5 | 3.79 | 0.50953 | — | no | chi2/dof 3.79 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", "U'", "U''"] |
| x0.45_background_Nmin4096_K2 | 5 | 1.42 | 0.50712 | 0.00032 | yes |  |
| x0.45_background_Nmin8192_K1 | 5 | 2.82 | 0.50853 | — | no | chi2/dof 2.82 > 1.5; mean |pull| > 1.2 for ["Y'", "Y''", "U'", "U''"] |
| x0.45_background_Nmin8192_K2 | 5 | 1.31 | 0.50617 | 0.00046 | yes |  |
| x0.45_background_Nmin16384_K1 | 5 | 1.84 | 0.50760 | — | no | chi2/dof 1.84 > 1.5 |
| x0.45_background_Nmin16384_K2 | 5 | 1.30 | 0.50596 | 0.00066 | yes |  |
| x0.45_second_Nmin4096_K1 | 5 | 2.92 | 0.51316 | — | no | chi2/dof 2.92 > 1.5; mean |pull| > 1.2 for ['Y', "Y''", 'U', "U''"] |
| x0.45_second_Nmin4096_K2 | 5 | 1.22 | 0.50726 | 0.00046 | yes |  |
| x0.45_second_Nmin8192_K1 | 5 | 2.11 | 0.51159 | — | no | chi2/dof 2.11 > 1.5; mean |pull| > 1.2 for ["U''"] |
| x0.45_second_Nmin8192_K2 | 5 | 1.21 | 0.50641 | 0.00078 | yes |  |
| x0.45_second_Nmin16384_K1 | 5 | 1.40 | 0.50989 | 0.00084 | yes |  |
| x0.45_second_Nmin16384_K2 | 5 | 1.21 | 0.50757 | 0.00102 | no | structured residuals |
| x0.6_leading_Nmin4096_K1 | 6 | 6.67 | 0.50956 | — | no | chi2/dof 6.67 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.6_leading_Nmin4096_K2 | 6 | 2.33 | 0.50944 | — | no | chi2/dof 2.33 > 1.5; mean |pull| > 1.2 for ["U'"] |
| x0.6_leading_Nmin8192_K1 | 5 | 2.79 | 0.51009 | — | no | chi2/dof 2.79 > 1.5; mean |pull| > 1.2 for ["Y'", "Y''", "U'", "U''"] |
| x0.6_leading_Nmin8192_K2 | 6 | 1.68 | 0.50909 | — | no | chi2/dof 1.68 > 1.5 |
| x0.6_leading_Nmin16384_K1 | 6 | 1.85 | 0.50948 | — | no | chi2/dof 1.85 > 1.5; mean |pull| > 1.2 for ["U''"] |
| x0.6_leading_Nmin16384_K2 | 6 | 1.42 | 0.50871 | 0.00046 | no | structured residuals |
| x0.6_background_Nmin4096_K1 | 6 | 6.57 | 0.50842 | — | no | chi2/dof 6.57 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.6_background_Nmin4096_K2 | 6 | 1.50 | 0.50686 | — | no | chi2/dof 1.50 > 1.5 |
| x0.6_background_Nmin8192_K1 | 5 | 2.81 | 0.50964 | — | no | chi2/dof 2.81 > 1.5; mean |pull| > 1.2 for ["Y'", "Y''", "U'", "U''"] |
| x0.6_background_Nmin8192_K2 | 6 | 1.34 | 0.50656 | 0.00043 | yes |  |
| x0.6_background_Nmin16384_K1 | 6 | 1.85 | 0.50866 | — | no | chi2/dof 1.85 > 1.5; mean |pull| > 1.2 for ["U''"] |
| x0.6_background_Nmin16384_K2 | 6 | 1.30 | 0.50679 | 0.00058 | no | structured residuals |
| x0.6_second_Nmin4096_K1 | 6 | 4.88 | 0.51007 | — | no | chi2/dof 4.88 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.6_second_Nmin4096_K2 | 6 | 1.29 | 0.50687 | 0.00031 | yes |  |
| x0.6_second_Nmin8192_K1 | 5 | 2.18 | 0.51215 | — | no | chi2/dof 2.18 > 1.5; mean |pull| > 1.2 for ["U''"] |
| x0.6_second_Nmin8192_K2 | 6 | 1.23 | 0.50685 | 0.00072 | yes |  |
| x0.6_second_Nmin16384_K1 | 6 | 1.42 | 0.51038 | 0.00074 | yes |  |
| x0.6_second_Nmin16384_K2 | 6 | 1.23 | 0.50817 | 0.00093 | no | structured residuals |
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

Cross-check: pass; distinct eligible series ['xc0.45_star', 'xc0.45_plus', 'xc0.6_star', 'xc0.6_plus'] (duplicates removed: []); standalone: {'status': 'ok', 'Delta_inf': 0.5064032140215227, 'sigma_inf': 0.0017232580770339956, 'model_spread': 0.0015299100033311919, 'omega_profile_half_range': 0.0023869694181444245, 'Delta_omega_prime': 0.003916879421475616, 'omega_range': [0.33, 0.36], 'common_valid': 300}
Crossing value: Delta_inf = 0.50640 ± 0.00172 (sigma_inf) ± 0.00392 (Delta_omega') from ['xc0.45_star', 'xc0.45_plus', 'xc0.6_star', 'xc0.6_plus']
Largest usable pairs: 131072-262144: Delta_eff(U) = 0.50585 ± 0.00118, Delta_eff(Y) = 0.50027 ± 0.00103 (300 valid draws; series xc0.45_plus), 262144-524288: Delta_eff(U) = 0.50841 ± 0.00127, Delta_eff(Y) = 0.50198 ± 0.00116 (300 valid draws; series xc0.45_star)
- xc0.45_star: Delta_inf 0.50669 omega' 0.35 chi2/dof 3.87/4 pairs [8192, 16384, 32768, 262144] — eligible
- xc0.45_plus: Delta_inf 0.50457 omega' 0.36 chi2/dof 6.59/4 pairs [32768, 65536, 131072, 262144] — eligible
- xc0.6_star: Delta_inf 0.50763 omega' 0.33 chi2/dof 6.28/4 pairs [32768, 65536, 131072, 262144] — eligible
- xc0.6_plus: Delta_inf 0.50612 omega' 0.36 chi2/dof 6.02/4 pairs [32768, 65536, 131072, 262144] — eligible
Reblocking: block 2048: sigma_stat 0.00034 (ok); block 8192: sigma_stat 0.00031 (ok)

