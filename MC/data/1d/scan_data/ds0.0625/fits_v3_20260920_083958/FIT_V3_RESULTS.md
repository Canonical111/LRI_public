# FIT v3 results (production; x-windows; schedule 20260916, bootstrap 300, calibration 500)

Protocol: FIT_MODEL_V3.md §4 (decision table §4.6). Selection blind to Delta_epsilon; (beta_c, Delta_eps) for the windows frozen in pre.json.

## Delta_sigma = 0.0625 (s = 0.875)

**Decision: CROSS-CHECK UNAVAILABLE**

Quoted: Delta_epsilon = 0.59003 ± 0.00035 (stat) ± 0.00150 (sys; ratio to median sigma_stat 2.5)
from x0.45_leading_Nmin4096_K1 degree 5 (chi2/dof 254.7/243); quotable 50; range [0.5883404713918948, 0.5913461661904059]

Equilibration (population rule): PASS — groups 70, hot/cold |z|>3: 0 (0.0%), half-chain |z|>3: 5 (0.9%)
Coverage guard: 54/54 configurations admissible

| configuration | d* | chi2/dof | Delta_eps | sigma_stat | quotable | reasons |
|---|---|---|---|---|---|---|
| x0.45_leading_Nmin4096_K1 | 5 | 1.05 | 0.59003 | 0.00035 | yes |  |
| x0.45_leading_Nmin4096_K2 | 5 | 1.00 | 0.59095 | 0.00053 | yes |  |
| x0.45_leading_Nmin8192_K1 | 5 | 1.03 | 0.58998 | 0.00047 | yes |  |
| x0.45_leading_Nmin8192_K2 | 5 | 1.02 | 0.59073 | 0.00069 | yes |  |
| x0.45_leading_Nmin16384_K1 | 5 | 1.06 | 0.58986 | 0.00063 | yes |  |
| x0.45_leading_Nmin16384_K2 | 5 | 1.06 | 0.59038 | 0.00079 | yes |  |
| x0.45_background_Nmin4096_K1 | 5 | 1.06 | 0.59007 | 0.00037 | yes |  |
| x0.45_background_Nmin4096_K2 | 5 | 1.00 | 0.59107 | 0.00056 | yes |  |
| x0.45_background_Nmin8192_K1 | 5 | 1.02 | 0.58979 | 0.00051 | yes |  |
| x0.45_background_Nmin8192_K2 | 5 | 1.01 | 0.59068 | 0.00070 | yes |  |
| x0.45_background_Nmin16384_K1 | 5 | 1.06 | 0.58946 | 0.00089 | yes |  |
| x0.45_background_Nmin16384_K2 | 5 | 1.06 | 0.58998 | 0.00094 | yes |  |
| x0.45_second_Nmin4096_K1 | 5 | 1.05 | 0.58971 | 0.00048 | yes |  |
| x0.45_second_Nmin4096_K2 | 5 | 1.01 | 0.59114 | 0.00066 | yes |  |
| x0.45_second_Nmin8192_K1 | 5 | 1.01 | 0.58896 | 0.00081 | yes |  |
| x0.45_second_Nmin8192_K2 | 5 | 1.01 | 0.59010 | 0.00128 | yes |  |
| x0.45_second_Nmin16384_K1 | 5 | 1.05 | 0.58834 | 0.00105 | yes |  |
| x0.45_second_Nmin16384_K2 | 5 | 1.05 | 0.58688 | 0.00221 | no | residual gate not evaluable |
| x0.6_leading_Nmin4096_K1 | 5 | 1.06 | 0.59027 | 0.00034 | yes |  |
| x0.6_leading_Nmin4096_K2 | 5 | 1.06 | 0.59048 | 0.00042 | yes |  |
| x0.6_leading_Nmin8192_K1 | 5 | 1.09 | 0.59049 | 0.00044 | yes |  |
| x0.6_leading_Nmin8192_K2 | 5 | 1.09 | 0.59077 | 0.00061 | yes |  |
| x0.6_leading_Nmin16384_K1 | 5 | 1.15 | 0.59082 | 0.00061 | yes |  |
| x0.6_leading_Nmin16384_K2 | 5 | 1.15 | 0.59101 | 0.00083 | yes |  |
| x0.6_background_Nmin4096_K1 | 5 | 1.06 | 0.59031 | 0.00032 | yes |  |
| x0.6_background_Nmin4096_K2 | 5 | 1.06 | 0.59056 | 0.00040 | yes |  |
| x0.6_background_Nmin8192_K1 | 5 | 1.09 | 0.59044 | 0.00044 | yes |  |
| x0.6_background_Nmin8192_K2 | 5 | 1.10 | 0.59075 | 0.00060 | yes |  |
| x0.6_background_Nmin16384_K1 | 5 | 1.16 | 0.59080 | 0.00065 | yes |  |
| x0.6_background_Nmin16384_K2 | 5 | 1.16 | 0.59095 | 0.00089 | yes |  |
| x0.6_second_Nmin4096_K1 | 5 | 1.06 | 0.59025 | 0.00038 | yes |  |
| x0.6_second_Nmin4096_K2 | 5 | 1.06 | 0.59069 | 0.00057 | yes |  |
| x0.6_second_Nmin8192_K1 | 5 | 1.10 | 0.59025 | 0.00055 | yes |  |
| x0.6_second_Nmin8192_K2 | 5 | 1.10 | 0.59069 | 0.00097 | yes |  |
| x0.6_second_Nmin16384_K1 | 5 | 1.16 | 0.58998 | 0.00083 | no | bootstrap valid 223 < 270 |
| x0.6_second_Nmin16384_K2 | 5 | 1.16 | 0.58919 | 0.00169 | no | bootstrap valid 217 < 270 |
| x0.35_leading_Nmin4096_K1 | 5 | 1.03 | 0.58993 | 0.00041 | yes |  |
| x0.35_leading_Nmin4096_K2 | 5 | 0.99 | 0.59077 | 0.00055 | yes |  |
| x0.35_leading_Nmin8192_K1 | 5 | 1.01 | 0.58985 | 0.00048 | yes |  |
| x0.35_leading_Nmin8192_K2 | 5 | 1.00 | 0.59046 | 0.00073 | yes |  |
| x0.35_leading_Nmin16384_K1 | 5 | 1.04 | 0.58972 | 0.00066 | yes |  |
| x0.35_leading_Nmin16384_K2 | 5 | 1.04 | 0.58999 | 0.00084 | yes |  |
| x0.35_background_Nmin4096_K1 | 5 | 1.04 | 0.58999 | 0.00040 | yes |  |
| x0.35_background_Nmin4096_K2 | 5 | 0.99 | 0.59093 | 0.00057 | yes |  |
| x0.35_background_Nmin8192_K1 | 5 | 1.00 | 0.58972 | 0.00054 | yes |  |
| x0.35_background_Nmin8192_K2 | 5 | 0.99 | 0.59050 | 0.00081 | yes |  |
| x0.35_background_Nmin16384_K1 | 5 | 1.04 | 0.58943 | 0.00081 | yes |  |
| x0.35_background_Nmin16384_K2 | 5 | 1.04 | 0.58965 | 0.00106 | yes |  |
| x0.35_second_Nmin4096_K1 | 5 | 1.03 | 0.58981 | 0.00050 | yes |  |
| x0.35_second_Nmin4096_K2 | 5 | 0.99 | 0.59135 | 0.00072 | yes |  |
| x0.35_second_Nmin8192_K1 | 5 | 1.00 | 0.58934 | 0.00078 | yes |  |
| x0.35_second_Nmin8192_K2 | 5 | 1.00 | 0.59049 | 0.00116 | yes |  |
| x0.35_second_Nmin16384_K1 | 5 | 1.04 | 0.58889 | 0.00103 | yes |  |
| x0.35_second_Nmin16384_K2 | 5 | 1.05 | 0.58823 | 0.00212 | no | residual gate not evaluable |

