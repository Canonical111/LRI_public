# Results map: resum_d23

Every quoted number: the macro of the paper's numbers.tex, its text as printed, the record it is recomputed from,
the rule, the command (run from Resummation/) and the tolerance. Tolerance of every macro row: the recomputed value,
rounded half-up to the digits the macro prints, equals the printed value (verify/rsum_lib.py); a number word ("nine")
is compared with the value rounded to an integer. "note only" = defined in numbers.tex but no longer printed (INFO
row). Source of the printed texts: results/quoted_numbers.json (generated from the paper's numbers.tex).

Top-level map of all packages: `results_map.md` in Resummation/.

| Macro | Printed | Status | Record | Rule | Command | Tolerance |
|---|---|---|---|---|---|---|
| `\RStwoDenv` | `5.2\times10^{-3}` | printed | `code/resum_d23/2d/results/curves.csv` | largest curvature core-band width | `make -C code/resum_d23 -f public.mk replay` | half-up to the printed digits |
| `\RSthreeDenv` | `1.5\times10^{-4}` | printed | `code/resum_d23/3d/results/curves.csv` | largest slope core-band width | `make -C code/resum_d23 -f public.mk replay` | half-up to the printed digits |
| `\RStwoDendpointMid` | `4.7\times10^{-3}` | note only | `code/resum_d23/2d/results/curves.csv` | largest \|tangent, value or direct CB8 - curvature_CB8\| at Ds = 0.3, 0.35, 0.4 (s = 1.2-1.4) | `make -C code/resum_d23 -f public.mk replay` | half-up to the printed digits |
| `\RStwoDendpoint` | `7.5\times10^{-3}` | printed | `code/resum_d23/2d/results/curves.csv` | largest \|value_CB8 or tangent_CB8 - curvature_CB8\| | `make -C code/resum_d23 -f public.mk replay` | half-up to the printed digits |
| `\RSthreeDcone` | `7\times10^{-5}` | note only | `code/resum_d23/3d/results/curves.csv` | largest \|slope_SR_low/high - slope_CB8\| | `make -C code/resum_d23 -f public.mk replay` | half-up to the printed digits |
| `\RSgffOnlyTwo` | `1.0049` | printed | `code/resum_d23/2d/results/curves.csv` | direct_CB8 at 1/8 | `make -C code/resum_d23 -f public.mk replay` | half-up to the printed digits |
| `\RSgffOnlyThree` | `1.4161` | printed | `code/resum_d23/3d/results/curves.csv` | direct_CB8 at S | `make -C code/resum_d23 -f public.mk replay` | half-up to the printed digits |
| `\RSgffDevTwo` | `5.2\times10^{-3}` | printed | `code/resum_d23/2d/results/curves.csv` | largest \|direct_CB8 - curvature_CB8\| | `make -C code/resum_d23 -f public.mk replay` | half-up to the printed digits |
| `\RSgffDevThree` | `3.4\times10^{-3}` | note only | `code/resum_d23/3d/results/curves.csv` | largest \|direct_CB8 - slope_CB8\| | `make -C code/resum_d23 -f public.mk replay` | half-up to the printed digits |
| `\RScbThreeTwo` | `0.087` | printed | `code/resum_d23/combined/cb3_gff_only.csv, 2d/results/curves.csv` | largest \|CB3 - curvature_CB8\| in d = 2 | `make -C code/resum_d23 -f public.mk replay` | half-up to the printed digits |

Tables tab:num1-3 (Appendix "Numerical results"): the cells taken from this folder, as printed.

| Table | d | Delta_sigma | Column | Printed | Record | Command | Tolerance |
|---|---|---|---|---|---|---|---|
| tab:num2 | 2 | 0.125 | Resummed | 1 | `code/resum_d23/2d/results/curves.csv (curvature_CB8)` | `make -C code/resum_d23 -f public.mk replay` | as printed (half-up); interpolated values: 10 x the interpolation error below the distance to a rounding boundary |
| tab:num2 | 2 | 0.126 | Resummed | 1.00000 | `code/resum_d23/2d/results/curves.csv (curvature_CB8)` | `make -C code/resum_d23 -f public.mk replay` | as printed (half-up); interpolated values: 10 x the interpolation error below the distance to a rounding boundary |
| tab:num2 | 2 | 0.135 | Resummed | 0.99962 | `code/resum_d23/2d/results/curves.csv (curvature_CB8)` | `make -C code/resum_d23 -f public.mk replay` | as printed (half-up); interpolated values: 10 x the interpolation error below the distance to a rounding boundary |
| tab:num2 | 2 | 0.15 | Resummed | 0.99780 | `code/resum_d23/2d/results/curves.csv (curvature_CB8)` | `make -C code/resum_d23 -f public.mk replay` | as printed (half-up); interpolated values: 10 x the interpolation error below the distance to a rounding boundary |
| tab:num2 | 2 | 0.175 | Resummed | 0.99242 | `code/resum_d23/2d/results/curves.csv (curvature_CB8)` | `make -C code/resum_d23 -f public.mk replay` | as printed (half-up); interpolated values: 10 x the interpolation error below the distance to a rounding boundary |
| tab:num2 | 2 | 0.2 | Resummed | 0.98542 | `code/resum_d23/2d/results/curves.csv (curvature_CB8)` | `make -C code/resum_d23 -f public.mk replay` | as printed (half-up); interpolated values: 10 x the interpolation error below the distance to a rounding boundary |
| tab:num2 | 2 | 0.25 | Resummed | 0.97114 | `code/resum_d23/2d/results/curves.csv (curvature_CB8)` | `make -C code/resum_d23 -f public.mk replay` | as printed (half-up); interpolated values: 10 x the interpolation error below the distance to a rounding boundary |
| tab:num2 | 2 | 0.3 | Resummed | 0.96118 | `code/resum_d23/2d/results/curves.csv (curvature_CB8)` | `make -C code/resum_d23 -f public.mk replay` | as printed (half-up); interpolated values: 10 x the interpolation error below the distance to a rounding boundary |
| tab:num2 | 2 | 0.35 | Resummed | 0.95810 | `code/resum_d23/2d/results/curves.csv (curvature_CB8)` | `make -C code/resum_d23 -f public.mk replay` | as printed (half-up); interpolated values: 10 x the interpolation error below the distance to a rounding boundary |
| tab:num2 | 2 | 0.4 | Resummed | 0.96257 | `code/resum_d23/2d/results/curves.csv (curvature_CB8)` | `make -C code/resum_d23 -f public.mk replay` | as printed (half-up); interpolated values: 10 x the interpolation error below the distance to a rounding boundary |
| tab:num2 | 2 | 0.45 | Resummed | 0.97543 | `code/resum_d23/2d/results/curves.csv (curvature_CB8)` | `make -C code/resum_d23 -f public.mk replay` | as printed (half-up); interpolated values: 10 x the interpolation error below the distance to a rounding boundary |
| tab:num2 | 2 | 0.475 | Resummed | 0.98584 | `code/resum_d23/2d/results/curves.csv (curvature_CB8)` | `make -C code/resum_d23 -f public.mk replay` | as printed (half-up); interpolated values: 10 x the interpolation error below the distance to a rounding boundary |
| tab:num2 | 2 | 0.495 | Resummed | 0.99678 | `code/resum_d23/2d/results/curves.csv (curvature_CB8)` | `make -C code/resum_d23 -f public.mk replay` | as printed (half-up); interpolated values: 10 x the interpolation error below the distance to a rounding boundary |
| tab:num3 | 3 | 0.518149 | Resummed | 1.41263 | `code/resum_d23/3d/results/curves.csv (slope_CB8)` | `make -C code/resum_d23 -f public.mk replay` | as printed (half-up); interpolated values: 10 x the interpolation error below the distance to a rounding boundary |
| tab:num3 | 3 | 0.52 | Resummed | 1.41313 | `code/resum_d23/3d/results/curves.csv (slope_CB8)` | `make -C code/resum_d23 -f public.mk replay` | as printed (half-up); interpolated values: 10 x the interpolation error below the distance to a rounding boundary |
| tab:num3 | 3 | 0.525 | Resummed | 1.41449 | `code/resum_d23/3d/results/curves.csv (slope_CB8)` | `make -C code/resum_d23 -f public.mk replay` | as printed (half-up); interpolated values: 10 x the interpolation error below the distance to a rounding boundary |
| tab:num3 | 3 | 0.535 | Resummed | 1.41719 | `code/resum_d23/3d/results/curves.csv (slope_CB8)` | `make -C code/resum_d23 -f public.mk replay` | as printed (half-up); interpolated values: 10 x the interpolation error below the distance to a rounding boundary |
| tab:num3 | 3 | 0.55 | Resummed | 1.42123 | `code/resum_d23/3d/results/curves.csv (slope_CB8)` | `make -C code/resum_d23 -f public.mk replay` | as printed (half-up); interpolated values: 10 x the interpolation error below the distance to a rounding boundary |
| tab:num3 | 3 | 0.575 | Resummed | 1.42807 | `code/resum_d23/3d/results/curves.csv (slope_CB8)` | `make -C code/resum_d23 -f public.mk replay` | as printed (half-up); interpolated values: 10 x the interpolation error below the distance to a rounding boundary |
| tab:num3 | 3 | 0.6 | Resummed | 1.43524 | `code/resum_d23/3d/results/curves.csv (slope_CB8)` | `make -C code/resum_d23 -f public.mk replay` | as printed (half-up); interpolated values: 10 x the interpolation error below the distance to a rounding boundary |
| tab:num3 | 3 | 0.625 | Resummed | 1.44299 | `code/resum_d23/3d/results/curves.csv (slope_CB8)` | `make -C code/resum_d23 -f public.mk replay` | as printed (half-up); interpolated values: 10 x the interpolation error below the distance to a rounding boundary |
| tab:num3 | 3 | 0.65 | Resummed | 1.45154 | `code/resum_d23/3d/results/curves.csv (slope_CB8)` | `make -C code/resum_d23 -f public.mk replay` | as printed (half-up); interpolated values: 10 x the interpolation error below the distance to a rounding boundary |
| tab:num3 | 3 | 0.675 | Resummed | 1.46116 | `code/resum_d23/3d/results/curves.csv (slope_CB8)` | `make -C code/resum_d23 -f public.mk replay` | as printed (half-up); interpolated values: 10 x the interpolation error below the distance to a rounding boundary |
| tab:num3 | 3 | 0.7 | Resummed | 1.47214 | `code/resum_d23/3d/results/curves.csv (slope_CB8)` | `make -C code/resum_d23 -f public.mk replay` | as printed (half-up); interpolated values: 10 x the interpolation error below the distance to a rounding boundary |
| tab:num3 | 3 | 0.725 | Resummed | 1.48488 | `code/resum_d23/3d/results/curves.csv (slope_CB8)` | `make -C code/resum_d23 -f public.mk replay` | as printed (half-up); interpolated values: 10 x the interpolation error below the distance to a rounding boundary |
| tab:num3 | 3 | 0.74 | Resummed | 1.49360 | `code/resum_d23/3d/results/curves.csv (slope_CB8)` | `make -C code/resum_d23 -f public.mk replay` | as printed (half-up); interpolated values: 10 x the interpolation error below the distance to a rounding boundary |
| tab:num3 | 3 | 0.745 | Resummed | 1.49674 | `code/resum_d23/3d/results/curves.csv (slope_CB8)` | `make -C code/resum_d23 -f public.mk replay` | as printed (half-up); interpolated values: 10 x the interpolation error below the distance to a rounding boundary |
| tab:num3 | 3 | 0.7499 | Resummed | 1.49993 | `code/resum_d23/3d/results/curves.csv (slope_CB8)` | `make -C code/resum_d23 -f public.mk replay` | as printed (half-up); interpolated values: 10 x the interpolation error below the distance to a rounding boundary |

Also checked: the plotted data equal the curve tables; combined/literature_mc_2d3d.csv regenerates byte for byte.
`replay-full` reruns the ten scripts and the CB3 script and compares every output (1e-12).
