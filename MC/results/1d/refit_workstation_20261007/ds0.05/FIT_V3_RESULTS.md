# FIT v3 results (production; x-windows; schedule 20260916, bootstrap 300, calibration 500)

Protocol: FIT_MODEL_V3.md §4 (decision table §4.6). Selection blind to Delta_epsilon; (beta_c, Delta_eps) for the windows frozen in pre.json.

## Delta_sigma = 0.05 (s = 0.9)

**Decision: ACCEPTED**

Quoted: Delta_epsilon = 0.61987 ± 0.00055 (stat) ± 0.00220 (sys; ratio to median sigma_stat 2.8)
from x0.45_leading_Nmin4096_K1 degree 4 (chi2/dof 129.9/125); quotable 72; range [0.6184537925965343, 0.6228565741599875]

Equilibration (population rule): PASS — groups 50, hot/cold |z|>3: 0 (0.0%), half-chain |z|>3: 1 (0.2%)
Coverage guard: 72/72 configurations admissible

| configuration | d* | chi2/dof | Delta_eps | sigma_stat | quotable | reasons |
|---|---|---|---|---|---|---|
| x0.45_leading_Nmin4096_K1 | 4 | 1.04 | 0.61987 | 0.00055 | yes |  |
| x0.45_leading_Nmin4096_K2 | 4 | 0.93 | 0.62099 | 0.00067 | yes |  |
| x0.45_leading_Nmin8192_K1 | 4 | 0.96 | 0.62051 | 0.00077 | yes |  |
| x0.45_leading_Nmin8192_K2 | 4 | 0.88 | 0.62183 | 0.00091 | yes |  |
| x0.45_leading_Nmin16384_K1 | 4 | 0.89 | 0.61990 | 0.00107 | yes |  |
| x0.45_leading_Nmin16384_K2 | 4 | 0.87 | 0.62107 | 0.00132 | yes |  |
| x0.45_background_Nmin4096_K1 | 4 | 1.02 | 0.61960 | 0.00057 | yes |  |
| x0.45_background_Nmin4096_K2 | 4 | 0.92 | 0.62075 | 0.00068 | yes |  |
| x0.45_background_Nmin8192_K1 | 4 | 0.96 | 0.62046 | 0.00076 | yes |  |
| x0.45_background_Nmin8192_K2 | 4 | 0.88 | 0.62194 | 0.00095 | yes |  |
| x0.45_background_Nmin16384_K1 | 4 | 0.91 | 0.62017 | 0.00103 | yes |  |
| x0.45_background_Nmin16384_K2 | 4 | 0.87 | 0.62164 | 0.00136 | yes |  |
| x0.45_second_Nmin4096_K1 | 4 | 0.98 | 0.61865 | 0.00066 | yes |  |
| x0.45_second_Nmin4096_K2 | 4 | 0.91 | 0.61992 | 0.00083 | yes |  |
| x0.45_second_Nmin8192_K1 | 4 | 0.91 | 0.61929 | 0.00087 | yes |  |
| x0.45_second_Nmin8192_K2 | 4 | 0.87 | 0.62069 | 0.00123 | yes |  |
| x0.45_second_Nmin16384_K1 | 4 | 0.91 | 0.62055 | 0.00124 | yes |  |
| x0.45_second_Nmin16384_K2 | 4 | 0.85 | 0.62286 | 0.00180 | yes |  |
| x0.45_log_Nmin4096_K1 | 4 | 0.99 | 0.61968 | 0.00054 | yes |  |
| x0.45_log_Nmin4096_K2 | 4 | 0.90 | 0.62066 | 0.00066 | yes |  |
| x0.45_log_Nmin8192_K1 | 4 | 0.96 | 0.62072 | 0.00080 | yes |  |
| x0.45_log_Nmin8192_K2 | 4 | 0.89 | 0.62188 | 0.00092 | yes |  |
| x0.45_log_Nmin16384_K1 | 4 | 0.91 | 0.61920 | 0.00116 | yes |  |
| x0.45_log_Nmin16384_K2 | 4 | 0.88 | 0.62097 | 0.00150 | yes |  |
| x0.6_leading_Nmin4096_K1 | 5 | 1.15 | 0.61923 | 0.00035 | yes |  |
| x0.6_leading_Nmin4096_K2 | 5 | 1.00 | 0.62044 | 0.00043 | yes |  |
| x0.6_leading_Nmin8192_K1 | 5 | 1.05 | 0.61981 | 0.00048 | yes |  |
| x0.6_leading_Nmin8192_K2 | 5 | 0.98 | 0.62099 | 0.00059 | yes |  |
| x0.6_leading_Nmin16384_K1 | 4 | 1.00 | 0.62042 | 0.00062 | yes |  |
| x0.6_leading_Nmin16384_K2 | 4 | 1.00 | 0.62096 | 0.00087 | yes |  |
| x0.6_background_Nmin4096_K1 | 5 | 1.14 | 0.61911 | 0.00038 | yes |  |
| x0.6_background_Nmin4096_K2 | 5 | 1.00 | 0.62040 | 0.00043 | yes |  |
| x0.6_background_Nmin8192_K1 | 5 | 1.03 | 0.61986 | 0.00046 | yes |  |
| x0.6_background_Nmin8192_K2 | 5 | 0.96 | 0.62112 | 0.00062 | yes |  |
| x0.6_background_Nmin16384_K1 | 4 | 1.01 | 0.62067 | 0.00068 | yes |  |
| x0.6_background_Nmin16384_K2 | 4 | 1.00 | 0.62142 | 0.00088 | yes |  |
| x0.6_second_Nmin4096_K1 | 5 | 1.08 | 0.61845 | 0.00039 | yes |  |
| x0.6_second_Nmin4096_K2 | 5 | 0.97 | 0.61979 | 0.00048 | yes |  |
| x0.6_second_Nmin8192_K1 | 5 | 0.97 | 0.61922 | 0.00053 | yes |  |
| x0.6_second_Nmin8192_K2 | 5 | 0.92 | 0.62043 | 0.00070 | yes |  |
| x0.6_second_Nmin16384_K1 | 4 | 1.01 | 0.62074 | 0.00078 | yes |  |
| x0.6_second_Nmin16384_K2 | 4 | 1.00 | 0.62182 | 0.00105 | yes |  |
| x0.6_log_Nmin4096_K1 | 5 | 1.12 | 0.61928 | 0.00034 | yes |  |
| x0.6_log_Nmin4096_K2 | 5 | 1.00 | 0.62039 | 0.00043 | yes |  |
| x0.6_log_Nmin8192_K1 | 5 | 1.05 | 0.62004 | 0.00058 | yes |  |
| x0.6_log_Nmin8192_K2 | 5 | 0.99 | 0.62106 | 0.00069 | yes |  |
| x0.6_log_Nmin16384_K1 | 4 | 1.01 | 0.61991 | 0.00090 | yes |  |
| x0.6_log_Nmin16384_K2 | 4 | 1.01 | 0.62059 | 0.00094 | yes |  |
| x0.35_leading_Nmin4096_K1 | 4 | 1.04 | 0.61987 | 0.00055 | yes |  |
| x0.35_leading_Nmin4096_K2 | 4 | 0.93 | 0.62099 | 0.00067 | yes |  |
| x0.35_leading_Nmin8192_K1 | 4 | 0.96 | 0.62051 | 0.00077 | yes |  |
| x0.35_leading_Nmin8192_K2 | 4 | 0.88 | 0.62183 | 0.00091 | yes |  |
| x0.35_leading_Nmin16384_K1 | 4 | 0.89 | 0.61990 | 0.00107 | yes |  |
| x0.35_leading_Nmin16384_K2 | 4 | 0.87 | 0.62107 | 0.00132 | yes |  |
| x0.35_background_Nmin4096_K1 | 4 | 1.02 | 0.61960 | 0.00057 | yes |  |
| x0.35_background_Nmin4096_K2 | 4 | 0.92 | 0.62075 | 0.00068 | yes |  |
| x0.35_background_Nmin8192_K1 | 4 | 0.96 | 0.62046 | 0.00076 | yes |  |
| x0.35_background_Nmin8192_K2 | 4 | 0.88 | 0.62194 | 0.00095 | yes |  |
| x0.35_background_Nmin16384_K1 | 4 | 0.91 | 0.62017 | 0.00103 | yes |  |
| x0.35_background_Nmin16384_K2 | 4 | 0.87 | 0.62164 | 0.00136 | yes |  |
| x0.35_second_Nmin4096_K1 | 4 | 0.98 | 0.61865 | 0.00066 | yes |  |
| x0.35_second_Nmin4096_K2 | 4 | 0.91 | 0.61992 | 0.00083 | yes |  |
| x0.35_second_Nmin8192_K1 | 4 | 0.91 | 0.61929 | 0.00087 | yes |  |
| x0.35_second_Nmin8192_K2 | 4 | 0.87 | 0.62069 | 0.00123 | yes |  |
| x0.35_second_Nmin16384_K1 | 4 | 0.91 | 0.62055 | 0.00124 | yes |  |
| x0.35_second_Nmin16384_K2 | 4 | 0.85 | 0.62286 | 0.00180 | yes |  |
| x0.35_log_Nmin4096_K1 | 4 | 0.99 | 0.61968 | 0.00054 | yes |  |
| x0.35_log_Nmin4096_K2 | 4 | 0.90 | 0.62066 | 0.00066 | yes |  |
| x0.35_log_Nmin8192_K1 | 4 | 0.96 | 0.62072 | 0.00080 | yes |  |
| x0.35_log_Nmin8192_K2 | 4 | 0.89 | 0.62188 | 0.00092 | yes |  |
| x0.35_log_Nmin16384_K1 | 4 | 0.91 | 0.61920 | 0.00116 | yes |  |
| x0.35_log_Nmin16384_K2 | 4 | 0.88 | 0.62097 | 0.00150 | yes |  |

