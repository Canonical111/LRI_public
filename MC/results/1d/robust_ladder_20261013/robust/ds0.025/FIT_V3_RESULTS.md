# FIT v3 results (production; x-windows; schedule 20260916, bootstrap 300, calibration 500)

Protocol: FIT_MODEL_V3.md §4 (decision table §4.6). Selection blind to Delta_epsilon; (beta_c, Delta_eps) for the windows frozen in pre.json.

## Delta_sigma = 0.025 (s = 0.95)

**Decision: ACCEPTED (sigma_sys-dominated)**

Quoted: Delta_epsilon = 0.71115 ± 0.00049 (stat) ± 0.00959 (sys; ratio to median sigma_stat 7.9)
from x0.45_leading_Nmin4096_K1 degree 4 (chi2/dof 272.2/197); quotable 68; range [0.6968615974769856, 0.7160475660858338]

Equilibration (population rule): PASS — groups 50, hot/cold |z|>3: 0 (0.0%), half-chain |z|>3: 0 (0.0%)
Coverage guard: 72/72 configurations admissible

| configuration | d* | chi2/dof | Delta_eps | sigma_stat | quotable | reasons |
|---|---|---|---|---|---|---|
| x0.45_leading_Nmin4096_K1 | 4 | 1.38 | 0.71115 | 0.00049 | yes |  |
| x0.45_leading_Nmin4096_K2 | 4 | 1.20 | 0.71151 | 0.00048 | yes |  |
| x0.45_leading_Nmin8192_K1 | 4 | 1.13 | 0.71173 | 0.00077 | yes |  |
| x0.45_leading_Nmin8192_K2 | 4 | 1.06 | 0.71210 | 0.00078 | yes |  |
| x0.45_leading_Nmin16384_K1 | 4 | 1.01 | 0.71184 | 0.00120 | yes |  |
| x0.45_leading_Nmin16384_K2 | 4 | 1.00 | 0.71217 | 0.00124 | yes |  |
| x0.45_background_Nmin4096_K1 | 4 | 1.38 | 0.70998 | 0.00088 | yes |  |
| x0.45_background_Nmin4096_K2 | 4 | 1.21 | 0.71119 | 0.00088 | yes |  |
| x0.45_background_Nmin8192_K1 | 4 | 1.11 | 0.70931 | 0.00141 | yes |  |
| x0.45_background_Nmin8192_K2 | 4 | 1.06 | 0.71046 | 0.00146 | yes |  |
| x0.45_background_Nmin16384_K1 | 4 | 1.02 | 0.71245 | 0.00215 | yes |  |
| x0.45_background_Nmin16384_K2 | 4 | 1.01 | 0.71359 | 0.00205 | yes |  |
| x0.45_second_Nmin4096_K1 | 4 | 1.13 | 0.69768 | 0.00207 | no | structured residuals |
| x0.45_second_Nmin4096_K2 | 4 | 1.10 | 0.70073 | 0.00248 | yes |  |
| x0.45_second_Nmin8192_K1 | 4 | 1.04 | 0.70066 | 0.00307 | yes |  |
| x0.45_second_Nmin8192_K2 | 4 | 1.03 | 0.70326 | 0.00349 | yes |  |
| x0.45_second_Nmin16384_K1 | 4 | 0.99 | 0.70460 | 0.00408 | yes |  |
| x0.45_second_Nmin16384_K2 | 4 | 1.00 | 0.70518 | 0.00516 | yes |  |
| x0.45_log_Nmin4096_K1 | 4 | 1.39 | 0.71109 | 0.00059 | yes |  |
| x0.45_log_Nmin4096_K2 | 4 | 1.21 | 0.71165 | 0.00058 | yes |  |
| x0.45_log_Nmin8192_K1 | 4 | 1.14 | 0.71133 | 0.00089 | yes |  |
| x0.45_log_Nmin8192_K2 | 4 | 1.07 | 0.71183 | 0.00089 | yes |  |
| x0.45_log_Nmin16384_K1 | 4 | 1.02 | 0.71170 | 0.00129 | yes |  |
| x0.45_log_Nmin16384_K2 | 4 | 1.01 | 0.71213 | 0.00143 | yes |  |
| x0.6_leading_Nmin4096_K1 | 4 | 1.39 | 0.71098 | 0.00045 | yes |  |
| x0.6_leading_Nmin4096_K2 | 5 | 1.15 | 0.71149 | 0.00045 | yes |  |
| x0.6_leading_Nmin8192_K1 | 4 | 1.14 | 0.71179 | 0.00072 | yes |  |
| x0.6_leading_Nmin8192_K2 | 4 | 1.05 | 0.71221 | 0.00075 | yes |  |
| x0.6_leading_Nmin16384_K1 | 4 | 0.96 | 0.71187 | 0.00110 | yes |  |
| x0.6_leading_Nmin16384_K2 | 4 | 0.95 | 0.71223 | 0.00114 | yes |  |
| x0.6_background_Nmin4096_K1 | 4 | 1.39 | 0.70977 | 0.00086 | yes |  |
| x0.6_background_Nmin4096_K2 | 5 | 1.16 | 0.71134 | 0.00085 | yes |  |
| x0.6_background_Nmin8192_K1 | 4 | 1.13 | 0.70968 | 0.00132 | yes |  |
| x0.6_background_Nmin8192_K2 | 4 | 1.05 | 0.71097 | 0.00132 | yes |  |
| x0.6_background_Nmin16384_K1 | 4 | 0.98 | 0.71219 | 0.00218 | yes |  |
| x0.6_background_Nmin16384_K2 | 4 | 0.96 | 0.71352 | 0.00211 | yes |  |
| x0.6_second_Nmin4096_K1 | 4 | 1.12 | 0.69733 | 0.00200 | no | structured residuals |
| x0.6_second_Nmin4096_K2 | 4 | 1.09 | 0.70024 | 0.00227 | yes |  |
| x0.6_second_Nmin8192_K1 | 4 | 1.04 | 0.70002 | 0.00266 | no | structured residuals |
| x0.6_second_Nmin8192_K2 | 4 | 1.02 | 0.70317 | 0.00304 | yes |  |
| x0.6_second_Nmin16384_K1 | 4 | 0.94 | 0.70458 | 0.00385 | yes |  |
| x0.6_second_Nmin16384_K2 | 4 | 0.95 | 0.70536 | 0.00511 | yes |  |
| x0.6_log_Nmin4096_K1 | 4 | 1.41 | 0.71093 | 0.00055 | yes |  |
| x0.6_log_Nmin4096_K2 | 5 | 1.16 | 0.71170 | 0.00057 | yes |  |
| x0.6_log_Nmin8192_K1 | 4 | 1.14 | 0.71128 | 0.00081 | yes |  |
| x0.6_log_Nmin8192_K2 | 4 | 1.06 | 0.71183 | 0.00087 | yes |  |
| x0.6_log_Nmin16384_K1 | 4 | 0.97 | 0.71179 | 0.00118 | yes |  |
| x0.6_log_Nmin16384_K2 | 4 | 0.96 | 0.71228 | 0.00127 | yes |  |
| x0.35_leading_Nmin4096_K1 | 5 | 1.17 | 0.71233 | 0.00065 | yes |  |
| x0.35_leading_Nmin4096_K2 | 4 | 1.09 | 0.71237 | 0.00063 | yes |  |
| x0.35_leading_Nmin8192_K1 | 4 | 0.97 | 0.71298 | 0.00106 | yes |  |
| x0.35_leading_Nmin8192_K2 | 4 | 0.94 | 0.71314 | 0.00106 | yes |  |
| x0.35_leading_Nmin16384_K1 | 4 | 0.91 | 0.71279 | 0.00154 | yes |  |
| x0.35_leading_Nmin16384_K2 | 4 | 0.89 | 0.71303 | 0.00154 | yes |  |
| x0.35_background_Nmin4096_K1 | 5 | 1.19 | 0.71180 | 0.00120 | yes |  |
| x0.35_background_Nmin4096_K2 | 4 | 1.10 | 0.71233 | 0.00112 | yes |  |
| x0.35_background_Nmin8192_K1 | 4 | 0.95 | 0.70989 | 0.00181 | yes |  |
| x0.35_background_Nmin8192_K2 | 4 | 0.93 | 0.71058 | 0.00188 | yes |  |
| x0.35_background_Nmin16384_K1 | 4 | 0.92 | 0.71174 | 0.00288 | yes |  |
| x0.35_background_Nmin16384_K2 | 4 | 0.91 | 0.71284 | 0.00291 | yes |  |
| x0.35_second_Nmin4096_K1 | 4 | 1.07 | 0.69686 | 0.00289 | yes |  |
| x0.35_second_Nmin4096_K2 | 4 | 1.05 | 0.70006 | 0.00339 | yes |  |
| x0.35_second_Nmin8192_K1 | 4 | 0.89 | 0.70282 | 0.00405 | yes |  |
| x0.35_second_Nmin8192_K2 | 4 | 0.89 | 0.70416 | 0.00509 | yes |  |
| x0.35_second_Nmin16384_K1 | 4 | 0.84 | 0.70352 | 0.00579 | no | residual gate not evaluable |
| x0.35_second_Nmin16384_K2 | 4 | 0.84 | 0.71605 | 0.00346 | yes |  |
| x0.35_log_Nmin4096_K1 | 5 | 1.19 | 0.71248 | 0.00080 | yes |  |
| x0.35_log_Nmin4096_K2 | 4 | 1.10 | 0.71258 | 0.00079 | yes |  |
| x0.35_log_Nmin8192_K1 | 4 | 0.96 | 0.71231 | 0.00102 | yes |  |
| x0.35_log_Nmin8192_K2 | 4 | 0.93 | 0.71253 | 0.00104 | yes |  |
| x0.35_log_Nmin16384_K1 | 4 | 0.87 | 0.71192 | 0.00137 | yes |  |
| x0.35_log_Nmin16384_K2 | 4 | 0.85 | 0.71214 | 0.00141 | yes |  |

