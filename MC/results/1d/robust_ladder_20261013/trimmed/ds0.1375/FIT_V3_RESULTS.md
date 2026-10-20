# FIT v3 results (production; x-windows; schedule 20260916, bootstrap 300, calibration 500)

Protocol: FIT_MODEL_V3.md §4 (decision table §4.6). Selection blind to Delta_epsilon; (beta_c, Delta_eps) for the windows frozen in pre.json.

## Delta_sigma = 0.1375 (s = 0.725)

**Decision: ACCEPTED (sigma_sys-dominated)**

Quoted: Delta_epsilon = 0.49856 ± 0.00030 (stat) ± 0.00180 (sys; ratio to median sigma_stat 4.0)
from x0.45_background_Nmin4096_K2 degree 4 (chi2/dof 231.6/194); quotable 17; range [0.4983574940179536, 0.5019628871947912]

Equilibration (population rule): PASS — groups 70, hot/cold |z|>3: 0 (0.0%), half-chain |z|>3: 1 (0.2%)
Coverage guard: 54/54 configurations admissible

| configuration | d* | chi2/dof | Delta_eps | sigma_stat | quotable | reasons |
|---|---|---|---|---|---|---|
| x0.45_leading_Nmin4096_K1 | 5 | 6.69 | 0.50205 | — | no | chi2/dof 6.69 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.45_leading_Nmin4096_K2 | 4 | 2.71 | 0.50197 | — | no | chi2/dof 2.71 > 1.5; mean |pull| > 1.2 for ["Y'", "U'"] |
| x0.45_leading_Nmin8192_K1 | 5 | 3.80 | 0.50119 | — | no | chi2/dof 3.80 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U''"] |
| x0.45_leading_Nmin8192_K2 | 5 | 1.71 | 0.50136 | — | no | chi2/dof 1.71 > 1.5 |
| x0.45_leading_Nmin16384_K1 | 5 | 2.25 | 0.49995 | — | no | chi2/dof 2.25 > 1.5; mean |pull| > 1.2 for ['Y', "Y''", 'U'] |
| x0.45_leading_Nmin16384_K2 | 4 | 1.34 | 0.50001 | 0.00055 | yes |  |
| x0.45_background_Nmin4096_K1 | 3 | 268.96 | 0.52547 | — | no | chi2/dof 268.96 > 1.5; flags: nonlinear parameter at search boundary; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.45_background_Nmin4096_K2 | 4 | 1.19 | 0.49856 | 0.00030 | yes |  |
| x0.45_background_Nmin8192_K1 | 5 | 3.57 | 0.49961 | — | no | chi2/dof 3.57 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U''"] |
| x0.45_background_Nmin8192_K2 | 5 | 1.05 | 0.49853 | 0.00042 | yes |  |
| x0.45_background_Nmin16384_K1 | 4 | 2.26 | 0.49838 | — | no | chi2/dof 2.26 > 1.5; mean |pull| > 1.2 for ["Y''", 'U'] |
| x0.45_background_Nmin16384_K2 | 3 | 206.84 | 0.57539 | — | no | chi2/dof 206.84 > 1.5; flags: nonlinear parameter at search boundary; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.45_second_Nmin4096_K1 | 3 | 269.60 | 0.52652 | — | no | chi2/dof 269.60 > 1.5; flags: nonlinear parameter at search boundary; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.45_second_Nmin4096_K2 | 5 | 1.06 | 0.49878 | 0.00036 | yes |  |
| x0.45_second_Nmin8192_K1 | 5 | 2.40 | 0.50173 | — | no | chi2/dof 2.40 > 1.5; mean |pull| > 1.2 for ['Y', "Y''", 'U', "U''"] |
| x0.45_second_Nmin8192_K2 | 5 | 1.04 | 0.49872 | 0.00045 | yes |  |
| x0.45_second_Nmin16384_K1 | 5 | 1.49 | 0.49970 | 0.00088 | yes |  |
| x0.45_second_Nmin16384_K2 | 3 | 206.93 | 0.57827 | — | no | chi2/dof 206.93 > 1.5; flags: nonlinear parameter at search boundary; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.6_leading_Nmin4096_K1 | 6 | 10.80 | 0.49910 | — | no | chi2/dof 10.80 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.6_leading_Nmin4096_K2 | 6 | 3.46 | 0.50175 | — | no | chi2/dof 3.46 > 1.5; mean |pull| > 1.2 for ["Y'", "U'"] |
| x0.6_leading_Nmin8192_K1 | 6 | 3.90 | 0.50093 | — | no | chi2/dof 3.90 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U''"] |
| x0.6_leading_Nmin8192_K2 | 6 | 1.69 | 0.50146 | — | no | chi2/dof 1.69 > 1.5 |
| x0.6_leading_Nmin16384_K1 | 6 | 2.30 | 0.49957 | — | no | chi2/dof 2.30 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U'] |
| x0.6_leading_Nmin16384_K2 | 3 | 495.03 | 0.57790 | — | no | chi2/dof 495.03 > 1.5; flags: nonlinear parameter at search boundary; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.6_background_Nmin4096_K1 | 6 | 9.70 | 0.49703 | — | no | chi2/dof 9.70 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.6_background_Nmin4096_K2 | 6 | 1.27 | 0.49840 | 0.00026 | yes |  |
| x0.6_background_Nmin8192_K1 | 3 | 586.18 | 0.52760 | — | no | chi2/dof 586.18 > 1.5; flags: nonlinear parameter at search boundary; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.6_background_Nmin8192_K2 | 3 | 522.03 | 0.51692 | — | no | chi2/dof 522.03 > 1.5; flags: nonlinear parameter at search boundary; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.6_background_Nmin16384_K1 | 3 | 574.53 | 0.51768 | — | no | chi2/dof 574.53 > 1.5; flags: nonlinear parameter at search boundary; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.6_background_Nmin16384_K2 | 3 | 499.93 | 0.57383 | — | no | chi2/dof 499.93 > 1.5; flags: nonlinear parameter at search boundary; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.6_second_Nmin4096_K1 | 6 | 6.24 | 0.49784 | — | no | chi2/dof 6.24 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.6_second_Nmin4096_K2 | 6 | 1.16 | 0.49836 | 0.00028 | yes |  |
| x0.6_second_Nmin8192_K1 | 3 | 584.69 | 0.53147 | — | no | chi2/dof 584.69 > 1.5; flags: nonlinear parameter at search boundary; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.6_second_Nmin8192_K2 | 3 | 520.06 | 0.58299 | — | no | chi2/dof 520.06 > 1.5; flags: nonlinear parameter at search boundary; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.6_second_Nmin16384_K1 | 3 | 576.86 | 0.51886 | — | no | chi2/dof 576.86 > 1.5; flags: nonlinear parameter at search boundary; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.6_second_Nmin16384_K2 | 3 | 489.40 | 0.57664 | — | no | chi2/dof 489.40 > 1.5; flags: nonlinear parameter at search boundary; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.35_leading_Nmin4096_K1 | 6 | 4.00 | 0.50091 | — | no | chi2/dof 4.00 > 1.5; mean |pull| > 1.2 for ['Y', "Y''", 'U', "U''"] |
| x0.35_leading_Nmin4096_K2 | 4 | 2.16 | 0.50284 | — | no | chi2/dof 2.16 > 1.5; mean |pull| > 1.2 for ["Y'"] |
| x0.35_leading_Nmin8192_K1 | 4 | 2.79 | 0.49987 | — | no | chi2/dof 2.79 > 1.5; mean |pull| > 1.2 for ["Y''", 'U'] |
| x0.35_leading_Nmin8192_K2 | 4 | 1.46 | 0.50196 | 0.00038 | yes |  |
| x0.35_leading_Nmin16384_K1 | 4 | 1.69 | 0.49838 | — | no | chi2/dof 1.69 > 1.5 |
| x0.35_leading_Nmin16384_K2 | 4 | 1.12 | 0.50057 | 0.00061 | yes |  |
| x0.35_background_Nmin4096_K1 | 6 | 3.61 | 0.49904 | — | no | chi2/dof 3.61 > 1.5; mean |pull| > 1.2 for ['Y', "Y''", 'U'] |
| x0.35_background_Nmin4096_K2 | 4 | 1.11 | 0.49908 | 0.00038 | yes |  |
| x0.35_background_Nmin8192_K1 | 5 | 2.49 | 0.49786 | — | no | chi2/dof 2.49 > 1.5; mean |pull| > 1.2 for ["Y''"] |
| x0.35_background_Nmin8192_K2 | 4 | 1.04 | 0.49886 | 0.00050 | yes |  |
| x0.35_background_Nmin16384_K1 | 4 | 1.68 | 0.49741 | — | no | chi2/dof 1.68 > 1.5; mean |pull| > 1.2 for ["Y''"] |
| x0.35_background_Nmin16384_K2 | 4 | 1.04 | 0.49873 | 0.00075 | yes |  |
| x0.35_second_Nmin4096_K1 | 6 | 3.05 | 0.50207 | — | no | chi2/dof 3.05 > 1.5; mean |pull| > 1.2 for ['Y', "Y''", 'U', "U''"] |
| x0.35_second_Nmin4096_K2 | 4 | 1.04 | 0.49916 | 0.00039 | yes |  |
| x0.35_second_Nmin8192_K1 | 5 | 1.88 | 0.49950 | — | no | chi2/dof 1.88 > 1.5; mean |pull| > 1.2 for ["Y''"] |
| x0.35_second_Nmin8192_K2 | 4 | 1.04 | 0.49898 | 0.00051 | yes |  |
| x0.35_second_Nmin16384_K1 | 4 | 1.27 | 0.49836 | 0.00116 | yes |  |
| x0.35_second_Nmin16384_K2 | 4 | 1.04 | 0.49913 | 0.00101 | yes |  |

