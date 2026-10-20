# Where each NRG number comes from

Every NRG number the paper prints: the record that holds it, the command that recomputes it, and the comparison
tolerance. Paths are relative to `NRG/`. Paper: `../paper/main.tex`, its `sections/` and `numbers.tex` (texts frozen in
`verify/quoted_numbers.json`; check V8 compares them with the paper). The values with their full error budget are in
`results/ds13_final.json` and the note (`note/lri_nrg_1d_note.pdf`, Sec. 4 and App. D).

**Commands.** `make replay` recomputes everything from the 197 records in `data/records/` inside `.work/` (about 20 s;
needs `../MC/data/1d/scan_data/FIT_V3_SCAN.json` for the comparison) and then runs `make verify`, which compares
`.work/` with the released files and writes `.work/reproduced/VERIFY.md`. `make verify` alone re-checks an existing
`.work/`. `make test` (solver tests, code checksums, self-tests of the second implementation) and `make smoke` (a small
new critical search with both solvers) check the code; neither reproduces a quoted number.

**Chain.** `data/records/` (each record sha256-bound to the solver source, check V0) → `code/analysis/summarize.py` →
`code/analysis/build_tables.py` (estimator: `code/analysis/estimator.py`) → `results/ds13_final.json` →
`code/analysis/note_numbers.py` → `note/tables/numbers.tex` → the paper's `\NRG...`
macros. The Monte Carlo comparison goes through `method_comparison/compare_methods.py` →
`method_comparison/comparison.json`.

**Check V8** (`verify/verify.py`). Every row below is one entry of `verify/quoted_numbers.json`, which holds the text as
printed in the paper (for a statement the paper makes without a number, a fixed wording of the fact); V8 recomputes that text from the regenerated files and writes one line per id in
`.work/reproduced/VERIFY.md`. Compare rule "equal" for counts, statements and labels; otherwise equal, or numbers within one
unit of their last printed digit with exponents equal (the same rule as for the note tables, V2: least-squares fits
differ in their last bits across NumPy/SciPy builds and CPUs). One more V8 line compares the listed texts with
`../paper/numbers.tex` and checks that the `\NRG` macros printed by `main.tex` and `sections/` are exactly those listed; it reads SKIP
when `NRG/` is copied without `../paper`. The record tolerances behind the texts: `results/ds13_final.json` floats to
1e-8 + 1e-6 relative (V1), Δ_E and δ_tot of the 13 points also to 1e-9 absolute (V7, `verify/expected.json`),
`method_comparison/comparison.json` to 1e-9 + 1e-9 relative (V4).

**Status.** final, plateau: the value of the settled window, flat across its neighbors. final, extrapolated in chain
depth: the local exponent extrapolated along the RG time (Δσ = 0.2, 0.175). Not converged in chain depth (Δσ = 0.249,
0.24, 0.225): the settled value, shown in brackets, with no error and used in no comparison. Errors are linear sums
δ_tot = δ_depth + δ_K + δ_Λ, error scales and not standard deviations (note Sec. 4). The paper says "chain length" where
the note and this folder say "chain depth": the number of Wilson-chain sites, that is, the RG time reached.

## Table tab:num1 (Appendix "Numerical results", d = 1), column NRG

The table gives the best value of each method at each coupling; its NRG column prints Δ_E with δ_tot, in brackets
where the point is not converged in chain depth. The error budget of each point and the parameters of the central item
(Λ = 3, K = 128, n_b = 16) are not in the paper; they are in the note (Sec. 4) and in `results/ds13_final.json`.