Cross-check: CROSS-CHECK UNAVAILABLE (fewer than 2 eligible series); distinct eligible series [] (duplicates removed: []); standalone: {'status': 'EXTRAPOLATION UNAVAILABLE (fewer than 2 distinct eligible series)'}
Crossing value: unavailable
Largest usable pairs: 131072-262144: Delta_eff(U) = 0.58891 ± 0.00126, Delta_eff(Y) = 0.58503 ± 0.00089 (300 valid draws; series xc0.45_star), 262144-524288: Delta_eff(U) = 0.59212 ± 0.00142, Delta_eff(Y) = 0.58934 ± 0.00098 (300 valid draws; series xc0.45_star)
- xc0.45_star: Delta_inf 0.59266 omega' 0.34 chi2/dof 8.40/4 pairs [32768, 65536, 131072, 262144] — extrapolation chi2/dof 2.10 > 2.0
- xc0.45_plus: Delta_inf 0.59247 omega' 0.31 chi2/dof 10.24/4 pairs [32768, 65536, 131072, 262144] — extrapolation chi2/dof 2.56 > 2.0
- xc0.6_star: Delta_inf 0.59206 omega' 0.41 chi2/dof 8.83/4 pairs [32768, 65536, 131072, 262144] — extrapolation chi2/dof 2.21 > 2.0
- xc0.6_plus: Delta_inf 0.59393 omega' 0.29 chi2/dof 9.96/4 pairs [32768, 65536, 131072, 262144] — extrapolation chi2/dof 2.49 > 2.0
Reblocking: block 2048: sigma_stat 0.00035 (ok); block 8192: sigma_stat 0.00033 (ok)