Cross-check: pass; distinct eligible series ['xc0.45_star', 'xc0.45_plus', 'xc0.6_plus', 'xc0.6_star'] (duplicates removed: []); standalone: {'status': 'ok', 'Delta_inf': 0.6239324591697275, 'sigma_inf': 0.003475995950410038, 'model_spread': 0.002675987097122634, 'omega_profile_half_range': 0.005053933714631198, 'Delta_omega_prime': 0.007729920811753832, 'omega_range': [0.24, 0.4], 'common_valid': 300}
Crossing value: Delta_inf = 0.62393 ± 0.00348 (sigma_inf) ± 0.00773 (Delta_omega') from ['xc0.45_star', 'xc0.45_plus', 'xc0.6_plus', 'xc0.6_star']
Largest usable pairs: 131072-262144: Delta_eff(U) = 0.62114 ± 0.00257, Delta_eff(Y) = 0.61741 ± 0.00168 (300 valid draws; series xc0.45_star), 262144-524288: Delta_eff(U) = 0.61849 ± 0.00256, Delta_eff(Y) = 0.61726 ± 0.00172 (300 valid draws; series xc0.45_star)
- xc0.45_star: Delta_inf 0.62127 omega' 0.40 chi2/dof 3.04/4 pairs [2048, 65536, 131072, 262144] — eligible
- xc0.45_plus: Delta_inf 0.62193 omega' 0.36 chi2/dof 2.85/4 pairs [32768, 65536, 131072, 262144] — eligible
- xc0.6_plus: Delta_inf 0.62594 omega' 0.25 chi2/dof 6.42/4 pairs [32768, 65536, 131072, 262144] — eligible
- xc0.6_star: Delta_inf 0.62663 omega' 0.24 chi2/dof 6.65/4 pairs [32768, 65536, 131072, 262144] — eligible
Reblocking: block 2048: sigma_stat 0.00058 (ok); block 8192: sigma_stat 0.00055 (ok)