| id | quoted (macro) | printed | status | record | command | tolerance |
|---|---|---|---|---|---|---|
| T.DE.0.249 | `\NRGDETwoFortyNine` | `[0.5080]` | not converged in chain depth: shown, no error, used in no comparison | `results/ds13_final.json` [ds=0.249] Delta_E; `verify/expected.json`; via note macro `\nrgDETwoFortyNine` (`note/tables/numbers.tex`) in brackets | `make replay` (V8) | equal, or ±1 in the last printed digit (exponents equal); Δ_E, δ_tot to 1e-9 absolute (V7) |
| T.DE.0.24 | `\NRGDETwoForty` | `[0.4989]` | not converged in chain depth: shown, no error, used in no comparison | `results/ds13_final.json` [ds=0.24] Delta_E; `verify/expected.json`; via note macro `\nrgDETwoForty` (`note/tables/numbers.tex`) in brackets | `make replay` (V8) | equal, or ±1 in the last printed digit (exponents equal); Δ_E, δ_tot to 1e-9 absolute (V7) |
| T.DE.0.225 | `\NRGDETwoTwentyFive` | `[0.4897]` | not converged in chain depth: shown, no error, used in no comparison | `results/ds13_final.json` [ds=0.225] Delta_E; `verify/expected.json`; via note macro `\nrgDETwoTwentyFive` (`note/tables/numbers.tex`) in brackets | `make replay` (V8) | equal, or ±1 in the last printed digit (exponents equal); Δ_E, δ_tot to 1e-9 absolute (V7) |
| T.DE.0.2 | `\NRGDETwoHundred` | `0.4830(7)` | final, extrapolated in chain depth | `results/ds13_final.json` [ds=0.2] Delta_E, total; `verify/expected.json`; via note macro `\nrgDETwoHundred` (`note/tables/numbers.tex`) | `make replay` (V8) | equal, or ±1 in the last printed digit (exponents equal); Δ_E, δ_tot to 1e-9 absolute (V7) |
| T.DE.0.175 | `\NRGDEOneSeventyFive` | `0.48390(35)` | final, extrapolated in chain depth | `results/ds13_final.json` [ds=0.175] Delta_E, total; `verify/expected.json`; via note macro `\nrgDEOneSeventyFive` (`note/tables/numbers.tex`) | `make replay` (V8) | equal, or ±1 in the last printed digit (exponents equal); Δ_E, δ_tot to 1e-9 absolute (V7) |
| T.DE.0.15 | `\NRGDEOneFifty` | `0.49111(11)` | final, plateau | `results/ds13_final.json` [ds=0.15] Delta_E, total; `verify/expected.json`; via note macro `\nrgDEOneFifty` (`note/tables/numbers.tex`) | `make replay` (V8) | equal, or ±1 in the last printed digit (exponents equal); Δ_E, δ_tot to 1e-9 absolute (V7) |
| T.DE.0.125 | `\NRGDEOneTwentyFive` | `0.50567(5)` | final, plateau | `results/ds13_final.json` [ds=0.125] Delta_E, total; `verify/expected.json`; via note macro `\nrgDEOneTwentyFive` (`note/tables/numbers.tex`) | `make replay` (V8) | equal, or ±1 in the last printed digit (exponents equal); Δ_E, δ_tot to 1e-9 absolute (V7) |
| T.DE.0.1 | `\NRGDEOneHundred` | `0.529608(33)` | final, plateau | `results/ds13_final.json` [ds=0.1] Delta_E, total; `verify/expected.json`; via note macro `\nrgDEOneHundred` (`note/tables/numbers.tex`) | `make replay` (V8) | equal, or ±1 in the last printed digit (exponents equal); Δ_E, δ_tot to 1e-9 absolute (V7) |
| T.DE.0.075 | `\NRGDESeventyFive` | `0.566260(30)` | final, plateau | `results/ds13_final.json` [ds=0.075] Delta_E, total; `verify/expected.json`; via note macro `\nrgDESeventyFive` (`note/tables/numbers.tex`) | `make replay` (V8) | equal, or ±1 in the last printed digit (exponents equal); Δ_E, δ_tot to 1e-9 absolute (V7) |
| T.DE.0.05 | `\NRGDEFifty` | `0.622115(27)` | final, plateau | `results/ds13_final.json` [ds=0.05] Delta_E, total; `verify/expected.json`; via note macro `\nrgDEFifty` (`note/tables/numbers.tex`) | `make replay` (V8) | equal, or ±1 in the last printed digit (exponents equal); Δ_E, δ_tot to 1e-9 absolute (V7) |
| T.DE.0.025 | `\NRGDETwentyFive` | `0.713422(29)` | final, plateau | `results/ds13_final.json` [ds=0.025] Delta_E, total; `verify/expected.json`; via note macro `\nrgDETwentyFive` (`note/tables/numbers.tex`) | `make replay` (V8) | equal, or ±1 in the last printed digit (exponents equal); Δ_E, δ_tot to 1e-9 absolute (V7) |
| T.DE.0.01 | `\NRGDETen` | `0.80975(5)` | final, plateau | `results/ds13_final.json` [ds=0.01] Delta_E, total; `verify/expected.json`; via note macro `\nrgDETen` (`note/tables/numbers.tex`) | `make replay` (V8) | equal, or ±1 in the last printed digit (exponents equal); Δ_E, δ_tot to 1e-9 absolute (V7) |
| T.DE.0.001 | `\NRGDEOne` | `0.93742(11)` | final, plateau | `results/ds13_final.json` [ds=0.001] Delta_E, total; `verify/expected.json`; via note macro `\nrgDEOne` (`note/tables/numbers.tex`) | `make replay` (V8) | equal, or ±1 in the last printed digit (exponents equal); Δ_E, δ_tot to 1e-9 absolute (V7) |

