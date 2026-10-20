# FIT v3 results (production; x-windows; schedule 20260916, bootstrap 300, calibration 500)

Protocol: FIT_MODEL_V3.md §4 (decision table §4.6). Selection blind to Delta_epsilon; (beta_c, Delta_eps) for the windows frozen in pre.json.

## Delta_sigma = 0.1125 (s = 0.775)

**Decision: ACCEPTED (sigma_sys-dominated)**

Quoted: Delta_epsilon = 0.52020 ± 0.00025 (stat) ± 0.00217 (sys; ratio to median sigma_stat 3.8)
from x0.45_leading_Nmin4096_K2 degree 5 (chi2/dof 257.8/194); quotable 41; range [0.5177340475693888, 0.5220749209655736]

Equilibration (population rule): PASS — groups 70, hot/cold |z|>3: 0 (0.0%), half-chain |z|>3: 0 (0.0%)
Coverage guard: 54/54 configurations admissible

| configuration | d* | chi2/dof | Delta_eps | sigma_stat | quotable | reasons |
|---|---|---|---|---|---|---|
| x0.45_leading_Nmin4096_K1 | 5 | 1.99 | 0.52091 | — | no | chi2/dof 1.99 > 1.5; mean |pull| > 1.2 for ["U''"] |
| x0.45_leading_Nmin4096_K2 | 5 | 1.33 | 0.52020 | 0.00025 | yes |  |
| x0.45_leading_Nmin8192_K1 | 5 | 1.46 | 0.52051 | 0.00031 | yes |  |
| x0.45_leading_Nmin8192_K2 | 5 | 1.04 | 0.51964 | 0.00033 | yes |  |
| x0.45_leading_Nmin16384_K1 | 5 | 1.12 | 0.52067 | 0.00045 | yes |  |
| x0.45_leading_Nmin16384_K2 | 5 | 0.99 | 0.51990 | 0.00052 | yes |  |
| x0.45_background_Nmin4096_K1 | 5 | 1.97 | 0.52035 | — | no | chi2/dof 1.97 > 1.5; mean |pull| > 1.2 for ["U''"] |
| x0.45_background_Nmin4096_K2 | 5 | 0.98 | 0.51816 | 0.00035 | yes |  |
| x0.45_background_Nmin8192_K1 | 5 | 1.47 | 0.52047 | 0.00048 | yes |  |
| x0.45_background_Nmin8192_K2 | 5 | 0.95 | 0.51822 | 0.00046 | yes |  |
| x0.45_background_Nmin16384_K1 | 5 | 1.12 | 0.51988 | 0.00062 | yes |  |
| x0.45_background_Nmin16384_K2 | 5 | 0.91 | 0.51812 | 0.00067 | yes |  |
| x0.45_second_Nmin4096_K1 | 5 | 1.55 | 0.52313 | — | no | chi2/dof 1.55 > 1.5 |
| x0.45_second_Nmin4096_K2 | 5 | 0.91 | 0.51851 | 0.00049 | yes |  |
| x0.45_second_Nmin8192_K1 | 5 | 1.29 | 0.52207 | 0.00057 | yes |  |
| x0.45_second_Nmin8192_K2 | 5 | 0.93 | 0.51849 | 0.00062 | yes |  |
| x0.45_second_Nmin16384_K1 | 5 | 1.10 | 0.52063 | 0.00074 | yes |  |
| x0.45_second_Nmin16384_K2 | 5 | 0.90 | 0.51773 | 0.00073 | yes |  |
| x0.6_leading_Nmin4096_K1 | 7 | 3.03 | 0.52117 | — | no | chi2/dof 3.03 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", "U''"] |
| x0.6_leading_Nmin4096_K2 | 6 | 1.49 | 0.52002 | 0.00022 | no | structured residuals |
| x0.6_leading_Nmin8192_K1 | 5 | 1.45 | 0.52039 | 0.00027 | yes |  |
| x0.6_leading_Nmin8192_K2 | 3 | 130.33 | 0.56016 | — | no | chi2/dof 130.33 > 1.5; flags: nonlinear parameter at search boundary; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.6_leading_Nmin16384_K1 | 3 | 139.40 | 0.54930 | — | no | chi2/dof 139.40 > 1.5; flags: nonlinear parameter at search boundary; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.6_leading_Nmin16384_K2 | 3 | 112.29 | 0.57109 | — | no | chi2/dof 112.29 > 1.5; flags: nonlinear parameter at search boundary; mean |pull| > 1.2 for ['Y', "Y'", "Y''", 'U', "U'", "U''"] |
| x0.6_background_Nmin4096_K1 | 7 | 3.04 | 0.52109 | — | no | chi2/dof 3.04 > 1.5; mean |pull| > 1.2 for ['Y', "Y'", "Y''", "U''"] |
| x0.6_background_Nmin4096_K2 | 6 | 1.07 | 0.51792 | 0.00028 | yes |  |
| x0.6_background_Nmin8192_K1 | 5 | 1.46 | 0.52055 | 0.00043 | yes |  |
| x0.6_background_Nmin8192_K2 | 6 | 1.01 | 0.51816 | 0.00043 | yes |  |
| x0.6_background_Nmin16384_K1 | 5 | 1.16 | 0.51997 | 0.00059 | yes |  |
| x0.6_background_Nmin16384_K2 | 5 | 1.00 | 0.51833 | 0.00061 | yes |  |
| x0.6_second_Nmin4096_K1 | 7 | 2.32 | 0.52374 | — | no | chi2/dof 2.32 > 1.5; mean |pull| > 1.2 for ["Y''", 'U', "U''"] |
| x0.6_second_Nmin4096_K2 | 6 | 0.99 | 0.51817 | 0.00035 | yes |  |
| x0.6_second_Nmin8192_K1 | 5 | 1.29 | 0.52175 | 0.00046 | yes |  |
| x0.6_second_Nmin8192_K2 | 5 | 1.01 | 0.51916 | 0.00057 | yes |  |
| x0.6_second_Nmin16384_K1 | 5 | 1.13 | 0.52053 | 0.00058 | yes |  |
| x0.6_second_Nmin16384_K2 | 5 | 1.00 | 0.51825 | 0.00071 | yes |  |
| x0.35_leading_Nmin4096_K1 | 5 | 2.01 | 0.52098 | — | no | chi2/dof 2.01 > 1.5; mean |pull| > 1.2 for ["U''"] |
| x0.35_leading_Nmin4096_K2 | 5 | 1.29 | 0.52019 | 0.00026 | yes |  |
| x0.35_leading_Nmin8192_K1 | 5 | 1.30 | 0.52015 | 0.00037 | yes |  |
| x0.35_leading_Nmin8192_K2 | 5 | 1.02 | 0.51998 | 0.00037 | yes |  |
| x0.35_leading_Nmin16384_K1 | 5 | 1.11 | 0.52045 | 0.00058 | yes |  |
| x0.35_leading_Nmin16384_K2 | 5 | 1.00 | 0.52017 | 0.00057 | yes |  |
| x0.35_background_Nmin4096_K1 | 5 | 2.00 | 0.52058 | — | no | chi2/dof 2.00 > 1.5; mean |pull| > 1.2 for ["U''"] |
| x0.35_background_Nmin4096_K2 | 5 | 0.97 | 0.51828 | 0.00038 | yes |  |
| x0.35_background_Nmin8192_K1 | 5 | 1.31 | 0.51982 | 0.00064 | yes |  |
| x0.35_background_Nmin8192_K2 | 5 | 0.95 | 0.51838 | 0.00061 | yes |  |
| x0.35_background_Nmin16384_K1 | 5 | 1.11 | 0.51968 | 0.00087 | yes |  |
| x0.35_background_Nmin16384_K2 | 5 | 0.95 | 0.51831 | 0.00085 | yes |  |
| x0.35_second_Nmin4096_K1 | 5 | 1.56 | 0.52316 | — | no | chi2/dof 1.56 > 1.5 |
| x0.35_second_Nmin4096_K2 | 5 | 0.89 | 0.51874 | 0.00054 | yes |  |
| x0.35_second_Nmin8192_K1 | 5 | 1.24 | 0.52141 | 0.00085 | yes |  |
| x0.35_second_Nmin8192_K2 | 5 | 0.93 | 0.51855 | 0.00072 | yes |  |
| x0.35_second_Nmin16384_K1 | 5 | 1.11 | 0.52013 | 0.00104 | yes |  |
| x0.35_second_Nmin16384_K2 | 5 | 0.94 | 0.51779 | 0.00084 | yes |  |

