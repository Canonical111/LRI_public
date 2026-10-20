# FIT v3 results (production; x-windows; schedule 20260916, bootstrap 300, calibration 500)

Protocol: FIT_MODEL_V3.md §4 (decision table §4.6). Selection blind to Delta_epsilon; (beta_c, Delta_eps) for the windows frozen in pre.json.

## Delta_sigma = 0.075 (s = 0.85)

**Decision: ACCEPTED**

Quoted: Delta_epsilon = 0.56694 ± 0.00037 (stat) ± 0.00139 (sys; ratio to median sigma_stat 2.4)
from x0.45_leading_Nmin4096_K2 degree 4 (chi2/dof 110.9/112); quotable 30; range [0.5661420485330997, 0.5689279101351578]

Equilibration (population rule): PASS — groups 50, hot/cold |z|>3: 0 (0.0%), half-chain |z|>3: 1 (0.2%)
Coverage guard: 36/54 configurations admissible

| configuration | d* | chi2/dof | Delta_eps | sigma_stat | quotable | reasons |
|---|---|---|---|---|---|---|
| x0.45_leading_Nmin4096_K1 | 5 | 1.00 | 0.56732 | 0.00036 | yes |  |
| x0.45_leading_Nmin4096_K2 | 4 | 0.99 | 0.56694 | 0.00037 | yes |  |
| x0.45_leading_Nmin8192_K1 | 4 | 1.03 | 0.56813 | 0.00053 | yes |  |
| x0.45_leading_Nmin8192_K2 | 4 | 1.01 | 0.56743 | 0.00059 | yes |  |
| x0.45_leading_Nmin16384_K1 | 4 | 1.01 | 0.56800 | 0.00073 | yes |  |
| x0.45_leading_Nmin16384_K2 | 4 | 1.02 | 0.56772 | 0.00089 | yes |  |
| x0.45_background_Nmin4096_K1 | 5 | 1.01 | 0.56725 | 0.00054 | yes |  |
| x0.45_background_Nmin4096_K2 | 4 | 1.00 | 0.56659 | 0.00050 | yes |  |
| x0.45_background_Nmin8192_K1 | 4 | 1.03 | 0.56807 | 0.00067 | yes |  |
| x0.45_background_Nmin8192_K2 | 4 | 0.99 | 0.56691 | 0.00068 | yes |  |
| x0.45_background_Nmin16384_K1 | 4 | 1.02 | 0.56826 | 0.00081 | yes |  |
| x0.45_background_Nmin16384_K2 | 4 | 1.03 | 0.56788 | 0.00106 | yes |  |
| x0.45_second_Nmin4096_K1 | 4 | 1.01 | 0.56893 | 0.00054 | yes |  |
| x0.45_second_Nmin4096_K2 | 4 | 0.97 | 0.56747 | 0.00079 | yes |  |
| x0.45_second_Nmin8192_K1 | 3 | 2.28 | 0.56816 | — | no | chi2/dof 2.28 > 1.5; flags: nonlinear parameter at search boundary; mean |pull| > 1.2 for ["Y''", "U''"] |
| x0.45_second_Nmin8192_K2 | 3 | 2.30 | 0.56774 | — | no | chi2/dof 2.30 > 1.5; flags: nonlinear parameter at search boundary; mean |pull| > 1.2 for ["Y''", "U''"] |
| x0.45_second_Nmin16384_K1 | 3 | 2.27 | 0.56751 | — | no | chi2/dof 2.27 > 1.5; flags: nonlinear parameter at search boundary; mean |pull| > 1.2 for ["Y''", "U''"] |
| x0.45_second_Nmin16384_K2 | 3 | 2.30 | 0.56803 | — | no | chi2/dof 2.30 > 1.5; flags: nonlinear parameter at search boundary; mean |pull| > 1.2 for ["Y''", "U''"] |
| x0.6_leading_Nmin4096_K1 | 5 | 1.12 | 0.56719 | 0.00027 | yes |  |
| x0.6_leading_Nmin4096_K2 | 5 | 1.08 | 0.56668 | 0.00030 | yes |  |
| x0.6_leading_Nmin8192_K1 | 5 | 0.95 | 0.56708 | 0.00041 | yes |  |
| x0.6_leading_Nmin8192_K2 | 5 | 0.96 | 0.56711 | 0.00051 | yes |  |
| x0.6_leading_Nmin16384_K1 | 5 | 0.94 | 0.56731 | 0.00068 | yes |  |
| x0.6_leading_Nmin16384_K2 | 5 | 0.95 | 0.56747 | 0.00090 | yes |  |
| x0.6_background_Nmin4096_K1 | 5 | 1.07 | 0.56709 | 0.00032 | yes |  |
| x0.6_background_Nmin4096_K2 | 5 | 1.02 | 0.56614 | 0.00039 | yes |  |
| x0.6_background_Nmin8192_K1 | 5 | 0.95 | 0.56698 | 0.00047 | yes |  |
| x0.6_background_Nmin8192_K2 | 5 | 0.96 | 0.56688 | 0.00070 | yes |  |
| x0.6_background_Nmin16384_K1 | 5 | 0.96 | 0.56744 | 0.00075 | yes |  |
| x0.6_background_Nmin16384_K2 | 5 | 0.96 | 0.56787 | 0.00109 | yes |  |
| x0.6_second_Nmin4096_K1 | 5 | 1.08 | 0.56739 | 0.00037 | yes |  |
| x0.6_second_Nmin4096_K2 | 5 | 1.04 | 0.56619 | 0.00056 | yes |  |
| x0.6_second_Nmin8192_K1 | 5 | 0.97 | 0.56713 | 0.00060 | yes |  |
| x0.6_second_Nmin8192_K2 | 5 | 0.98 | 0.56712 | 0.00098 | yes |  |
| x0.6_second_Nmin16384_K1 | 3 | 4.04 | 0.56844 | — | no | chi2/dof 4.04 > 1.5; mean |pull| > 1.2 for ["Y''", "U''"] |
| x0.6_second_Nmin16384_K2 | 3 | 3.92 | 0.57081 | — | no | chi2/dof 3.92 > 1.5; mean |pull| > 1.2 for ["Y''", "U''"] |