## Section "Nonperturbative results" (sec: nonpert), paragraph NRG

"In d=1, NRG gives Δ_E at \NRGnPoints{} couplings (Table tab:num1). The three points closest to s=1/2 are not converged in
chain length and enter no comparison. Near s=1, NRG reproduces the dual expansion of Table tab:sr through C^SR_5(1); the
term of C^SR_6(1) is of the size of the NRG error, and the higher ones are smaller." The comparison (sec: compare, last
paragraph) and the discussion repeat the last two statements.

| id | quoted (macro) | printed | status | record | command | tolerance |
|---|---|---|---|---|---|---|
| N.points | `\NRGnPoints` | `13` | count | `results/ds13_final.json` (rows); via rule `n_points` of `verify/verify.py` | `make replay` (V8) | equal; record floats 1e-8 + 1e-6 relative (V1) |
| N.nc | — (statement) | `3: 0.249, 0.24, 0.225` | not converged in chain depth | `results/ds13_final.json` status; via rule `nc_points` of `verify/verify.py` | `make replay` (V8) | equal; record floats 1e-8 + 1e-6 relative (V1) |
| S.dual | — (statement) | `size of D_n falls for n = 2..5: yes; size of D_5 1.1 delta_tot; C^SR_6 term 1.3 delta_tot; C^SR_7, C^SR_8 terms at most 0.1 delta_tot` | final, plateau (Δσ = 0.01); comparison with the short-range dual series | `results/ds13_final.json` [ds=0.01] Delta_E, total; `verify/expected.json`; C^SR_1..8(1): the closed forms of paper Eqs. eq:sr-closed and eq:sr-C8; via rule `dual_series` of `verify/verify.py` | `make replay` (V8) | equal; Δ_E, δ_tot to 1e-9 absolute (V7) |

The row S.dual in numbers, from the full-precision Δ_E = 0.8097473093 at Δσ = 0.01 (δ_tot = 4.7e-5): the differences
from the series through C^SR_n(1) are D_2 = +4.7473e-3, D_3 = -9.8006e-4, D_4 = +2.3956e-4, D_5 = -5.2818e-5
(1.1 δ_tot); the term of C^SR_6(1) is -5.87e-5 (1.25 δ_tot) and gives D_6 = +5.8e-6; the terms of C^SR_7(1) and
C^SR_8(1) are 5.1e-6 and 2.5e-6 (0.11 and 0.05 δ_tot). The coefficients are mapped in `../SRI/docs/dual_d1/results_map.md`.

## Figure fig:cmp1d (`01_methods_clean.pdf`, Sec. Resummation)