Cross-check: pass; distinct eligible series ['xc0.45_star', 'xc0.45_plus', 'xc0.6_star', 'xc0.6_plus'] (duplicates removed: []); standalone: {'status': 'ok', 'Delta_inf': 0.5178988287058871, 'sigma_inf': 0.0008649480020593292, 'model_spread': 0.0036659529631369314, 'omega_profile_half_range': 0.005772473002803591, 'Delta_omega_prime': 0.009438425965940522, 'omega_range': [0.26, 0.42], 'common_valid': 300}
Crossing value: Delta_inf = 0.51790 ± 0.00086 (sigma_inf) ± 0.00944 (Delta_omega') from ['xc0.45_star', 'xc0.45_plus', 'xc0.6_star', 'xc0.6_plus']
Largest usable pairs: 131072-262144: Delta_eff(U) = 0.51943 ± 0.00122, Delta_eff(Y) = 0.51436 ± 0.00102 (300 valid draws; series xc0.45_star), 262144-524288: Delta_eff(U) = 0.51851 ± 0.00128, Delta_eff(Y) = 0.51397 ± 0.00114 (300 valid draws; series xc0.45_star)
- xc0.45_star: Delta_inf 0.51777 omega' 0.39 chi2/dof 2.33/4 pairs [8192, 65536, 131072, 262144] — eligible
- xc0.45_plus: Delta_inf 0.51698 omega' 0.42 chi2/dof 4.04/4 pairs [8192, 65536, 131072, 262144] — eligible
- xc0.6_star: Delta_inf 0.51803 omega' 0.37 chi2/dof 4.30/4 pairs [8192, 65536, 131072, 262144] — eligible
- xc0.6_plus: Delta_inf 0.52431 omega' 0.26 chi2/dof 3.40/4 pairs [32768, 65536, 131072, 262144] — eligible
Reblocking: block 2048: sigma_stat 0.00024 (ok); block 8192: sigma_stat 0.00023 (ok)

