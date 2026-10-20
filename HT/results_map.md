# Where each HT number comes from

Every quoted number: the record that holds it, the command that recomputes it, and the comparison tolerance.

Assembled from the package authors' texts. Inside a package section, relative paths are relative to that package's folder `code/<package>/` unless they start with `HT/`. The values themselves are in `note/README.md` and the note.

- d = 1: dressed phi^4 Hamiltonian truncation: `lri_dressed_phi4_hpc`, `lri_dressed_phi4_hpc_analysis`, `lri_dressed_phi4_independent_check`
- d = 2: dressed-window Hamiltonian truncation: `lri_2d_window_hpc`, `lri_2d_window_indep`
- d = 3: dressed-window Hamiltonian truncation: `lri_3d_window_hpc`, `lri_3d_window_indep`

## d = 1: dressed phi^4 Hamiltonian truncation

### `lri_dressed_phi4_hpc`

Folder: `code/lri_dressed_phi4_hpc/`.

#### results_map: d = 1 finite-coupling HT

Every quoted d = 1 finite-coupling HT number. Paper (main.tex at f496d39a, 2026-10-19; not in the Supplementary Material): Sec. Results, subsection "Nonperturbative results" (sec: nonpert; HTnpNmax, HTnpEpsDiff) and subsection "Comparison" (sec: compare; the sentence of row C9; Fig. fig:cmp1d); Sec. "Discussion" (sec: discuss; the sentence of row C9 again); Appendix "The truncation artifact and its correction" (app: window; HTnpRawViol, HTnpViolN, HTnpWinReduce, HTnpIdentN, HTnpResSig, HTnpResE, HTnpRawShift, HTnpDensK, HTnpBasisErr, and Table tab:win, six rows of the note's Table tab:d1-ident: row V7); Appendix "Numerical results" (app: numerics; HT column and caption of Table tab:num1: HTnpDE*, in brackets HTnpNforty*, HTnpTrust, HTnpNmax). Macros are those of numbers.tex. Rows without a macro, and rows whose macro is marked "not printed in the paper" (it stays defined in numbers.tex), are quoted in the HT note (note/, Sections on d = 1) only. Paths relative to `HT/`. Command A = `make -C code/lri_dressed_phi4_hpc_analysis -f public.mk replay` (public/replay_ht1d.py, row id in the first column); command B = `make -C code/lri_dressed_phi4_independent_check -f public.mk replay` (public/replay_indep.py). Records: `data/HT_1d/dens_v1/campaigns/*/results/` (dens), `data/HT_1d/prod_window/campaigns/*/results/` (prod), `code/lri_dressed_phi4_hpc_analysis/identities/` (identity records). Expected values and rules: `results/HT_1d/quoted_numbers.json`.

| row | quoted (macro) | value | estimator | records | comparison |
|---|---|---|---|---|---|
| A:S1 | HTnpNmin (not printed in the paper) | 12 | smallest cutoff of the fitted series | dens | equal |
| A:S2 | HTnpNmax | 40 | largest cutoff common to all 13 Ds | dens | equal |
| A:S3 | HTnpNminRange (not printed in the paper) | 12 – 24 | N_min values of the fit family | dens | equal |
| A:S4 | HTnpNfits (not printed in the paper) | 21 | fits per Ds | dens | equal |
| A:S5 | HTnpDensK | 16 | nz of the dens16 records | stored bases | equal |
| A:S6 | HTnpDensTrain (not printed in the paper) | 24 | bath_cut of the 13 stored bases | stored bases | equal |
| A:S7 | HTnpDensTeacher (not printed in the paper) | 48 | teacher_nz of the stored bases | stored bases | equal |
| A:S8 | - | 24 | keep of the stored bases | stored bases | equal |
| A:S9 | HTnpBasisErr | 1e-6 | max \|dens16 - largest-nz prod record (nz >= 48, osc 384, consistent)\| at N = 32 | prod + dens | <= quoted bound |
| A:S10 | HTnpOmegaMin, HTnpSpreadMax (not printed in the paper) | 0.45, 2e-3 | protocol constants; A2 checks that the shipped dens_v1.py reproduces the stable flags | — | not computed (judgement) |
| A:S11 | HTnpOmegaRange (not printed in the paper) | 0.6 – 0.9 | min, max of fit.omega_median over the stable Ds | dens | both ends rounded as quoted |
| A:V1 | HTnpRawViol | 0.06 – 0.25 | min, max \|v1\| over raw records, Ds <= 0.1, N = 16..28, sigma/shadow/E, unambiguous | identity records | both ends rounded as quoted |
| A:V2 | HTnpWinReduce | 10 – 40 | min, max \|v1 raw / v1 window\| for sigma at N = 28, Ds <= 0.15 | identity records | both ends rounded to the quoted significant figures (1 sig.) |
| A:V3 | HTnpResSig | 0.01 | median \|v1 window\| of sigma and shadow at N = 28, Ds <= 0.1, unambiguous | identity records | within a factor 2 |
| A:V4 | HTnpResE | 0.05 | max \|v1 window\| of epsilon at N = 28, Ds <= 0.05, unambiguous | identity records | rounded to the quoted significant figures (1 sig.) |
| A:V5 | HTnpViolN | 16 – 28 | cutoffs of the raw identity records behind V1 (Ds <= 0.1; min, max N) | identity records | both ends rounded as quoted |
| A:V6 | HTnpIdentN | 28 | cutoff of the identity table (note Table tab:d1-ident, paper Table tab:win) and of V2-V4: largest N of the identity records | identity records | rounded to the quoted decimals |
| A:V7 | (paper: the six rows of Table tab:win, copied from note Table tab:d1-ident) | 6 table rows (Ds = 0.2 to 0.025) | rows of the identity table at N = 28, Ds = 0.2, 0.15, 0.1, 0.075, 0.05, 0.025: raw and window level-1 violations of sigma, phi^3 and E, as printed | identity records | equal |
| A:E1 | HTnpOmegaEffOneTwentyFive (not printed in the paper) | 0.64 | omega_eff at N ~ 35 from slopes 4 cutoff units apart | dens | rounded to the quoted decimals |
| A:E2 | HTnpOmegaEffOneHundred (not printed in the paper) | 0.68 | omega_eff at N ~ 35 from slopes 4 cutoff units apart | dens | rounded to the quoted decimals |
| A:E3 | HTnpOmegaEffSeventyFive (not printed in the paper) | 0.70 – 0.80 | omega_eff at N ~ 15 and ~ 35 | dens | both ends rounded as quoted |
| A:E4 | HTnpOmegaEffFifty (not printed in the paper) | 0.92 – 1.16 | omega_eff at N ~ 15 and ~ 35 | dens | both ends rounded as quoted |
| A:E5 | HTnpHoldoutCut, HTnpHoldout (not printed in the paper) | 2.3e-6 | dens_v1_holdout.json, by_cut 32: max \|actual - median prediction\| over N = 34..40, Ds >= 0.05 | dens | rounded to the quoted significant figures (2 sig.) |
| A:E6 | HTnpOneSided (not printed in the paper) | 5e-4 | slope(N 38-40) x (1/w - 1/(w + 0.2)), w = omega_eff(35) | dens | rounded to the quoted significant figures (1 sig.) |
| A:E7 | HTnpExtrapShift (not printed in the paper) | 1.6e-3 – 2.5e-3 | D_inf - Delta(N = 40), min and max over Ds = 0.075, 0.1, 0.125 | dens | both ends rounded to the quoted significant figures (2 sig.) |
| A:E8 | HTnpTwentyFivePeak (not printed in the paper) | 22 | argmax_N Delta(N) | dens | equal |
| A:E9 | HTnpSlopeTwentyFive (not printed in the paper) | -1.3e-3 | (Delta(40) - Delta(38)) / ln(40/38) | dens | rounded to the quoted significant figures (2 sig.) |
| A:E10 | HTnpSlopeTen (not printed in the paper) | -6.2e-3 | (Delta(40) - Delta(38)) / ln(40/38) | dens | rounded to the quoted significant figures (2 sig.) |
| A:P1 | HTnpEpsDiff | -4e-8 | D_inf - (1/2 - eps/6 + sum_{k=2..7} C_k eps^k), C_k = GFF d = 1 coefficients (extrapolate.REF_EPS) | dens | rounded to the quoted significant figures (1 sig.) |
| A:P2 | HTnpEpsBand (not printed in the paper) | 0.49419 – 0.49426 | min, max of the partial sums through eps^4..eps^7 | dens | both ends rounded as quoted |
| A:P3 | - | True | D_inf inside that band | dens | true |
| A:P4 | HTnpEpsLevel (not printed in the paper) | 1e-6 | judgement | — | not computed (judgement) |
| A:T01 | HTnpNfortyTwoFortyNine (not printed in the paper) | 0.4993430 | Delta_thermal of the dens16 record at N = 40 (via dens_v1_extrapolation.json "values") | dens | rounded to the quoted decimals |
| A:T02 | HTnpNfortyTwoForty (not printed in the paper) | 0.494186 | Delta_thermal of the dens16 record at N = 40 (via dens_v1_extrapolation.json "values") | dens | rounded to the quoted decimals |
| A:T03 | HTnpNfortyTwoTwentyFive (not printed in the paper) | 0.487982 | Delta_thermal of the dens16 record at N = 40 (via dens_v1_extrapolation.json "values") | dens | rounded to the quoted decimals |
| A:T04 | HTnpNfortyTwoHundred (not printed in the paper) | 0.482839 | Delta_thermal of the dens16 record at N = 40 (via dens_v1_extrapolation.json "values") | dens | rounded to the quoted decimals |
| A:T05 | HTnpNfortyOneSeventyFive (not printed in the paper) | 0.483541 | Delta_thermal of the dens16 record at N = 40 (via dens_v1_extrapolation.json "values") | dens | rounded to the quoted decimals |
| A:T06 | HTnpNfortyOneFifty (not printed in the paper) | 0.490388 | Delta_thermal of the dens16 record at N = 40 (via dens_v1_extrapolation.json "values") | dens | rounded to the quoted decimals |
| A:T07 | HTnpNfortyOneTwentyFive (not printed in the paper) | 0.504561 | Delta_thermal of the dens16 record at N = 40 (via dens_v1_extrapolation.json "values") | dens | rounded to the quoted decimals |
| A:T08 | HTnpNfortyOneHundred (not printed in the paper) | 0.528210 | Delta_thermal of the dens16 record at N = 40 (via dens_v1_extrapolation.json "values") | dens | rounded to the quoted decimals |
| A:T09 | HTnpNfortySeventyFive (not printed in the paper) | 0.564851 | Delta_thermal of the dens16 record at N = 40 (via dens_v1_extrapolation.json "values") | dens | rounded to the quoted decimals |
| A:T10 | HTnpNfortyFifty | 0.620671 | Delta_thermal of the dens16 record at N = 40 (via dens_v1_extrapolation.json "values") | dens | rounded to the quoted decimals |
| A:T11 | HTnpNfortyTwentyFive | 0.710577 | Delta_thermal of the dens16 record at N = 40 (via dens_v1_extrapolation.json "values") | dens | rounded to the quoted decimals |
| A:T12 | HTnpNfortyTen | 0.809111 | Delta_thermal of the dens16 record at N = 40 (via dens_v1_extrapolation.json "values") | dens | rounded to the quoted decimals |
| A:T13 | HTnpNfortyOne | 0.969338 | Delta_thermal of the dens16 record at N = 40 (via dens_v1_extrapolation.json "values") | dens | rounded to the quoted decimals |
| A:D01 | HTnpDEtwoFortyNine | 0.49934358(9) | dens_v1.py: median and half-spread of the accepted fits (fit.D_inf, fit.spread_half) | dens | value and error rounded as quoted |
| A:D02 | HTnpDEtwoForty | 0.4942198(26) | dens_v1.py: median and half-spread of the accepted fits (fit.D_inf, fit.spread_half) | dens | value and error rounded as quoted |
| A:D03 | HTnpDEtwoTwentyFive | 0.488080(5) | dens_v1.py: median and half-spread of the accepted fits (fit.D_inf, fit.spread_half) | dens | value and error rounded as quoted |
| A:D04 | HTnpDEtwoHundred | 0.483024(5) | dens_v1.py: median and half-spread of the accepted fits (fit.D_inf, fit.spread_half) | dens | value and error rounded as quoted |
| A:D05 | HTnpDEoneSeventyFive | 0.483909(15) | dens_v1.py: median and half-spread of the accepted fits (fit.D_inf, fit.spread_half) | dens | value and error rounded as quoted |
| A:D06 | HTnpDEoneFifty | 0.491209(33) | dens_v1.py: median and half-spread of the accepted fits (fit.D_inf, fit.spread_half) | dens | value and error rounded as quoted |
| A:D07 | HTnpDEoneTwentyFive | 0.50612(4) | dens_v1.py: median and half-spread of the accepted fits (fit.D_inf, fit.spread_half) | dens | value and error rounded as quoted |
| A:D08 | HTnpDEoneHundred | 0.53048(12) | dens_v1.py: median and half-spread of the accepted fits (fit.D_inf, fit.spread_half) | dens | value and error rounded as quoted |
| A:D09 | HTnpDEseventyFive | 0.56733(20)(-50) | dens_v1.py: median and half-spread of the accepted fits (fit.D_inf, fit.spread_half) | dens | value and error rounded as quoted |
| A:D10 | HTnpDEfiftyFOneTwo | 0.6220 – 0.6224 | min, max D_inf of the accepted fits of the named forms (N <= 40) | dens | both ends rounded as quoted |
| A:D11 | HTnpDEfiftyFthree | 0.618 | min D_inf of the accepted F3 fits | dens | rounded to the quoted decimals |
| A:D12 | HTnpTrust | 1e-4 | judgement | — | not computed (judgement) |
| A:D13 | - | 3.3e-5 | max fit.spread_half over Ds >= 0.15 | dens | rounded to the quoted significant figures (2 sig.) |
| A:U00 | - | one-sided at 0.075 only | judgement; omega_eff trends in results/HT_1d/holdout_and_local_exponent.md | — | not computed (judgement) |
| A:U01 | - | final | stable flag of dens_v1.py and sign of dDelta/dlnN at N = 40 | dens | computed part of the status word |
| A:U02 | - | final | stable flag of dens_v1.py and sign of dDelta/dlnN at N = 40 | dens | computed part of the status word |
| A:U03 | - | final | stable flag of dens_v1.py and sign of dDelta/dlnN at N = 40 | dens | computed part of the status word |
| A:U04 | - | final | stable flag of dens_v1.py and sign of dDelta/dlnN at N = 40 | dens | computed part of the status word |
| A:U05 | - | final | stable flag of dens_v1.py and sign of dDelta/dlnN at N = 40 | dens | computed part of the status word |
| A:U06 | - | final | stable flag of dens_v1.py and sign of dDelta/dlnN at N = 40 | dens | computed part of the status word |
| A:U07 | - | final | stable flag of dens_v1.py and sign of dDelta/dlnN at N = 40 | dens | computed part of the status word |
| A:U08 | - | final | stable flag of dens_v1.py and sign of dDelta/dlnN at N = 40 | dens | computed part of the status word |
| A:U09 | - | one-sided | stable flag of dens_v1.py and sign of dDelta/dlnN at N = 40 | dens | computed part of the status word |
| A:U10 | - | unstable | stable flag of dens_v1.py and sign of dDelta/dlnN at N = 40 | dens | computed part of the status word |
| A:U11 | - | no limit | stable flag of dens_v1.py and sign of dDelta/dlnN at N = 40 | dens | computed part of the status word |
| A:U12 | - | no limit | stable flag of dens_v1.py and sign of dDelta/dlnN at N = 40 | dens | computed part of the status word |
| A:U13 | - | no limit | stable flag of dens_v1.py and sign of dDelta/dlnN at N = 40 | dens | computed part of the status word |
| A:C1 | HTnpNRGmax (not printed in the paper) | 1.1e-3 | max \|D_inf - NRG Delta_E\| over 0.075 <= Ds <= 0.2 | results/HT_1d/nrg_reference.json + dens | rounded to the quoted significant figures (2 sig.) |
| A:E11 | - | 0.39 – 0.46 | omega_eff at N ~ 15 and ~ 35, Ds = 0.249 (slow rise at weak coupling) | dens | both ends rounded as quoted |
| A:E12 | - | 1e-5 | Ds = 0.249: bias of a further rise of omega_eff by 0.2 (as E6) is below | dens | <= quoted bound |
| A:C2 | - | 4.5e-4, 8.7e-4, 1.1e-3 | D_inf - NRG at Ds = 0.125, 0.1, 0.075 (2 significant figures) | dens + results/HT_1d/nrg_reference.json | each rounded to the quoted significant figures (2 sig.) |
| A:C3 | - | 0.032 | Ds = 0.001: Delta(N = 40) - NRG | dens + results/HT_1d/nrg_reference.json | rounded to the quoted decimals |
| A:S12 | - | 0.15 | A = Ds/4 + r - g/2 at the tuned couplings (dens16): largest Ds at which its sign changes with the cutoff (A < 0 at every N for Ds = 0.2, 0.175; > 0 at Ds >= 0.225) | dens | rounded to the quoted decimals |
| A:B1 | - | 0.710632, 0.710934, 0.710959 | energy zero-mode basis at Ds = 0.025, N = 28, consistent window: Delta_eps for nz = 32, 40, 48 (prod records) | prod | each rounded to the quoted decimals |
| A:D14 | - | 1.2e-4 | largest fit half-spread among the final results (Ds >= 0.1) | dens | rounded to the quoted significant figures (2 sig.) |
| A:M3 | - | 1.6e-4 | largest tail-model shift (F4 with two free exponents; drifting local exponent) of the window limit at 0.075 <= Ds <= 0.125 | dens | rounded to the quoted significant figures (2 sig.) |
| A:M4 | - | True | NRG lies in the bracket [Delta(40), Delta(40) + slope(40)/omega_eff(35)] of the window series at every 0.075 <= Ds <= 0.2 | dens + results/HT_1d/nrg_reference.json | true |
| A:M5 | - | True | the raw limit lies below NRG and the window limit above it at 0.075 <= Ds <= 0.125 | dens + prod + results/HT_1d/nrg_reference.json | true |
| A:M6 | - | 6.6e-4, 2.3e-3, 1.7e-3 | window minus raw limit at Ds = 0.125, 0.1, 0.075 (2 significant figures) | dens + prod | each rounded to the quoted significant figures (2 sig.) |
| A:M7 | - | 1.3e-4 | largest \|window - raw\| limit difference at Ds = 0.2, 0.175, 0.15 | dens + prod | rounded to the quoted significant figures (2 sig.) |
| A:C5 | HTnpNRGmin (not printed in the paper) | 1e-4 | smallest D_inf - NRG at 0.075 <= Ds <= 0.15 (at 0.15) | dens + results/HT_1d/nrg_reference.json | rounded to the quoted significant figures (1 sig.) |
| A:C6 | - | 1e-4 | D_inf - NRG at Ds = 0.175, 0.2 is below 1e-4 | dens + results/HT_1d/nrg_reference.json | <= quoted bound |
| A:C7 | - | True | D_inf > NRG at every 0.075 <= Ds <= 0.2 | dens + results/HT_1d/nrg_reference.json | true |
| A:C8 | - | True | D_inf - NRG exceeds the fit half-spread at Ds = 0.1 and 0.125 | dens + results/HT_1d/nrg_reference.json | true |
| A:C9 | (paper: 'agree to within two parts in a thousand ... 0.075 <= Ds <= 0.2'; repeated in the Discussion) | 2e-3 | max \|D_inf - NRG\| / NRG at 0.075 <= Ds <= 0.2 is at most 2e-3 | dens + results/HT_1d/nrg_reference.json | <= quoted bound |
| A:M10 | HTnpRawShift | 7e-4 – 2.3e-3 | window minus raw limit at 0.075 <= Ds <= 0.125 (min with 1, max with 2 significant figures) | dens + prod | ends rounded to 1 and 2 significant figures |
| B:B6 | HTnpDoneIndep (not printed in the paper) | 5e-9 | max \|Delta_eps blind - Delta_eps production (largest nz)\| over the 38 compared points | code/lri_dressed_phi4_independent_check/results/indep_results.json + prod + dens | 1 sig. |
| B:B4, B5 | (note) | 1.3e-9, 4.8e-9 | the same, for production nz 48 (or Ds >= 0.2) and nz 24/32 | same | <= quoted |
| B:B7 | HTnpBasisErr (N <= 20 part) | 1e-6 | max \|blind - dens16\| at N = 12, 16, 20 (consistent) | same | <= quoted |
| B:B8 | (note) | 3e-7 | max \|C2 fit - exact C2(N)\| over N = 0..16, raw and consistent | indep_results.json (C2_fits) | <= quoted |

Record integrity and code binding (rows A:R1-R7, A:W1, A:A0-A4, A:I0, B:B1-B3) are listed in the replay tables. Not quoted from these packages but used in the paper: the MC and resummed columns of Table tab:num1 and the MC comparison (Resummation and MC folders). The paper quotes no core-hours; the d = 1 cost, about 2.1x10^4 core-hours (prod1-7 1.06x10^4 + dens_v1 about 1.0x10^4, from sacct), is in code/lri_dressed_phi4_hpc/REPRODUCE.md.

### `lri_dressed_phi4_hpc_analysis`

Folder: `code/lri_dressed_phi4_hpc_analysis/`.

_Same text as under `lri_dressed_phi4_hpc` above; the package ships an identical copy._

### `lri_dressed_phi4_independent_check`

Folder: `code/lri_dressed_phi4_independent_check/`.

_Same text as under `lri_dressed_phi4_hpc` above; the package ships an identical copy._

## d = 2: dressed-window Hamiltonian truncation

### `lri_2d_window_hpc`

Folder: `code/lri_2d_window_hpc/`.

#### d = 2 finite-coupling HT: every quoted number, its record, command and tolerance

Paper (final text, paper/ at commit a6772872, 2026-10-19; the research notes form the Supplemental Material):
- Sec. Results, subsection "Nonperturbative results" (sec: nonpert): the d = 2, 3 sentence of the paragraph
  "Hamiltonian truncation" (N = `\HTnpDtwoNmax`, too few cutoffs to extrapolate, finite-cutoff values) and Fig.
  fig:cmp2d3d (set in subsection "Resummation", sec: resum; left panel, green squares; open at Δσ = 0.125, 0.126, where
  the largest cutoff is smaller);
- Sec. Results, subsection "Comparison" (sec: compare): "Hamiltonian truncation at finite cutoff lies above the curve by
  up to about 1% at 0.175 ≤ Δσ ≤ 0.3". Our side is `largest_N.csv` (d2.largest_N); the resummed curve and the ~1% are
  not checked here (they belong to the resummation/comparison export);
- Supplemental Material, front matter "AI agents and reproducibility" (paper/supplement/ai_front.tex; the paper's Sec.
  AI moved there), item "Independent recomputation": "the Hamiltonian-truncation solvers"; the d = 2 solver is
  `lri_2d_window_indep` (checks i2.*; written with the production code at hand, not blind);
- Appendix "Numerical results" (app: numerics), Table tab:num2, column "HT, N = `\HTnpDtwoNmax`": the 13 values of
  `largest_N.csv` rounded once to five decimals, in brackets at Δσ = 0.125, 0.126 (N = 22), and the caption's "at
  N = 24 the tuning conditions have no solution there" (d2.no_root). Checks d2.largest_N, d2.num2, d2.Nmax, d2.no_root.
  The other two columns (MC, resummed) are not ours.
The paper prints no other d = 2 HT number. The finite-N behaviour (`\HTnpDtwoConvStep`, `\HTnpDtwoMonoSteps`,
`\HTnpDtwoMonoShrink`, `\HTnpDtwoFallSmall`, `\HTnpDtwoFallLarge`, `\HTnpDtwoFold`), printed until 827a27bf in Table
tab:htnp23, and `\HTnpDtwoCfourLog`, `\HTnpDtwoIndep`, `\HTnpDtwoIndepL`, `\HTnpDtwoNoRoot` are still defined in
numbers.tex but not printed; those rows, and the rows marked "HT note only", are quoted in the HT note only.

Cutoff: the paper's N is the bath level cutoff `L` of the code and the records (`L<N>_z<nz>.json`). Δσ = x in the code; ε = 2s − 2 = 2 − 4Δσ.

Commands run from `HT/code/<package>`:
- `R` = `make -f public.mk replay` in `lri_2d_window_hpc` (public/replay_d2.py);
- `I` = `make -f public.mk replay` in `lri_2d_window_indep` (public/replay_indep.py).
Each prints its check name and PASS/FAIL. Status words follow the paper: **finite-N** values are values of the truncated
model at that cutoff, not continuum values; no d = 2 extrapolation is quoted.

| Result (check name) | Paper macro / place | Quoted value | Recomputed from | Command | Tolerance | Status |
|---|---|---|---|---|---|---|
| d2.records.* | (integrity) | 348 records; self-hash, gates, source hash c16207e2… = shipped code 889a968 | `data/HT_2d/prod1/chains/*/L*_z*.json` | R | exact | — |
| d2.points | (integrity) | `results/HT_2d/prod1/points.csv` = records | points.csv vs records | R | exact | — |
| d2.Nmax | `\HTnpDtwoNmax` (Sec. nonpert; Table tab:num2, header and caption) | N = 24 (22 at Δσ = 0.125, 0.126); N = 8, 10, …, 24 | records (nz = 16, main) | R | exact | finite-N |
| d2.conv_step | HT note only (`\HTnpDtwoConvStep`, not printed) | last step (N 22→24) ≤ 2.6e-6 at Δσ ≥ 0.45 (largest 2.536e-6 at 0.45) | records | R | bound | finite-N |
| d2.mono.rises | HT note only ("0.25–0.4 rises") | every step > 0 at 0.25, 0.3, 0.35, 0.4 | records | R | sign | finite-N |
| d2.mono_steps | HT note only (`\HTnpDtwoMonoSteps`, not printed) | last steps (0.6–4.3)e-4 at 0.25–0.4 (5.86e-5 … 4.30e-4) | records | R | 2 significant digits | finite-N |
| d2.mono_shrink | HT note only (`\HTnpDtwoMonoShrink`, not printed) | steps shrink by 8 to 16 % per step (15.6, 13.5, 11.3, 7.7 % at 0.25 … 0.4) | 1 − geometric mean of the last four step ratios | R | nearest integer | finite-N |
| d2.nonmono_0.2 | HT note only ("0.2 not monotone") | sign change of the steps at Δσ = 0.2 | records | R | sign | finite-N |
| d2.fall | HT note only ("0.125–0.175 falls; steps do not shrink") | steps < 0 from N = 10 on; last ≥ previous in size | records | R | sign, ratio ≥ 1 | finite-N; method fails here (caveat) |
| d2.fall_small | HT note only (`\HTnpDtwoFallSmall`, not printed) | 1.0e-3 (last step, Δσ = 0.175, N 22→24: −1.046e-3) | records | R | 2 significant digits | finite-N |
| d2.fall_large | HT note only (`\HTnpDtwoFallLarge`, not printed) | 2.0e-2 (last step, Δσ = 0.125, N 20→22: −2.022e-2) | records | R | 2 significant digits | finite-N |
| d2.largest_N | Fig. fig:cmp2d3d, left panel, green squares (filled N = 24; open N = 22 at Δσ = 0.125, 0.126); Table tab:num2 (via d2.num2); our side of the Comparison "about 1%" sentence | 13 values of Δ_E at the largest N | `results/HT_2d/prod1/largest_N.csv` vs records | R | exact | finite-N, not continuum |
| d2.num2 | Table tab:num2, column "HT, N = 24": 0.94003 and 0.94568 in brackets (N = 22; Δσ = 0.125, 0.126), then 0.96203, 0.99023, 0.99972, 0.99530, 0.97771, 0.96349, 0.95782, 0.96179, 0.97528, 0.98581, 0.99678 (Δσ = 0.135 … 0.495) | the 13 cells | `largest_N.csv`, rounded once to five decimals (half up); brackets ⇔ N = 22 | R | exact after rounding | finite-N, not continuum |
| d2.nz.z20, d2.nz.z12 | HT note only: zero-mode basis convergence | max abs(nz20 − nz16) = 9.4e-11; max abs(nz12 − nz16) = 5.2e-7 | records | R | ≤ 1e-10; ≤ 6e-7 | — |
| d2.no_root | Table tab:num2, caption: "at N = 24 the tuning conditions have no solution there" (Δσ = 0.125, 0.126) | f1 > 0 on f2 = 0 at all 6 θ0, both Δσ (min 1.60e-3) | `results/HT_2d/valley_N24/*.json` | R | sign | FINAL for the truncated model at N = 24 on the scanned range θ0 ∈ [12.5, 15.5] |
| d2.valley.min | HT note only (`\HTnpDtwoNoRoot` defined, not printed) | quartic-fit minima of f1: 2.686e-3 (θ0 ≈ 14.03, Δσ = 0.125), 1.556e-3 (θ0 ≈ 14.06, 0.126) | valley JSONs | R | 1e-6 | — |
| d2.fold | HT note only (`\HTnpDtwoFold`, not printed) | fold at Δσ ≈ 0.1274 (N = 24) | linear extrapolation of the minimum in Δσ (saddle-node) | R | 5e-5 | estimate (two Δσ values; linearity assumed) |
| d2.valley.on_curve | (integrity) | abs(f2) ≤ 1e-9 at every recorded point; f1, f2 = stored energies | valley JSONs | R | 1e-9; 1e-12 | — |
| d2.pert_consistent.0.495 / .0.475 | HT note only (supports the C4 ln N statement) | Δ_E(N) − Padé[4/4] of the consistent C0..C8(N): ≤ 9.4e-12 (0.495), ≤ 7.6e-8 (0.475), N = 8…24 | records + `data/HT_2d/pert_crosscheck/consistent_C0_C8.csv` | R | ≤ 1e-11; ≤ 1e-7 | supporting check: the ε expansion of this model is the consistent scheme |
| `\HTnpDtwoCfourLog` | HT note only (`\HTnpDtwoCfourLog` = −0.027, defined, not printed) | ln N coefficient of C4(N), consistent scheme: −365/(4374π) = −0.02656 | **HT_Pert** (exact C4(L) to L = 2000) | `make -f public.mk replay` in `HT_Pert/code/lri_2d_coeff_independent_check`, check `p2.c4_log_consistent` | — | FINAL (HT_Pert) |
| i2.outputs, i2.bind | (integrity) | 155 outputs, 0 failures; 465 embedded production values = shipped records | `results/HT_2d/independent_check/out_sym/*.json` | I | exact | — |
| i2.dE.N12_16 | HT note only (`\HTnpDtwoIndep`, not printed); Supplemental Material front matter, "Independent recomputation", "the Hamiltonian-truncation solvers" | 1.4e-12: independent − production Δ_E, every Δσ, N = 12 and 16, K ≥ 32 | out_sym | I | 2 significant digits | verified (the model is computed correctly) |
| i2.levels.N12_16 | HT note only | five even, five odd levels and E_v(M) ≤ 1e-11 (7.6e-12) | out_sym | I | ≤ 1e-11 | — |
| i2.dE.N18, i2.dE.N20 | HT note only | 4.5e-12 (N = 18, Δσ ≤ 0.15), 4.6e-11 (N = 20, Δσ ≤ 0.175), K ≥ 32 | out_sym | I | ≤ 5e-12; ≤ 5e-11 | — |
| i2.dE.N22 | HT note only (`\HTnpDtwoIndepL`, not printed) | 4.4e-10 (Δσ = 0.125), 4.0e-10 (0.126), N = 22, K = 32 | out_sym | I | 2 significant digits | limited by K = 32 (differences grow ~9× per step with one sign) |
| i2.retune.* | HT note only | re-tuned roots from shifted seeds: ≤ 9e-11 (N ≤ 12), 3.6e-8 (N = 16, K = 24 limited) | out_sym | I | ≤ 1e-10; ≤ 4e-8 | — |

Paper history: the wording notes of 2026-10-13 were applied by Draft on 2026-10-14 (`\HTnpDtwoConvStep` = 2.6×10⁻⁶,
"≤ 2.6×10⁻⁶"; `\HTnpDtwoMonoShrink` = "8 to 16"). Table tab:htchecks, which printed `\HTnpDtwoIndep` "(N = 12, 16)", was
removed when the paper was restructured on 2026-10-14; Table tab:release was gone (comments only) when paper/ entered the
repository on 2026-10-15 (0f43fa14). Commit 827a27bf (2026-10-16)
replaced Table tab:htnp23, which printed the finite-N behaviour, by Table tab:num2, which prints the largest-N values
(new check d2.num2; the Resummation replay checks the same cells against `largest_N.csv`). In the final text a6772872
(2026-10-19) the d = 2 statements, the 13 cells, the caption and the plotted points are unchanged; Sec. AI moved to
the Supplemental Material front matter and Fig. fig:cmp2d3d to subsection "Resummation".

### `lri_2d_window_indep`

Folder: `code/lri_2d_window_indep/`.

_see the first section of this dimension (one text for the dimension)._

## d = 3: dressed-window Hamiltonian truncation

### `lri_3d_window_hpc`

Folder: `code/lri_3d_window_hpc/`.

#### d = 3 finite-coupling HT: every quoted number → record, command, tolerance

Scope: every d = 3 finite-coupling Hamiltonian-truncation number in the paper and in the HT note's d = 3 sections.
In the paper (main.tex, final text at commit a6772872):
- Table `tab:num3`, column "HT, N = 20", in Appendix "Numerical results" (`app: numerics`; `sections/app_numerics.tex`):
  ΔE at N = 20 for all 15 Ds (row NUM3);
- Fig. `fig:cmp2d3d`, right panel, green squares, in Sec. Results, subsection "Resummation" (`sec: resum`;
  `sections/resummation.tex`);
- the text of Sec. Results, subsection "Nonperturbative results" (`sec: nonpert`; `sections/nonperturbative.tex`),
  which gives the largest cutoff (row NMAX).

The paper uses two d = 3 macros of `numbers.tex`, `\HTnpDthreeNmax` and `\HTnpDthreeSR` (the Table `tab:num3` entry at
Ds = 0.518149). It prints the other 14 entries of the HT column of Table `tab:num3` as numbers. Rows marked "note:"
are quoted only in the HT note. Where such a row names a macro, `numbers.tex` still defines it, but the paper does not
use it. The check id is the row name in `make replay` and in the note's reproduction table.

Paths are relative to `HT/`. Records: `data/HT_3d/campaigns/<campaign>/results/<group>/x<Ds>/window_L<N>.json`
(campaigns `grid18` and `grid18sri` for N = 8–18, `grid20`, `grid20sri` and `l20x06` for N = 20). Commands run from
`code/lri_3d_window_hpc` (`make -f public.mk replay`) or `code/lri_3d_window_indep`, or from `HT/` as
`make replay`.

| check id | quoted (macro) | value | records | command | tolerance / rule |
|---|---|---|---|---|---|
| REC-MANIFEST, REC-RECORDS, REC-SRC | (integrity) | 105 records, 1 source hash | all `window_L*.json` of the table, `data/HT_3d/MANIFEST.sha256` | `make -f public.mk replay` | every file's sha256 as listed; `record_sha256` = sha256 of the record's canonical JSON; accepted; tuning residual ≤ max(1e-10, 5·3e-11); eigenpair residual ≤ 1e-8; measured Δσ = Ds and Δφ³ = 3 − Ds to 1e-9; the seed and basis inputs named in each record are the shipped files (sha256); every record's `source_sha256` equals `ht3d.hpc.source_hash()` of the shipped `code/` |
| TABLE | the note's Table d3:finiteN; its N = 20 row is plotted in Fig. `fig:cmp2d3d` (green squares) and printed in Table `tab:num3` (row NUM3) | ΔE(Ds, N), 15 Ds × N = 8…20 | the 105 records | `make -f public.mk replay` | rebuilt `finite_L_table.csv` identical, byte for byte, to `results/HT_3d/finite_L_table.csv` |
| CONFIG | note: teacher N_t = 6 with 24 states per parity of a 192-level oscillator, 20 kept; n_z = 16; tuning tolerance 3e-11; bath-state limits 1e7 (N = 16), 5e7 (18), 2e8 (20) | as stated | the 15 `teacher_L6.json` and the 105 window records (`configuration`, `basis_input.retained`) | `make -f public.mk replay` | exact |
| SIZE | note: J = 0 inversion-even bath states 110, 371, 1285, 4486, 15 815, 55 859, 196 585 at N = 8 … 20 | same | window records: `dimension` / (2 · `nz_per_parity`) | `make -f public.mk replay` | exact, the same at every Ds |
| PROJECTOR | note: gesdd → gesvd fallbacks in 8 of 17 335 blocks (N = 18) and 62 of 40 033 (N = 20); max \|J₊Q\| = 5.8e-15 | same | `scalar_projector_checks` of the N = 18, 20 records | `make -f public.mk replay` | exact counts; residual < 1e-14 |
| COST-L18 | note: N = 18 point (J = 1 diagnostics, 16 cores) 34–74 min, 38.5 GiB | same | window_L18 records (`elapsed_total_seconds`, `peak_rss_kib`) | `make -f public.mk replay` | integer minutes; 0.1 GiB |
| NMAX | `\HTnpDthreeNmax` = 20 | 20 | 15 × `window_L20.json` | `make -f public.mk replay` | largest N with an accepted record at all 15 Ds; exact |
| NUM3 | Table `tab:num3`, column "HT, N = 20": 1.41924 (`\HTnpDthreeSR`), 1.41951, 1.42026, 1.42182, 1.42435, 1.42923, 1.43511, 1.44218, 1.45062, 1.46053, 1.47192, 1.48486, 1.49360, 1.49674, 1.49993 at Ds = 0.518149 … 0.7499 | ΔE(Ds, 20) | 15 × `window_L20.json` | `make -f public.mk replay` | each ΔE(Ds, 20) rounded to 5 decimals equals the printed value |
| CONV-STEP | note: last step < 10⁻⁷ at Ds ≥ 0.74 (`\HTnpDthreeConvStep`) | 7.34e-8 | `window_L18`, `window_L20` at Ds = 0.74, 0.745, 0.7499 | `make -f public.mk replay` | max \|ΔE(20) − ΔE(18)\| < 1e-7 |
| MONO-STEPS | note: (2.2–6.1)×10⁻⁴ (`\HTnpDthreeMonoSteps`) | 2.218e-4 (0.625) … 6.073e-4 (0.518149) | `window_L18`, `window_L20` at 0.518149 ≤ Ds ≤ 0.625 | `make -f public.mk replay` | min and max of ΔE(20) − ΔE(18) to 2 significant digits |
| MONO-RISE | note: "rise monotonically" | strictly increasing, N = 8…20 | `window_L8`…`window_L20` at 0.518149 ≤ Ds ≤ 0.625 | `make -f public.mk replay` | every step positive |
| MONO-SHRINK | note: 8 to 19 percent (`\HTnpDthreeMonoShrink`) | 7.6 % (0.625) … 18.6 % (0.518149) | `window_L16`, `L18`, `L20` at 0.518149 ≤ Ds ≤ 0.625 | `make -f public.mk replay` | 100·(1 − d₂₀/d₁₈), dₙ = ΔE(N) − ΔE(N−2), min and max rounded to integers |
| NO-SHRINK | note: at 0.65 and 0.675 "the steps do not yet shrink" | d₂₀/d₁₈ = 0.992 (0.65), 1.225 (0.675) | `window_L16`, `L18`, `L20` at 0.65, 0.675 | `make -f public.mk replay` | d₂₀/d₁₈ > 0.99 at both |
| SR-L20 | `\HTnpDthreeSR` = 1.41924 (Table `tab:num3`); note: 1.41924, "still rises" | 1.41924372 | `grid20sri/.../x0.518149/window_L20.json` | `make -f public.mk replay` | ΔE(20) at Ds = 0.518149 to 5 decimals; d₂₀ > 0 |
| SR-GAP | note: "6.6×10⁻³ above the Ising value" | 6.618e-3 | the same record; Ising ΔE = 1.41262528 (cited) | `make -f public.mk replay` | 2 significant digits |
| BP-0.7 | note: continuum 1.47214(3) at Ds = 0.7 (`\HTnpDthreeBPerr` = 3×10⁻⁵) | 1.4721437 ± 2.9e-5 (29 approximants) | C₀…C₇ of d = 3 (main.tex Table `tab:pt`, Sec. Results, subsection "Around the generalized free field"; records in the GFF folder), in `public/bp_x07.py` | `make -f public.mk replay` (or `python3 public/bp_x07.py --x 0.7`) | median 1.4721437 to 1e-7; half-spread (max − min)/2 to 1 significant digit; n = 29 |
| BP-DEV | note: 2.2×10⁻⁴, "lies below it" and "moves away" (`\HTnpDthreeBPdev`) | 2.189e-4 | BP-0.7 and `grid20/.../x0.7/window_L20.json` (plus `grid18/.../x0.7/window_L16`, `L18`) | `make -f public.mk replay` | BP(0.7) − ΔE(0.7, 20) to 2 significant digits; ΔE(16) > ΔE(18) > ΔE(20), all below BP |
| C4-RATIO | note: 60 % (`\HTnpDthreeCfourRatio`) | 60.26 % | C₄ of the consistent window at L = 20, 0.7400078407, from `HT_Pert` (package `lri_ht3d_pert`, `results_expanse_2026-10/SUMMARY.md`), over C₄(3) = 1.228063545 | `make -f public.mk replay` (reads `../../../HT_Pert/results/HT_3d/SUMMARY.md`; set `PERT_SUMMARY=` to another copy) | ratio rounded to an integer percent; SKIP if the HT_Pert record is absent (the number is then replayed in HT_Pert only) |
| INDEP-TUNED | note: 2×10⁻¹¹ at N ≤ 12 (`\HTnpDthreeIndep`) | 1.89e-11 | `code/lri_3d_window_indep/results/cmp_*.json` (23 comparisons, N = 8, 10, 12) | `make -C code/lri_3d_window_indep -f public.mk replay` | max \|ΔE(indep, tuned) − ΔE(production)\| to 1 significant digit |
| INDEP-FIXED | note: "at the production couplings to at most 1.8×10⁻¹², with 16 or 24 local states" | 1.8e-12 | same | same | max over K = 16 and 24 at the production couplings ≤ 3e-12 |
| INDEP-RESID, INDEP-PKG | (integrity) | resid ≤ 9.5e-13 | same, plus the production records | same | every independent tuning converged to ≤ 1e-12; the production (r, g, ΔE) that each comparison used equal the shipped records and `indep_extract.json` exactly |
| COST-L20 | note only: "27–104 min and 84–87 GiB per N = 20 point; 239 min and 328 GiB at Ds = 0.6 with J = 1 diagnostics" | same | the 15 `window_L20.json` (`elapsed_total_seconds`, `peak_rss_kib`) | `make -f public.mk replay` | rounded to integer minutes and GiB |
| — | note: Ising value 1.41263 (`\HTnpDthreeSRexact`) | 1.41262528(29) | literature (bootstrap: Chang et al. 2024; Simmons-Duffin 2016) | not replayed | cited input; 1.41262528, the value SR-GAP uses, rounds to 1.41263 |

Not replayed here, by design:
- the continuum coefficients C₀…C₇ of d = 3 (inputs of BP-0.7): GFF folder (`GFF/results/C6_3`, `C7_3`, closed forms
  in `GFF/code/LRI_C5_d3`);
- C₄(L = 20) of the consistent window (input of C4-RATIO): HT_Pert;
- the comparison of the N = 20 values with the CB8 resummation in Fig. `fig:cmp2d3d`, and the "Resummed" and "MC"
  columns of Table `tab:num3`: Resummation and MC folders. The Resummation replay also checks the HT column of
  Table `tab:num3` against the `window_L20.json` records.

### `lri_3d_window_indep`

Folder: `code/lri_3d_window_indep/`.

#### lri_3d_window_indep: quoted numbers

The rows INDEP-TUNED, INDEP-FIXED, INDEP-RESID and INDEP-PKG of `../lri_3d_window_hpc/results_map.md` (one d = 3
results map for both packages). The paper quotes no number from this package; the HT note quotes:

| check id | quoted | value | records | command | tolerance |
|---|---|---|---|---|---|
| INDEP-TUNED | note: 2×10⁻¹¹ at N ≤ 12 (`\HTnpDthreeIndep`, defined in `numbers.tex`, not used in the paper) | 1.89e-11 | `results/cmp_*.json` (23) | `make -f public.mk replay` | 1 significant digit |