The NRG symbols of the paper's d = 1 figure (orange circles) are the 13 rows of `results/ds13_final.json`: `Delta_E` as the
point, `total` as the bar, `status` for filled (converged in chain depth) or open (not converged). Command: `make replay`
(V1: floats to 1e-8 + 1e-6 relative; V7: Δ_E and δ_tot to 1e-9 absolute). The figure itself is drawn by `../Resummation`
from its frozen copy `Resummation/data/inputs/NRG/ds13_final.json`, which `make -C ../Resummation check-inputs` requires to
be byte-identical to `NRG/results/ds13_final.json` (sha256 ed33e680…); the plotted points are in
`Resummation/results/figures/fig_cmp1d_points.csv` and are checked by the Resummation replay.

## Numbers that use NRG values and are mapped by another folder

| quoted | where | mapped in | NRG input |
|---|---|---|---|
| "Hamiltonian truncation and NRG agree to within two parts in a thousand" (wherever the truncation is extrapolated and NRG is converged, 0.075 ≤ Δσ ≤ 0.2) | Introduction; Sec. Comparison; Sec. Discussion | `../HT/results_map.md`, the rows that compare with NRG | `HT/results/HT_1d/nrg_reference.json`, a byte copy of `results/ds13_final.json` |
| `\CMPnrgCB` ("within … of every converged NRG value") | Sec. Comparison; Sec. Discussion | `../Resummation/results_map.md` | `Resummation/data/inputs/NRG/ds13_final.json` (byte copy, checked by `check-inputs`) |

## Statements without a printed number, not recomputed by V8

| statement | where | backed by |
|---|---|---|
| "A blind second implementation reproduces the Wilson chain and the estimates" | Sec. Nonperturbative results | `independent_check/` (written from `SPEC.md` only): `make test` runs its 38 self-tests; `make replay` recomputes the comparison (V3: `independent_check_compare/compare.json`, `.md`, `trusted_windows.json`, `.md`, floats to 1e-14 + 1e-12 relative) and checks 16 values in `verify/expected.json` (V7: window differences to 1e-12, α_c differences to 1e-15). Result (note Sec. 8.1): chain coefficients equal to rounding (better than 1e-15), α_c bitwise or to 7.2e-14, Δ_E to 3.1e-7 in 316 windows. |
| "NRG: a linear sum of chain-length, truncation and discretization errors" | Table tab:num1 caption | definition of the estimator and budget: `code/analysis/estimator.py`, `code/analysis/build_tables.py`, note Secs. 3.7 and 4 |
| "Except near the mean-field end, where NRG does not converge" | Introduction | the row N.nc above |
| "Hamiltonian truncation, NRG and MC agree at the sub-percent level" (away from the mean-field end), for the NRG–MC pairs | Introduction; Sec. Comparison; Sec. Discussion | `method_comparison/comparison.json` (V4: floats to 1e-9 + 1e-9 relative; MC from `../MC/data/1d/scan_data/FIT_V3_SCAN.json`): at the seven converged NRG points with an MC value, 0.025 ≤ Δσ ≤ 0.175, \|NRG − MC\|/NRG is at most 0.54% (Δσ = 0.1); note Sec. 8. The pairs with Hamiltonian truncation are mapped in `../HT/results_map.md`. |

## Not covered by `make replay`

The production itself (197 records, 178 thread-hours on a Slurm cluster): `REPRODUCE.md` §5 reruns it, and the replay
starts from its records. `make smoke` reruns one small critical search with both solvers and compares it with
`verify/smoke_expected.json`; it checks the code, not a quoted number.

## Defined in `../paper/numbers.tex` but not printed