Cross-check: pass; distinct eligible series ['xc0.45_star', 'xc0.45_plus', 'xc0.6_plus', 'xc0.6_star'] (duplicates removed: []); standalone: {'status': 'ok', 'Delta_inf': 0.49782932862443585, 'sigma_inf': 0.0009379493934793814, 'model_spread': 0.000225589576145796, 'omega_profile_half_range': 0.0006274427904729984, 'Delta_omega_prime': 0.0008530323666187944, 'omega_range': [0.35, 0.37], 'common_valid': 300}
Crossing value: Delta_inf = 0.49783 ± 0.00094 (sigma_inf) ± 0.00085 (Delta_omega') from ['xc0.45_star', 'xc0.45_plus', 'xc0.6_plus', 'xc0.6_star']
Largest usable pairs: 131072-262144: Delta_eff(U) = 0.50053 ± 0.00119, Delta_eff(Y) = 0.49211 ± 0.00110 (300 valid draws; series xc0.45_star), 262144-524288: Delta_eff(U) = 0.49889 ± 0.00134, Delta_eff(Y) = 0.49182 ± 0.00123 (300 valid draws; series xc0.45_star)
- xc0.45_star: Delta_inf 0.49817 omega' 0.36 chi2/dof 1.16/4 pairs [8192, 65536, 131072, 262144] — eligible
- xc0.45_plus: Delta_inf 0.49785 omega' 0.35 chi2/dof 1.01/4 pairs [8192, 65536, 131072, 262144] — eligible
- xc0.6_plus: Delta_inf 0.49772 omega' 0.35 chi2/dof 1.21/4 pairs [8192, 65536, 131072, 262144] — eligible
- xc0.6_star: Delta_inf 0.49781 omega' 0.37 chi2/dof 2.10/4 pairs [8192, 65536, 131072, 262144] — eligible
Reblocking: block 2048: sigma_stat 0.00030 (ok); block 8192: sigma_stat 0.00033 (ok)

