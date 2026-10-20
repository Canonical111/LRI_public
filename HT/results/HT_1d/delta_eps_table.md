# Delta_eps of the d = 1 long-range Ising model from finite-coupling HT (dens_v1)

Consistent full-vacuum window, 16 density-basis states per parity, osc 384, even cutoffs N = 12..40. D_inf: median of the accepted fits (F1, F2, F3 x N_min 12..24) and half their spread (a model spread, not a confidence interval). omega: median exponent of the accepted fits. Status words are part of the result (quoted_numbers.json). NRG: bosonic NRG of the sub-ohmic spin-boson model (NRG folder), for comparison. Written by code/lri_dressed_phi4_hpc_analysis/public/make_tables_ht1d.py from dens_v1_extrapolation.json.

| Ds | eps = 1 - 4 Ds | Delta(N = 40) | dDelta/dlnN at N = 40 | D_inf | omega | accepted fits | status | NRG |
|---|---|---|---|---|---|---|---|---|
| 0.249 | 0.004 | 0.4993430 | +3.20e-07 | 0.4993436 ± 9.3e-08 | 0.57 | 21 | final | 0.50803 ± 0.00000 |
| 0.24 | 0.040 | 0.4941859 | +2.05e-05 | 0.4942198 ± 2.6e-06 | 0.61 | 21 | final | 0.49892 ± 0.00000 |
| 0.225 | 0.100 | 0.4879817 | +7.27e-05 | 0.4880804 ± 5.2e-06 | 0.74 | 21 | final | 0.48967 ± 0.00000 |
| 0.2 | 0.200 | 0.4828395 | +1.54e-04 | 0.4830244 ± 4.7e-06 | 0.82 | 21 | final | 0.48298 ± 0.00071 |
| 0.175 | 0.300 | 0.4835405 | +2.84e-04 | 0.4839086 ± 1.5e-05 | 0.75 | 21 | final | 0.48390 ± 0.00035 |
| 0.15 | 0.400 | 0.4903877 | +5.62e-04 | 0.4912086 ± 3.3e-05 | 0.67 | 21 | final | 0.49111 ± 0.00011 |
| 0.125 | 0.500 | 0.5045609 | +1.04e-03 | 0.5061186 ± 4.3e-05 | 0.66 | 21 | final | 0.50567 ± 0.00005 |
| 0.1 | 0.600 | 0.5282101 | +1.64e-03 | 0.5304771 ± 1.2e-04 | 0.72 | 21 | final | 0.52961 ± 0.00003 |
| 0.075 | 0.700 | 0.5648514 | +2.11e-03 | 0.5673260 ± 2.0e-04 (one-sided −5e-4) | 0.86 | 21 | one-sided | 0.56626 ± 0.00003 |
| 0.05 | 0.800 | 0.6206712 | +1.78e-03 | 0.6220–0.6224 (F1, F2); F3 down to 0.618 | 1.12 | 19 | unstable | 0.62212 ± 0.00003 |
| 0.025 | 0.900 | 0.7105771 | -1.34e-03 | — | 0.44 | 11 | no limit | 0.71342 ± 0.00003 |
| 0.01 | 0.960 | 0.8091106 | -6.24e-03 | — | 0.41 | 14 | no limit | 0.80975 ± 0.00005 |
| 0.001 | 0.996 | 0.9693379 | -1.51e-03 | — | — | 0 | no limit | 0.93742 ± 0.00011 |
