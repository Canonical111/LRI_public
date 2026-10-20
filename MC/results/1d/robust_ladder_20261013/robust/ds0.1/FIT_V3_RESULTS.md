# FIT v3 results (production; x-windows; schedule 20260916, bootstrap 300, calibration 500)

Protocol: FIT_MODEL_V3.md §4 (decision table §4.6). Selection blind to Delta_epsilon; (beta_c, Delta_eps) for the windows frozen in pre.json.

## Delta_sigma = 0.1 (s = 0.8)

**Decision: ACCEPTED (sigma_sys-dominated)**

Quoted: Delta_epsilon = 0.53248 ± 0.00020 (stat) ± 0.00242 (sys; ratio to median sigma_stat 4.9)
from x0.45_leading_Nmin4096_K1 degree 5 (chi2/dof 295.5/207); quotable 49; range [0.5293885570007248, 0.5342323459350007]

Equilibration (population rule): PASS — groups 70, hot/cold |z|>3: 0 (0.0%), half-chain |z|>3: 0 (0.0%)
Coverage guard: 54/54 configurations admissible

| configuration | d* | chi2/dof | Delta_eps | sigma_stat | quotable | reasons |
|---|---|---|---|---|---|---|
| x0.45_leading_Nmin4096_K1 | 5 | 1.43 | 0.53248 | 0.00020 | yes |  |
| x0.45_leading_Nmin4096_K2 | 5 | 1.19 | 0.53186 | 0.00022 | yes |  |
| x0.45_leading_Nmin8192_K1 | 5 | 1.24 | 0.53223 | 0.00029 | yes |  |
| x0.45_leading_Nmin8192_K2 | 5 | 1.10 | 0.53154 | 0.00033 | yes |  |
| x0.45_leading_Nmin16384_K1 | 5 | 1.07 | 0.53178 | 0.00043 | yes |  |
| x0.45_leading_Nmin16384_K2 | 5 | 1.04 | 0.53131 | 0.00047 | yes |  |
| x0.45_background_Nmin4096_K1 | 5 | 1.41 | 0.53198 | 0.00031 | yes |  |
| x0.45_background_Nmin4096_K2 | 5 | 1.03 | 0.53041 | 0.00030 | yes |  |
| x0.45_background_Nmin8192_K1 | 5 | 1.24 | 0.53175 | 0.00043 | yes |  |
| x0.45_background_Nmin8192_K2 | 5 | 1.03 | 0.53023 | 0.00042 | yes |  |
| x0.45_background_Nmin16384_K1 | 5 | 1.04 | 0.53057 | 0.00060 | yes |  |
| x0.45_background_Nmin16384_K2 | 5 | 0.96 | 0.52939 | 0.00066 | yes |  |
| x0.45_second_Nmin4096_K1 | 5 | 1.20 | 0.53394 | 0.00065 | yes |  |
| x0.45_second_Nmin4096_K2 | 5 | 0.98 | 0.53102 | 0.00057 | yes |  |
| x0.45_second_Nmin8192_K1 | 5 | 1.16 | 0.53327 | 0.00069 | yes |  |
| x0.45_second_Nmin8192_K2 | 5 | 0.99 | 0.53029 | 0.00092 | yes |  |
| x0.45_second_Nmin16384_K1 | 5 | 1.01 | 0.53173 | 0.00088 | yes |  |
| x0.45_second_Nmin16384_K2 | 5 | 0.96 | 0.52951 | 0.00097 | yes |  |
| x0.6_leading_Nmin4096_K1 | 7 | 1.75 | 0.53292 | — | no | chi2/dof 1.75 > 1.5; mean |pull| > 1.2 for ["U''"] |
| x0.6_leading_Nmin4096_K2 | 7 | 1.21 | 0.53195 | 0.00020 | yes |  |
| x0.6_leading_Nmin8192_K1 | 5 | 1.24 | 0.53231 | 0.00026 | yes |  |
| x0.6_leading_Nmin8192_K2 | 5 | 1.10 | 0.53165 | 0.00030 | yes |  |
| x0.6_leading_Nmin16384_K1 | 5 | 1.10 | 0.53185 | 0.00040 | yes |  |
| x0.6_leading_Nmin16384_K2 | 5 | 1.06 | 0.53134 | 0.00040 | no | structured residuals |
| x0.6_background_Nmin4096_K1 | 7 | 1.75 | 0.53272 | — | no | chi2/dof 1.75 > 1.5; mean |pull| > 1.2 for ["U''"] |
| x0.6_background_Nmin4096_K2 | 7 | 1.01 | 0.53038 | 0.00028 | yes |  |
| x0.6_background_Nmin8192_K1 | 5 | 1.24 | 0.53197 | 0.00037 | yes |  |
| x0.6_background_Nmin8192_K2 | 5 | 1.03 | 0.53034 | 0.00039 | yes |  |
| x0.6_background_Nmin16384_K1 | 5 | 1.07 | 0.53086 | 0.00055 | yes |  |
| x0.6_background_Nmin16384_K2 | 5 | 0.99 | 0.52957 | 0.00057 | yes |  |
| x0.6_second_Nmin4096_K1 | 7 | 1.39 | 0.53497 | — | no | mean |pull| > 1.2 for ["U''"] |
| x0.6_second_Nmin4096_K2 | 7 | 0.97 | 0.53086 | 0.00055 | yes |  |
| x0.6_second_Nmin8192_K1 | 5 | 1.18 | 0.53313 | 0.00056 | yes |  |
| x0.6_second_Nmin8192_K2 | 5 | 1.01 | 0.53041 | 0.00063 | yes |  |
| x0.6_second_Nmin16384_K1 | 5 | 1.05 | 0.53166 | 0.00066 | yes |  |
| x0.6_second_Nmin16384_K2 | 5 | 0.99 | 0.52962 | 0.00080 | yes |  |
| x0.35_leading_Nmin4096_K1 | 5 | 1.34 | 0.53251 | 0.00021 | yes |  |
| x0.35_leading_Nmin4096_K2 | 5 | 1.11 | 0.53187 | 0.00023 | yes |  |
| x0.35_leading_Nmin8192_K1 | 5 | 1.17 | 0.53234 | 0.00029 | yes |  |
| x0.35_leading_Nmin8192_K2 | 5 | 1.02 | 0.53164 | 0.00033 | yes |  |
| x0.35_leading_Nmin16384_K1 | 5 | 0.98 | 0.53217 | 0.00051 | yes |  |
| x0.35_leading_Nmin16384_K2 | 5 | 0.96 | 0.53185 | 0.00056 | yes |  |
| x0.35_background_Nmin4096_K1 | 5 | 1.34 | 0.53214 | 0.00031 | yes |  |
| x0.35_background_Nmin4096_K2 | 5 | 0.98 | 0.53052 | 0.00032 | yes |  |
| x0.35_background_Nmin8192_K1 | 5 | 1.18 | 0.53215 | 0.00050 | yes |  |
| x0.35_background_Nmin8192_K2 | 5 | 0.97 | 0.53044 | 0.00045 | yes |  |
| x0.35_background_Nmin16384_K1 | 5 | 0.96 | 0.53075 | 0.00085 | yes |  |
| x0.35_background_Nmin16384_K2 | 5 | 0.89 | 0.52948 | 0.00075 | yes |  |
| x0.35_second_Nmin4096_K1 | 5 | 1.07 | 0.53423 | 0.00056 | yes |  |
| x0.35_second_Nmin4096_K2 | 5 | 0.90 | 0.53151 | 0.00066 | yes |  |
| x0.35_second_Nmin8192_K1 | 5 | 1.06 | 0.53384 | 0.00063 | yes |  |
| x0.35_second_Nmin8192_K2 | 5 | 0.92 | 0.53100 | 0.00089 | yes |  |
| x0.35_second_Nmin16384_K1 | 5 | 0.94 | 0.53204 | 0.00148 | yes |  |
| x0.35_second_Nmin16384_K2 | 5 | 0.89 | 0.53043 | 0.00147 | no | bootstrap valid 234 < 270 |

