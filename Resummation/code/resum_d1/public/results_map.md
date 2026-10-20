# Results map: resum_d1

Every quoted number: the macro of the paper's numbers.tex, its text as printed, the record it is recomputed from,
the rule, the command (run from Resummation/) and the tolerance. Tolerance of every macro row: the recomputed value,
rounded half-up to the digits the macro prints, equals the printed value (verify/rsum_lib.py); a number word ("nine")
is compared with the value rounded to an integer. "note only" = defined in numbers.tex but no longer printed (INFO
row). Source of the printed texts: results/quoted_numbers.json (generated from the paper's numbers.tex).

Top-level map of all packages: `results_map.md` in Resummation/.

| Macro | Printed | Status | Record | Rule | Command | Tolerance |
|---|---|---|---|---|---|---|
| `\RSgffOnlyEnd` | `0.567` | printed | `code/resum_d1/update_2026-10-13/C8_1_ext/pipeline_K8/results/curve_K.csv` | direct_L8 at Delta_sigma = 0 | `make -C code/resum_d1 -f public.mk replay` | half-up to the printed digits |
| `\RSoneDmin` | `0.4828` | printed | `code/resum_d1/update_2026-10-13/C8_1_ext/pipeline_K8/results/curve_K.csv` | minimum of endpoint_v_K8_L8 over the grid | `make -C code/resum_d1 -f public.mk replay` | half-up to the printed digits |
| `\RSoneDminAt` | `0.192` | printed | `code/resum_d1/update_2026-10-13/C8_1_ext/pipeline_K8/results/curve_K.csv` | grid point of that minimum | `make -C code/resum_d1 -f public.mk replay` | half-up to the printed digits |
| `\RSoneDatOne` | `0.5302` | note only | `code/resum_d1/update_2026-10-13/C8_1_ext/pipeline_K8/results/curve_K.csv` | endpoint_v_K8_L8 at 0.1 | `make -C code/resum_d1 -f public.mk replay` | half-up to the printed digits |
| `\RSoneDatOneRange` | `[0.5280,\,0.5316]` | note only | `code/resum_d1/update_2026-10-13/C8_1_ext/pipeline_K8/results/curve_K.csv` | union of the K = 5..8 core bands at 0.1 | `make -C code/resum_d1 -f public.mk replay` | half-up to the printed digits |
| `\RSoneDenv` | `4.7\times10^{-3}` | printed | `code/resum_d1/update_2026-10-13/C8_1_ext/pipeline_K8/results/curve_K.csv` | largest width of the K = 5..8 envelope | `make -C code/resum_d1 -f public.mk replay` | half-up to the printed digits |
| `\RScoreKeight` | `2.3\times10^{-4}` | note only | `code/resum_d1/update_2026-10-13/C8_1_ext/pipeline_K8/results/curve_K.csv` | core-band width at 0.05, K = 8 | `make -C code/resum_d1 -f public.mk replay` | half-up to the printed digits |
| `\RScoreKfour` | `3.4\times10^{-3}` | note only | `code/resum_d1/update_2026-10-13/C8_1_ext/pipeline_K8/results/curve_K.csv` | core-band width at 0.05, K = 4 | `make -C code/resum_d1 -f public.mk replay` | half-up to the printed digits |
| `\RSnineOnePct` | `3.5\times10^{-4}` | printed | `code/resum_d1/update_2026-10-13/C8_1_ext/pipeline_K8/results/c9cb8_sensitivity_K.csv` | K = 8 curve at 0.1: change for 1% of C9 (CB8 prediction as reference) | `make -C code/resum_d1 -f public.mk replay` | half-up to the printed digits |
| `\RSnineCeightAmp` | `nine` | printed | `code/resum_d1/update_2026-10-13/C8_1_ext/pipeline_K8/results/precision_budget_K.csv` | C8 term of the input budget at 0.1, K = 8: order 9 / order 8, rounded to an integer | `make -C code/resum_d1 -f public.mk replay` | half-up to the printed digits |
| `\RSnineImplied` | `-2.190\times10^{8}\text{ and }{-2.178}\times10^{8}` | printed | `code/resum_d1/update_2026-10-13/C8_1_ext/pipeline_K8/results/c9_predictions_K.csv` | smallest and largest C9(1) implied by CB8 (K = 4, 8) and PB[3/5] (K = 8), endpoint-v, b_L = 3 | `make -C code/resum_d1 -f public.mk replay` | half-up to the printed digits |
| `\RSnineSpread` | `0.5` | printed | `code/resum_d1/update_2026-10-13/C8_1_ext/pipeline_K8/results/c9_predictions_K.csv` | their spread (max - min) / \|mean\|, in % | `make -C code/resum_d1 -f public.mk replay` | half-up to the printed digits |

Tables tab:num1-3 (Appendix "Numerical results"): the cells taken from this folder, as printed.

| Table | d | Delta_sigma | Column | Printed | Record | Command | Tolerance |
|---|---|---|---|---|---|---|---|
| tab:num1 | 1 | 0.001 | Resummed | 0.93742 | `code/resum_d1/update_2026-10-13/C8_1_ext/pipeline_K8/results/curve_K.csv (endpoint_v_K8_L8)` | `make -C code/resum_d1 -f public.mk replay` | as printed (half-up); interpolated values: 10 x the interpolation error below the distance to a rounding boundary |
| tab:num1 | 1 | 0.01 | Resummed | 0.80975 | `code/resum_d1/update_2026-10-13/C8_1_ext/pipeline_K8/results/curve_K.csv (endpoint_v_K8_L8)` | `make -C code/resum_d1 -f public.mk replay` | as printed (half-up); interpolated values: 10 x the interpolation error below the distance to a rounding boundary |
| tab:num1 | 1 | 0.0125 | Resummed | 0.78915 | `code/resum_d1/update_2026-10-13/C8_1_ext/pipeline_K8/results/curve_K.csv (endpoint_v_K8_L8)` | `make -C code/resum_d1 -f public.mk replay` | as printed (half-up); interpolated values: 10 x the interpolation error below the distance to a rounding boundary |
| tab:num1 | 1 | 0.025 | Resummed | 0.71343 | `code/resum_d1/update_2026-10-13/C8_1_ext/pipeline_K8/results/curve_K.csv (endpoint_v_K8_L8)` | `make -C code/resum_d1 -f public.mk replay` | as printed (half-up); interpolated values: 10 x the interpolation error below the distance to a rounding boundary |
| tab:num1 | 1 | 0.0375 | Resummed | 0.66146 | `code/resum_d1/update_2026-10-13/C8_1_ext/pipeline_K8/results/curve_K.csv (endpoint_v_K8_L8)` | `make -C code/resum_d1 -f public.mk replay` | as printed (half-up); interpolated values: 10 x the interpolation error below the distance to a rounding boundary |
| tab:num1 | 1 | 0.05 | Resummed | 0.62223 | `code/resum_d1/update_2026-10-13/C8_1_ext/pipeline_K8/results/curve_K.csv (endpoint_v_K8_L8)` | `make -C code/resum_d1 -f public.mk replay` | as printed (half-up); interpolated values: 10 x the interpolation error below the distance to a rounding boundary |
| tab:num1 | 1 | 0.0625 | Resummed | 0.59139 | `code/resum_d1/update_2026-10-13/C8_1_ext/pipeline_K8/results/curve_K.csv (endpoint_v_K8_L8)` | `make -C code/resum_d1 -f public.mk replay` | as printed (half-up); interpolated values: 10 x the interpolation error below the distance to a rounding boundary |
| tab:num1 | 1 | 0.075 | Resummed | 0.56663 | `code/resum_d1/update_2026-10-13/C8_1_ext/pipeline_K8/results/curve_K.csv (endpoint_v_K8_L8)` | `make -C code/resum_d1 -f public.mk replay` | as printed (half-up); interpolated values: 10 x the interpolation error below the distance to a rounding boundary |
| tab:num1 | 1 | 0.0875 | Resummed | 0.54656 | `code/resum_d1/update_2026-10-13/C8_1_ext/pipeline_K8/results/curve_K.csv (endpoint_v_K8_L8)` | `make -C code/resum_d1 -f public.mk replay` | as printed (half-up); interpolated values: 10 x the interpolation error below the distance to a rounding boundary |
| tab:num1 | 1 | 0.1 | Resummed | 0.53025 | `code/resum_d1/update_2026-10-13/C8_1_ext/pipeline_K8/results/curve_K.csv (endpoint_v_K8_L8)` | `make -C code/resum_d1 -f public.mk replay` | as printed (half-up); interpolated values: 10 x the interpolation error below the distance to a rounding boundary |
| tab:num1 | 1 | 0.1125 | Resummed | 0.51703 | `code/resum_d1/update_2026-10-13/C8_1_ext/pipeline_K8/results/curve_K.csv (endpoint_v_K8_L8)` | `make -C code/resum_d1 -f public.mk replay` | as printed (half-up); interpolated values: 10 x the interpolation error below the distance to a rounding boundary |
| tab:num1 | 1 | 0.125 | Resummed | 0.50643 | `code/resum_d1/update_2026-10-13/C8_1_ext/pipeline_K8/results/curve_K.csv (endpoint_v_K8_L8)` | `make -C code/resum_d1 -f public.mk replay` | as printed (half-up); interpolated values: 10 x the interpolation error below the distance to a rounding boundary |
| tab:num1 | 1 | 0.1375 | Resummed | 0.49808 | `code/resum_d1/update_2026-10-13/C8_1_ext/pipeline_K8/results/curve_K.csv (endpoint_v_K8_L8)` | `make -C code/resum_d1 -f public.mk replay` | as printed (half-up); interpolated values: 10 x the interpolation error below the distance to a rounding boundary |
| tab:num1 | 1 | 0.15 | Resummed | 0.49171 | `code/resum_d1/update_2026-10-13/C8_1_ext/pipeline_K8/results/curve_K.csv (endpoint_v_K8_L8)` | `make -C code/resum_d1 -f public.mk replay` | as printed (half-up); interpolated values: 10 x the interpolation error below the distance to a rounding boundary |
| tab:num1 | 1 | 0.1625 | Resummed | 0.48714 | `code/resum_d1/update_2026-10-13/C8_1_ext/pipeline_K8/results/curve_K.csv (endpoint_v_K8_L8)` | `make -C code/resum_d1 -f public.mk replay` | as printed (half-up); interpolated values: 10 x the interpolation error below the distance to a rounding boundary |
| tab:num1 | 1 | 0.1727335 | Resummed | 0.48465 | `code/resum_d1/update_2026-10-13/C8_1_ext/pipeline_K8/results/curve_K.csv (endpoint_v_K8_L8)` | `make -C code/resum_d1 -f public.mk replay` | as printed (half-up); interpolated values: 10 x the interpolation error below the distance to a rounding boundary |
| tab:num1 | 1 | 0.175 | Resummed | 0.48424 | `code/resum_d1/update_2026-10-13/C8_1_ext/pipeline_K8/results/curve_K.csv (endpoint_v_K8_L8)` | `make -C code/resum_d1 -f public.mk replay` | as printed (half-up); interpolated values: 10 x the interpolation error below the distance to a rounding boundary |
| tab:num1 | 1 | 0.1875 | Resummed | 0.48291 | `code/resum_d1/update_2026-10-13/C8_1_ext/pipeline_K8/results/curve_K.csv (endpoint_v_K8_L8)` | `make -C code/resum_d1 -f public.mk replay` | as printed (half-up); interpolated values: 10 x the interpolation error below the distance to a rounding boundary |
| tab:num1 | 1 | 0.2 | Resummed | 0.48312 | `code/resum_d1/update_2026-10-13/C8_1_ext/pipeline_K8/results/curve_K.csv (endpoint_v_K8_L8)` | `make -C code/resum_d1 -f public.mk replay` | as printed (half-up); interpolated values: 10 x the interpolation error below the distance to a rounding boundary |
| tab:num1 | 1 | 0.225 | Resummed | 0.48808 | `code/resum_d1/update_2026-10-13/C8_1_ext/pipeline_K8/results/curve_K.csv (endpoint_v_K8_L8)` | `make -C code/resum_d1 -f public.mk replay` | as printed (half-up); interpolated values: 10 x the interpolation error below the distance to a rounding boundary |
| tab:num1 | 1 | 0.24 | Resummed | 0.49422 | `code/resum_d1/update_2026-10-13/C8_1_ext/pipeline_K8/results/curve_K.csv (endpoint_v_K8_L8)` | `make -C code/resum_d1 -f public.mk replay` | as printed (half-up); interpolated values: 10 x the interpolation error below the distance to a rounding boundary |
| tab:num1 | 1 | 0.249 | Resummed | 0.49934 | `code/resum_d1/update_2026-10-13/C8_1_ext/pipeline_K8/results/curve_K.csv (endpoint_v_K8_L8)` | `make -C code/resum_d1 -f public.mk replay` | as printed (half-up); interpolated values: 10 x the interpolation error below the distance to a rounding boundary |

Also checked by the replay: the plotted data equal the curve and comparison tables; references_nrg_rev2.csv and
update_2026-10-14/k4_vs_k8_discrimination.csv regenerate byte for byte from data/inputs. `replay-full` reruns the
chain and compares all 40 outputs (abs diff <= 1e-12 + 1e-12 abs(value); fits 1e-6 relative); the quoted numbers,
including the ninth-order scenario rows, are recomputed from the rerun.
