# Results map of SRI/ (expansions about the short-range end)

Every number of the paper's Sec. 3.2 ("Near the short-range end") that SRI/ reproduces: each \SR* macro the paper
prints (its text as in the paper's numbers.tex, frozen in `results/quoted_numbers.json`, generated 2026-10-18), the displayed
equations and the table cells, with the status of the result, the record it is recomputed from (paths relative to
`code/<package>/`), the rule, the command (run from `SRI/`) and the tolerance. `make replay` runs every row; each
package's full map, with the cited checks and the INFO rows, is `docs/<package>/results_map.md`.

| Macro | Printed | Status | Package | Record | Rule | Command | Tolerance |
|---|---|---|---|---|---|---|---|
| `\SRorderword` | `eight` | closed form through C7, C8 numerical | `dual_d1` | `data/coefficients.json (registry of C^SR_1..C^SR_8)` | number of coefficients in the registry | `make -C code/dual_d1 -f public.mk replay` | exact text |
| `\SRorderLitword` | `two` | literature (cited) | `dual_d1` | `Benedetti:2024wgx, Benedetti:2025nzp; registry entries n = 1, 2` | published orders C^SR_1, C^SR_2 | `make -C code/dual_d1 -f public.mk replay` | exact text (INFO: cited, not recomputed) |
| `\SRCthree` | `5.72737` | proved closed form within the matched two-coupling prescription | `dual_d1` | `data/coefficients.json /coefficients/2 (expression, 70-digit decimal)` | the closed form of eq:sr-closed evaluated with mpmath at 50 digits | `make -C code/dual_d1 -f public.mk replay` | recomputed value rounded half-up to the printed digits equals the printed text |
| `\SRCfour` | `-12.1962` | proved closed form within the prescription | `dual_d1` | `data/coefficients.json /coefficients/3` | eq:sr-closed, mpmath 50 digits | `make -C code/dual_d1 -f public.mk replay` | recomputed value rounded half-up to the printed digits equals the printed text |
| `\SRCfive` | `29.2378` | proved closed form within the prescription (exact certificate) | `dual_d1` | `data/coefficients.json /coefficients/4` | eq:sr-closed, mpmath 50 digits; certificate replayed | `make -C code/dual_d1 -f public.mk replay` | recomputed value rounded half-up to the printed digits equals the printed text |
| `\SRCsix` | `-58.6657` | proved closed form within the prescription (exact certificate) | `dual_d1` | `data/coefficients.json /coefficients/5` | eq:sr-closed, mpmath 50 digits; certificate replayed | `make -C code/dual_d1 -f public.mk replay` | recomputed value rounded half-up to the printed digits equals the printed text |
| `\SRCseven` | `51.0690` | proved closed form within the prescription (exact certificate) | `dual_d1` | `data/coefficients.json /coefficients/6` | eq:sr-closed, mpmath 50 digits; certificate (weights 2-5 in replay, all in replay-full) | `make -C code/dual_d1 -f public.mk replay` | recomputed value rounded half-up to the printed digits equals the printed text |
| `\SRCeight` | `247.381` | conjectured closed form eq:sr-C8 (tab:sr cell \ptConj), agreeing with the numerical record to about 85 digits (record without an error bound; one input, P6, cross-checked to about 57 decimal places, quoted in the SRI note only) | `dual_d1` | `data/archived/C8_zeta_candidate/result.json /C8_assembled_without_candidate; data/archived/C8_P6_exact_sources/P6_full/P6_eval{70,100}.json` | the stored numerical record; its inputs re-assembled to better than 1e-95; the two P6 evaluations give C8 values 2.2e-57 apart (row "C8 cross-check (two P6 runs)") | `make -C code/dual_d1 -f public.mk replay` | recomputed value rounded half-up to the printed digits equals the printed text; 57 places exact |
| `\SRCeightMag` | `247.38\pm0.13` | numerical (empirical numerical uncertainty: a linear sum of the differences between three complete runs and a validated roundoff estimate, not a standard deviation or a bound; two check criteria amended after their data were seen, SRI note App. I.7) | `integ_d1` | `results/C8_record_v2.json /C8, /C8_error (sha256 0d463b29...20ec0c)` | the verbatim c8_assemble.py --verify on the 29 frozen inputs (/inputs); the error is 3/4 of that of f_3_0_1 from the verbatim M4B gate v2 rerun on the shipped run outputs | `make -C code/integ_d1 -f public.mk replay` | recomputed value rounded half-up to the printed digits equals the printed text (value and error) |
| `\SRtwoCtwo` | `-4.06627` | closed form, conditional on one unproved step (uniform remainder) | `c2_closed_d2` | `outputs/summary.json /C2 (72 digits)` | the closed form cf:cr-c2 evaluated with mpmath at 50 digits; the study rerun in a copy | `make -C code/c2_closed_d2 -f public.mk replay` | recomputed value rounded half-up to the printed digits equals the printed text; \|diff\| < 1e-45 vs summary.json |
| `\SRtwoCtwoMC` | `-4.075\pm0.019` | numerical (one standard error) | `c2_closed_d2` | `mc/run_{A,B,C}/out_*.txt -> public/mc_combined.json /combined/{C2,C2_se}` | per-chunk outputs recombined by public/c2lib.py (cut Lambda > -15, inverse-variance mean) | `make -C code/c2_closed_d2 -f public.mk replay` | recomputed value rounded half-up to the printed digits equals the printed text (value and error) |
| `\SRintegClosedDev` | `7\times10^{-26}` | numerical (check) | `integ_d1` | `results/C8_record_v2.json /C3_C7 and the verbatim gate outputs (unrounded assembly)` | largest relative difference of the magnetization-scheme C3..C7 from the closed forms (C6) | `make -C code/integ_d1 -f public.mk replay` | recomputed value rounded half-up to the printed digits equals the printed text |
| `\SRCeightMagDiff` | `2.5\times10^{-5}` | numerical (comparison) | `integ_d1` | `results/C8_record_v2.json /C8 against the record of dual_d1 (eq:C8num)` | \|C8 (magnetization scheme) - C8 record\| = 2.506e-5 | `make -C code/integ_d1 -f public.mk replay` | recomputed value rounded half-up to the printed digits equals the printed text (absolute value) |
| `\SRthreeCone` | `0.2732` | numerical | `c1_d3` | `outputs/tables/current_summary.json /retained/C1` | the package workflow rerun from scratch in .work/; c_1 = a0/b0 | `make -C code/c1_d3 -f public.mk replay` | recomputed value rounded half-up to the printed digits equals the printed text; rerun within 5e-10 |
| `\SRthreeConeRange` | `[0.2690,\,0.2760]` | conditional (assumed gaps: no unlisted Z2-even primary below 8, Z2-odd below 7) | `c1_d3` | `outputs/tables/current_summary.json /recommended_working_summary/interval` | hull of the nominal and doubled-padding envelopes, rounded outward to 0.001 | `make -C code/c1_d3 -f public.mk replay` | recomputed value rounded half-up to the printed digits equals the printed text |
| `\SRthreeConeBRRZ` | `0.27(4)` | literature (cited) | `c1_d3` | `Behan:2017emf` | published estimate | `make -C code/c1_d3 -f public.mk replay` | exact text (INFO: cited, not recomputed) |
| `\SRtwoCtwoHT` | `-4.0670(24)` | numerical (linear sum of systematic diagnostics, not an s.d.) | `c2_cylinder_d2` | `results/continuum_2026-10/generations/<G>/C2_estimate.json /final/{C2,dC2}` | regulator fits, joint fit and error budget recomputed from results/continuum_2026-10/generations/<G>/continuum_points.json | `make -C code/c2_cylinder_d2 -f public.mk replay` | recomputed value rounded half-up to the printed digits equals the printed text (value; uncertainty in units of the last digit) |
| `\SRtwoCtwoHTDev` | `2\times10^{-4}` | numerical | `c2_cylinder_d2` | `results/continuum_2026-10/generations/<G>/C2_estimate.json /final/C2 and the closed form (mpmath)` | \|C2_HT - C2_closed\| / \|C2_closed\| = 1.917e-4 | `make -C code/c2_cylinder_d2 -f public.mk replay` | recomputed value rounded half-up to the printed digits equals the printed text |

Defined in numbers.tex but not printed (INFO rows of the replays of their packages): `\SRorderLit` = `2`, `\SRorder` = `8`, `\SRclosed` = `7`, `\SRCeightIndep` = `242.8\pm2.4`, `\SRCeightPull` = `1.9`, `\SRCeightPullMax` = `4.0`, `\SRindepPullMax` = `0.9`, `\SRthreeConeImplDev` = `10^{-12}`, `\SRtwoCtwoHTNmax` = `1024`.

## Equations and tables

| Item | Status | Package | Record | Rule | Command | Tolerance |
|---|---|---|---|---|---|---|
| eq:sr-closed (C^SR_3(1)..C^SR_7(1)) | proved closed forms within the prescription | `dual_d1`, `indep_d1` | `data/coefficients.json` (expressions) | the TeX parsed into rational coefficients of zeta products | `make -C code/dual_d1 -f public.mk replay` | exact equality of every coefficient |
| eq:sr-C8 (C^SR_8(1) closed form) | conjectured; "agrees with the numerical value of C^SR_8(1) to about 85 digits" | `dual_d1` | `data/archived/C8_zeta_candidate/result.json` | exact coefficients; candidate minus the numerical record | `make -C code/dual_d1 -f public.mk replay` | coefficients exact; \|residual\| = 3.1e-86, below the record's printing floor 1.8e-85 (not an interval bound) |
| tab:sr, row C^SR_n(1) | as the macros (n = 8: \ptConj, conjectured closed form) | `dual_d1` | the macros above | each cell holds its macro and status marker | `make -C code/dual_d1 -f public.mk replay` | exact |
| tab:sr, row C^SR_n(2) | C^SR_1(2) = 0 literature; C^SR_2(2) closed form | `c2_closed_d2` | `outputs/summary.json` | cells; the study's first-order integral vanishes | `make -C code/c2_closed_d2 -f public.mk replay` | exact |
| tab:sr, row C^SR_n(3) | numerical | `c1_d3` | `outputs/tables/current_summary.json` | cells | `make -C code/c1_d3 -f public.mk replay` | exact |
| tab:htpert, row C^SR_2(2), and its caption | numerical | `c2_cylinder_d2` | `results/quoted_numbers.json` /tab_htpert_c2 and results/continuum_2026-10/generations/<G> | the row prints \SRtwoCtwoHT and \SRtwoCtwoHTDev; the caption states the error kind | `make -C code/c2_cylinder_d2 -f public.mk replay` | exact |
| appendix cf:sec:cr2 (R_Gamma, P, Q, T, Eq. cf:cr-c2) | closed form | `c2_closed_d2` | `outputs/summary.json` | the printed parameters and the closed form, mpmath 50 digits | `make -C code/c2_closed_d2 -f public.mk replay` | \|diff\| < 1e-45 |

## Values for other folders

`results/sr_values.json`: every value above as a decimal string with status, file and JSON pointer (stable pointers `/d1/C/1` to `/d1/C/8`, `/d2/c2/closed`, `/d2/c2/mc`, `/d2/c2/cylinder`, `/d3/c1/value`, `/d3/c1/range`, `/d3/S`, `/d3/E_SR`); `make check-values` checks each against the tree.

## Per-package maps

- `docs/dual_d1/results_map.md`
- `docs/indep_d1/results_map.md`
- `docs/integ_d1/results_map.md`
- `docs/c2_closed_d2/results_map.md`
- `docs/c2_cylinder_d2/results_map.md`
- `docs/c1_d3/results_map.md`
- `docs/closure_d1/results_map.md`