Cross-check: pass; distinct eligible series ['xc0.45_star', 'xc0.45_plus', 'xc0.6_star', 'xc0.6_plus'] (duplicates removed: []); standalone: {'status': 'ok', 'Delta_inf': 0.568427353527079, 'sigma_inf': 0.002073476548977049, 'model_spread': 0.003975471353193705, 'omega_profile_half_range': 0.006462322063043924, 'Delta_omega_prime': 0.010437793416237628, 'omega_range': [0.33, 0.52], 'common_valid': 300}
Crossing value: Delta_inf = 0.56843 ± 0.00207 (sigma_inf) ± 0.01044 (Delta_omega') from ['xc0.45_star', 'xc0.45_plus', 'xc0.6_star', 'xc0.6_plus']
Largest usable pairs: 131072-262144: Delta_eff(U) = 0.56704 ± 0.00184, Delta_eff(Y) = 0.56277 ± 0.00136 (300 valid draws; series xc0.45_star), 262144-524288: Delta_eff(U) = 0.56759 ± 0.00204, Delta_eff(Y) = 0.56588 ± 0.00157 (300 valid draws; series xc0.6_star)
- xc0.45_star: Delta_inf 0.56726 omega' 0.40 chi2/dof 3.02/4 pairs [1024, 2048, 4096, 131072] — eligible
- xc0.45_plus: Delta_inf 0.56226 omega' 0.52 chi2/dof 3.21/4 pairs [4096, 8192, 16384, 131072] — eligible
- xc0.6_star: Delta_inf 0.57021 omega' 0.33 chi2/dof 4.75/4 pairs [32768, 65536, 131072, 262144] — eligible
- xc0.6_plus: Delta_inf 0.56959 omega' 0.44 chi2/dof 4.92/4 pairs [32768, 65536, 131072, 262144] — eligible
Reblocking: block 2048: sigma_stat 0.00042 (ok); block 8192: sigma_stat 0.00042 (ok)