Cross-check: pass; distinct eligible series ['xc0.45_plus', 'xc0.45_star', 'xc0.6_star', 'xc0.6_plus'] (duplicates removed: []); standalone: {'status': 'ok', 'Delta_inf': 0.5297488499364367, 'sigma_inf': 0.0013499050177659955, 'model_spread': 0.0009247651768289344, 'omega_profile_half_range': 0.0015551133212542978, 'Delta_omega_prime': 0.0024798784980832322, 'omega_range': [0.46, 0.51], 'common_valid': 300}
Crossing value: Delta_inf = 0.52975 ± 0.00135 (sigma_inf) ± 0.00248 (Delta_omega') from ['xc0.45_plus', 'xc0.45_star', 'xc0.6_star', 'xc0.6_plus']
Largest usable pairs: 131072-262144: Delta_eff(U) = 0.53021 ± 0.00121, Delta_eff(Y) = 0.52511 ± 0.00095 (300 valid draws; series xc0.45_star), 262144-524288: Delta_eff(U) = 0.52958 ± 0.00129, Delta_eff(Y) = 0.52790 ± 0.00107 (300 valid draws; series xc0.45_star)
- xc0.45_plus: Delta_inf 0.52886 omega' 0.50 chi2/dof 3.60/4 pairs [32768, 65536, 131072, 262144] — eligible
- xc0.45_star: Delta_inf 0.53030 omega' 0.49 chi2/dof 5.82/4 pairs [32768, 65536, 131072, 262144] — eligible
- xc0.6_star: Delta_inf 0.53071 omega' 0.46 chi2/dof 5.23/4 pairs [32768, 65536, 131072, 262144] — eligible
- xc0.6_plus: Delta_inf 0.52920 omega' 0.51 chi2/dof 4.25/4 pairs [32768, 65536, 131072, 262144] — eligible
Reblocking: block 2048: sigma_stat 0.00023 (ok); block 8192: sigma_stat 0.00023 (ok)

