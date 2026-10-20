# FIT v3 results (production; x-windows; schedule 20260916, bootstrap 300, calibration 500)

Protocol: FIT_MODEL_V3.md §4 (decision table §4.6). Selection blind to Delta_epsilon; (beta_c, Delta_eps) for the windows frozen in pre.json.

## Delta_sigma = 0.0875 (s = 0.825)

**Decision: ACCEPTED**

Quoted: Delta_epsilon = 0.54761 ± 0.00032 (stat) ± 0.00194 (sys; ratio to median sigma_stat 2.8)
from x0.45_leading_Nmin4096_K1 degree 5 (chi2/dof 113.9/111); quotable 34; range [0.5460390168498158, 0.5499101884840263]

Equilibration (population rule): PASS — groups 50, hot/cold |z|>3: 1 (2.0%), half-chain |z|>3: 1 (0.2%)
Coverage guard: 36/54 configurations admissible

| configuration | d* | chi2/dof | Delta_eps | sigma_stat | quotable | reasons |
|---|---|---|---|---|---|---|
| x0.45_leading_Nmin4096_K1 | 5 | 1.03 | 0.54761 | 0.00032 | yes |  |
| x0.45_leading_Nmin4096_K2 | 5 | 0.93 | 0.54723 | 0.00034 | yes |  |
| x0.45_leading_Nmin8192_K1 | 5 | 0.98 | 0.54752 | 0.00045 | yes |  |
| x0.45_leading_Nmin8192_K2 | 5 | 0.93 | 0.54709 | 0.00047 | yes |  |
| x0.45_leading_Nmin16384_K1 | 5 | 0.92 | 0.54772 | 0.00068 | yes |  |
| x0.45_leading_Nmin16384_K2 | 5 | 0.87 | 0.54692 | 0.00073 | yes |  |
| x0.45_background_Nmin4096_K1 | 5 | 1.04 | 0.54741 | 0.00048 | yes |  |
| x0.45_background_Nmin4096_K2 | 5 | 0.91 | 0.54646 | 0.00050 | yes |  |
| x0.45_background_Nmin8192_K1 | 5 | 0.97 | 0.54767 | 0.00074 | yes |  |
| x0.45_background_Nmin8192_K2 | 5 | 0.92 | 0.54650 | 0.00083 | yes |  |
| x0.45_background_Nmin16384_K1 | 5 | 0.94 | 0.54794 | 0.00135 | yes |  |
| x0.45_background_Nmin16384_K2 | 5 | 0.87 | 0.54604 | 0.00124 | yes |  |
| x0.45_second_Nmin4096_K1 | 5 | 1.00 | 0.54906 | 0.00108 | yes |  |
| x0.45_second_Nmin4096_K2 | 5 | 0.91 | 0.54706 | 0.00109 | yes |  |
| x0.45_second_Nmin8192_K1 | 5 | 0.92 | 0.54890 | 0.00098 | yes |  |
| x0.45_second_Nmin8192_K2 | 5 | 0.90 | 0.54779 | 0.00114 | yes |  |
| x0.45_second_Nmin16384_K1 | 5 | 0.95 | 0.54877 | 0.00143 | yes |  |
| x0.45_second_Nmin16384_K2 | 4 | 0.98 | 0.54785 | 0.00166 | no | bootstrap valid 232 < 270 |
| x0.6_leading_Nmin4096_K1 | 5 | 1.18 | 0.54843 | 0.00027 | yes |  |
| x0.6_leading_Nmin4096_K2 | 5 | 0.90 | 0.54743 | 0.00032 | yes |  |
| x0.6_leading_Nmin8192_K1 | 5 | 0.89 | 0.54767 | 0.00045 | yes |  |
| x0.6_leading_Nmin8192_K2 | 5 | 0.85 | 0.54728 | 0.00048 | yes |  |
| x0.6_leading_Nmin16384_K1 | 5 | 0.83 | 0.54782 | 0.00065 | yes |  |
| x0.6_leading_Nmin16384_K2 | 5 | 0.80 | 0.54719 | 0.00066 | yes |  |
| x0.6_background_Nmin4096_K1 | 5 | 1.18 | 0.54864 | 0.00035 | yes |  |
| x0.6_background_Nmin4096_K2 | 5 | 0.88 | 0.54678 | 0.00044 | yes |  |
| x0.6_background_Nmin8192_K1 | 5 | 0.88 | 0.54776 | 0.00064 | yes |  |
| x0.6_background_Nmin8192_K2 | 5 | 0.84 | 0.54665 | 0.00075 | yes |  |
| x0.6_background_Nmin16384_K1 | 5 | 0.84 | 0.54791 | 0.00097 | yes |  |
| x0.6_background_Nmin16384_K2 | 5 | 0.79 | 0.54622 | 0.00115 | yes |  |
| x0.6_second_Nmin4096_K1 | 6 | 0.97 | 0.54991 | 0.00045 | yes |  |
| x0.6_second_Nmin4096_K2 | 5 | 0.87 | 0.54721 | 0.00073 | yes |  |
| x0.6_second_Nmin8192_K1 | 5 | 0.84 | 0.54874 | 0.00075 | yes |  |
| x0.6_second_Nmin8192_K2 | 5 | 0.83 | 0.54767 | 0.00097 | yes |  |
| x0.6_second_Nmin16384_K1 | 3 | 15.15 | 0.55603 | — | no | chi2/dof 15.15 > 1.5; flags: nonlinear parameter at search boundary; mean |pull| > 1.2 for ["U''"] |
| x0.6_second_Nmin16384_K2 | 5 | 0.81 | 0.54640 | 0.00160 | yes |  |

Cross-check: pass; distinct eligible series ['xc0.45_plus', 'xc0.45_star', 'xc0.6_plus', 'xc0.6_star'] (duplicates removed: []); standalone: {'status': 'ok', 'Delta_inf': 0.5471070029345905, 'sigma_inf': 0.0011251937319071148, 'model_spread': 0.0010199999659748493, 'omega_profile_half_range': 0.0022560800395252656, 'Delta_omega_prime': 0.003276080005500115, 'omega_range': [0.29, 0.48], 'common_valid': 300}
Crossing value: Delta_inf = 0.54711 ± 0.00113 (sigma_inf) ± 0.00328 (Delta_omega') from ['xc0.45_plus', 'xc0.45_star', 'xc0.6_plus', 'xc0.6_star']
Largest usable pairs: 131072-262144: Delta_eff(U) = 0.54516 ± 0.00173, Delta_eff(Y) = 0.54184 ± 0.00134 (300 valid draws; series xc0.6_star), 262144-524288: Delta_eff(U) = 0.54724 ± 0.00187, Delta_eff(Y) = 0.54402 ± 0.00149 (300 valid draws; series xc0.6_star)
- xc0.45_plus: Delta_inf 0.54801 omega' 0.48 chi2/dof 5.07/4 pairs [2048, 4096, 8192, 65536] — eligible
- xc0.45_star: Delta_inf 0.54792 omega' 0.44 chi2/dof 6.64/4 pairs [8192, 16384, 32768, 65536] — eligible
- xc0.6_plus: Delta_inf 0.54630 omega' 0.36 chi2/dof 2.82/4 pairs [8192, 65536, 131072, 262144] — eligible
- xc0.6_star: Delta_inf 0.54597 omega' 0.29 chi2/dof 1.87/4 pairs [32768, 65536, 131072, 262144] — eligible
Reblocking: block 2048: sigma_stat 0.00035 (ok); block 8192: sigma_stat 0.00034 (ok)