These 136 NRG macros are defined but appear nowhere in `main.tex` or `sections/` and are not mapped or checked:
`\NRGfive`, `\NRGOmega`, `\NRGLambda`, `\NRGkeep`, `\NRGnb`, `\NRGsitesPerDecade`, `\NRGNmin`, `\NRGNmax`, `\NRGscaleMin`, `\NRGscaleMax`, `\NRGnRuns`, `\NRGfrac`, `\NRGbisectTol`, `\NRGalphacShift`, `\NRGwinMin`, `\NRGwinFrac`, `\NRGwinEnd`, `\NRGqVar`, `\NRGqRes`, `\NRGlnInvDalpha`, `\NRGKspread`, `\NRGnbEight`, `\NRGnbTen`, `\NRGnbTwelve`, `\NRGedge`, `\NRGLflat`, `\NRGLtwoShift`, `\NRGLtwoKconv`, `\NRGLonefiveMove`, `\NRGKneeded`, `\NRGerrSmall`, `\NRGerrMid`, `\NRGerrOneSeventyFive`, `\NRGerrTwoHundred`, `\NRGtau`, `\NRGdriftMaxPlateau`, `\NRGdriftMinNoPlateau`, `\NRGnLambdaKdbl`, `\NRGnLambdaKdblword`, `\NRGslopeLate`, `\NRGseriesMedDiffTwoHundred`, `\NRGytNLOOne`, `\NRGnloDiffOne`, `\NRGsrDiffTwo`, `\NRGsrDiffThree`, `\NRGsrDiffFour`, `\NRGsrDiffFive`, `\NRGmcAccN`, `\NRGmcWithinLin`, `\NRGmcRatioMax`, `\NRGmcDiffMax`, `\NRGmcNeg`, `\NRGmcCrossMax`, `\NRGminVal`, `\NRGindepConfigs`, `\NRGindepConfigsword`, `\NRGindepChain`, `\NRGindepAlpha`, `\NRGindepDE`, `\NRGindepTrusted`, `\NRGytOne`, `\NRGytOneKT`, `\NRGytTen`, `\NRGytTenKT`, `\NRGexcessTwoFortyNine`, `\NRGexcessTwoForty`, `\NRGexcessTwoTwentyFive`, `\NRGseriesErrTwoFortyNine`, `\NRGseriesAgreeTwoForty`, `\NRGseriesSpreadTwoHundred`, `\NRGdepthTwoFortyNine`, `\NRGKTwoFortyNine`, `\NRGLTwoFortyNine`, `\NRGtotTwoFortyNine`, `\NRGnqTwoFortyNine`, `\NRGnqTwoFortyNineword`, `\NRGdepthTwoForty`, `\NRGKTwoForty`, `\NRGLTwoForty`, `\NRGtotTwoForty`, `\NRGnqTwoForty`, `\NRGdepthTwoTwentyFive`, `\NRGKTwoTwentyFive`, `\NRGLTwoTwentyFive`, `\NRGtotTwoTwentyFive`, `\NRGnqTwoTwentyFive`, `\NRGdepthTwoHundred`, `\NRGKTwoHundred`, `\NRGLTwoHundred`, `\NRGtotTwoHundred`, `\NRGnqTwoHundred`, `\NRGdepthOneSeventyFive`, `\NRGKOneSeventyFive`, `\NRGLOneSeventyFive`, `\NRGtotOneSeventyFive`, `\NRGnqOneSeventyFive`, `\NRGdepthOneFifty`, `\NRGKOneFifty`, `\NRGLOneFifty`, `\NRGtotOneFifty`, `\NRGnqOneFifty`, `\NRGdepthOneTwentyFive`, `\NRGKOneTwentyFive`, `\NRGLOneTwentyFive`, `\NRGtotOneTwentyFive`, `\NRGnqOneTwentyFive`, `\NRGdepthOneHundred`, `\NRGKOneHundred`, `\NRGLOneHundred`, `\NRGtotOneHundred`, `\NRGnqOneHundred`, `\NRGdepthSeventyFive`, `\NRGKSeventyFive`, `\NRGLSeventyFive`, `\NRGtotSeventyFive`, `\NRGnqSeventyFive`, `\NRGdepthFifty`, `\NRGKFifty`, `\NRGLFifty`, `\NRGtotFifty`, `\NRGnqFifty`, `\NRGdepthTwentyFive`, `\NRGKTwentyFive`, `\NRGLTwentyFive`, `\NRGtotTwentyFive`, `\NRGnqTwentyFive`, `\NRGdepthTen`, `\NRGKTen`, `\NRGLTen`, `\NRGtotTen`, `\NRGnqTen`, `\NRGdepthOne`, `\NRGKOne`, `\NRGLOne`, `\NRGtotOne`, `\NRGnqOne`.
