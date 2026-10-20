# Results map: comparison

Every quoted number: the macro of the paper's numbers.tex, its text as printed, the record it is recomputed from,
the rule, the command (run from Resummation/) and the tolerance. Tolerance of every macro row: the recomputed value,
rounded half-up to the digits the macro prints, equals the printed value (verify/rsum_lib.py); a number word ("nine")
is compared with the value rounded to an integer. "note only" = defined in numbers.tex but no longer printed (INFO
row). Source of the printed texts: results/quoted_numbers.json (generated from the paper's numbers.tex).

Top-level map of all packages: `results_map.md` in Resummation/.

| Macro | Printed | Status | Record | Rule | Command | Tolerance |
|---|---|---|---|---|---|---|
| `\CMPhtCB` | `5\times10^{-4}` | printed | `code/resum_d1/update_2026-10-13/C8_1_ext/pipeline_K8/results/comparison_points_K.csv` | largest \|HT - CB8\| over final HT | `make -C code/comparison -f public.mk replay` | half-up to the printed digits |
| `\CMPhtCBos` | `7\times10^{-4}` | note only | `code/resum_d1/update_2026-10-13/C8_1_ext/pipeline_K8/results/comparison_points_K.csv` | \|HT - CB8\| at the one-sided point | `make -C code/comparison -f public.mk replay` | half-up to the printed digits |
| `\CMPnrgCB` | `7.6\times10^{-4}` | printed | `code/resum_d1/update_2026-10-13/C8_1_ext/pipeline_K8/results/comparison_points_K.csv` | largest \|NRG - CB8\| over converged NRG (all below) | `make -C code/comparison -f public.mk replay` | half-up to the printed digits |
| `\CMPmcCB` | `3.2\times10^{-3}` | printed | `code/resum_d1/update_2026-10-13/C8_1_ext/pipeline_K8/results/comparison_points_K.csv` | largest \|MC - CB8\| over accepted MC | `make -C code/comparison -f public.mk replay` | half-up to the printed digits |
| `\CMPmcNrgRel` | `0.54` | note only | `code/resum_d1/update_2026-10-13/C8_1_ext/pipeline_K8/results/comparison_points_K.csv` | largest \|MC - NRG\|/mean in %, accepted MC with converged NRG | `make -C code/comparison -f public.mk replay` | half-up to the printed digits |
| `\CMPhtMcRel` | `0.38` | note only | `code/resum_d1/update_2026-10-13/C8_1_ext/pipeline_K8/results/comparison_points_K.csv` | \|HT - MC\|/mean in % at 0.1 | `make -C code/comparison -f public.mk replay` | half-up to the printed digits |
| `\CMPmcGauss` | `0.006\text{--}0.010` | printed | `data/inputs/MC/1d/{final_table.csv, largest_pairs_rows.tex}; code/resum_d1/update_2026-10-13/C8_1_ext/pipeline_K8/results/curve_K.csv` | \|MC - CB8\| at 0.2125..0.2375 (min, max) | `make -C code/comparison -f public.mk replay` | half-up to the printed digits |
| `\CMPtwoUfour` | `0.0015` | printed | `data/inputs/MC/2d/evaluation_2d.json; code/resum_d23/2d/results/curves.csv` | largest \|Deff(U4, 512->1024) - CB8\| at s = 1.2-1.4 | `make -C code/comparison -f public.mk replay` | half-up to the printed digits |
| `\CMPtwoUfourEnds` | `0.005\text{--}0.02` | printed | `as \CMPtwoUfour` | \|Deff(U4) - CB8\| at s = 1.05, 1.1, 1.5-1.7 (min, max) | `make -C code/comparison -f public.mk replay` | half-up to the printed digits |
| `\CMPthreeMC` | `1.0\times10^{-3}` | printed | `data/inputs/MC/3d/evaluation_3d.json; code/resum_d23/3d/results/curves.csv` | accepted MC at s = 1.6 minus CB8 | `make -C code/comparison -f public.mk replay` | half-up to the printed digits |
| `\CMPthreeMCsr` | `0.022\text{--}0.033` | printed | `as \CMPthreeMC` | s = 1.7, 1.85, 1.9 minus CB8 (min, max) | `make -C code/comparison -f public.mk replay` | half-up to the printed digits |
| `\CMPkfourKeight` | `1.3\times10^{-3}` | printed | `code/resum_d1/update_2026-10-13/C8_1_ext/pipeline_K8/results/curve_K.csv` | largest \|CB8(K=4) - CB8(K=8)\| | `make -C code/comparison -f public.mk replay` | half-up to the printed digits |

Tables tab:num1-3 (Appendix "Numerical results"): the cells taken from this folder, as printed.

| Table | d | Delta_sigma | Column | Printed | Record | Command | Tolerance |
|---|---|---|---|---|---|---|---|
| tab:num2 | 2 | 0.125 | HT | [0.94003] | `data/inputs/HT/HT_2d/largest_N.csv (Delta_E, N)` | `make -C code/comparison -f public.mk replay` | as printed (half-up); interpolated values: 10 x the interpolation error below the distance to a rounding boundary |
| tab:num2 | 2 | 0.126 | HT | [0.94568] | `data/inputs/HT/HT_2d/largest_N.csv (Delta_E, N)` | `make -C code/comparison -f public.mk replay` | as printed (half-up); interpolated values: 10 x the interpolation error below the distance to a rounding boundary |
| tab:num2 | 2 | 0.135 | HT | 0.96203 | `data/inputs/HT/HT_2d/largest_N.csv (Delta_E, N)` | `make -C code/comparison -f public.mk replay` | as printed (half-up); interpolated values: 10 x the interpolation error below the distance to a rounding boundary |
| tab:num2 | 2 | 0.15 | HT | 0.99023 | `data/inputs/HT/HT_2d/largest_N.csv (Delta_E, N)` | `make -C code/comparison -f public.mk replay` | as printed (half-up); interpolated values: 10 x the interpolation error below the distance to a rounding boundary |
| tab:num2 | 2 | 0.15 | MC | 0.9773(17) | `data/inputs/MC/2d/evaluation_2d.json (Delta_eff_U4, sigma_U4, pair 512->1024)` | `make -C code/comparison -f public.mk replay` | PDG rule (value and error) |
| tab:num2 | 2 | 0.175 | HT | 0.99972 | `data/inputs/HT/HT_2d/largest_N.csv (Delta_E, N)` | `make -C code/comparison -f public.mk replay` | as printed (half-up); interpolated values: 10 x the interpolation error below the distance to a rounding boundary |
| tab:num2 | 2 | 0.2 | HT | 0.99530 | `data/inputs/HT/HT_2d/largest_N.csv (Delta_E, N)` | `make -C code/comparison -f public.mk replay` | as printed (half-up); interpolated values: 10 x the interpolation error below the distance to a rounding boundary |
| tab:num2 | 2 | 0.2 | MC | 0.9698(18) | `data/inputs/MC/2d/evaluation_2d.json (Delta_eff_U4, sigma_U4, pair 512->1024)` | `make -C code/comparison -f public.mk replay` | PDG rule (value and error) |
| tab:num2 | 2 | 0.25 | HT | 0.97771 | `data/inputs/HT/HT_2d/largest_N.csv (Delta_E, N)` | `make -C code/comparison -f public.mk replay` | as printed (half-up); interpolated values: 10 x the interpolation error below the distance to a rounding boundary |
| tab:num2 | 2 | 0.25 | MC | 0.9661(18) | `data/inputs/MC/2d/evaluation_2d.json (Delta_eff_U4, sigma_U4, pair 512->1024)` | `make -C code/comparison -f public.mk replay` | PDG rule (value and error) |
| tab:num2 | 2 | 0.3 | HT | 0.96349 | `data/inputs/HT/HT_2d/largest_N.csv (Delta_E, N)` | `make -C code/comparison -f public.mk replay` | as printed (half-up); interpolated values: 10 x the interpolation error below the distance to a rounding boundary |
| tab:num2 | 2 | 0.3 | MC | 0.9627(20) | `data/inputs/MC/2d/evaluation_2d.json (Delta_eff_U4, sigma_U4, pair 512->1024)` | `make -C code/comparison -f public.mk replay` | PDG rule (value and error) |
| tab:num2 | 2 | 0.35 | HT | 0.95782 | `data/inputs/HT/HT_2d/largest_N.csv (Delta_E, N)` | `make -C code/comparison -f public.mk replay` | as printed (half-up); interpolated values: 10 x the interpolation error below the distance to a rounding boundary |
| tab:num2 | 2 | 0.35 | MC | 0.9584(20) | `data/inputs/MC/2d/evaluation_2d.json (Delta_eff_U4, sigma_U4, pair 512->1024)` | `make -C code/comparison -f public.mk replay` | PDG rule (value and error) |
| tab:num2 | 2 | 0.4 | HT | 0.96179 | `data/inputs/HT/HT_2d/largest_N.csv (Delta_E, N)` | `make -C code/comparison -f public.mk replay` | as printed (half-up); interpolated values: 10 x the interpolation error below the distance to a rounding boundary |
| tab:num2 | 2 | 0.4 | MC | 0.9631(22) | `data/inputs/MC/2d/evaluation_2d.json (Delta_eff_U4, sigma_U4, pair 512->1024)` | `make -C code/comparison -f public.mk replay` | PDG rule (value and error) |
| tab:num2 | 2 | 0.45 | HT | 0.97528 | `data/inputs/HT/HT_2d/largest_N.csv (Delta_E, N)` | `make -C code/comparison -f public.mk replay` | as printed (half-up); interpolated values: 10 x the interpolation error below the distance to a rounding boundary |
| tab:num2 | 2 | 0.45 | MC | 0.9659(23) | `data/inputs/MC/2d/evaluation_2d.json (Delta_eff_U4, sigma_U4, pair 512->1024)` | `make -C code/comparison -f public.mk replay` | PDG rule (value and error) |
| tab:num2 | 2 | 0.475 | HT | 0.98581 | `data/inputs/HT/HT_2d/largest_N.csv (Delta_E, N)` | `make -C code/comparison -f public.mk replay` | as printed (half-up); interpolated values: 10 x the interpolation error below the distance to a rounding boundary |
| tab:num2 | 2 | 0.475 | MC | 0.9702(25) | `data/inputs/MC/2d/evaluation_2d.json (Delta_eff_U4, sigma_U4, pair 512->1024)` | `make -C code/comparison -f public.mk replay` | PDG rule (value and error) |
| tab:num2 | 2 | 0.495 | HT | 0.99678 | `data/inputs/HT/HT_2d/largest_N.csv (Delta_E, N)` | `make -C code/comparison -f public.mk replay` | as printed (half-up); interpolated values: 10 x the interpolation error below the distance to a rounding boundary |
| tab:num3 | 3 | 0.518149 | HT | 1.41924 (`\HTnpDthreeSR`) | `code/resum_d23/3d/inputs/ht_l20/ (window_L20.json, Delta_thermal)` | `make -C code/comparison -f public.mk replay` | as printed (half-up); interpolated values: 10 x the interpolation error below the distance to a rounding boundary |
| tab:num3 | 3 | 0.52 | HT | 1.41951 | `code/resum_d23/3d/inputs/ht_l20/ (window_L20.json, Delta_thermal)` | `make -C code/comparison -f public.mk replay` | as printed (half-up); interpolated values: 10 x the interpolation error below the distance to a rounding boundary |
| tab:num3 | 3 | 0.525 | HT | 1.42026 | `code/resum_d23/3d/inputs/ht_l20/ (window_L20.json, Delta_thermal)` | `make -C code/comparison -f public.mk replay` | as printed (half-up); interpolated values: 10 x the interpolation error below the distance to a rounding boundary |
| tab:num3 | 3 | 0.535 | HT | 1.42182 | `code/resum_d23/3d/inputs/ht_l20/ (window_L20.json, Delta_thermal)` | `make -C code/comparison -f public.mk replay` | as printed (half-up); interpolated values: 10 x the interpolation error below the distance to a rounding boundary |
| tab:num3 | 3 | 0.55 | HT | 1.42435 | `code/resum_d23/3d/inputs/ht_l20/ (window_L20.json, Delta_thermal)` | `make -C code/comparison -f public.mk replay` | as printed (half-up); interpolated values: 10 x the interpolation error below the distance to a rounding boundary |
| tab:num3 | 3 | 0.575 | HT | 1.42923 | `code/resum_d23/3d/inputs/ht_l20/ (window_L20.json, Delta_thermal)` | `make -C code/comparison -f public.mk replay` | as printed (half-up); interpolated values: 10 x the interpolation error below the distance to a rounding boundary |
| tab:num3 | 3 | 0.6 | HT | 1.43511 | `code/resum_d23/3d/inputs/ht_l20/ (window_L20.json, Delta_thermal)` | `make -C code/comparison -f public.mk replay` | as printed (half-up); interpolated values: 10 x the interpolation error below the distance to a rounding boundary |
| tab:num3 | 3 | 0.625 | HT | 1.44218 | `code/resum_d23/3d/inputs/ht_l20/ (window_L20.json, Delta_thermal)` | `make -C code/comparison -f public.mk replay` | as printed (half-up); interpolated values: 10 x the interpolation error below the distance to a rounding boundary |
| tab:num3 | 3 | 0.65 | HT | 1.45062 | `code/resum_d23/3d/inputs/ht_l20/ (window_L20.json, Delta_thermal)` | `make -C code/comparison -f public.mk replay` | as printed (half-up); interpolated values: 10 x the interpolation error below the distance to a rounding boundary |
| tab:num3 | 3 | 0.675 | HT | 1.46053 | `code/resum_d23/3d/inputs/ht_l20/ (window_L20.json, Delta_thermal)` | `make -C code/comparison -f public.mk replay` | as printed (half-up); interpolated values: 10 x the interpolation error below the distance to a rounding boundary |
| tab:num3 | 3 | 0.7 | HT | 1.47192 | `code/resum_d23/3d/inputs/ht_l20/ (window_L20.json, Delta_thermal)` | `make -C code/comparison -f public.mk replay` | as printed (half-up); interpolated values: 10 x the interpolation error below the distance to a rounding boundary |
| tab:num3 | 3 | 0.725 | HT | 1.48486 | `code/resum_d23/3d/inputs/ht_l20/ (window_L20.json, Delta_thermal)` | `make -C code/comparison -f public.mk replay` | as printed (half-up); interpolated values: 10 x the interpolation error below the distance to a rounding boundary |
| tab:num3 | 3 | 0.74 | HT | 1.49360 | `code/resum_d23/3d/inputs/ht_l20/ (window_L20.json, Delta_thermal)` | `make -C code/comparison -f public.mk replay` | as printed (half-up); interpolated values: 10 x the interpolation error below the distance to a rounding boundary |
| tab:num3 | 3 | 0.745 | HT | 1.49674 | `code/resum_d23/3d/inputs/ht_l20/ (window_L20.json, Delta_thermal)` | `make -C code/comparison -f public.mk replay` | as printed (half-up); interpolated values: 10 x the interpolation error below the distance to a rounding boundary |
| tab:num3 | 3 | 0.7499 | HT | 1.49993 | `code/resum_d23/3d/inputs/ht_l20/ (window_L20.json, Delta_thermal)` | `make -C code/comparison -f public.mk replay` | as printed (half-up); interpolated values: 10 x the interpolation error below the distance to a rounding boundary |

Also checked: the HT, NRG and MC values inside comparison_points_K.csv equal the frozen records; INFO row for
the d = 2 sentence without a macro ("finite-cutoff HT lies above the curve by up to about 1% at
0.175 <= Delta_sigma <= 0.3": largest relative excess 1.00%); results/comparison/*.csv regenerate byte for byte.
Cross-package checks run by the top-level `make replay`: verify/figure_data.py (figure CSVs) and
verify/check_inputs.py (frozen inputs against the sibling folders).