Cross-check: pass; distinct eligible series ['xc0.45_star', 'xc0.45_plus', 'xc0.6_star', 'xc0.6_plus'] (duplicates removed: []); standalone: {'status': 'ok', 'Delta_inf': 0.7090561948996359, 'sigma_inf': 0.00901981711595995, 'model_spread': 0.0018653864756143501, 'omega_profile_half_range': 0.013222021744028256, 'Delta_omega_prime': 0.015087408219642606, 'omega_range': [0.43, 0.54], 'common_valid': 300}
Crossing value: Delta_inf = 0.70906 ± 0.00902 (sigma_inf) ± 0.01509 (Delta_omega') from ['xc0.45_star', 'xc0.45_plus', 'xc0.6_star', 'xc0.6_plus']
Largest usable pairs: 131072-262144: Delta_eff(U) = 0.70341 ± 0.00320, Delta_eff(Y) = 0.70153 ± 0.00174 (300 valid draws; series xc0.45_star), 262144-524288: Delta_eff(U) = 0.70940 ± 0.00371, Delta_eff(Y) = 0.70439 ± 0.00202 (300 valid draws; series xc0.45_star)
- xc0.45_star: Delta_inf 0.71170 omega' 0.43 chi2/dof 7.57/4 pairs [32768, 65536, 131072, 262144] — eligible
- xc0.45_plus: Delta_inf 0.70797 omega' 0.54 chi2/dof 6.99/4 pairs [32768, 65536, 131072, 262144] — eligible
- xc0.6_star: Delta_inf 0.70954 omega' 0.51 chi2/dof 7.35/4 pairs [32768, 65536, 131072, 262144] — eligible
- xc0.6_plus: Delta_inf 0.70857 omega' 0.52 chi2/dof 6.15/4 pairs [32768, 65536, 131072, 262144] — eligible
Reblocking: block 2048: sigma_stat 0.00053 (ok); block 8192: sigma_stat 0.00055 (ok)

