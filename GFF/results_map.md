# Where each GFF number comes from

Every quoted number: the record that holds it, the command that recomputes it, and the comparison tolerance.

Assembled from the package authors' texts. Inside a package section, relative paths are relative to that package's folder `code/<package>/` unless they start with `GFF/`. The values themselves are in `note/README.md` and the note.

- C0-C5 in closed form, d = 1: `lri_numerical_resolution`, `lri_psi_complete_update`, `lri_fixed_hypergeometric_update`
- C0-C5 in closed form, general d: `lri_general_special_functions_update`, `lri_general_closed_update`, `lri_general_periodization_update`
- Closed forms of L2, K2 and C5(2): `LRI_C5_d2_simplify`, `LRI_C5_d2_proof`
- d = 3 specialization and the generic-dimensional reduction of L_d, Z_d, K_d: `lri_d3_reduction_update`, `lri_d3_matrix_update`, `LRI_C5_general_d`, `LRI_C5_d3`
- C6(1) and its analytic representation: `LRI_C6_1D_HPC`, `C6_research_note`, `LRI_C6_closed_form_review`
- Finite kernels, power compensation, C6(2) and C6(3): `lri_C6_d2_complete_update`, `lri_C6_d3_complete_update`, `LRI_C6_D2_HPC`, `LRI_C6_D3_HPC`
- Full C7(1), C7(2), C7(3): `LRI_C7_HPC`, `LRI_C7_D2_HPC`, `LRI_C7_D3_HPC`
- Full C8(1), C8(2), C8(3) and the independent checks: `LRI_C8_HPC`, `LRI_C8_D2_HPC`, `LRI_C8_shared`, `LRI_C8_D2_HPC_optimized`, `LRI_C8_D3_HPC`, `LRI_C8_D3_OPT`

## C0-C5 in closed form, d = 1

### `lri_numerical_resolution`

Folder: `code/lri_numerical_resolution/`.

#### results_map: one-dimensional analytic C5 (note at fa71533)

Line numbers refer to the note at commit fa71533; the section numbers cited here are unchanged in the current
edition (01c3f5d, review of 15 October 2026), and so are all quoted values.

Paths are under `GFF/`. NR = `code/lri_numerical_resolution`, PSI = `code/lri_psi_complete_update`,
FIX = `code/lri_fixed_hypergeometric_update`; `make -C <pkg> -f public.mk <target>`. Every quoted string and its
rule is in `results/closed_forms_1/C5_1_quoted.json` (id in the last column). Rules: **digit** = |recomputed -
quoted| <= one unit in the last quoted digit; **exact** = integers, hashes, rationals, words equal; **10x** = an
observed residual passes if the recomputed one is at most ten times the quoted one (its last digits depend on the
platform; observed identical here). Record comparisons: regenerated vs shipped record, numbers to the stated
relative tolerance, everything else exact.

##### Closed-form values

| Quoted number | Note | Recomputed by (file -> target) | Rule | id |
|---|---|---|---|---|
| C5(1) = -731.13947662454 | Sec. 1 table l.101; Sec. 22.10 l.8364 | NR `verification/records/reference.json` (fresh, `audit.py --refresh-reference`) -> replay; PSI `verification/coefficient_values.json` -> test; FIX `public/sec11_closed_forms.py` -> test | digit | C5_1_table |
| C5(1) = -731.139476624539825853869126582527... | Sec. 14 l.2531 | same three | digit (1e-30) | C5_1_sec14 |
| C5(1) = -731.139476624539825853869126582527231 | Sec. 20.7 l.6916 (C62d's section) | same three | digit (1e-33) | C5_1_sec20 |
| C5(1) = -731.139476624..., -731.139477 | Sec. 20.8 l.6996; Sec. 27.9 l.10879 | same three | digit | C5_1_sec20_short, C5_1_sec27 |
| C5 to 55 digits | NR README | NR reference -> replay | digit (1e-52) | R_C5_55 |
| C5 to 53 digits | PSI README | PSI coefficient_values -> test | digit | R_C5_psi |
| C2(1) = 0.657131263981, C3(1) = -3.719856322902, C4(1) = 45.42488010356 | Sec. 1 table l.98-100; Sec. 22.10 | PSI coefficient_values -> test; FIX sec11 -> test | digit | C2_1, C3_1, C4_1 |
| K = 39.33156912825903905750318715159786152304... | Sec. 8 l.1136 | PSI coefficient_values (polygamma form) -> test, `numerical_checks.json` (endpoint master, 110 digits) -> replay; NR reference -> replay; FIX sec11 -> test | digit (1e-38) | K |
| P4 = 2229.5220610709419642945251997485... | Sec. 9 l.1452 | NR reference (mpmath 4F3(1), 80 digits) -> replay; FIX sec11 (70 digits) -> test; PSI (reused 240-digit F+-) -> test | digit (1e-28) | P4 |
| P5 = 28599.2931765621035366464770214... | Sec. 10 l.2215 | FIX `verification/fixed_hypergeometric_checks.json` (five values and Gamma quadrature, 100 digits) -> replay, sec11 -> test; NR reference (Gamma quadrature) -> replay; PSI (Gamma moment, 70 digits) -> test | digit (1e-25) | P5 |
| Gamma integral minus five-value P5 = 3.63e-121 at 125 digits | Sec. 10 l.2212-2213 | FIX record `higher_precision_control` -> replay | 10x | P5_gamma_minus_fixed_125 |
| the same, 3.6305549201712e-121; 9.3633527093844e-97 at 100 digits | FIX README | FIX record -> replay | 10x | R_P5_gamma_minus_fixed_125, _100 |
| endpoint master minus polygamma K = 6.387e-109; bilinear 2.673e-51; complex 1.39e-102; max C0..C5 residual 9.28e-69 | PSI README | PSI numerical_checks -> replay; complex_bilinear_130 and coefficient_values -> test | 10x | R_K_endpoint_resid, R_bilinear_50, R_complex_130, R_C0C5_max_resid |

##### Graph control (Section 14) and package report

| Quoted number | Note | Recomputed by | Rule | id |
|---|---|---|---|---|
| degree 22 span: -731.1394766245375925, +2.2334e-12 | l.2523 | NR `verification/records/resolution_audit.json` (`audit.py`) -> test | digit | graph_22_span(_resid) |
| degree 22 maxgap: -731.1394766245106192, +2.9207e-11 | l.2524 | same | digit | graph_22_maxgap(_resid) |
| degree 24 span: -731.1394766245391892, +6.3667e-13 | l.2525 | same | digit | graph_24_span(_resid) |
| degree 24 maxgap: -731.1394766245368057, +3.0201e-12 | l.2526 | same | digit | graph_24_maxgap(_resid) |
| N_lower = 32 | l.2518 | same (`lower_degree` of each case) | exact | graph_lower_degree |
| same-degree full vs combined channel < 1.7e-12 | l.2515-2516 | same (`C5_minus_scalar_control`, degree 18, max 1.688e-12) | strict bound | graph_same_degree_full_vs_combined |
| delta C5 = (5/729) delta H_{5,-1} | l.2505 | NR `exact_decimal_audit.json` (rational arithmetic) -> test | exact | graph_dC5_dH |
| 59,145 ordered graphs; 9,540 zero-weight graphs | l.2511-2512 | NR `graph_regeneration.json`, `enumeration_audit.json` -> replay | exact | graph_ordered, graph_zero_weight |
| 49,605 nonzero graphs, 335 exponent groups; 60 sectors, 342 groups, no a=-2 sector | NR README | same -> replay | exact | R_nonzero_graphs, R_exponent_groups |
| executed graph inputs SHA-256 | NR `verification/inputs/executed_graph_hashes.json` | `regenerate_graph_audit.py` -> replay | exact | - |
| degree-24 values to 26 digits, residuals 6.3666689095762e-13, 3.0201411349529e-12 | NR README | `resolution_audit.json` -> test | digit | R_24_* |
| old printed span -731.1394766152787; old minus closed +9.2611258538691265825e-9; budget closes | NR README | `resolution_audit.json` `error_budgets` -> test | digit; budget residual <= 1e-60 | R_old_* |
| degree-18 long-double control shift about -7.96e-9 | NR README | `resolution_audit.json` -> test | +-0.01e-9 | R_scalar18_shift |

##### Certificate and classes (Sections 4, 12, 13, Appendix A)

| Quoted statement | Note | Recomputed by | Rule | id |
|---|---|---|---|---|
| b4, c4, D5 remainder from the certificate; RG assembly = closed C5 | Sec. 4.2.3, 13 | NR `symbolic_audit.json` (SymPy) -> test; assembly minus closed form -1.1e-78 at 80 digits in `reference.json` -> replay | exact; <= 1e-70 | - |
| 26 four-loop and 92 five-loop certificate rows | Sec. 13; App. A l.12449 | NR symbolic_audit -> test; `public/graph_classes.py` -> replay | exact | classes_4loop_nonwheel, classes_5loop_certificate |
| 129 classes = 92 + 6 wheel insertions + 3 primitive + 28 zero-weight | Sec. 13 l.2483; App. A | NR `public/graph_classes.py` (new) -> replay | exact | classes_5loop* |
| wheel table: classes 51, 78, 99, 113, 124, 128 with words, Aut and d_G | Sec. 12 l.2316-2321 | same | exact | wheel_table |
| K proof steps and all C0..C5 / L rewritings | Sec. 4.2, 8 | PSI `symbolic_checks.json` -> test | exact | - |
| Barnes kernel R(s) = -128C + ... + 192DC^5 | Sec. 10.4 (fp:eq:kernel) | FIX `public/kernel_identity.py` (new) -> test | exact | - |
| Y_2 9F8 = 8F7 form; Section 4 unreduced C5 = Section 1.1 form | Sec. 4.1, 4 | FIX sec11 -> test | <= 1e-60 at 70 digits | - |

##### Record comparisons (regenerated vs shipped)

| Record | Target | Tolerance (relative to max(1,|x|)) | Observed |
|---|---|---|---|
| NR symbolic_audit, exact_decimal_audit, graph_regeneration, enumeration_audit | test/replay | exact | identical (graph_regeneration: only elapsed time differs) |
| NR resolution_audit (saved and fresh reference), lower_controls, reference | test/replay | 1e-55 (80-digit records) | deviation 0 |
| PSI symbolic_checks / coefficient_values / complex_bilinear_130 / numerical_checks | test/replay | exact / 1e-55 / 1e-90 / 1e-45 | deviation 0 |
| FIX fixed_hypergeometric_checks | replay | 1e-85 | deviation 0 |
| checksum lists (NR, FIX `sha256_manifest.json`; PSI `public/bundle_sha256.txt`) | test | sha256 exact, not-exported files skipped | 39/76, 5/98, 14/24 verified |

### `lri_psi_complete_update`

Folder: `code/lri_psi_complete_update/`.

_same as the section above (one text for the whole unit)._

### `lri_fixed_hypergeometric_update`

Folder: `code/lri_fixed_hypergeometric_update/`.

_same as the section above (one text for the whole unit)._

## C0-C5 in closed form, general d

### `lri_general_special_functions_update`

Folder: `code/lri_general_special_functions_update/`.

#### Results map: general-d C0..C5 (note git fa71533; paper at f496d39a: Table tab:pt of `sections/perturbation.tex`, formulas of `sections/app_closed_forms.tex`)

Paths are relative to `GFF/code/<package>/`. "replay" = `make -f public.mk replay` of that package; expected values in
`GFF/results/closed_forms_general/C0_C5/expected.json`. Status: result of the replay in the mock public layout on macOS
(2026-10-13, two Python environments; see `requirements.txt`).

##### Owned by this unit

| Quantity | Value as quoted | Where quoted | Package | Record, field | Recomputed by | Tolerance | Status |
|---|---|---|---|---|---|---|---|
| C0..C3(d) | d/2, -1/6, A/9, (A^2+R-8Q)/108 | note gd:C03 l.2614-2618, gs:C0C4 l.3184-3188, Sec 1.1 l.183-187; paper eq. cf:gd-C03 (app_closed_forms.tex l.40) | special | `verification/symbolic_checks.json` `checks.C1`, `C2`, `C3` (residuals), `all_exact` | `python3 code/symbolic_checks.py --output X` (in a copy) | residual exactly "0"; record byte-identical | PASS |
| b3, c3 | gd:bc3 | note l.2623-2627 | special | `verification/general_special/exact_checks.json` `b3`, `c3` | `sum4.py`, `sum5.py`, `exact_audit.py` | SymPy-equal to the note's formula | PASS |
| 648 C4(d) = 16P4 - A^3 - 8AQ - 3AR + 53U/2 - 3V | formula | note gs:C0C4 l.3184-3188, Sec 1.1 l.183-187; paper: in the Supplemental Material (Part I, Sec. 1.1), not in the paper body | special | `exact_checks.json` `C4` | same | SymPy-equal; record byte-identical | PASS |
| 46656 C5(d) = ... | formula | note gs:C5 l.3189-3194, Sec 1.1 l.188-193; paper: in the Supplemental Material (Part I, Sec. 1.1), not in the paper body | special | `exact_checks.json` `C5` | same | SymPy-equal; record byte-identical | PASS |
| b4, c4, D4, D5 | formulas | note gs:b4 l.3226-3228, gs:c4 l.3229-3231, gs:D4 l.3232-3234, gs:D5 l.3238-3244 | special | `exact_checks.json` `b4`, `c4`, `D4`, `D5` | same | SymPy-equal | PASS |
| d = 1 specialization, mass-Gamma cancellation, K subtraction | true | note Sec 13.1-13.2 | special | `exact_checks.json` `checks.*` | `exact_audit.py` (asserts) | all true | PASS |
| C4(2) | 5.048868431 | note Sec 1 table l.100, Sec 13.7 l.3778; `\CfourTwo` | special | `verification/general_special/coefficient_values_new.json` row d=2, spins=512, `coefficients[4]` = 5.0488684313554110686 | `assemble_results.py` (from `spectral_master_values.json`) | record rounded to 9 decimals = printed; record byte-identical; margin to the rounding boundary 1.4e-10 vs drift 3.1e-12 from regenerated masters | PASS |
| C5(2) | -38.833645896 | l.101, l.3778; `\CfiveTwo` | special | same row, `coefficients[5]` = -38.833645896225706749 | same | same; margin 2.7e-10 | PASS |
| C4(3) | 1.228063545 | l.100, l.3779; `\CfourThree` | special | row d=3, spins=512, `coefficients[4]` = 1.2280635453277584416 | same | same; margin 1.7e-10 | PASS |
| C5(3) | -5.850351421 | l.101, l.3779; `\CfiveThree` | special | row d=3, spins=512, `coefficients[5]` = -5.8503514207515487491 | same | same; margin 2.5e-10 | PASS |
| C2(2), C3(2) | 0.308065413582, -0.874850012653 | Sec 1 table l.98-99; `\CtwoTwo`, `\CthreeTwo` | special | row d=2, `coefficients[2]`, `[3]` | same | rounded = printed (exact polygamma / exact Q2) | PASS (owner proposed, see note_changes / open decisions) |
| C2(3), C3(3) | 0.181221785406, -0.353581520433 | l.98-99; `\CtwoThree`, `\CthreeThree` | special | row d=3, `coefficients[2]`, `[3]` | same | rounded = printed; C3(3) margin 3.0e-13 vs drift 6e-14 | PASS (owner proposed) |
| Q2 = Gamma(1/4)^8/(24 pi^4) | 12.7713811986469576577497636845240084220372849859347... | note gc:Q2number l.3802 (gc:Q2, Sec 1.1); paper: closed form in eq. cf:d123-blocks, digits not printed in the paper at f496d39a (were app_closed_forms l.263, 29 decimals) | closed | `verification/general_closed/identity_checks.json` `Q2.gamma_ratio` | `python3 code/general_closed/check_new_identities.py` | rounded to the printed 49 decimals = printed; record byte-identical; |record - Gamma form| <= 1e-55 | PASS |
| Z2 = 4 G Q2 | identity | note gs:Z2exact | closed (and special, d=2 row `Z`) | `identity_checks.json` `Z2`; `coefficient_values_new.json` d=2 `Z` | same; `assemble_results.py` | <= 1e-55 (closed), <= 1e-30 (special record, 35 digits) | PASS |
| Horn values of L_d, Z_d, K_d | 244, 318, 386; at most 6 variables | note Sec 14.6 table l.4222-4224 | closed | `verification/general_closed/horn_arrays/summary.json` `functions`, `max_variables` | `python3 code/general_closed/horn_compiler.py --out DIR` | exact; arrays decompressed byte-identical | PASS |
| Horn values of Q, P4, P5a, P5b; totals | 20, 56, 6024, 9036; 16084 values, 450409 parameter rows | package README (not the note) | closed | `summary.json`; `array_manifest.json` `functions`, `parameter_rows` | full compiler (`test`) | exact | PASS (replay reads the records; regeneration of P5a/P5b in `test`) |
| P4(2) | 250.48731558186728553185175688791140716835571092358... | note Sec 14.2 l.3895; paper: closed form eq. cf:d2-P, digits not printed in the paper at f496d39a (were l.304, 25 digits) | periodization | `verification/general_periodization/d2_inherited_periods.json` `P4` | `check_two_dimensional.py` -> `check_d2_control.py` -> `check_d2_inherited_periods.py` | rounded = printed; records byte-identical (timing aside) | PASS |
| P5(2) | 1548.082640233120615132439... | note 953aa45 l.4341 (30 digits) and l.4552 (50 digits); paper: eq. cf:d2-P, digits not printed in the paper at f496d39a (were l.304) | periodization | `d2_inherited_periods.json` `P5` | same | rounded = printed | PASS |
| P4(2), P5(2) quadratics vs independent 70-digit d=2 values | 6e-59, 2e-58 | package README | periodization | `d2_inherited_periods.json` `P4_difference`, `P5_difference` | same | <= 1e-55 | PASS |
| (B_{7,0..6}) at q = 1/2 | pi^6 (20,0,28,0,84,0,924) | note Sec 15.5 l.4826 | periodization | `verification/general_periodization/exact_algebra.json` `B7_over_pi6` | `check_exact_algebra.py` | exact | PASS |

##### Cross-checks (values owned by other units)

| Quantity | Owner and source | Compared with | Tolerance | Observed |
|---|---|---|---|---|
| C4(2), C5(2) closed forms (paper eqs. cf:d2-C04, cf:d2-C5 and Table tab:pt `\CfourTwo`, `\CfiveTwo`; note l.3915) | closed_forms_2 | special: `coefficient_values_new.json` d=2; periodization: closed forms evaluated with this P4(2), P5(2) | 1e-11 (special); printed 25 digits (periodization) | 5.6e-13, 3.5e-13; exact to 25 digits |
| L2, K2 (note l.3896-3897) | closed_forms_2 | special d=2 masters `L`, `K`; periodization -2 log2 P4(2) | relative 1e-11; printed 50 digits | 2.2e-13, 4.1e-13; exact to 50 digits |
| C3(2) closed form (paper Table tab:pt `\CthreeTwo`, eq. cf:gd-C03 with cf:d123-blocks) | published | special d=2 `coefficients[3]` | 1e-24 | 2.4e-27 |
| C4(3), C5(3) to 50 digits (note l.390; the paper prints `\CfourThree`, `\CfiveThree` in Table tab:pt) | C63d | special d=3 coefficients | 1e-11 | 1.4e-13, 2.2e-13 |
| Q3, P4(3), P5(3), K3, L3, Z3 (note l.6062-6064, l.7538; L3, Z3: note 953aa45 l.4348, l.4351; not printed in the paper at f496d39a) | C63d | special d=3 masters | relative 1e-11 | 3e-14 to 2.1e-13 |
| C0..C5(1) (note Sec 1 table) | C71d | special d=1 row (general formula with the d=1 periods) | printed digits | exact |
| graph rows 26 + 92 + 6 + 3 + 28 (note App. A l.12449) | C71d (d=1 certificate) | special `exact_checks.json` `graph_rows` | exact | equal |

### `lri_general_closed_update`

Folder: `code/lri_general_closed_update/`.

_same as the section above (one text for the whole unit)._

### `lri_general_periodization_update`

Folder: `code/lri_general_periodization_update/`.

_same as the section above (one text for the whole unit)._

## Closed forms of L2, K2 and C5(2)

### `LRI_C5_d2_simplify`

Folder: `code/LRI_C5_d2_simplify/`.

#### Results map: d = 2 closed forms of L2, K2 and C5(2)

The note is at HEAD fa71533; line numbers refer to `long_range_ising_condensed.tex`. Paper at f496d39a: `numbers.tex`, Table tab:pt (`sections/perturbation.tex`), the formulas of `sections/app_closed_forms.tex`
and `sections/app_closed_forms.tex`.

Commands:
- S = `make -C GFF/code/LRI_C5_d2_simplify -f public.mk replay`
- P = `make -C GFF/code/LRI_C5_d2_proof -f public.mk replay`

Status:
- PASS: verified 2026-10-13 in the mock public layout (Python 3.10.11, mpmath 1.2.1, sympy 1.11.1; replay also with
  mpmath 1.3.0 and 1.4.1).
- "rounding": correct rounding at the printed digits, from an 80-digit evaluation.

##### Owned by closed_forms_2

| Number (location) | Value | Source: file, field | Command | Tolerance | Status |
|---|---|---|---|---|---|
| C5(2), Sec 1 table (l.101), Sec 16.7 table (l.3778), `\CfiveTwo` (numbers.tex l.39; Table tab:pt, perturbation.tex l.24) | -38.833645896 | closed form `gc:C5twoClosed` (`public/closed_forms_d2.py`); owned value `results/closed_forms_2/closed_forms_2.json` `values_70_digits.C5_2` | S | rounding | PASS |
| C5(2), l.3915 (25 digits; not printed in the paper at f496d39a, which gives the closed form eq. cf:d2-C5) | -38.83364589622536055293698… | same | S | rounding | PASS |
| C5(2): `gc:C5twoClosed` = `gc:d2coefficients` with L2, K2 inserted (l.3903-3907; l.3812-3818) | identity | `drafter/check_algebra.py` (exact) and an 80-digit evaluation | P (exact), S (numeric) | exact 0; numeric 1e-75 | PASS |
| L2 to fifty digits (l.3896) | -347.24915312320113105847678307522316920816760199487… | closed form; record `LRI_C5_d2_simplify/confirm_dps70.json` `checks.L2` | S | rounding; record vs closed form 1e-67 abs | PASS |
| K2 to fifty digits (l.3897) | 3.5181091385902522416490901703077395226226728094710… | closed form; record `checks.K2` | S | same | PASS |
| `gc:L2closed`: three forms; `gc:K2closed`: two forms (l.3830-3837) | identities | 80-digit evaluation | S | 1e-75 | PASS |
| 70-digit residual of `gc:L2closed` (l.3885) | 4.5x10^-69 | `confirm_dps70.json` `checks["L2+2log2*P4(=8pi^3ab)"]` = -4.5467e-69 | S: read, then re-assembled by the shipped `parallel_eval.py` from the 50 stored sums | string at 2 s.f.; re-assembled <= 1e-65 (sums stored at 70 digits) | PASS |
| 70-digit residual of `gc:K2closed` (l.3885) | 2.0x10^-70 | `checks["K2-(32G^2-28z3log2)"]` = -1.9999e-70 | S | same | PASS |
| Independent spectral residuals (l.3892) | 1.7x10^-79, 3.1x10^-62 | `GFF/code/LRI_C5_d3/wf_d2check/d2check_results.json` `L2_plus_2log2P4.run4`, `K2_minus_32G2_plus_28z3log2.run4` (C63d; sha256 pinned) | S | string at 2 s.f. | PASS |
| Single-sum closed forms vs 70-digit values (l.5144) | 3x10^-70 | `LRI_C5_d2_proof/L2_singlesums/check_vs_C62d_dps70.json` (largest of 4: 2.9e-70) | P: re-run, JSON byte-identical | string at 1 s.f. | PASS |
| Jets (`gc:L2taylor`) and chain (1/2)W'(1/2) = L2 (l.5145-5146) | 10^-82 | `review_L2_singlesums_numerics_r0/s3.log` (3 lines, max 1.54e-82) | P: read (Mathematica re-run in `replay-wl`) | order of magnitude | PASS |
| Generating functions and moments (l.5146-5148) | about 35 digits | `drafter/check_series.out` (G1-G3: 34.3-35.9 digits; moments 38.6-39.3) | P: read (`replay-wl` re-runs) | >= 34 digits | PASS |
| W4(2;2x) factorized vs spectral, x = 2/5, 1/2, 3/5 (l.5181-5182) | 2x10^-70 | `review_L2_structural_numerics_r0/spec_*.json` refitted by `public/spec_analyze_scaled.py`: 1.47e-71, 1.60e-70, 5.55e-71 | P: re-run (the shipped `spec_analyze.py` stops with a singular matrix) | string at 1 s.f. (largest, rounded up) | PASS |
| `gc:K2master` vs 2D y-quadrature (l.5444-5446) | 38 to 68 digits at seven tau | `review_K2_d1template_numerics_r0/logs/rC*.log` + `K2_d1template_fix1/composite_tau037.out` (tau 2/7: 68, 3/5: 58, 1/7, 3/10, 9/20, 1/2: 47, 37/100: 38) | P: read | exact digit counts | PASS |
| Star formula vs one-parameter representation (l.5446-5447) | 56 digits at fourteen points | `K2_d1template_fix1/check_lemma1_star.out` (min 55.9) | P: read | rounding | PASS |
| Twelve cell integrals vs 2I_j (l.5448-5449) | between 18 and 25 digits | `review_K2_selberg_numerics_r0/partA2_direct2d_0.3.out` (12 cells, 18.0-24.2) | P: read | range | PASS (the recorded range ends at 24; see note_changes.md, optional) |
| `gs:Ksubtraction` (independent spectral code) vs `gc:K2master` (l.5449-5450) | 54 digits at tau = 0.1, 0.23 | `review_K2_selberg_numerics_r0/spectral_hp55.out` (54.8), `spectral_hp55_023.out` (53.6) | P: read | rounding | PASS |
| pi^2[F(3/10)^2 + F(7/10)^2] (l.5453) | 47.790785413226103671… | mpmath 3F2 at 30 digits; `drafter/check_series.out` | P: recomputed | rounding; Mathematica value within 1e-27 | PASS |
| Twelve-term form vs closed form at tau = 3/10 (l.5451-5454) | 37 digits | `drafter/check_series.out` (37.3) | P: read | integer part | PASS |
| Machine checks cited: `verify_symbolic.py` (l.4899), `region_sum_matrix.py` (l.5295), `laurent_K2_sympy.py` (l.5390) | exact | the scripts' outputs (`verify_symbolic_report.json`, `.out`) | P (and `test`) | identical output | PASS |
| `laurent_K2.wl` (l.5391) | exact | `K2_selberg/laurent_K2.out` | `make -f public.mk replay-wl` (Mathematica) | identical result lines | not run here (CLUSTER_CHECKS.md) |

##### Cross-checks of numbers owned elsewhere (S, rows marked [cross-check])

| Number (location) | Owner | Value | Status |
|---|---|---|---|
| P4(2) to fifty digits (l.3895); the paper gives the closed form eq. cf:d2-P | `results/closed_forms_general/C0_C5` | 250.48731558186728553185175688791140716835571092358… | PASS |
| Q2 (l.3802); the paper gives the closed form in eq. cf:d123-blocks | same | 12.7713811986469576577497636845240084220372849859347… | PASS |
| P5(2), C3(2), C4(2) to 25 digits (not printed in the paper at f496d39a; P5(2): note 953aa45 l.4341); C3(2), C4(2) (Sec 1 table l.99-100; Table tab:pt `\CthreeTwo`, `\CfourTwo`) | same | 1548.082640233120615132439…; -0.8748500126526336895122636…; 5.048868431354847007612317… | PASS |
| C5(2) end to end (l.6917), C5(2) (l.6996) | `results/closed_forms_general/reduction_d` | -38.8336458962253605529369824675329232 | PASS |
| K2 = K_d at d = 2 (l.7612) | same | 3.5181091385902522416490901703077… | PASS |
| B+- (Euler-Maclaurin, `confirm_dps70.json`) vs mpmath 4F3(1) | — | 181.330506917…, 42.591509616… | PASS (1e-70) |
| C5(2) of `drafter/check_series.out` (Mathematica, 30 digits) vs closed form | — | -38.833645896225360552936982467533 | PASS (P) |

### `LRI_C5_d2_proof`

Folder: `code/LRI_C5_d2_proof/`.

_same as the section above (one text for the whole unit)._

## d = 3 specialization and the generic-dimensional reduction of L_d, Z_d, K_d

### `lri_d3_reduction_update`

Folder: `code/lri_d3_reduction_update/`.

#### Results map: the d = 3 research-bundle packages (C63d, 2026-10-13)

Every number or exact statement that the condensed note (`GFF/LRI_condensed_note/long_range_ising_condensed.tex` at
fa71533) quotes from these packages is listed below with its record, command, tolerance and reason. The column "SM"
names where the d = 3 paragraph of the paper's closed-form appendix (`paper/sections/app_closed_forms.tex`, App. A)
printed a number; that paragraph was removed on 2026-10-14. In the final paper (f496d39a) App. A keeps only A_3, R_3 and
the formula for Q_3 (eq. cf:d123-blocks and the sentence after it), and Table 1 of Sec. 3 prints C_2(3) ... C_5(3).

Commands run from `GFF/code/<package>`:
- `T` = `make -f public.mk test`;
- `R` = `make -f public.mk replay` (R includes T).

The quoted values with tolerances are in:
- `GFF/results/closed_forms_3/d3_specialization_quoted.json` (packages 1 and 2);
- `GFF/results/C6_3/power_compensation_quoted.json` (package 3).

Every row is checked twice: on the shipped record, and (T or R) on the record the original script writes again in
`.work/pkg/`. The local run on 2026-10-13 passed every row, and every rerun was bitwise equal to the delivered record.

##### 1. `lri_d3_reduction_update`: note section "Three dimensions: half-shift determinants and rank-two functions"

| quoted (note eq. / place) | SM | value | record | script | tolerance and why | cmd |
|---|---|---|---|---|---|---|
| Q_3 (values subsection) | cf:d3Q3, tab. cf:tab:d3 | 5.01710256455385536959085484569018… | `verification/general_d3/period_values.json`, run dps 90 | `verify_d3.py` | 10⁻³² (one unit in the last of the 33 shown decimals; the note truncates or rounds) | T, R |
| P_4(3) | tab. cf:tab:d3 | 62.0583279434066724664633885840967… | same | same | 10⁻³¹, same reason | T, R |
| P_5(3) | tab. cf:tab:d3 | 240.340317759083549816366546388004… | same | same | 10⁻³⁰, same reason (rounded up from …003598) | T, R |
| "formula and fresh Gamma-kernel integrations agree at about 10⁻⁵¹, 10⁻⁵², 10⁻⁵³" | text after tab. cf:tab:d3 | −1.47e−51, −1.53e−52, −2.41e−53 | `period_values.json` (90 digits) − `fresh_spectral.json` (60 digits); also stored in `comparison_summary.json` | `verify_d3.py`, `check_spectral.py` | "about 10^k" read as 10^(k−1) < \|r\| < 10^(k+1); equality with `comparison_summary.json` to 10⁻²⁰ relative (a difference of two stored strings) | T, R |
| changed-precision agreement (same sentence) | | 55 vs 90 digits: ≤ 1.6e−49 (P_5) | `period_values.json` | `verify_d3.py` | < 10⁻⁴⁸; the 55-digit run limits | T, R |
| Q_3 = 4π²𝔥₃(0) − Γ(1/4)¹⁰/(48π^{7/2}) (td:Qanswer) with 𝖷₃(0) = −2√2π^{3/2}𝔥₃(0) (td:zeroSamples) | cf:d3Q3; final paper: App. A after eq. cf:d123-blocks | exact identity; numerically 1.2e−79 | `exact_algebra.json` ("Q3 Gamma and Horn formula"); `period_values.json` | `check_exact.py`; replay formula | exact (SymPy); numeric < 10⁻⁷⁵ at 90 digits | T, R |
| P_4(3) formula (td:P4answer, td:P4data with 𝔟₄ in Gamma form) | cf:d3P4 | exact; numerically 8.6e−87 | `exact_algebra.json` ("P4 real-node formula"); `period_values.json` | same | exact; < 10⁻⁷⁵ | T, R |
| P_5(3) formula (td:P5answer, td:sevenE) | cf:d3P5 | exact; numerically 1.5e−84 | `exact_algebra.json` ("P5 normalization"); `period_values.json` | same | exact; < 10⁻⁷⁵ | T, R |
| quadratic rule (td:quadraticRule); odd coefficients (td:sevenOddCoefficients); even residue weight −32(9p₀+13p₁+22p₂) | | exact | `exact_algebra.json` | `check_exact.py` | exact | T |
| residue weights B_{r,k}/π^{r−1} (td:residueWeights) | | (8, −6√2, 12); (32, −24√2, 40, −40√2); (2624, …, 7392) | `exact_algebra.json` | `check_exact.py` | exact (SymPy) | T |
| a₃b₃ = Γ(1/4)¹⁰/(16√2π⁴), 𝔟₄ = Γ(1/4)⁶/(16π^{5/2}) (td:gammaAmplitudes) | | errors 1.4e−79, 5.2e−88 | `period_values.json` (gamma_product_error, Dougall_b4_error) | `verify_d3.py` | < 10⁻⁷⁵ at 90 digits | T, R |
| two-variable values: 𝔥₃(0); 𝔥₄(0), 𝔥₄(1/8); 𝔥₇ at 0, ±1/16, 3/16, 5/16; arguments (1,1), (−1,1); all rows positive rational (td:Hbase, td:Hseven, td:fiveHornNodes) | text after cf:d3P5 | 1, 2, 5 values | `horn_arrays.json` | `check_exact.py` | exact | T |
| finite-mode identities (td:momentModes); half-shift determinants (td:determinants) at off-grid complex points | | ≤ 2.4e−67, 5.0e−70 | `identities.json` | `verify_d3.py` | < 10⁻⁶⁰ at 75 digits | T, R |
| complex-node variants (fixed-complex-node formulas) equal the real-node ones | | ≤ 2.7e−65 | `identities.json` | `verify_d3.py` | < 10⁻⁶⁰ at 75 digits | T, R |
| literal ordinary pFq calls equal the accelerated moments (package README) | | ≤ 2.1e−38 | `literal_hypergeometric.json` | `verify_d3.py` | < 10⁻³⁵ at 40 digits | T, R |
| package README counts: 25 identities, 288 Horn coefficients, 8 arrays | | | `exact_algebra.json` | `check_exact.py` | exact | T |
| Section 1 table, d = 3: C₂ = 0.181221785406, C₃ = −0.353581520433, C₄ = 1.228063545 | paper Table 1 (Sec. 3) | | `comparison_summary.json` | none shipped (record only) | one unit in the last shown digit. These entries belong to the general-d rows; this is a cross-check only. | T |

Rerun-against-record tolerances (R):
- `period_values.json`: 10⁻⁴⁵;
- `identities.json`: 10⁻⁶⁵;
- `literal_hypergeometric.json`: 10⁻³⁵;
- `fresh_spectral.json`: 10⁻⁴⁰.

All are absolute and at least ten digits wider than the working precision. They allow another mpmath backend or
platform to change the last guard digits. The local runs were bitwise equal.

##### 2. `lri_d3_matrix_update`: same section, subsections on the rank-two normalization and the five-loop dictionary

| quoted (note eq.) | SM | value | record | script | tolerance and why | cmd |
|---|---|---|---|---|---|---|
| ₃F₂^(α=2)(3/4,3/4,3/4;3/2,3/2;zI₂) = 1 + 3/8 z + 2769/12800 z² + 15113/102400 z³ (rt:scalarDistinction) | text near cf:d3matrixF | | `verification/rank_two_checks.json` | `rank_two_checks.py` | exact (rationals) | T |
| scalar ₃F₂ with the same parameters = 1 + 3/16 z + 1029/12800 z² + 9317/204800 z³ (rt:scalarDistinction) | | | same | same | exact | T |
| Q_3 = 4π² ₃F₂^(α=2)(…; I₂) − Γ(1/4)¹⁰/(48π^{7/2}) (rt:Q3); 𝔥₄(0) = ₄F₃^(α=2), 𝔥₄(1/8) = ₅F₄^(α=2) (rt:P4blocks); 𝔥₇ as three functions at −I₂ (rt:H7matrix) | cf:d3Q3, cf:d3h, cf:d3h7matrix | parameter dictionary | same | same | exact (strings and Jack α = 2, size 2, argument I₂ or −I₂) | T |
| coefficientwise identity (hook weights, wheel and five-loop partition coefficients); package README: 1107 exact checks | "the identification … is coefficientwise" | 1107 | same | same | exact count; interior partial sums at 90 digits < 10⁻⁸⁵ (recorded 7.7e−92) | T |
| Q_3, P_4(3), P_5(3) at 100 digits (formula-side consistency) | | as in §1 | `verification/fresh_primitive_values.json` | `recompute_d3_periods.py` | one unit in the last shown digit; rerun against record < 10⁻⁹⁰ | T, R |
| Sec 19 (d3:values): bounded scalar catalogue search, 6479 entries, no relation | | | `verification/scalar_catalog_search.json` | `scalar_catalog_search.py` | exact count and empty match list | `make -f public.mk search` |

##### 3. `lri_C6_d3_complete_update`: note sections "Analytic power-sector compensation at d = 2, 3" (d = 3 part) and "Finite-scheme sixth-order assembly" (d = 3 part)

| quoted (note eq. / place) | value | record | script | tolerance and why | cmd |
|---|---|---|---|---|---|
| M_d at d = 3: M₃ = −16π/15 (d3six:sunset); C(0) = M₃, C′(0) = 7/4 M₃(A+N), N = 62/15 − π − 4 log 2 (d3six:chainJet) | −3.3510321638… | `records/core_propagation_checks.json` (chain_constant, chain_linear) | `check_core_propagation.py` | < 10⁻⁷⁰ (75 digits) | T |
| core jet 8/z² + 2A/z, A = 2 + 4 log 2 − π (d3six:coreJet) | | same (core_pole_jet) | same | < 10⁻⁷⁰ | T |
| two sunset graphs L6G106, L6G117: each −4M₃P_4(3) to b₆, 0 to c₆ | | `records/power_ms_d3_shifted.json` | `power_ms_d3.py` | < 10⁻⁶⁰ | T, R |
| 1, 5, 31 power classes at loops 3, 4, 5; 121 at six loops with 3w_B − w_A ≠ 0, 52 with zero weight | | `records/graph_coverage.json`; `power_ms_d3_shifted.json` | `check_coverage.py`; `power_ms_d3.py` | exact | T, R |
| two non-power four-loop graphs rejected by the coordinate reduction (L4G009, L4G027), supplied by the finite kernels | | `power_ms_d3_*.json` (failed lists) | `power_ms_d3.py` | exact; no power graph fails | T, R |
| unknown core: r_L5G086 ≐ 2F₀/5, r_L6G332 ≐ AF₀/3 + 2F₁/15, r_L6G333 ≐ AF₀/3 − 2F₁/15 (d3six:coreResidues); 9/2(r₃₃₂ + r₃₃₃) − 15/2 A r₀₈₆ ≐ 0 (d3six:unknownCancellation) | exact | `records/unknown_core_cancellation.json` | `check_unknown_core.py` | exact (SymPy) | T |
| trial (u₀,u₁) = (0,0), (101,−37) change the residues as predicted, "to better than 4×10⁻⁷³" | max 3.5e−73 | `records/core_propagation_checks.json` | `check_core_propagation.py` (on the rerun power records in R) | < 4×10⁻⁷³ (the note's bound) | T, R |
| b₃ᵖ = M, c₃ᵖ = M/3, b₄ᵖ = −11/2 AM − 3/2 MN, c₄ᵖ = −7/6 AM − MN/2 (d3six:lowerPower) | | `records/power_assembly_polynomial.json` (exact); `correction_power_ms_d3_*.json` (graph recursion) | `power_assembly_polynomial.py`; `power_ms_d3.py` + `analyze_power.py` | exact; recursion < 10⁻⁶⁰ | T, R |
| δR = M/24 (2727A³ + 603A²N − 8AM + 72AQ + 63AR − 216NQ + 27NR − 192P − 318U + 36V) (d3six:deltaR) | exact | `records/power_assembly_polynomial.json` | `power_assembly_polynomial.py` | exact (SymPy) | T |
| Δp,higher = +0.0736516970441648694692229455611…, Δp,lower = −0.0736516970441648694692229455611… at 90 digits (d3six:powerNumbers) | | `records/correction_power_ms_d3_shifted.json` | `power_ms_d3.py` (POWER_DPS=90, core 101, −37) + `analyze_power.py` | 10⁻³¹ (one unit in the last of 31 shown decimals) | T, R |
| sum −1.02×10⁻⁸⁹ (90 digits) | −1.0218e−89 | same | same | rounds to the three shown digits | T, R |
| separate 75-digit run, different core assignments: −1.94×10⁻⁷⁵ | −1.9371e−75 | `records/correction_power_ms_d3_complete.json` | POWER_DPS=75, core 0, 0 | same | T, R |
| stress test Q = 7, P = 11, 𝒦 = 5, Z = 13, core (−17, 29), 65 digits: 1.52×10⁻⁶⁵ | 1.5173e−65 | `records/correction_power_ms_d3_arbitrary_masters.json` | POWER_DPS=65 with those values | same | T, R |
| 660 sixth-order classes = 487 power-free + 173 with a power subgraph; 1, 5, 16, 76, 395 nonzero kernels at L = 2…6; "edge lists and rational weights were checked again against the inventory" (subsection "The changes required by dimension three") | | `records/graph_coverage.json` | `check_coverage.py` | exact (the script asserts every kernel's weights and edges) | T |
| "All 20 Gamma logarithmic jets and five normalizations … 65-digit Cauchy … maximum absolute discrepancy 2.27×10⁻⁵⁹" (d3six:GammaJets, d3six:norm) | 2.2666e−59 | `records/gamma_checks.json` | `check_gamma_d3.py` | count exact; rounds to the shown digits; each < 10⁻⁵⁷ (script assertion) | T |
| b_{2,0…4} = −9.7859764118999280, 13.1771369571188313, −16.3759608428540408, 19.5740514096297382, −22.7913170046010398; radii 0.05, 0.07 with 48, 64 nodes at 60 digits (d3six:twoLoopValues) | | `records/two_loop_d3.json` | `two_loop_d3.py` | one unit in the 16th decimal, for both radii; radii agree to 1.3e−54 (< 10⁻⁵⁰) | T |
| 256 exact checks, including 32 of the constant-MS sixth-order assembly (d3six:lagrange) | | `records/mom_lagrange_d3_checks.json` | `check_mom_d3.py` | exact | T |
| inputs Q_3, P_4(3) of the audit | 39 and 38 decimals in the code | `code/power_ms_d3.py`, `code/analyze_power.py` defaults | (read by the replay) | equal to §1 within one unit of the 33rd decimal | T |

Rerun-against-record tolerances (R): per-graph poles, b and c of each audit within 10^−(dps−10), and corrections within
the same. Observed: all 931 numbers of each audit are bitwise equal.

##### Not covered here

- C6(3) itself (33.5754 ± 0.0005), its estimator, SE and gates: `GFF/code/LRI_C6_D3_HPC` and `GFF/results/C6_3/`
  (C6_3 entry).
- C5(3), 𝒦₃, ℒ₃, Z₃ and C4(3) at 50 digits: `GFF/code/LRI_C5_d3` and `GFF/results/closed_forms_3/LRI_C5_d3_quoted.json`.
  They use Q_3, P_4(3), P_5(3) from §1.
- The d = 2 part of the Section 33 row "Power compensation and finite kernels" (`lri_C6_d2_complete_update`): C62d.

### `lri_d3_matrix_update`

Folder: `code/lri_d3_matrix_update/`.

_same as the section above (one text for the whole unit)._

### `LRI_C5_general_d`

Folder: `code/LRI_C5_general_d/`.

#### Results map: LRI_C5_general_d (note Sections 20 and 21)

Every number that the note (at commit fa71533) and the paper (at f496d39a: Table tab:pt only) quote for this package, plus the values earlier versions of the paper printed (kept as cross-checks), with its record, the command that checks it and the tolerance. Paths are relative to `GFF/code/LRI_C5_general_d/`. Section 20 rows come from `GFF/results/closed_forms_general/reduction_d/expected.json` and are checked by `public/replay.py`. The Section 21 rows are by session C63d (checked by `public/replay_K_d.py`). Both run under `make -f public.mk replay`, and every row passed on 2026-10-13 in a mock export (Python 3.10.11, mpmath 1.2.1).

**Tolerances.** All values are deterministic mpmath evaluations (pure Python big integers, no BLAS). Records are compared byte for byte or line for line. Quoted numbers are compared at their printed digits by the rule of each row:

- **value**: the record rounded to the printed digits equals the quoted number; with a trailing ellipsis, truncation is also accepted.
- **bound**: the record, truncated to the printed significant digits, is at most the bound.
- **range**: both ends, rounded or truncated.
- **lower**: the record is at least the quoted number.
- **exact**: equal integers.

All records that `public/replay.py` reads are bound by SHA-256 in `expected.json`. The code md5s that the records themselves pin are checked as well.

**Status column.** "owner" means this package is the source of the quoted value. "cross-check" means another package owns the value and this one reproduces it. All rows are FINAL as of the note at fa71533, except the one row whose note text changes (N9).

##### Section 20 (and the paper): checked by `public/replay.py`

| id | quoted | where | record (field) | recomputed by | rule | status |
|---|---|---|---|---|---|---|
| `C5_1_end_to_end` | -731.139476624539825853869126582527231 | note l.6916 | review/joint/numerics-end-to-end/e2e_report.json ["1"]["values"]["C5_reduced_jetK_P5hp"] | e2e.py samples_dps60.json (in replay; byte-identical report) | round to printed digits (ellipsis: or truncate) | owner |
| `C5_2_end_to_end` | -38.8336458962253605529369824675329232 | note l.6917 | e2e_report.json ["2"]["values"]["C5_reduced_jetK_P5hp"] | e2e.py samples_dps60.json (in replay; byte-identical report) | round to printed digits (ellipsis: or truncate) | owner |
| `C5_3_end_to_end` | -5.850351420751327229217944230497744300111 | note l.6918 | e2e_report.json ["3"]["values"]["C5_reduced_jetK_P5hp"] | e2e.py samples_dps60.json (in replay; byte-identical report) | round to printed digits (ellipsis: or truncate) | owner |
| `C5_1_vs_note` | 3e-34 | note l.6920 | recomputed from e2e_report.json and the note string; also e2e checks C5red_jetK_P5hp_vs_note | e2e.py samples_dps60.json (in replay; byte-identical report) | record truncated to printed digits <= bound | owner |
| `C5_2_vs_closed` | 2e-50 | note l.6921 | e2e_report.json ["2"]["checks"]["C5red_jetK_vs_C5_twoClosed"] | e2e.py samples_dps60.json (in replay; byte-identical report) | record truncated to printed digits <= bound | owner |
| `C5_3_vs_d3` | 5e-45 | note l.6921-6922 | e2e_report.json ["3"]["checks"]["C5red_jetK_P5hp_vs_LRI_C5_d3_json"] (five-node K) and e2e_k3.log (three-node K), both at full precision | e2e.py; public/e2e_k3_public.py (in replay) | record truncated to printed digits <= bound | owner |
| `masters_vs_codes` | 2.1e-48 | note l.6908 | specialize/results/c5_assembly_dps50.json dev_P4_compact, dev_L_compact, dev_Z_Qform, dev_Q_c0form | specialize/c5_assembly.py 50 (replay-full) | record truncated to printed digits <= bound | owner |
| `block_reduced_form` | 1.2e-48 | note l.6909 | c5_assembly_dps50.json dev_Bred_vs_B | specialize/c5_assembly.py 50 (replay-full) | record truncated to printed digits <= bound | owner |
| `block_vs_closed_d12` | 4e-50 | note l.6910 | c5_assembly_dps50.json dev_*_ref at d = 1, 2 | specialize/c5_assembly.py 50 (replay-full) | record truncated to printed digits <= bound | owner |
| `block_vs_spectral_refs` | 4e-50 | note l.6910 | recomputed from L/results/val50.json, Z/results/zj90.json, references/reference_values.json; record.json "block <= 4.0e-50" | from the records in replay; the records: L/run_validation.py, Z/z_jets.py (replay-full) | record truncated to printed digits <= bound | owner |
| `block_d3_Q3_limited` | 6e-34 | note l.6912 | c5_assembly_dps50.json dev_B_ref at d = 3 | specialize/c5_assembly.py 50 (replay-full) | record truncated to printed digits <= bound | owner |
| `lattice_identities_d12` | 1e-44 .. 1e-46 | note l.6899-6900 | output of specialize/check_special.py (rerun by replay) | specialize/check_special.py (in replay; log written to public/out) | both ends, rounded or truncated | owner |
| `landen_relations` | 5e-46 | note l.6900 | check_special.py output | specialize/check_special.py (in replay; log written to public/out) | record truncated to printed digits <= bound | owner |
| `P4_L_from_modes_d12` | 2e-45 | note l.6901 | check_special.py output | specialize/check_special.py (in replay; log written to public/out) | record truncated to printed digits <= bound | owner |
| `d3_dictionary` | 1.2e-51 | note l.6902-6903 | specialize/results/check_d3_dps50.log | specialize/check_d3.py 50 (in replay; identical log) | record truncated to printed digits <= bound | owner |
| `d3_L3_formula` | 5e-64 | note l.6904 | specialize/results/check_d3_dps50.log | specialize/check_d3.py 50 (in replay; identical log) | record truncated to printed digits <= bound | owner |
| `DL_identity` | 1e-57 | note l.6772 | public/check_DL_Phat.py from samples_dps60.json and specialize/L3_final_values.json | public/check_DL_Phat.py (in replay) | record truncated to printed digits <= bound | owner |
| `DL_value_d3` | -1332.48 | note l.6772 | public/check_DL_Phat.py | public/check_DL_Phat.py (in replay) | round to printed digits (ellipsis: or truncate) | owner |
| `Phat_prime_d3` | 274.55 | note l.6772 | specialize/L3_final_values.json Phat_prime | public/check_DL_Phat.py (record value of specialize/L3_final_values.json) | round to printed digits (ellipsis: or truncate) | owner |
| `pole_node_vs_multinode` | 5e-21 .. 3e-23 | note l.6905-6906 | specialize/results/check_taylor_dps30.log | specialize/check_taylor.py 30 (replay-full; 37 s on 4 cores) | both ends, rounded or truncated | owner; note change N9 (fa71533 prints 3e-21 .. 3e-23) |
| `topmode_balanced` | 2.4e-51 .. 1.6e-49 | note l.6446-6447 | review/topmode-numeric/results/probe_*.json (superseded entries as in summarize.py) | record only (independent review code; rerun is R2, REPRODUCE.md) | both ends, rounded or truncated | owner |
| `topmode_balanced_count` | 22 | note l.6447 | review/topmode-numeric/results/probe_*.json | record only (independent review code; rerun is R2, REPRODUCE.md) | equal | owner |
| `topmode_surviving` | 1.6e-3 .. 1 | note l.6447-6448 | review/topmode-numeric/results/probe_*.json | record only (independent review code; rerun is R2, REPRODUCE.md) | both ends, rounded or truncated | owner |
| `topmode_unbalanced` | 6.7e-4 .. 4.6e-2 | note l.6444-6445 | probe_ctrl.json | record only (independent review code; rerun is R2, REPRODUCE.md) | both ends, rounded or truncated | owner |
| `topmode_no_1plusz` | 1.9e-3 | note l.6445 | probe_ctrl.json N1r4 | record only (independent review code; rerun is R2, REPRODUCE.md) | round to printed digits (ellipsis: or truncate) | owner |
| `higher_modes_c53_c64` | 1.6e-3 .. 0.16 | note l.6462 | probe_*.json, r = 5, 6 | record only (independent review code; rerun is R2, REPRODUCE.md) | both ends, rounded or truncated | owner |
| `unbalanced_control_fr` | 0.017 | note l.6443 | review/foundation-rigor/results/control_unbalanced.log (17-node summary "top") | record only (independent review code; rerun is R2, REPRODUCE.md) | round to printed digits (ellipsis: or truncate) | owner |
| `lemmaG_mixed` | 2.8e-48 .. 4.7e-44 | note l.6449, 6925 | review/lemmaG-numeric/results/summary.json | review/lemmaG-numeric/summarize.py rebuilds summary.json from the per-case results (in replay); the per-case runs are R2 (about 50 core-h) | both ends, rounded or truncated | owner |
| `lemmaG_R` | 6.5e-47 .. 5.2e-45 | note l.6451-6452, 6926 | summary.json | review/lemmaG-numeric/summarize.py rebuilds summary.json from the per-case results (in replay); the per-case runs are R2 (about 50 core-h) | both ends, rounded or truncated | owner |
| `lemmaG_W0` | 3.0e-46 | note l.6926 | summary.json | review/lemmaG-numeric/summarize.py rebuilds summary.json from the per-case results (in replay); the per-case runs are R2 (about 50 core-h) | round to printed digits (ellipsis: or truncate) | owner |
| `lemmaG_fine` | 9.3e-54 | note l.6452, 6927 | summary.json *_fine | review/lemmaG-numeric/summarize.py rebuilds summary.json from the per-case results (in replay); the per-case runs are R2 (about 50 core-h) | record truncated to printed digits <= bound | owner |
| `lemmaG_continued` | 2e-47 | note l.6928 | summary.json *_cont_fine | review/lemmaG-numeric/summarize.py rebuilds summary.json from the per-case results (in replay); the per-case runs are R2 (about 50 core-h) | record truncated to printed digits <= bound | owner |
| `lemmaG_controls` | 0.0013 .. 0.047 | note l.6930 | review/lemmaG-numeric/results/summary_controls.json imbalance_A1 | review/lemmaG-numeric/summarize.py (in replay) | both ends, rounded or truncated | owner |
| `lemmaG_external` | 1e-15 | note l.6455 | results/external_comparison.json | review/lemmaG-numeric/compare_external.py (in replay) | record truncated to printed digits <= bound | owner |
| `check_topG_modes` | 1e-24 .. 9e-16 | note l.6459 | foundation/check_topG.log | foundation/check_topG.py (in replay; identical log) | both ends, rounded or truncated | owner |
| `check_topG_controls` | 9e-10 .. 2e-5 | note l.6461 | foundation/check_topG.log | foundation/check_topG.py (in replay; identical log) | both ends, rounded or truncated | owner |
| `check_topG_identities` | 1e-29 | note l.6935 | foundation/check_topG.log | foundation/check_topG.py (in replay; identical log) | record truncated to printed digits <= bound | owner |
| `review_offcentre_digits` | 44 .. 53 | note l.6940 | review/formula-from-text/compare.out | record only (independent review code; rerun is R2, REPRODUCE.md) | both ends, rounded or truncated | owner |
| `review_P4_digits` | 31 .. 39 | note l.6940-6941 | compare.out | record only (independent review code; rerun is R2, REPRODUCE.md) | both ends, rounded or truncated | owner |
| `review_L_digits` | 31 .. 38 | note l.6941 | compare.out | record only (independent review code; rerun is R2, REPRODUCE.md) | both ends, rounded or truncated | owner |
| `review_coeff_functions` | 1.2e-38 | note l.6942 | review/L-rigor/coeff_check.log "worst" | record only (independent review code; rerun is R2, REPRODUCE.md) | record truncated to printed digits <= bound | owner |
| `review_Z1_digits` | 30.7 | note l.6942 | compare.out (d = 1) | record only (independent review code; rerun is R2, REPRODUCE.md) | round to printed digits (ellipsis: or truncate) | owner |
| `review_Z2_digits` | 35.2 | note l.6942 | compare.out (d = 2) | record only (independent review code; rerun is R2, REPRODUCE.md) | round to printed digits (ellipsis: or truncate) | owner |
| `review_Z3_digits` | 29.5 | note l.6942 | compare.out (d = 3) | record only (independent review code; rerun is R2, REPRODUCE.md) | round to printed digits (ellipsis: or truncate) | owner |
| `review_block_digits` | 30.4 .. 35.6 | note l.6943 | compare.out | record only (independent review code; rerun is R2, REPRODUCE.md) | both ends, rounded or truncated | owner |
| `c0hat_gamma_offcentre` | 1e-40 | note l.6981 | review/Z-rigor/d3_gamma_offcenter.log | record only (independent review code; rerun is R2, REPRODUCE.md) | record truncated to printed digits <= bound | owner |
| `pslq_c0hat` | 1e11 | note l.6887 | specialize/results/gamma_c0_dps80.json | specialize/gamma_c0.py 80 (replay-full PSLQ=1) | record >= quoted | owner |
| `pslq_DL` | 3e3 | note l.6889-6892 | specialize/results/pslq_L_dps110.json | specialize/pslq_L.py 110 (replay-full PSLQ=1) | record >= quoted | owner |
| `k3_three_node` | 3.8e-45, 5.0e-44, -8.1e-43 | note l.7631 | review/joint/numerics-end-to-end/e2e_k3.log | public/e2e_k3_public.py k3_jets.json (in replay); the jets: kjet3.py (R2, 30 min on 8 cores) | each rounded to printed digits | owner |
| `xc_C5_table_sec1` | -731.13947662454, -38.833645896, -5.850351421 | note l.101; paper Table tab:pt `\CfiveOne`, `\CfiveTwo`, `\CfiveThree` | e2e_report.json | e2e.py (in replay) | each rounded to printed digits | cross-check |
| `xc_C5_status` | -731.139476624…, -38.8336458962…, -5.85035142075… | note l.6996 | e2e_report.json | e2e.py (in replay) | each rounded to printed digits | cross-check |
| `xc_C5_1_note33` | -731.139476624539825853869126582527… | note l.2531 | e2e_report.json | e2e.py (in replay) | round to printed digits (ellipsis: or truncate) | cross-check |
| `xc_C5_2_note25` | -38.83364589622536055293698… | note l.3915 | e2e_report.json | e2e.py (in replay) | round to printed digits (ellipsis: or truncate) | cross-check |
| `xc_paper_C5_3` | -5.85035142075132722921794423049774… | note l.390 (50 digits); not printed in the paper at f496d39a (was app_closed_forms.tex l.588) | e2e_report.json | e2e.py (in replay) | round to printed digits (ellipsis: or truncate) | cross-check |
| `xc_paper_L3` | -62.7105849683876693472961734335348… | note 953aa45 l.4348 (30 digits); not printed in the paper at f496d39a (was l.585) | e2e_report.json ["3"]["values"]["L"] | e2e.py (in replay) | round to printed digits (ellipsis: or truncate) | cross-check |
| `xc_paper_dH` | 2539.52445251775601935… | not printed in the paper at f496d39a (was app_closed_forms.tex l.572); a check of the record | specialize/results/check_d3_dps50.log | specialize/check_d3.py 50 (in replay; identical log) | round to printed digits (ellipsis: or truncate) | cross-check |
| `xc_paper_da` | 11.38885029910005086619… | not printed in the paper at f496d39a (was app_closed_forms.tex l.572); a check of the record | specialize/results/check_d3_dps50.log | specialize/check_d3.py 50 (in replay; identical log) | round to printed digits (ellipsis: or truncate) | cross-check |

Supporting row, not a printed number: `closed_forms_d12_records`. The masters P4, L, 3Q and Z of the code records at d = 1, 2 equal their closed forms to 9.7e-81, the limit of the 80-digit evaluation in replay.

**Records with no rerun in `replay` or `replay-full`.** These are the independent review codes in `review/topmode-numeric/`, `review/lemmaG-numeric/` (per-case runs), `review/formula-from-text/`, `review/L-rigor/`, `review/Z-rigor/` and `review/foundation-rigor/`. Their outputs ship, and `replay` reads the quoted numbers from them. Rerunning them costs about 100 core-hours of cluster time (REPRODUCE.md, R2).

**One stale log.** `Z/results/compare_refs.log` was written against the 45-digit reference strings that `references/reference_values.json` held before 2026-10-03 01:21. Against the current 50-digit file, the deviations are at most 4.9e-50 (`replay-full`, job Z_refs, and the row `block_vs_spectral_refs`). That is the figure the note quotes.

##### Section 21 (K_d): checked by `public/replay_K_d.py` (session C63d)

*This section was written by C63d (`GFF/d3/K_general_for_C62d/results_map_K_d.md`) and is merged here unchanged. Its expected strings are in `public/expected_K_d.json`, and its table is in `public/out/replay_K_d/REPLAY_K_d.md`.*

Paths are relative to `GFF/code/LRI_C5_general_d/`. The command for every row is `python3 public/replay_K_d.py`; through
C62d's public.mk it runs as part of `replay` (see `public_mk_lines.txt`). The expected strings are in
`public/expected_K_d.json`, copied from the note at fa71533. Every row passed on 2026-10-13 (`replay_K_d_local_run.txt`).

Tolerances:
- **round** = correct rounding to the printed digits, as the note states for the values table.
- **2 sig** / **1 sig** = the computed deviation printed to the note's two or one significant digits.

All inputs are stored records with 34 to 430 digits, evaluated in mpmath at 72–120 digits. Nothing depends on the
platform.

| quoted | where (fa71533) | record and computation | tolerance |
|---|---|---|---|
| 𝒦_d at d = 0.8, 1, 1.25, 1.5, 2, 2.5, 2.75, 3 (32 digits each; e.g. 𝒦_3 = 1.1485946495271793365566463108107…) | 21.10 values table (l.7608-7615) | `K_general/position_space/K_d_values_mb_D100.json` (100 digits, Arb trapezoid on Re z = −q/3) | round |
| r3 at the same 8 d (34 digits; e.g. 767.2452094446567860904798157376224 at d = 1) | 21.10 values table | r3 = s3 + 4[𝒦_d − (U/8)(ψ(1) + ψ(2q) + 4ψ(q))] (gdk:Kr3) from the 100-digit 𝒦_d; s3 from gdk:sk, checked against the Taylor series of gdk:Sclosed (2.4e-117) | round |
| "gdk:Kr3 with the printed r3 reproduces the printed 𝒦_d to 3e-32 (10^-33 against the 100-digit values)" | 21.10 text (l.7601-7604) | from the printed strings: 2.4e-32 and 9.5e-34 | ≤ 3e-32, ≤ 1e-33 |
| r3(1) = 767.2452094446567860904798157376224…, r3(2) = 35.63714944308140680727039972168179… | 21.8 (l.7496-7520) | closed forms s3 + 4𝒦 − 2(π³ + 28ζ3)(3γ + 7 log 2 + π) with eq:KprovedFinal; s3 + 128G² − 168ζ3 log 2 − 42γζ3 | round |
| (U/8)[ψ(1) + ψ(1/2) + 4ψ(1/4)] = ½(π³ + 28ζ3)(3γ + 7 log 2 + π) | 21.8 (l.7499) | mpmath, 120 digits: 5.0e-119 | ≤ 1e-100 |
| 𝒦_3 = 1.14859464952717933655664631081067318763… (430 digits); r3(3) = 4.511759358236005780256620897961575… | 21.8 (l.7537-7541) | `../LRI_C5_d3/wf_K3/K3_value.json` | one unit; round. SKIP if LRI_C5_d3 is absent. |
| spectral reference column: −1.9e-49, 1.8e-49, 1.9e-49, 5.2e-51, 2.1e-50 (d = 0.8, 1.25, 1.5, 2.5, 2.75) | 21.10 routes table (l.7639-7646) | `references/reference_values.json` (K) vs the 100-digit values | 2 sig |
| Abel–Plana column: 8.2e-57, −2.4e-55, 2.1e-56, −1.2e-55, −8.3e-56 | same | `K_general/refcheck/refcheck_values.json` | 2 sig |
| five-node jet column: −8.0e-47, −4.8e-37, −1.0e-41, −9.6e-46, 5.2e-48, 5.4e-44, 6.0e-44, −1.4e-43 | same | 𝒦_d recomputed through gdk:Ktau from the stored 48-point 72-digit τ-circles `K_general/R_part/prod/prod_B_d*.json`; the stored K_d field gives the same digits | 2 sig (both) |
| three-node jet column: −8.1e-47, −1.0e-41, −1.4e-45, 4.1e-44, −3.5e-44, −9.5e-43 (d = 0.8, 1.25, 1.5, 2.5, 2.75, 3) | same | gdk:Ktau from `K_general/note_fragment/topmode/results/kjet3_B_d{0.8,1.25,2.75}.json` (job 569317) and `review/joint/numerics-end-to-end/k3_jets.json` (d = 1.5, 2.5, 3; job 569482) | 2 sig |
| through gdk:Kr3 instead: 3.8e-45, 5.0e-44, −8.1e-43 | 21.10 Routes (l.7630) | `k3_jets.json` | 2 sig |
| position space vs closed forms and 𝒦_3: 5.2e-101, −1.5e-100, 3.6e-100 | 21.10 routes table, last column; 21.8 (3.6e-100) | (𝒦_MB − exact)/exact with eq:KprovedFinal, gc:K2closed, the 430-digit 𝒦_3 | 2 sig |
| five-node version vs eq:KprovedFinal, gc:K2closed, 𝒦_3: 5e-37, 5e-48, 1.4e-43 | 21.8 Consistency (l.7545-7549) | prod_B circles through gdk:Ktau | 1 or 2 sig as printed |
| sampled r3(1), r3(2) agree with the closed forms to 1e-32 | 21.8 Consistency (l.7550) | `K_general/R_part/R_part_results.json` (Laurent tables): 9.6e-33 | ≤ 1e-32 |
| \|r0 − s0\|, \|r1 − s1\|, \|r2 − s2 − 3U/2\| ≤ 5e-32; gdk:Kr3 reproduces 𝒦_d to 1e-33 | 21.10 Further checks, Low orders (l.7658-7660) | same Laurent tables: 4.8e-32; 9.5e-34 | ≤ 5e-32; ≤ 1e-33 |
| \|F2 − 3U/2\| between 1e-47 and 4e-35 in the 72-digit jets | same (l.7660) | `prod_B_d*.json` (tE2) | 1 sig at both ends |
| orders t^0, t^1 (gdk:MBidentities) hold to 1e-101 at all eight d | 21.10 Inputs (M) and (J) (l.7666) | `K_d_values_mb_D100.json` (check_t0, check_t1): max 6.6e-102 | ≤ 1e-101 |
| three-node 𝒦_d equals the five-node value to 3e-49, 3.5e-47, 9.5e-44 (d = 0.8, 1.25, 2.75) | 21.10 Three nodes (l.7680) | kjet3 vs prod_B circles, both through gdk:Ktau | printed digits |
| two contours and step sizes agree to 3e-55 at d = 0.8, 1.25, 1.5, 2.5 | 21.10 Position space (l.7684) | `K_general/position_space/K_mb_d*_D50_c*.json` vs D100: max 2.45e-55 | ≤ 3e-55 |
| independent double precision: 𝒦_d to 7e-14, the two identities to 2e-13 | 21.10 Position space (l.7685-7688) | stored `K_general/note_fragment/fragment_checks/check_barnes.json`: 𝒦 7.2e-14; identities 3.1e-15 relative, **9.1e-13 absolute** (d = 1) | 1 sig for 𝒦; ≤ 2e-13 relative for the identities (fa71533 wording); the corrected wording of `../closed_forms_3/section33_row.tex`, "10^-12 absolute (3·10^-15 relative)", is checked too |
| optional `--recompute`: 𝒦_d at 40 digits for d = 1, 2, 3 by `K_general/position_space/kmb_flint.py` | (production code of the 100-digit values) | equals the stored `K_mb_d*_D40.json` string for string and the 100-digit values to ≤ 1e-38 | identical; ≤ 1e-38 |

Statements in Section 21 that the replay does not recompute: S-family agreement at 36 points, lattice route, τ-circles;
samples at eight (d, τ); termwise identities 6e-39; growth bounds; top modes; the d = 3 determinant to 1.1e-24; "A
caution". Their records and logs ship under `K_general/S_part/`, `R_part/`, `note_fragment/growth/checks/`,
`note_fragment/topmode/`, `fragment_checks/check_blocks.log` and `test_build_joint/check_kbracket_d08*.log`, with
the scripts that wrote them. The original table builders `fragment_checks/build_table.py`,
`test_build_joint/check_r3_34.py`, `check_r3_special.py` and `check_k3_routes.py` also run in the public tree and
reproduce their shipped logs.

### `LRI_C5_d3`

Folder: `code/LRI_C5_d3/`.

#### closed_forms_3 (LRI_C5_d3): quoted numbers → record, command, tolerance

Sources: the condensed note `GFF/LRI_condensed_note/long_range_ising_condensed.tex` at fa71533 (section and line), and the
paper (final text f496d39a): Table 1 of Sec. 3 (macros of `paper/numbers.tex`) and the closed-form appendix
`paper/sections/app_closed_forms.tex` (App. A). "SM" below names where App. A printed a number in its d = 3 paragraph,
which was removed on 2026-10-14; in the final paper App. A keeps only A_3, R_3 and the formula for Q_3 (eq.
cf:d123-blocks and the sentence after it). Those rows stay as checks of the records. All paths
are relative to `GFF/code/LRI_C5_d3/`. The command for every row is `make -f public.mk replay`, which runs
`public/replay_c5_d3.py` with `../../results/closed_forms_3/LRI_C5_d3_quoted.json` (row id in brackets). All values were
recomputed on 2026-10-13 and agree (`replay_local_run.txt`: 56 PASS, 0 FAIL, 0 SKIP).

Tolerance kinds:
- **unit** = |value − quoted| ≤ one unit in the last quoted digit. The TeX marks omitted digits with `\ldots` and may
  truncate or round.
- **round** = the value rounded to the quoted number of significant digits equals the string, as the table convention
  states.
- **2 sig** = a quoted deviation reproduced to its two printed significant digits.

The values are mpmath evaluations of stored high-precision records, so no platform or BLAS sensitivity applies.

##### Coefficients at d = 3

| quoted | where | record and how | tolerance |
|---|---|---|---|
| C5(3) = −5.8503514207513272292179442304977443001109973463783… (50 digits) | note 1.1 (l.390), 19.8 (l.6078); SM eq. cf:d3C5value | gs:C5 at q = 3/4 at 460 digits with K3 (`wf_K3/K3_value.json`, 430 digits), L3 (`wf_L3/L3_final_values.json`), Z3 (`wf_Z3/Z3_values.json`), Q3, P4(3), P5(3) (`inputs/general_d3/period_values.json`, 90-digit run) [C5_3_50]; also `c5_value.json`, regenerated byte-identically by `compute_c5.py` | unit (1e-49). The digits are limited by P5(3), confirmed independently to about 1e-53. |
| C5(3) = −5.850351420751327229217944230497744300111 | note 20.7 (l.6918), the generic-d end-to-end value | same [C5_3_note20]; the note's "agree with LRI_C5_d3 to 5e-45" is the joint review's figure (5.2e-45, three-node K) | unit (1e-39) |
| C5(3) = −5.85035142075132722921794423049774… | SM table cf:tab:d3 | same [C5_3_paper34] | unit |
| C5(3) = −5.85035142075… | note 20.8 (l.6996) | same [C5_3_short] | unit |
| C5(3) = −5.850351421 | note 1 table (l.101), 16.8 (l.3779); paper Table 1 (\CfiveThree) | same [C5_3_table] | round |
| C4(3) = 1.2280635453276230799666561680749… | SM eq. cf:d3C4value, table | 648 C4 = 16P4 − A³ − 8AQ − 3AR + (53/2)U − 3V (note 1.1) with the 90-digit periods [C4_3_paper] | unit |
| C4(3) = 1.228063545 | note 1 table (l.100), 16.8 (l.3779); paper Table 1 (\CfourThree) | same [C4_3_table] | round |
| C3(3) = −0.353581520433, C2(3) = 0.181221785406 | note 1 table (l.98-99); paper Table 1 (\CthreeThree, \CtwoThree) | (A² + R − 8Q3)/108 and A/9 [C3_3_table, C2_3_table] | round. Owned by the general C0..C5 row (C62d); recomputed here from the same inputs. |

##### Masters

| quoted | where | record and how | tolerance |
|---|---|---|---|
| Q3 = 5.01710256455385536959085484569018…, P4(3) = 62.0583279434066724664633885840967…, P5(3) = 240.340317759083549816366546388004… | note 19.8 (l.6062-6064); SM table | `inputs/general_d3/period_values.json` (90-digit run) [Q3, P4_3, P5_3] | unit. **Owned by bundle_d3** (lri_d3_reduction_update, same file). Rechecked here because C5(3) uses them; `make smoke` recomputes them at 90 digits (≤ 1.3e-88). |
| K3 = 1.14859464952717933655664631081067318763… | note 21.8 (l.7538); SM table | `wf_K3/K3_value.json` [K3] | unit |
| K3 = 1.1485946495271793365566463108107… | note 21.10 values table (l.7615) | the table prints the position-space value; checked here against K3 [K3_table] and by `LRI_C5_general_d/public/replay_K_d.py` | round |
| r3(3) = 4.511759358236005780256620897961575… | note 21.8 (l.7541), 21.10 table | gdk:Kr3 with K3 and the Bell polynomial s3 of gdk:sk [r3_3] | round (34 digits) |
| L3 = −62.7105849683876693472961734335348… | SM table (not printed in the note) | `wf_L3/L3_final_values.json`, regenerated by `wf_L3/final_form.py` from `pA_dps170.json` [L3] | unit |
| Z3 = 8.82092489306009248553686732817408… | SM table (not printed in the note) | `wf_Z3/Z3_values.json` = `derived_circ*.json` regenerated by `wf_Z3/derive.py` [Z3] | unit |
| 𝔡_H = 2539.52445251775601935…, 𝔡_a = 11.38885029910005086619… | SM (after eq. cf:d3L3) | `wf_L3/L3_final_values.json` (dH, da) [dH, da] | unit |
| (2/(πS⁷))𝔇_L = −1332.48, P̂' = 274.55 | note 20.4 (l.6772) | `wf_L3/L3_final_values.json` (dPdb_tdform from `tdform.py`, Phat_prime) [DL_frozen, Phat_prime]; the identity P̂' − 8√2 N_b⁴c41 + 32 N_b⁴c42 = dPdb_tdform holds to 4.9e-162 | round (2 decimals). "Holds to 1e-57 against C62d's 𝔇_L" is C62d's check. |

##### Accuracy and consistency statements

| quoted | where | how | tolerance |
|---|---|---|---|
| K3 to 430 digits | note 19.8, 21.8; SM | `wf_K3/run_hp3.json` vs `run_hp4.json`: 2.47e-433 [K3_430] | ≤ 1e-430 |
| K3 position space vs residue series 3.6e-100 (19.8: "4e-100") | note 21.8 (l.7539), 21.10; SM | (K_MB − K3)/K3 with `../LRI_C5_general_d/K_general/position_space/K_d_values_mb_D100.json` [K3_vs_MB] | 2 sig. SKIP if the sibling package is absent. |
| K3 vs 100-digit spectral run C: 1.5e-96 | WORKFLOW_RESULT.md | `run_C_combined.json` (regenerated by `hp_combine.py`) [K3_vs_runC] | ≤ 2e-96 |
| L3 agrees with the spectral evaluation "to all 43 established digits" | SM | vs `masters_d3.json`: 4.5e-53 relative [L3_vs_spectral43] | ≤ 1e-43 relative |
| Z3 agrees with the spectral evaluation "to 3e-98" | SM | vs `run_C_combined.json`: 2.86e-98 [Z3_vs_runC] | one significant digit |
| L3 to "about 158 digits", Z3 to "about 250 digits" | SM; `wf_L3` and `wf_Z3` records | two Cauchy runs each: L3 runs A/B identical in all 165 stored digits (B regenerated from `pB_dps170.json`); Z3 circles A2/B2 8.6e-254; `Z3_values.json` = derived values to 2.5e-249 [L3_158, Z3_250] | ≤ 1e-157, ≤ 1e-250 |
| 43 established digits of runs A/B | `pslq_d3.log`, README | run A vs B: 1.2e-45 relative [runs_AB_43] | ≤ 1e-43 relative |
| other inputs "known to about 1e-80" | note 19.8 (l.6081); SM | Q3, P4(3) of the 90-digit periods vs the 250- and 158-digit routes: 1.15e-79 [inputs_1e80] | ≤ 1e-78 |
| "Changed-precision ... agreed at about 1e-51, 1e-52 and 1e-53" | note 19.8 (l.6067) | `lri_d3_reduction_update/verification/general_d3/comparison_summary.json` | **bundle_d3's row** (not in this package) |
| reduced form of C5(3) agrees with the N3 form (WORKFLOW_RESULT: 2e-119) | WORKFLOW_RESULT.md §2 | both forms with the same inputs: 6.1e-164 [C5_N3_vs_reduced] | ≤ 1e-110 |
| d = 2 spectral residuals 1.7e-79 (L2) and 3.1e-62 (K2) | note 17.2 (l.3892), **C62d's row** | `wf_d2check/run4_combined.json`, regenerated byte-identically by `wf_d2check/combine_d2.py` | 2 sig |

##### Printed formulas checked with the stored values (no quoted digits)

| formula | where | residual |
|---|---|---|
| Q3 = 4π² 𝔥₃(0) − Γ(1/4)¹⁰/(48π^{7/2}) | note td:Qanswer (19), SM cf:d3Q3; final paper: App. A after eq. cf:d123-blocks | 1.6e-248 |
| Z3 = (4π²/3) 𝔱₃''(3/2) − (4G + π²/2) Γ(1/4)¹⁰/(16π^{7/2}) | note 20.4, SM cf:d3Z3 | 5.6e-248 |
| S'(3/2) = Γ(1/4)¹⁰/(64π^{9/2}) − π 𝔥₃(0) (dW3/db = 0) | WORKFLOW_RESULT.md, SM | 1.9e-249 |
| L3 = 4πP4 − 2π²X0 + 6√2π(π − 2 log 2)𝔞4𝔟4 − 2π𝔡_H + 12√2π𝔟4𝔡_a | note 20.4, SM cf:d3L3 | 5.0e-162 |
| P4(3) = 2πX0 − 10πXh + (14√2 − 20)π𝔞4𝔟4; 𝔟4 = Γ(1/4)⁶/(16π^{5/2}); c41 = 2𝔞4𝔟4 | note 19, SM | ≤ 8.6e-163 |
| d = 3 form of gs:C5 and of C4 (S(A), 720A² + 336π² − 4032, 53π³ − 1436ζ(3) − 48) | note 1.1, SM cf:d3C4, cf:d3C5, cf:d3S3 | exact (SymPy); numerically 2e-460 |

##### Not numbers but cited checks (records shipped, rerun documented in REPRODUCE, not in replay)

- "A PSLQ search at 420 digits in the bases of `LRI_C5_d3/wf_K3/` found no relation" (note 21.8): `wf_K3/pslq_K3_results_420.json` (`final_battery.py 420`).
- "lattice bounds / lattice reduction at 155 digits" for L3 (note 20.4; SM): `wf_L3/battery_final_dig155.json`, `_dig125.json`.
- No relation for 𝔱₃''(3/2) (SM): `wf_Z3/pslq_z3_results.json`.
- "the Gamma form of ĉ0 derived in LRI_C5_d3 ... confirmed numerically, also at b = 0.8 and complex b" and "c41(b) = 2𝔞4(b)𝔟4(b) for every b < 2 ... confirmed numerically to 1e-51" (note 20.4, 20.8). Evidence shipped (coordinator decision 2026-10-13): `wf_Z3_gamma_verify/` (check_amp.py with logs at 30 and 60 digits: the Gamma form at b = 1.1 ... 1.6 and b = 1.3 + 0.2i to about 1e-60; the b = 0.8 case is C62d's independent review, `LRI_C5_general_d/review/VERIFICATION.md` items C10 and O2) and `wf_V_L3_b4/` (check_b4.py, cmp_cauchy.py and logs). C62d's `specialize/check_d3.py` gives the 1e-51 figure. The outcomes are also recorded in `WORKFLOW_RESULT.md` §1. The note's wording stands. Both scripts carry an absolute `sys.path` line, so they need a path edit to rerun.

## C6(1) and its analytic representation

### `LRI_C6_1D_HPC`

Folder: `code/LRI_C6_1D_HPC/`.

#### Results map: C6(1) from exact all-graph sums

Every quoted number is checked by `make -f public.mk replay`, run from `GFF/code/LRI_C6_1D_HPC`. The row IDs are
those of `.work/replay_table.txt`. Files are relative to `GFF/`.

##### Tolerances

- **printed** means the record value rounds to the number as printed: |value − printed| ≤ half a unit in its last
  printed digit.
- **bitwise** means sha256 equality of a regenerated file.

##### Records shortened in the tables

| Short name | File |
|---|---|
| F | `results/C6_1/C6_final.json` |
| A | `results/C6_1/assembled.json` |
| R | `results/C6_1/rounding.json` |
| X | `results/C6_1/C7_crosscheck.json` |
| RR1 | `results/C6_1/lower_amplitude_precision/R6_comparison.json` |
| AC | `code/LRI_C6_1D_HPC/reference/additional_checks.json` |
| S | `results/C6_1/validation/summary.json` |

##### Quoted numbers

| Quoted number (where) | Record and field | Row | Tolerance |
|---|---|---|---|
| C6(1) = 14331.68703277 ± 0.00000049, N* = 22, M* = 40, f = 1 (note Sec 22.1, abstract; REPORT) | F `headline.C6`, `allowance_U`, `N_star`, `L5_M_star`, `f` | Q01 | exact string |
| 14331.6870328(5); unrounded 14331.68703276838 (note Sec 1, 1.2, 22.9) | F `headline.C6_unrounded` | Q02, Q03 | printed |
| U = ceil_2sf of the sum of six terms = 4.9e-7 | F `headline.components` | Q04 | exact |
| Terms 8.0e-8, 2.5e-9, 3.5e-7, 8.7e-9, 4.1e-8, 3.1e-9 (note Sec 22.5; REPORT) | F `headline.components.{U_conv, U_cut, U_round, U5, U5_round, Ulow}` | Q05 | printed |
| Calibration factor 1.03 (note Sec 22.5) | F `headline.cal` (= R `cal` 1.02865) | Q06 | printed |
| Degree table N = 6…22: C6 maxgap and span (9 decimals), maxgap − span, ρ(N) (note Sec 22.5; REPORT) | F `levels[]` (from A `levels[N].C6.L5_M40` and R `levels[N].rho`) | Q07, Q08 | printed |
| Last changes +3.3e-8, +4.0e-8; 2ρ(22) = 1.8e-7; stop at N* = 22 by rule (a) (note Sec 22.5) | F `levels[N=22].delta_*`, `rho`, `stop_a_converged_to_floor` | Q09, Q10 | printed; exact |
| Step ratios about 0.06 (maxgap) and 0.1 (span) (note Sec 22.5; REPORT) | F `levels[].ratio`, N = 12–20 | Q11 | range 0.04–0.08 and 0.03–0.14 |
| R6, J5 and K = R6 + (4/243) J5 for both cutoffs (note Sec 22.4 table) | A `configs.L5_M40.{maxgap,span}.{R6,J5,K}` | Q12 | printed |
| U5 = 2 max\|C6(M=40) − C6(M=36)\| = 8.7e-9 | F `diagnostics.L5_sequence_at_Nstar` | Q13 | printed |
| "From M = 28 onward, successive changes of C6 are at most 4.4e-9" (note Sec 22.4, public edition 97dd353; the earlier "M = 24 ... below 1e-11" was wrong) | records: up to 4.35e-9 for M = 28...40 | Q14 | bound |
| Lower-degree change 28 − 22: −1.54e-9 (maxgap), +4.14e-10 (span); Ulow = 3.1e-9 (note Sec 22.4) | AC `lower_order_degree_controls.*.N28_minus_N22`; `reference/assembly_lower6.json` | Q15, B13 | printed; 1e-40 for the identity |
| binary64 rerun of L2–L4: 6.0e-8 (−5.95e-8, −5.90e-8), giving ≈ 3e-11 (2.9e-11); ld reproduction 4.7e-17; R6 moves 1.3e-13, 2.7e-13; U unchanged, 5.5e-7 with the full difference (note Sec 22.4; REPORT addendum, RR-001) | RR1 | Q16, B10 | printed; exact for U |
| RG double-pole errors 9.2e-2, 8.0e-4, 5.2e-6, 6.9e-8 at N = 10, 14, 18, 22; triple pole 2.7e-9 at N = 22 (maxgap; note Sec 22.6) | F `diagnostics.pole_errors[N].maxgap["-2"]`, `["-3"]` | Q17 | printed |
| Exact versus old Monte Carlo, z in old SE: −0.57, −0.60 (8−6); +0.86, +1.33 (10−8); +0.09, +1.26 (all-graph 12−10) (note Sec 22.6; REPORT); light 12−10: +0.43, +0.80 (results dossier) | F `diagnostics.light_stratum_vs_reference_MC` | Q18 | printed |
| Old estimate 14331.77075 (SE 0.14344) high by 0.084, z = −0.58 (note Sec 22.1; REPORT) | F `diagnostics.old_result`; `reference/C6_result_original.json` | Q19, Q27 | printed |
| Hard stratum binary64 − extended: 5e-9, 7.6e-8, 1.5e-7 at N = 6, 8, 10 (note Sec 22.3) | A `diagnostics.hard_dbl_minus_ld_C6` (maxgap) | Q20 | printed |
| L5 binary64 − long double at M = 40: 1.2e-6; old retained five-loop inputs move C6 by −1.4e-5 and −6.6e-6 (REPORT) | F `diagnostics.L5_double_minus_longdouble_C6_at_Nstar`, `retained_pole_config` | Q21 | printed |
| Earlier degree-six value differs from the present one by 9e-6 (note Sec 22.3) | A `levels.6.H6_vector` against `reference/full_H_L6_N6_0_10000.json`: −9.5e-6, −9.7e-6 | Q22 | 8e-6 to 1.1e-5 (the note's "9e-6" is a rounded figure) |
| Light-stratum perturbation sensitivity "about 1e-10", not growing with N (note Sec 22.3) | R `levels[N].rho_light` (6.6e-11 to 6.7e-10) | Q23 | < 1e-9 for all N |
| Graph counts 59,145 / 9,540 / 49,605 and 2,427,005 / 289,590 / 2,137,415; Σw_A, Σw_B, Σw_H; every surviving w_H negative (note Sec 22.2 table) | S `gates.V1_enumeration_nv{6,7}.info`; AC `graphs6`, `graphs7` | Q24 | exact |
| AMD/Intel: binary64 bitwise; extended precision to 1.7e-16 (note Sec 22.3; REPORT) | S `gates.V11_*` | Q25 | printed |
| About 45 node-hours on 64-core processors (note Sec 22.3; REPORT 44.5) | F `diagnostics.stopping.resources.production_node_hours` (44.489) | Q26 | printed |
| C7-package six-loop stages: 14332.43593 ± 0.30500 at +2.46; 14331.98210 at +0.97; 14331.62055 at −0.22; step −0.45383, tail ratio 0.443, tail −0.36156 (note Sec 22.6 and the C7(1) check table; REPORT) | X `stages`, `C7_package_SE`, `step7`, `tail_ratio`, `tail` | Q28, Q29, B11 | printed; bitwise regeneration from `C7_final.json` |
| Stage headlines N* = 16: 14331.687033 ± 0.000058; 18: 14331.6870328 ± 0.0000036; 20: 14331.68703273 ± 3.0e-7 (driver log, review log; not in the note) | regenerated stage `C6_N{n}.json` | B07 | exact string |

##### Records regenerated bitwise

| Record | Row |
|---|---|
| `assembled.json`, `rounding.json` | B02, B03 |
| `decisions/decision_N{16,18,20,22}.json` | B01, B06 |
| `C6_final.json`, after restoring the one diagnostic changed by ee2e013 | B04 |
| the 62 level records, re-merged from `data/C6_1/runs` (input paths compared relative to `runs/`) | B08 |
| the 21 weight tables of `weights_manifest.json` | B09 |
| `R6_comparison.json` | B10 |
| `C7_crosscheck.json` | B11 |
| `reference/six_loop_algebra_checks.json`, the exact check of the RG assembly with ∂C6/∂c6 = 1/729 and ∂C6/∂b6 = −1/2187 (note Sec 22.2) | B12 |
| `reference/assembly_lower6.json` | B13 |

The hash bindings are rows I01–I19.

##### Not replayed from shipped records

These come from the recon jobs of PLAN.md Sec 2 on symmetry: 564716, 564722 and 564724.
- "Plain binary64 accumulation … shifts C6 by about 1e-5 at N = 6 and 2e-5 at N = 8" (note Sec 22.3).
- The recon double-pole and simple-pole reproduction figures of PLAN Sec 2.1.
- The validation cost of about 10 node-hours (REPORT). No accounting record of it ships.

### `C6_research_note`

Folder: `code/C6_research_note/`.

#### Results map: analytic representation of C6(1)

Note = condensed note at commit `fa71533` (the quoted values and the section numbers are unchanged in the current
edition, 01c3f5d, review of 15 October 2026). P = `GFF/code/C6_research_note`, R = `GFF/code/LRI_C6_closed_form_review`,
Q = `GFF/results/C6_1/analytic/quoted_numbers.json`. "replay" = `make -C P -f public.mk replay`, "review replay" =
`make -C R -f public.mk replay`; the row id is the id in the PASS/FAIL table.

| Quoted number (where) | Record | Command (row id) | Tolerance and why |
|---|---|---|---|
| C6(1) = 14331.68703275805 (abstract, Sec 1 table, 22.1, 22.10) | P `outputs/reassembly.json` `C6_reassembled_real_form`, regenerated by `code/make_outputs.py` | replay (`value.rounded_...`) | exact digits after rounding to 11 decimals |
| C6(1) = 14331.68703275805432044546325524621711831732... (Sec 1.2, 22.9) | same | replay (`value.leading_sec1.2_sec22.9`) | exact leading digits (38 decimals) |
| 14331.6870327580543204454632552462171183173230619887904582... (package note `\Crefval`, README) | same | replay (`value.leading_package_note_Crefval`) | exact leading digits (52 decimals) |
| the regenerated reassembly (8 blocks, 9 fixed values, C6 in three forms, discrepancies, exact polynomial checks) | P `outputs/reassembly.json`, `outputs/tables/*.csv`, `inputs/canonical/*.json` | replay (`reassembly.*`) | 1e-85 relative (110-digit assembly printed to 90-110 digits; allows mpmath/sympy version differences); 1e-37 for the 40-digit Barnes values G7, H7; canonical JSON bitwise; CSV 1e-30 relative |
| sector table E/2187 ... 96P_a/2187, 9 decimals (Sec 22.9) | P `outputs/reassembly.json` `blocks_r6` (E = known_real + (476/3)pi^3(32G+9pi^2), S_pol = known_real + log_sine_and_Clausen - E) | replay (`sector_table`, `sector_table.sum`) | exact digits; the sum equals C6 to 1e-84 (blocks printed to 90 significant digits) |
| interval width below 1.2e-145 (Sec 1.2, 22.9) | P `outputs/rerun/complete_refined/generated/results/complete_refined.json` | replay (`interval.width`, `interval.encoding`) | exact rational arithmetic on the dyadic bounds (2^-1280) |
| the quoted digits are certified (both bounds) | same | replay (`interval.digits.*`) | exact: both bounds truncate to the quoted string |
| reassembly inside the certificate; stage record identical; smoke ⊃ release ⊃ refined | same, and `code/stages/C6_complete_interval/results/complete_refined.json` | replay (`interval.contains_reassembly`, `interval.stage_record`, `interval.nested`) | 1e-90 (110-digit reassembly, observed 4.3e-93); bitwise; exact |
| graph sum 14331.68703276838 and 14331.6870328(5) (Sec 1, 1.2, 22.9) | `C6_final.json` of LRI_C6_1D_HPC (`headline.C6_unrounded`, `allowance_U`; sha256 `3ff496c2...`), pinned in Q | replay (`graph_sum.record`, `graph_sum.printed`) | exact digits; SKIP of the record row if the file is not found (pinned value used) |
| representation lies 1.03e-8 below the graph sum (Sec 1.2, 22.9) | reassembly and graph-sum record | replay (`difference.below`) | 3 significant digits |
| agreement to 1.0e-8 (abstract, Sec 1, 22.1, 22.10) | same | replay (`difference.agreement`) | 2 significant digits |
| 0.021 of the allowance (Sec 1.2, 22.9) | same | replay (`difference.allowance`) | 3 decimals |
| 3e-11 relative (Sec 1.2, 22.9) | same | replay (`difference.relative_level`) | 1 significant digit; it is U/C6 = 3.4e-11 (the difference itself is 7.2e-13 of C6; see SUMMARY open question 3) |
| R_{147,-3} = R_{148,-3} = 2/5; repair +659.278983 (22.9), +659.279 (1.2); 13672.408 without it (22.9) | P `complete_refined.json` `unchanged_source_correction` (polynomial evaluated at 60 digits) | replay (`repair.*`) | exact digits |
| PSLQ found no relation in three bases (Sec 22.9) | P `code/stages/C6_closed_form_attempt_report/recognition.json` | replay (`pslq.rerun`: `recognition.py` rerun, 150 digits, tol 1e-125, coefficients < 1e6, about 1 s) | exact: no relation in each basis; bases identical to the shipped record |
| review: reduced input re-evaluated to about 65 digits (Sec 22.9; REVIEW.md: difference 2e-66) | R `checks/reduced_input/assembly.json` vs P reassembly | review replay (`reduced_input.C6`) | absolute difference below 1e-65 |
| review: eight blocks to 69-81 digits (REVIEW.md) | R `checks/reduced_input/assemble.log` (and `assembly.json`) | review replay (`reduced_input.blocks`, `reduced_input.blocks_json`) | each in [69, 82) significant digits as printed by the review at full working precision; >= 69 from the 70-digit JSON |
| review: series and periodization identities better than 1e-63 (Sec 22.9) | R `ordinary.json` (eq:Pbseries, eq:B8series recomputed at 100 digits), `wheel.log`, `primitive_dps95.json`, `polylog.log` | review replay (`identities`) | 10 residuals, each below 1e-63 relative (observed 1e-69 to 1e-91, contour relation 0) |
| review: nine values by separate codes to 40-64 digits; eq. 3.5 rebuilt to 4e-50 | R `checks/final_values/{polylog_out,gvals_mb_50,reduced1d_40,primitive1d_40}.json`, `assemble.out` | review replay (`nine_values.1d`, `nine_values.reassembly`) | >= 40 digits (G7, H7 are stated to 40); rel diff <= 1e-49 |
| review: two-fold integrals directly, to 9-14 digits (Sec 22.9) | R `checks/final_values/h2d_nested.json`, `h2d_trap_{HW,H7,HP}.json` | review replay (`two_fold.direct`) | finest estimates all in [9, 15) digits (double precision; 9.2 is H* on the untilted contour) |
| review: repair +659.278983198744, difference -1.03e-8 = -0.021 U, 13672.408 | R `checks/c6_repair.py` (rerun, 30 digits) | review replay (`repair_and_graph_sum`) | exact digits as printed in REVIEW.md |
| fresh run of the 22 final-method tasks reproduces every shipped task output and the reassembly | P `outputs/rerun/<task>/` | `make -C P -f public.mk rerun-final` (one core, about 1 min) | bitwise for exact dyadic certificates and exact checks; 1e-30 relative for floating values; timing keys ignored |
| fresh run of the review's 49 commands gives the same agreements | R `.work/checks/` | `make -C R -f public.mk rerun` (one core, 17-29 min) | the review-replay tolerances above; exit status 0 for the 49 commands |

### `LRI_C6_closed_form_review`

Folder: `code/LRI_C6_closed_form_review/`.

_same as the section above (one text for the whole unit)._

## Finite kernels, power compensation, C6(2) and C6(3)

### `lri_C6_d2_complete_update`

Folder: `code/lri_C6_d2_complete_update/`.

#### Results map: d = 2 power-sector compensation and finite-scheme audits

Every number that note fa71533 quotes from `lri_C6_d2_complete_update` records. Command: `make -f public.mk replay` in
`GFF/code/lri_C6_d2_complete_update` (row names as printed). Paths are abbreviated:

| Short form | Full path |
|---|---|
| `R/` | `GFF/results/C6_2/power_compensation/` |
| `P/` | `GFF/code/lri_C6_d2_complete_update/reproduction/` |
| `N` | `lri_C6_d2_two_forest_update` |

Status column:
- **PASS(rerun)**: the delivered script was rerun and its record reproduced string-identically on 2026-10-13 (macOS,
  two Python stacks).
- **PASS(record)**: read from the shipped record.

Tolerance for every quoted row: half-even rounding to the printed digits.

##### Sec 24.1–24.3 (power-sector compensation, d = 2)

| Note | Quoted | File → field | Status |
|---|---|---|---|
| 24.3 (done:powerSums) | b_3^p = −4, c_3^p = −4/3 | `R/verification/power_cancellation_high.json` → `power_sector_sums.3` | PASS(rerun), within 1e-40 |
| 24.3 | b_4^p = 16A+24, c_4^p = 8A/3+8 | same → `.4` | PASS(rerun), within 1e-40 |
| 24.3 | b_5^p = −1540.38932947914290838…, c_5^p = −251.621917341000466476… | same → `.5` | PASS(rerun) |
| 24.3 | higher-order part / 2187 = 1.535501191157190785360393154334… | same → `higher_piece`; `R/verification/power_sector_audit.json` → `higher_part` | PASS(rerun) |
| 24.3 | Delta_p = −8.03e-34 (note) → **−8.02e-34** | `R/verification/power_cancellation.json` → `power_contribution_C6` (−8.0229e-34) | PASS(rerun) against −8.02e-34; **erratum E2** |
| 24.3 | Delta_p = 6.91e-47 | `.._high.json` → `power_contribution_C6`; audit → `computed_delta_C6`, `two_settings_delta_C6` | PASS(rerun) |
| 24.3 | sunset insertions L6G106, L6G117: 16 P4(2) each to b6, 32 P4(2) in all, 0 to c6 | `R/verification/analytic_extension_audit.json` → `sunset_contractions`; `power_cancellation*.json` → `sunset_on_wheel_contribution` | PASS(rerun) |
| 24.2 | Cauchy settings 32 nodes, r = 0.02, 45 digits; 48 nodes, r = 0.016, 55 digits | audit → `Cauchy_runs`; headers of `P/position_kite_leaf_ms_*.json` | PASS(rerun) |
| 24.2 | 2699 pole coefficients | audit → `pole_coefficients_compared` | PASS(rerun) |
| 24.2 | max discrepancy 7.39e-30 (note) → **7.38e-30** | audit → `max_absolute_comparison` (7.3822e-30) | PASS(rerun) against 7.38e-30; **erratum E1** |
| 24.2 | max discrepancy between admissible roots 7.97e-45 | audit → `max_root_discrepancy` | PASS(rerun) |
| 24.2 | all five powers one gives J = 3 Q_2; 3 symmetric tests, 5 completion transformations, changed-tail check | `R/reproduction/klt_checks.json` → `checks[*].kind/value`; Q_2 from `P/N/verification/reference_periods.json` | PASS(rerun); 3/5/2, max error 2.2e-43 |
| 24.1 | closed Gamma-sector classes 1, 2, 6, 15, 47, 137 | `P/N/analytic/verification/sp_exact.json` → `loops[*].count` | PASS(record); `regen` recomputes (sp_exact.py) |
| 24.1 | b_2 = −6A, c_2 = −A; b_3^Γ = 336ℓ²−4, c_3^Γ = 52ℓ²−4/3 | sp_exact.json → `loops[1..2].b/c` | PASS(record), exact sympy comparison |
| 24.1 (two:c5Gamma) | c_5^Γ polynomial | sp_exact.json → `loops[4].c` | PASS(record), exact |
| 24.1 (two:GammaAnswer) | 2187 Ξ_Γ polynomial | sp_exact.json → `loops[5].b/c`, `loops[4].c` | PASS(record), exact |
| 24.1 (two:GammaNumbers) | 12.17588503555361667474529…, Ξ_Γ = 4.274679502470384138347130… | computed from sp_exact.json at 45 digits; `R/reproduction/N/analytic/verification/gamma_and_coverage_checks.json` → `gamma_six_loop_only_value`, `gamma_physical_combination_value` | PASS(rerun of check_gamma_coverage.py) |

##### Sec 25.1–25.3 (finite-scheme assembly)

| Note | Quoted | File → field | Status |
|---|---|---|---|
| 25.1 | forest-to-RG polynomials, 532 beta and 383 mass monomials at six loops, all differences zero, all six orders | `R/reproduction/N/forest_exact_checks.json` → `checks` | PASS(record); rerun needs the unshipped forest files. The identity is also used by the C7(2) builder. |
| 25.2 | 1, 5, 16, 76, 395 nonzero kernels at L = 2–6; 493 exact Kirchhoff checks | `R/reproduction/kernel_map_checks.json` → `checks[*].graphs`, `total` | PASS(record); rerun needs the unshipped `powerfree_forests.json` (13 MiB). The same kernels ship in `LRI_C6_D2_HPC/inputs/`, and the C7(2) builder regenerates them (`legacy_mapping.json`). |
| 25.3 (done:twoLoopNumbers) | b_{2,0..4} = −16.63553233344, 29.02087369541, −47.11795797162, 74.14063002868, −114.64528966290 | `R/reproduction/fresh_two_loop_mom.json` → `records[0].b2_jets` | PASS(rerun); also equal (rel 0.0) to `GFF/code/LRI_C6_D2_HPC/inputs/two_loop.json` → `B2` |
| 25.3 | radii 0.05 and 0.08, 64 and 80 nodes, 65 digits; agreement with the saved input better than 6.8e-61 | same → `records[*].radius/nodes`, `dps`, `largest_difference_vs_saved_input` (6.785e-61) | PASS(rerun) |
| 25.3 | 192 exact checks, 24 of the constant-MS sixth-order assembly | `R/reproduction/mom_lagrange_checks.json` | PASS(rerun) |

##### Cross-checks with other units (optional rows; SKIP if the file is absent)

| Row | Source | Result (2026-10-13 mock) |
|---|---|---|
| power records byte-identical to the C6(2) package's copies | `GFF/code/LRI_C6_D2_HPC/reference/baseline_previous/baseline/lri_C6_d2_complete_update/verification/` | 3/3 |
| C6(2) + Delta_p = published estimator in double precision | `GFF/results/C6_2/C6_result.json` → `C6` = 362.36647176375726 | equal |
| explicit sixth-order power correction of C7(2) vs Delta_p (note Sec 28.7 quotes (3.3 ± 11.8)e-4) | `GFF/results/C7_2/C7_result.json` → `power_differences[6]`, `power_difference_errors[6]` | pull +0.28. The quoted value is owned by C7_2. |

##### Not replayed (archived records of the superseded estimator; note_changes.md A1–A6)

The following live only in `LRI_complete_research_bundle.zip`, which is not part of the repository:
- **Sec 23.** P3P4, 140.4255…, 4.49e-61, 158 checks, the Run A/B table, (two:inputNumerics), (two:jointNumerical),
  (two:additionalMassNumber), f2 and the control slopes.
- **Sec 25.4.** Run C, the 21703 binary128 calls and the 0.85 exponents.

K76 (done:knownMOM76) and P10, S26, S40 (meth:retained) are also in
`GFF/code/LRI_C6_D2_HPC/reference/.../mom_known_sectors.json`; the C6_2 unit owns them.

### `lri_C6_d3_complete_update`

Folder: `code/lri_C6_d3_complete_update/`.

_same as the section above (one text for the whole unit)._

### `LRI_C6_D2_HPC`

Folder: `code/LRI_C6_D2_HPC/`.

#### C6(2): every quoted number -> record, command, tolerance (note at fa71533; paper at f496d39a: `numbers.tex`, Table tab:pt)

Command for all rows marked `replay`: `make -f public.mk replay` in `GFF/code/LRI_C6_D2_HPC` (1 s; 78 rows: 75 PASS,
3 SKIP for the hosted files, 0 FAIL with numpy 1.23.5, 1.24.4 and 1.26.3). `R` = `GFF/results/C6_2/C6_result.json`;
`D` = `GFF/data/C6_2/run-20260928-m8192/`. "Printed digits": the recomputed value, printed with as many decimals as the
note, must equal the quoted text. The underlying fields are compared first to relative 1e-12 (headline) or 1e-7
(pulls, bootstrap, covariances); see `public/replay.py`.

| Quoted (where) | Value | Record and field | Command | Tolerance | Status |
|---|---|---|---|---|---|
| Value in the note (abstract l.62; Sec 1 table l.102; Sec 24.6 l.10059; boxed l.10149; note README l.41): allowance = 4 SE rounded up to a multiple of 0.001 | 362.366 ± 0.004 | `R.C6` rounded to 0.001; allowance = ceil(4 `R.sampling_standard_error` / 0.001) × 0.001 | replay | printed digits; allowance computed in Decimal | final |
| Value in the paper (`\CsixTwo`, numbers.tex l.26, Table tab:pt in perturbation.tex l.25; PDG rounding adopted 2026-10-14): 4 SE = 0.0031989 to two significant digits | 362.3665 ± 0.0032 | `R.C6`, `R.sampling_standard_error` | `make -f public.mk replay` (row "paper form (PDG rounding)") | printed digits | final |
| 4 SE (Sec 24.6) | 0.0032 | 4 `R.sampling_standard_error` | replay | printed digits | final |
| Estimator and SE (Sec 1 l.124) | 362.36647176375726, 0.0007997307 | `R.C6`, `R.sampling_standard_error` | replay | estimator relative 1e-12 (not bitwise across numpy builds); SE printed digits | final |
| Campaign table (Sec 24.6 l.10046-10048) | a 362.36672022 ± 0.00097561; b 362.36622331 ± 0.00126747; combined 362.36647176 ± 0.00079973 | `R.campaigns.{a,b}.{C6,sampling_se}`, `R.C6`, `R.sampling_standard_error` | replay | printed digits | final |
| Result table (Sec 24.9 l.10160) | 362.36647176, 0.00079973 | same | replay | printed digits | final |
| Campaign difference (l.10050; README l.73) | 0.31 combined SE | (a − b)/hypot(se_a, se_b) | replay | printed digits; gate ≤ 3 | final |
| Projection (l.10051-10053) | 0.0015, "about half" | archived fresh-only SE (`reference/verification/method_precision_results.json` ["2"]["fresh_only"]) / sqrt(2 × 8192); ratio 0.52 | replay | printed digits | final |
| Previous estimator and distance (l.10055-10056; README l.64, l.73) | 362.3489138 ± 0.1526445; 0.12 | `reference/verification/method_precision_results.json` ["2"] (hash checked against `reference/SHA256SUMS.json`); (C6 − old)/old SE | replay | printed digits; gate ≤ 3 | final (superseded estimator) |
| "190 times smaller" (note README l.73) | 190 | old SE / new SE = 190.9 | replay | integer part (the README truncates; 191 if rounded) | wording: optional fix "about 190" |
| C7(2) by-product (l.10063-10066; Sec 28 table l.11204; README l.73, l.77) | 362.3727 ± 0.0086 (362.3727456 ± 0.0085778), +0.73 | `GFF/results/C7_2/C7_result.json` (sha256 5c7a3318... checked) `coefficients[6]`, `standard_errors[6]`; pull against `R` | replay | printed digits | final; the C7 file's own `lower_order_checks` still uses the old reference 362.3489, so +0.73 exists only here |
| Error budget, d = 2 (Sec 24.8 l.10394) | 0.000005, 0.000113, 0.000365, 0.000702, 0.000000, 0.000800 | `R.error_by_loop`, `R.shared_reference_standard_error`, quadrature total | replay | printed digits | final |
| Lower-order pulls (l.10404; README l.73; `\PTlowerPullMax` = 2.3 of numbers.tex bounds them; not printed in the paper at f496d39a) | −0.97, −1.54, −1.07 | `R.lower_order_checks[].pull` (references in `tools/assemble.py`) | replay | printed digits; gate ≤ 4 | final |
| Bootstrap (l.10416-10420; README l.73) | 0.00080124 (4,096 resamples), mean − estimate −1.3e-5 | `R.bootstrap` | replay (recomputed with seed 82491001) | printed digits (field relative 1e-7; 7e-13 seen) | final |
| Archived Lagrange and delete-one checks, d = 2 (l.10411-10414) | 7e-13; below 3.4e-7 | `reference/verification/extra_checks.json` ["2"] `max_Lagrange_difference`, `nonlinear_jackknife_bias` | replay (reads the archived record) | printed digits; bound | final (archived checks of the previous estimator) |
| Sample design (l.10013-10027) | 5/16/76/395 classes; 64 replicates; 52- and 60-bit nets; separable map only in a at L=6; floor 4 × 2^13 on 28 kernels; 1,107,296,256 / 2,164,260,864 / 9,487,515,648 / 38,076,809,216 (385 kernels) / 5,645,533,184 (10 primitives) points per replicate; 7,229,621,141,504 samples | `D/groups/*/config.json` (`counts`, `samples`, `replicates`, `net.bits`, `grid`), `D/manifest.json` (`allocation_multiplier`), `tools/primitive_allocation.py` (`PIDS`) | replay | exact | final |
| Floor kernels have zero C6 projection (l.10019-10020) | 28 kernels | `D/groups/{a,b}_L6/graph_replicates.csv`: max |−b6 + 3c6|/(|b6| + 3|c6|) = 5.6e-20 over 3,584 sums (dC6/d(b6,c6) ∝ (−1, 3)) | replay | < 1e-15 | final |
| Execution (l.10039-10040) | 428 elements of 64 threads; 12,535 core-hours | `D/manifest.json` (`jobs`, `threads`); 12,535 from Slurm accounting (`GFF/results/C6_2/CAMPAIGN.md`); replay checks the native integration time in the merged records, 12,467 core-hours, is 0.97-1.00 of it | replay | exact / bracket | final (billed figure recorded, not recomputable) |
| Thread identity (l.10040-10043) | 2 × 1,024 tasks identical at 64 and 16 threads, 152,717 binary128 promotions | `GFF/results/C6_2/preflight/threadcheck-54508994.out` (THREADCHECK line) | replay reads the record; rerun template in REPRODUCE.md (64-core node, about 2 min) | exact | final (recorded) |
| Legacy-mode replay of all 492 kernels (l.10008-10011) | below 9e-20 normalized, equal promotion counts | output of `tests/validate.py` | `make -f public.mk test` (x86-64 Linux; see CLUSTER_CHECKS.md) | the test's own criteria (max 8.75e-20 recorded) | final |
| Fallback thresholds (l.10007-10008) | 1e-9, 1e-23 | `src/kernel.hpp` | code | exact | final |
| Combination rule (boxed eq. prec:d2combined, l.10032-10036) | (μ^a + μ^b)/2, σ_common = 0 | `R.campaign_weights` {a: 0.5, b: 0.5}, `R.shared_reference_standard_error` 0, `R.primitive_mode` recompute | replay (field comparison) | exact | final |
| Used elsewhere: C6(2) as the reference of the C6 by-product of C8(2) (Sec 31 l.11910: 362.3625083 ± 0.0116244, −0.34) | 362.36647176375726 ± 0.00079973 | hard-coded in `LRI_C8_D2_HPC/tools/assemble.py` | the C8_2 replay | — | owned by C8_2 |

### `LRI_C6_D3_HPC`

Folder: `code/LRI_C6_D3_HPC/`.

#### C6(3): every quoted number → file, command, tolerance

Note: `GFF/LRI_condensed_note/long_range_ising_condensed.tex` at `fa71533`.
- Section 1 (abstract-level summary, l. 62; table, l. 102; estimator table, l. 125; allowance sentence, l. 137–138).
- Section 26:
  - "Baseline campaigns" table, l. 9945–9946;
  - refinement table, l. 10334–10340;
  - "The three-dimensional production of September 2026" (`prec:d3production2026`), l. 10074–10148;
  - result, l. 10150–10161;
  - error budget, l. 10395;
  - final checks, l. 10405 and 10410–10419;
  - verification scope, l. 10427.
- `CAMPAIGN.md` (results/C6_3).
- Command: `make -f public.mk replay`, run from `GFF/code/LRI_C6_D3_HPC`. Row = the row of `.work/replay/REPLAY_C6_3.md`
  (52 rows; the local run is in `replay_local_run.txt`).
- Paths: `R` = `GFF/results/C6_3/results_run-20260929-m8192`; `P` = `GFF/code/LRI_C6_D3_HPC`.
- Every value below was recomputed on 2026-10-13 and agrees with the note.

##### Tolerances and why

- **Exact:** hashes, counts, design parameters, and the decimal rounding of the allowance (integers and strings; any
  change is a defect).
- **Relative 1e-12:** estimator and SE against `C6_result.json` and the note's 16-digit value. The float64 assembly
  (Jacobian products, BLAS) has CPU-dependent last bits: the Apple arm64 value is 33.57542664131542, the Expanse value
  33.57542664131543, i.e. 1 ulp; the C7(3) work measured 4 ulp on another CPU. 1e-12 is about 10⁴ ulp and still far
  below the 8th printed decimal.
- **Relative 1e-9:** every other float of `C6_result.json` (covariances, jet means, bootstrap). These are smaller
  quantities built from the same sums; the observed maximum deviation is 9.6e-14. The exception is the bootstrap mean
  shift, a difference of two O(30) numbers, which gets 1e-12 absolute.
- **Printed digits:** every number quoted in the note or `CAMPAIGN.md` is also compared at the precision at which it
  is printed (half-up rounding of the recomputed value).
- **Pulls and ratios:** printed to 2–3 decimals, so they are compared at that precision. Their gate thresholds (3, 4,
  ±20%) are checked as well.

##### Section 1

| quoted | value | file (field) | row | tolerance |
|---|---|---|---|---|
| C6(3) (summary, table) | 33.5754 ± 0.0005 | `R/C6_result.json` (`C6`, `sampling_standard_error`) → rule of `CAMPAIGN.md` | 41 (39, 38) | exact after rounding |
| underlying estimator | 33.57542664131543 | `R/C6_result.json` `C6` | 16, 18 | rel 1e-12 |
| sampling standard error | 0.0001185495235 | `R/C6_result.json` `sampling_standard_error` | 17 | 10 printed digits |
| allowance sentence: 4 SE rounded up to a multiple of 0.0001 | 0.0005 | same; `CAMPAIGN.md` Amendment 1 | 38, 39, 40 | exact (decimal) |
| table, d = 3 column, C0, C1, C2 | 3/2, −1/6, 0.181221785406 | `R/C6_result.json` `coefficients[0:3]` (exact inputs: `P/inputs/two_loop.json`) | 24 | exact, 1e-15, 12 decimals |
| table, C3, C4, C5 (d = 3) | −0.353581520433, 1.228063545, −5.850351421 | closed forms (`GFF/results/closed_forms_3/`, not this package); the same constants are `P/tools/assemble.py` `REFERENCE_LOWER`, against which the pulls are taken | 48 | printed digits |

##### Section 26.7 (`prec:d3production2026`)

| quoted | value | file | row | tolerance |
|---|---|---|---|---|
| nonzero classes at loops 3–6 | 5, 16, 76, 395 | `P/inputs/inventory.json` | 5 | exact |
| ten primitive six-loop kernels included | 10 | `P/tools/prepare_inputs.py` `PIDS`; `R/groups/*_L6/config.json` | 6 | exact |
| fallback thresholds | 10⁻⁹, 10⁻²³ | `P/src/kernel.hpp` | 14 | text |
| archived refinement streams replayed | 385,744,896 samples, fallback counts equal | `P/benchmarks/expanse_2026-09/logs/validation_54510646/archived_stream_replay.json`; `reference/records/new_*_d3_L*.json` | 35 | exact |
| refinement-only estimate reproduced bit for bit | 33.56084035 | same record (`C6_bitwise_identical: true`); recomputed from `reference/records` | 29, 36 | rel 1e-13 / printed |
| 64 replicates; conditional-draw map (layout 0); 52/60 bits | — | `R/groups/*/config.json` | 10 | exact |
| allocation × 2¹³ | 8192 | `R/manifest.json` `allocation.multiplier`; `config.json` vs `P/inputs/counts_L*.json` | 7 | exact |
| points per replicate, L = 3..6 | 1,241,513,984; 2,499,805,184; 9,743,368,192; 35,891,576,832 | `R/groups/*/config.json` `counts` | 8 | exact |
| kernel samples, both campaigns | 6,320,161,816,576 | `config.json` `samples` | 9 | exact |
| hashed group seeds | — | `config.json` `seed_scheme` | 10 | exact |
| weights w_a = w_b = 1/2, σ_common = 0 | — | `R/manifest.json` `campaign_weights`; `C6_result.json` `shared_reference_standard_error` | 11, 22 | exact |
| 458 independent 64-thread array elements | 458, 64 | `R/manifest.json` `jobs`, `threads` | 12 | exact |
| thread identity: 2 × 1024 tasks at 64 vs 16 threads identical, 141,994 binary128 promotions | — | `CAMPAIGN.md` only (job 54515886; logs not archived) | — | not replayable (documented) |
| campaign a | 33.57562307 ± 0.00015062 | `R/C6_result.json` `campaigns.a` | 19 | printed |
| campaign b | 33.57523021 ± 0.00018311 | `campaigns.b` | 20 | printed |
| combined | 33.57542664 ± 0.00011855 | `C6`, `sampling_standard_error` | 21 | printed |
| a/b difference | 1.66 combined SE | `campaigns` | 42 | printed; gate ≤ 3 |
| SE / plain-MC projection 0.00022 | 0.54 | `R/manifest.json` `estimates.projected_C6_sampling_se` | 49 | printed |
| distance from the previous estimator 33.5681968 ± 0.0241840 | 0.30 previous SE | `reference/verification/method_precision_results.json` `3`, recomputed from `reference/records` and `reference/baseline_previous/records` | 32, 44 | rel 1e-12; printed |
| distance from the refinement-only estimate | 0.52 refinement SE | as above (`fresh_only`) | 29, 51 | printed |
| 4 SE | 0.00047 | `C6_result.json` | 38 | 2 significant digits |
| C6(3) = 33.5754 ± 0.0005; first-registered step 0.001 | 0.0005; 0.001 | `CAMPAIGN.md` rule and Amendment 1 | 39, 40, 41 | exact |
| C7(3) by-product | 33.57387 ± 0.00198, −0.79 combined SE | `GFF/results/C7_3/run1-20260930-m4096/C7_result.json` `coefficients[6]`, `standard_errors[6]` (C7(3) group; the path is a proposal); the note's l. 11364 gives 33.5738672 ± 0.0019782 | 52 | printed |

##### Section 26: result, budget, final checks, baselines, refinement

| quoted | value | file | row | tolerance |
|---|---|---|---|---|
| eq. `meth:reported` (l. 10150) and verification scope (l. 10427) | C6(3) = 33.5754 ± 0.0005 | as Section 1 | 41 | exact |
| estimator table (d = 3) | 33.57542664, 0.00011855 | `C6_result.json` | 21 | printed |
| error budget (d = 3): L3, L4, L5, L6, common, total | 0.000001, 0.000021, 0.000058, 0.000101, 0.000000, 0.000119 | `C6_result.json` `error_by_loop`, `shared_reference_standard_error` | 22 | printed |
| lower-order pulls (d = 3) | −1.69, −1.09, +0.92 | `C6_result.json` `lower_order_checks` | 45–47 | printed; gate \|pull\| ≤ 4 |
| bootstrap SE (d = 3), 4096 resamples | 0.00011534 | `C6_result.json` `bootstrap` | 28, 43 | printed; recomputed with the production seed |
| bootstrap mean − estimate (d = 3) | +2.1 × 10⁻⁸ | same | 28 | printed (abs 1e-12 against the file) |
| previous estimator diagnostics (d = 3): Lagrange agreement, delete-one bias | 5 × 10⁻¹⁴, below 6.5 × 10⁻⁸ | `reference/verification/extra_checks.json` `3` | 37 | read, printed |
| baseline campaign A (d = 3) | 33.590772 ± 0.057948 | `reference/baseline_previous/records/prod_a_d3_L*.json` via `assemble.combine` | 33 | printed |
| baseline campaign B (d = 3) | 33.560344 ± 0.053265 | `…/prod_b_d3_L*.json` | 34 | printed |
| refinement A, B, refinement only (d = 3) | 33.59417512 ± 0.040029; 33.52750475 ± 0.039502; 33.56084035 ± 0.028119 | `reference/records/new_{a,b}_d3_L*.json`; `method_precision_results.json` | 29–31 | rel 1e-12; printed |
| refinement campaigns: 385,744,896 kernel evaluations at d = 3 | — | `reference/records` | 35 | exact |
| per-replicate points of the refinement (d = 3 row of the table at l. 10318) | 151,552; 305,152; 1,189,376; 4,381,184 | `P/inputs/counts_L*.json` (sum with zero targets raised to 4 = production per-replicate points / 8192) | 8 (implied) | exact |

The d = 2 entries of the shared Section 26 tables belong to C6(2) (C62d).

##### CAMPAIGN.md only

| quoted | value | row |
|---|---|---|
| plan: 458 jobs, 6.32e12 samples, 9,653 core-h, projected SE 0.00022 | | 9, 12, 13 |
| precision: 204× below the archived 0.0242 | 204 | 50 |
| C3–C5 estimates and SEs | −0.3535815650 (2.6e-8), 1.2280621550 (1.3e-6), −5.8503379659 (1.5e-5) | 25–27 |
| error by loop | L3 1.1e-6, L4 2.1e-5, L5 5.8e-5, L6 1.0e-4 | 23 |
| archived-value gate | 33.5754 − 33.5682 = +0.0072 = 0.30 archived SE | 44 |
| bootstrap ratio | 0.973 | 43 |
| C4 pull (erratum) | −1.09 | 46 |

Not replayed:
- the preflight timing (975 s, utilisation 0.979, RSS 121 MB) and the wall-clock log, which live only in the
  `CAMPAIGN.md` narrative;
- the thread-identity check (above).

The total of 1,402,407,967 binary128 and 185 300-digit promotions is printed as INFO (row 15). The note does not quote
it.

## Full C7(1), C7(2), C7(3)

### `LRI_C7_HPC`

Folder: `code/LRI_C7_HPC/`.

#### C7(1): quoted numbers -> records, commands, tolerances

Note = `GFF/LRI_condensed_note/long_range_ising_condensed.tex` at commit fa71533 (abstract l. 63; Section 1 tables
l. 103, 126 and allowance passage l. 139-141; Section 22 l. 8152-8160; Section 27 "Full seventh order in one dimension"
l. 10431-10928; Section 30 table l. 11544; Section 33 row l. 12342). The section numbers are unchanged in the current
edition (01c3f5d, review of 15 October 2026), where the Section 1 allowance passage became a table of rules with the
C7(1) paragraph below it and the Section 27 zero-pole sentence reads "71.6 above the uncontrolled". REPORT = `GFF/results/C7_1/REPORT.md` (68dc6be).
All paths below are relative to `GFF/`. `R` = `results/C7_1/`, `F` = `R/C7_final.json`, `A` = `R/combined_assembly.json`,
`P` = `code/LRI_C7_HPC/`.

Commands: Tier 1 `make -C code/LRI_C7_HPC -f public.mk replay` (git only, about 5 s, one core; 214 checks, table in
`code/LRI_C7_HPC/.work/replay7_tier1.txt`). Tier 2 `make -C code/LRI_C7_HPC -f public.mk fetch-data replay-full`
(hosted records; about 7 min, one core, < 2 GB; run 2026-10-13 on Expanse from the unpacked archive, job 54901438: 14 checks PASS).

Tolerance rules (Tier 1):
- **exact**: integers, strings, lists of labels or seeds, SHA-256 values.
- **sum 1e-12**: re-summation of the stored component means/covariances in the production order (assemble.py); the
  replay reports whether the result is bitwise identical (it is, on the Mac: every row "bitwise").
- **batch 1e-12 / 1e-10**: per-batch values rebuilt as 399 x (combined component) + retained primitive: C7 to 1e-12
  relative, SE to 1e-10 relative (observed max differences 3.5e-10 absolute on C7 ~ 3e5 and 8.5e-14 on SE ~ 200).
- **quoted**: the recomputed value rounded to the quoted number of digits equals the quoted text (rounded up for the
  allowances and the tree-point bounds, which the sources round up); one REPORT digit that is truncated instead of
  rounded is a WARN.
- **RECORDED**: needs the raw replicate streams; Tier 1 checks the recorded value and the arithmetic around it, Tier 2
  recomputes it (floats to 1e-12 relative, bootstrap SE to 1e-12 or WARN within 5% if NumPy's stream differs).

##### Headline and estimator

| Quoted | Where | Source / recomputation | Tolerance |
|---|---|---|---|
| C7(1) = −322550 ± 41 (the paper: ± 40, PDG rounding of 40.35; the note rounds the allowance up) | abstract, Sec 1 table, eq. c7f:answer, REPORT | K (P/reference/verification/full_affine_assembly.json) + sum of the 9576 estimator components of F (`components`, order of `sources`); allowance = ceil_2sf(max(4SE, 2\|R6\|+4SE_R6, 2\|R7\|+4SE_R7, half-split shift)+0.01) | sum 1e-12; quoted; allowance exact |
| estimator −322549.8888129889, SE 10.08791295 | Sec 1 estimator table | as above; SE = sqrt(cov77) | sum 1e-12; quoted |
| −322549.889, 10.088; bootstrap 10.111 | c7f:answer text | as above; bootstrap RECORDED (`F.bootstrap_se`) | quoted; Tier 2 |
| ±41 is the pre-registered policy, does not include truncation | Sec 1, c7f | candidates below | exact |
| −322524 ± 38 (truncation-aware, post hoc) | Sec 1, eq. c7f:truncationAware, REPORT | E6 + R7 + R7·r/(1−r), r = R7/R6 (C7 slots of `check_levels.refine7`, `power_levels.refine6`); σ = SE ⊕ SE_R7 ⊕ tail = 18.6; 2σ rounded up = 38 | quoted (ceil for 38) |
| step +10.40 ± 0.43, tail +15.59, ratio 0.600 (10.395/17.329), E7 −322539.5, −322523.9 | c7f, c7f:checks table, REPORT | same | quoted |
| shift +26, +26 + 2SE ≈ 46; intervals [−322591, −322509], [−322562, −322486] | REPORT | same | quoted |

##### Production, levels and allowance

| Quoted | Where | Source / recomputation | Tolerance |
|---|---|---|---|
| 399 batches (b001–b400 except b215) | c7f:production, REPORT, R/inclusion.txt | `A.batches` labels; seeds = sha256("C7-expanse-2026-09:batch:k")[:8] LE | exact |
| replicates 128 (power-free), 128/64 (coarse A/B), 128, 128, 64 (1→3, 3→5, 5→6), 64 (6→7 check) | c7f:production | `components[*].replicates` | exact |
| weights: power-free 1/2 each, coarse 2/3 and 1/3, refinements 1, primitive 1 (each /399) | c7f assembly | `A.sources[*].weight` vs P/tools/production.py specs() | exact |
| primitive −696179.472 ± 0.867 (REPORT −696179.47 ± 0.87; variance (0.8667)²); retained −696147.446 ± 25.368; 1.26 combined SE | c7f, REPORT | component `primitive/P1`; `A.retained_primitive_crosscheck` (= P/reference/verification/C7_assembled_result.json) | sum 1e-12; exact; quoted |
| 44 primitive classes; 2^23 points, 64 replicates | c7f, REPORT | P/reference/inputs/L7_coord.txt (primitive && !power); P1 manifest (hosted, Tier 2) | exact |
| about 2.5×10^5 core-hours | c7f:production; REPORT "about 250k core-hours (SU) for all batches, plus about 20 for P1 and about 60 for the combines" | R/production_run.json (recorded text) | recorded |
| resolution sequence −331309.98/6.14, −322614.21/9.21, −322567.22/10.01, −322549.89/10.09 (REPORT one decimal) | c7f table, REPORT | prefix sums K + free + primitive + coarse + refine3 + refine5 + refine6 | sum 1e-12 vs `F.resolution_sequence`; quoted |
| corrections +8695.78/6.86, +46.99/3.93, +17.33/1.21, +10.40/0.43 | c7f table | level sums of the components | sum 1e-12; quoted |
| step ratios 0.37 and 0.60 | c7f | R6/R5, R7/R6 | quoted |
| candidates 40.35, 39.50, 22.49, 12.58 (REPORT 40.4, 39.5, 22.5, 12.6); archived policy ±1000 | c7f, REPORT | 4SE; 2\|R6\|+4SE_R6; 2\|R7\|+4SE_R7; max\|half_i − C7\| (half splits RECORDED) | sum 1e-12; quoted |
| χ² = 348.9 for 398 dof | c7f, REPORT | per-batch C7_b, SE_b rebuilt from components; centre = C7 − (P1 − retained); Σ(C7_b − centre)²/(SE_b² − 25.3678²) | batch 1e-12/1e-10; chi² 1e-9; quoted |
| bootstrap 10.11 vs 10.09 | c7f, REPORT | RECORDED | Tier 2 |
| halves −322537.30, −322562.47 | c7f | RECORDED (`F.half_splits`) | Tier 2 |
| power-free A/B agree within 0.42 combined SE | c7f | campaign aggregates tprodA/B_L5..7 (max 0.422) | quoted |
| 24 spurious poles, max \|z\| 2.31 | c7f, REPORT | `F.spurious_pole_checks` (means RECORDED; z = mean/SE recomputed) | Tier 2 |
| controlled estimate 71.6 ± 41.0 above the uncontrolled −322621.5 ± 41.1 (the record's control field is uncontrolled − controlled = −71.6) | c7f, REPORT | `F.zero_pole_control`, `F.raw_uncontrolled` (RECORDED; total = Σ per L and uncontrolled − controlled recomputed) | Tier 2 |
| flag "C5 differs from its reference by −4.15 SE" | REPORT | regenerated from the lower-order checks | exact |
| 17 transient step failures, each resubmitted once | REPORT | R/resubmitted_elements.txt | exact |

##### Lower orders and truncation

| Quoted | Where | Source / recomputation | Tolerance |
|---|---|---|---|
| C5 −731.174185 ± 0.008355 vs −731.139477 (exact); C6 14332.435930 ± 0.305002 vs 14331.687033 | c7f:checks table | coefficients[5,6], sqrt(cov); references from P/tools/assemble.py REFS and the C6(1) result (14331.68703277, optional cross-check with results/C6_1/C6_final.json) | sum 1e-12; quoted |
| z −4.15 / −1.88 / −0.30 (C5), +2.46 / +0.97 / −0.22 (C6, new exact) | c7f:checks, Sec 22, REPORT addendum | (value + step [+ tail] − ref)/own SE | quoted |
| C6 14332.43593 ± 0.30500, 14331.98210, 14331.62055 | Sec 22 (l. 8152), REPORT | same | quoted |
| C6 vs old reference 14331.77075: +2.18/+0.69/−0.49 (own SE), +1.97/+0.63/−0.45 (with SE 0.14344) | REPORT | same | quoted |
| tail ratios 0.408, 0.443, 0.600; C6 correction −0.815; reference's 14332.554 → 14331.755, then −0.007: −0.81 | c7f, REPORT | R7/R6 per coefficient; cited values found in P/reference/long_range_ising_complete.tex | quoted; exact (string) |
| differences from the new C6: +0.74890, +0.29507, −0.06648 | REPORT addendum | same; −0.066486 is truncated in the REPORT (rounded −0.06649) | quoted; WARN |
| C3 = −3.71985632290349, C4 = 45.4248801371166; discrepancies 1.5e-12, 3.4e-8 | c7f:checks | K (deterministic low-loop assembly) vs REFS | quoted |

##### Inherited construction (reference/, the September 2026 archive)

| Quoted | Where | Source | Tolerance |
|---|---|---|---|
| 3986 classes, 125894580 labelled graphs, 1091 power, 845 nonzero 3c7−b7, 44 primitive | c7f inventory | P/reference/inputs/L7_coord.txt, L7_inventory.txt (Σ 8!/\|Aut\|), exact_zero_L7.txt | exact |
| 691 exact-zero classes; 151 of the 845 are zeros, 694 integrated; 24 and 132 at L5, L6 | c7f | same, L5/L6 | exact |
| monomial table (1/1 ... 4164/2935), all differences zero | c7f | P/reference/verification/forest_exact_checks_new.json | exact |
| 44 representatives matched to 14 periods | c7f | P/reference/verification/primitive_coverage_new.json | exact |
| 84 exact Jacobians; Z = (L+1)!L for L = 1..7; 32 exact rational tests | c7f | P/reference/verification/affine_and_tree_exact_checks.json | exact |
| 650 digits, 60 cases, 1.18e-14, 3.45e-18 | c7f | P/reference/verification/tree_point_checks.json (1.1734e-14, 3.4420e-18, rounded up) | exact; quoted (ceil) |
| four-loop degree 16 → 20 moves C7 by < 0.001 | c7f | P/reference/verification/lower_resolution_check.json (9.4e-4) | exact |
| binary128 replay on 112 degree-7 elements: 2.8e-12 vs 1.9e-11, worst 4.2e-14 (A5 not met: 9 of 112, 18×) | c7f, REPORT | P/docs/NUMERICS.md (recorded); rerun: `tests/check_quad.py` on a cluster node (C++ build) | cited (string) |

##### Archive, v1 and the note README

| Quoted | Where | Source | Tolerance |
|---|---|---|---|
| archive −323405.3, SE 5861.8 (REPORT −323405 ± 5862, ±24000; note README (−3.23 ± 0.24)×10^5) | note README, REPORT | `tools/assemble.py --original` (about 1 s) vs P/reference/verification/C7_assembled_result.json and P/tests/fixtures/assemble_original_0227dc5.json | sum 1e-12 (bitwise on the Mac); exact |
| z = 0.15 against the archive | REPORT; note README "0.15 of its sampling error" | (C7 − archive)/hypot(SE, SE_archive) = 0.146 (also 855.4/5861.8) | quoted |
| v1 (46 batches): −322554 ± 39, ±160; z = 0.11 | REPORT | R/v1_46batches/C7_final.json; z ignores that v1's batches are a subset | quoted |

##### Tier 2 only (hosted records)

`replay-full` reruns `tools/combine.py` (verbatim, commit 7320afc) on the merged records with a light campaign verifier and
compares `combined_assembly.json` and `C7_final.json` with R byte for byte (else floats to 1e-12 relative, the two fields that assemble.py forms as differences of nearly equal numbers (applied_zero_pole_control_C7, lower_order_checks[].difference_over_sampling_se) to 1e-12 of their inputs, bootstrap WARN within 5%). Byte-identical on Expanse
(2026-10-13) and symmetry Intel Xeon 6148 (2026-10-14); on symmetry AMD EPYC 8534P C7_final.json differs in the last bits
(C7_full and sampling_se by 1 ulp) and passes at these tolerances; combined_assembly.json is byte-identical there too.
It also checks: every hosted merged stream against the SHA-256 recorded in F; one executable (sha256 33bab738...) and one
design (fd356a15...) in all 399 production.json; the P1 manifest (seed 3929792552365635731, 44 classes × 2^23 points,
64 replicates); each batch's own C7_result.json against combine's per-batch value.

### `LRI_C7_D2_HPC`

Folder: `code/LRI_C7_D2_HPC/`.

#### C7(2): every quoted number -> record, field, command, tolerance

Command for every row: `make -f public.mk replay` in `GFF/code/LRI_C7_D2_HPC` (script `public/replay_c7d2.py`; about
4 s; 108 PASS, 2 SKIP on 2026-10-13 with numpy 1.23.5, 1.26.3 and 2.4.4). Abbreviations: R = `GFF/results/C7_2/C7_result.json`;
D = `GFF/data/C7_2/run1-20260930-m4096/`; P = `GFF/code/LRI_C7_D2_HPC/`. "Recomputed" means recombined from the 20
merged records by the delivered `tools/assemble.py evaluate()` (fb64c47), bootstrap included. "Printed digits" means equal
after rounding to the digits the note prints. Line numbers are those of the note at git HEAD fa71533.

##### Field-by-field
| What | Source | Tolerance | Status |
|---|---|---|---|
| all 277 fields of R (230 numeric) | recomputed vs R | headline fields 1e-12 relative (|ref| > 1e-9; else 1e-12 absolute); cancellation-limited fields (power correction and its SE, power differences and their errors, covariances, bootstrap) 1e-7 relative or 1e-12 |C7| absolute; integers, strings, hashes exact. Observed: headline <= 4e-15 relative, cancellation-limited <= 1.8e-12 absolute | PASS |
| bindings | sha256 of D/manifest.json = R `source_manifest_sha256`; P/tools = the 4 tools pinned by the plan; inputs manifest and cost model as pinned; 20 configs (manifest), 20 merged (R `merged_sha256`), payload hashes, identities, shapes | exact | PASS |
| executable `7e3c8c92…`; `graph_replicates.csv` | not shipped / hosted | — | SKIP (2 rows) |

##### Note text (and paper)
| Quoted (note place, line) | Value | Record / field | Tolerance | Status |
|---|---|---|---|---|
| abstract (l.63), Sec. 1 table (l.103), eq. c7d2:reported (l.10970); paper `\CsevenTwo` (Table tab:pt, perturbation.tex l.26) | -3876.1 +- 2.1 | R `C7_full`; allowance ceil_0.1(max(4 `sampling_standard_error`, max_j |`half_streams[j][7]` - C7|)) | printed digits | PASS |
| Sec. 1 estimator table (l.127) | -3876.1260927949925, 0.5244496691 | R `C7_full` (exact string), recomputed (1e-12 |C7|); `sampling_standard_error` | exact / printed digits | PASS |
| Sec. 1 allowance sentence (l.142-144) | 4 SE rounded up to 0.1 | as above | printed digits | PASS |
| Sec. 28.1 table (l.10957-10959) | -3876.0700590 +- 0.5224502; -0.0560338 +- 0.0458637; -3876.1260928 +- 0.5244497 | R `power_free_C7`, `power_free_se`, `power_correction`, `power_correction_se`, `C7_full`, `sampling_standard_error` | printed digits | PASS |
| Sec. 28.1 (l.10967-10969) | 4 SE = 2.098; half-stream deviations 0.36 | R `sampling_standard_error`, `half_streams` | printed digits | PASS |
| Sec. 28.1 (l.10971-10975) | previous -3950 +- 310 (estimator -3953.6336215, SE 76.7310362); new 1.01 previous SE from it | P `reference/RESULT.json` (`reported`, `full_C7_2`, `sampling_standard_error`); re-assembled by P `tools/reassemble_reference.py` (its own gate 2e-8; observed 1.8e-12) | printed digits | PASS |
| Sec. 28.2 table and text (l.10995-11010) | classes 8/27/129/660/3986; power 1/5/31/173/1091; nonzero mixed 1/3/20/107/709; integrated power 1/3/20/107/590; 459 and 639 zero classes; 2,254 + 44 + 590; L3-L6 5/16/76/395 and 1/3/20/107; 1,301 classes by edge-subgraph enumeration | P `reference/power_mass/verification/full_graph_coverage.json` (`loops`, `seventh_order_partition`), P `inputs/manifest.json` (`counts`), P `reference/power_mass/verification/edge_forests_L3..7.json` | exact | PASS |
| Sec. 28.3 (l.11057-11059) | Kirchhoff check agrees exactly at 66 configurations incl. endpoint-scaled | P `reference/power_mass/verification/kirchhoff_checks.json` | exact | PASS |
| Sec. 28.4 (l.11105-11113) | [z]b3p = 18.6743207750 from two quadratures differing by 4.6e-10; production b3p(0) = -3.99999979 +- **0.00000042** (note prints 0.00000043: erratum), [z]b3p = 18.6743200 +- 0.0000021, pulls +0.50, -0.36 | P `reference/power_mass/verification/three_loop_radial_check.json` (`runs[].b3_1`, `b3_0`); D `groups/{a,b}_power_L3/merged.json` (campaign means and SE as in `assemble.calculate`); equal to R `means.power.3[0..1]` | printed digits | PASS (with the erratum) |
| Sec. 28.5 (l.11132-11135) | 24 + 24 exact Lagrange-extraction cases | P `reference/power_mass/verification/assembly_checks.json` | exact | PASS |
| Sec. 28.6 production text (l.11138-11163) | 3,511 kernels zero normalized difference, identical promotions; point checks; 5,776 rows identical at 64/16 threads incl. 31,663 GMP promotions; 64 replicates; 52-/60-bit nets; rates x0.8/x0.9; every stratum >= 4 points x 2^12; 44 primitives at 2^26 points; 1,094,688,178,176 samples; weights 1/2; 350-digit GMP | `GFF/results/C7_2/evidence/buildtest-566254/full_validation.json`, `check_points.log`, `evidence/buildtest-566254.out` (THREADCHECK); D `manifest.json`, `groups/*/config.json`, `groups/*/merged.json` (`samples`) | exact | PASS |
| Sec. 28.6 (l.11160-11162) | ran on 14 AMD and 14 Intel nodes in about 6.5 hours | `GFF/results/C7_2/CAMPAIGN.md` (from the job logs, not shipped) | — | log only, not replayed |
| Sec. 28.6 campaign table (l.11179-11184) | a -3875.3202 +- 0.7266; b -3876.9320 +- 0.7565; halves -3876.4894, -3875.7627; combined -3876.1261 +- 0.5244; campaigns differ by 1.54 combined SE | R `campaigns`, `half_streams`, `C7_full`, `sampling_standard_error` | printed digits | PASS |
| Sec. 28.6 error table (l.11190-11193) | free 0.0007 0.0047 0.0200 0.0590 0.5187; power 0.0000 0.0001 0.0013 0.0130 0.0440 | R `error_by_loop` | printed digits | PASS |
| Sec. 28.7 checks table (l.11197-11204) | C3 -0.8748513621, 1.25e-6, -1.08; C4 5.0488792961, 3.01e-5, +0.36; C5 -38.8344913344, 5.07e-4, -1.67; C6 362.3727456, 0.0085778, +0.73 | R `coefficients[3..6]`, `standard_errors[3..6]`; references: exact values (13 digits, as in the delivered assembly), `GFF/results/C6_2/C6_result.json` (`C6`, `sampling_standard_error`) | printed digits | PASS. R's own `lower_order_checks` uses the stale C6 362.3489 without pulls (documented in `GFF/results/C7_2/README.md`; a replay row checks it is unchanged) |
| Sec. 28.7 (l.11207-11211) | power corrections (5.4 +- 15.1)e-8, (1.10 +- 1.85)e-5, (3.3 +- 11.8)e-4; order 3 at rounding; -0.056 +- 0.046 | R `power_differences`, `power_difference_errors` | printed digits | PASS |
| Sec. 28.7 (l.11212-11213) | bootstrap SE 0.52219 against 0.52445 | R `bootstrap.full_se[7]` (4,096 resamples, seed 70530413), `sampling_standard_error` | printed digits | PASS |
| Sec. 28.7 (l.11214-11217) | new value 1.01 previous SE from the previous estimator; power correction 0.33 previous SE from 1.750131 +- 5.424390 | R; P `reference/RESULT.json`, re-assembled by `tools/reassemble_reference.py` | printed digits | PASS |
| Sec. 26.6 (l.10065-10066), C6(2) section | by-product C6(2) = 362.3727 +- 0.0086, +0.73 | R `coefficients[6]`, `standard_errors[6]`; `GFF/results/C6_2/C6_result.json` | printed digits | PASS (also owned by C6_2 as a cross-check) |
| `\PTlowerPullMax` 2.3 (numbers.tex; not printed in the paper at f496d39a) | largest |pull| of all lower-order by-products (set by C7(3)) | our C3-C6 pulls (max 1.67) | <= 2.3 | PASS |

##### Owned elsewhere, using R as reference
- Sec. 28.7 (l.11219-11221), Sec. 31: the C8(2) by-product -3875.55 +- 0.29 (+0.97) — replay of C8_2.
- Sec. 28.7 (l.11222-11223), Sec. 31.7: the independent code's -3875.47 +- 0.35 (+1.04) — replay of C8_2_check (reads R).
- Sec. 31 ratio C8(2)/C7(2) = -11.86 — C8_2.

### `LRI_C7_D3_HPC`

Folder: `code/LRI_C7_D3_HPC/`.

#### C7(3): every number the condensed note quotes, mapped to a file, a command and a tolerance

Group C7(3) (session C63d), 2026-10-13. Note: `GFF/LRI_condensed_note/long_range_ising_condensed.tex` at `fa71533`
(abstract l.64; Section 1 ll.103, 128, 145-146; Section 26.7 ll.10134-10139; Section 29 `app:C7d3` ll.11225-11370;
Section 33 row ll.12356-12367) and the note README (ll.45, 67, 79). Paths below are relative to `GFF/`.

**Command.** `make -C code/LRI_C7_D3_HPC -f public.mk replay` runs `public/replay_C7_3.py`: pure Python (numpy), about
10 s on one core, no compiler, no hosted data. It writes `code/LRI_C7_D3_HPC/.work/replay/REPLAY.md` and `replay.json`,
prints the table and exits 1 on any FAIL. Each row below names its replay row id. The "replayed" column is the local run
of 2026-10-13 (macOS arm64, Python 3.10.12, NumPy 1.24.4; `replay_local_run.txt`); on AMD EPYC 7532/7543 (AVX2), where the
production assembled, the floats are bitwise those of the records.

**Abbreviations.**
- `R` = `results/C7_3/run1-20260930-m4096` (the production records, byte-identical); `P` = `code/LRI_C7_D3_HPC`.
- **A** = `R/C7_result.json`, recomputed from the 20 `R/groups/*/merged.json` by the production commit's
  `P/tools/assemble.py` (`calculate(..., bootstrap=4096)`, 4de9412). The replay first checks that the manifest binds the
  shipped tools, inputs, configs and merged records (hash chain), then that every field of `C7_result.json` is reproduced.
- **G** = the consistency gates of `P/reverify_a6ce987/tools/assemble.py` (`gate_checks`, a6ce987) with the references
  `P/reverify_a6ce987/references/lower_order_d3.json` (C3-C5: special-function values; C6: the 2026-09-29 C6(3)
  campaign, 33.57542664131543 +- 0.00011855; archived C7(3)); expected values in `results/C7_3/run1_report_bb9d2ca.json`.

**Tolerances and why.**
- Quoted numbers: the replayed value must round to the printed string, i.e. lie within half a unit of the last printed
  digit (plus 1e-12 relative for last-bit noise of another CPU type).
- The 17-digit estimator: 1e-12 relative. The float64 assembly is bitwise on the CPU type that assembled it, but NumPy
  and OpenBLAS SIMD paths change the last bits elsewhere (4 ulp on an AVX-512 node of symmetry; 5e-16 on the Mac). The
  same rule is `tools/report.py`'s (EXISTING_REL).
- Whole-record comparison (`asm.production`): 1e-12 for C7, SE and coefficients; 1e-10 for every other float, scaled by
  the largest entry of its vector (assemble.rounding_difference of a6ce987). The bootstrap bias is a difference of
  numbers of the size of the coefficients and is judged on their scale (on the Mac it differs by 6e-14 absolute).
- Gates (`gates.report`): bitwise on AVX2 AMD; elsewhere 1e-8 relative. The power differences are cancellations (d4 =
  2e-6 is the difference of two numbers near 1.23, so one ulp of them is 1e-10 of d4; on the Mac the largest gate
  difference is 4.5e-11, in d5). The order-3 power difference vanishes in exact
  arithmetic, so its pull is a ratio of rounding noise and is checked only for being at the rounding level.
- Counts, hashes, strings: exact.
- CITED: the number rests on a record that is not recomputable from the shipped files. There are two such rows; the
  source is named.

##### Identity and assembly rows (not quoted, but they carry the rest)

| replay row | check | result 2026-10-13 |
|---|---|---|
| `id.manifest`, `id.groups`, `id.merged` | run1 manifest sha256 eefa8432... = C7_result.source_manifest_sha256; 20 configs match the manifest; every merged.json has the right schema, manifest and config hash, payload hash, 64 replicates and jet shape; merged sha256 = C7_result.merged_sha256 | PASS |
| `id.tools`, `id.inputs`, `id.inputs_files`, `id.packs` | manifest tool_sha256 = shipped `P/tools/{production,assemble,common,prepare_inputs}.py`; inputs_manifest_sha256 5048b336... = `P/inputs/manifest.json`; small inputs and (after `setup`) the 10 packs match it | PASS (packs: SKIP before `make -f public.mk setup`, PASS after) |
| `id.cost_model`, `id.reverify_inputs` | `P/reverify_a6ce987/cost_models/gmp_symmetry_epyc7532.json` = run1's cost model (f815b1fa...); the re-verifier's inputs are byte-identical to the production inputs | PASS |
| `id.full_run` | `graph_replicates.csv` digests and byte-identity of the hosted full run directory | SKIP in `replay`; checked by `make -f public.mk reverify` |
| `asm.production`, `asm.metadata` | A: all 25 fields of `C7_result.json` | PASS (15 of 25 fields bitwise on the Mac, largest relative difference 6.4e-12, in the power correction; bitwise on AVX2 AMD per `run1_report_bb9d2ca.json`) |
| `asm.reverify`, `gates.*` | the a6ce987 assembly gives the same result and the gates of `run1_report_bb9d2ca.json`; no gate flagged; the report re-verified the same manifest and merged hashes, bitwise | PASS |

##### The quoted numbers

###### Abstract and Section 1

| quantity | quoted | replayed | source | tolerance | replay row |
|---|---|---|---|---|---|
| C7(3) = -220.35 +- 0.13 (4 SE rounded up to 0.01) | -220.35 +- 0.13 | -220.35 +- 0.13 | A | exact | `n.reported` |

###### Section 1 estimator table

| quantity | quoted | replayed | source | tolerance | replay row |
|---|---|---|---|---|---|
| underlying estimator | -220.35448047392794 | -220.35448047392805 | A | 1e-12 relative (bitwise on AVX2 AMD) | `n.estimator` |
| sampling standard error | 0.0318188006 | 0.031818800575 | A | half a unit of the last printed digit | `n.se` |

###### Section 29.1 Result and scope

| quantity | quoted | replayed | source | tolerance | replay row |
|---|---|---|---|---|---|
| 4 sigma-hat | 0.127 | 0.1272752023 | A | half a unit of the last printed digit | `n.4se` |
| power-free C7^pf(3) | -220.3723574 | -220.372357366 | A | half a unit of the last printed digit | `n.pf` |
| power-free SE | 0.0277073 | 0.0277073251594 | A | half a unit of the last printed digit | `n.pf_se` |
| power correction Delta_p C7(3) | 0.0178769 | 0.0178768920536 | A | half a unit of the last printed digit | `n.dp` |
| power correction SE | 0.0156478 | 0.0156478322911 | A | half a unit of the last printed digit | `n.dp_se` |
| complete C7(3) (table) | -220.3544805 | -220.354480474 | A | half a unit of the last printed digit | `n.full7` |
| complete SE (table) | 0.0318188 | 0.031818800575 | A | half a unit of the last printed digit | `n.full7_se` |
| first half-stream deviation from C7(3) | 0.034 | 0.0337990314248 | A | half a unit of the last printed digit | `n.half_dev1` |
| second half-stream deviation from C7(3) | 0.034 | 0.0337990295625 | A | half a unit of the last printed digit | `n.half_dev2` |
| 2D rule (max of 4 sigma and half-stream deviations) gives the same allowance | 0.13 | 0.13 | A | exact | `n.rule2d` |
| previous calculation reported -228 +- 16 | -228 +- 16 | -228 +- 16 (reference/README.md, verification/C7_full_result.json) | `P/reference/verification/C7_full_result.json` and `reference/README.md` | exact | `n.prev_report` |
| previous estimator | -227.6181095 | -227.618109475 | `P/reference/verification/C7_full_result.json` | half a unit of the last printed digit | `n.prev_est` |
| previous sampling SE | 3.8273969 | 3.82739687566 | `P/reference/verification/C7_full_result.json` | half a unit of the last printed digit | `n.prev_se` |
| new estimator minus previous, in previous SE | 1.90 | 1.89779874853 | A; `P/reference/verification/C7_full_result.json` | half a unit of the last printed digit | `n.prev_dist` |
| same, from the gate (archived C7, in archived SE) | 1.90 | 1.89779874853 | G | half a unit of the last printed digit | `n.prev_dist_gate` |

###### Section 29.2 Kernel, normalization and coverage

| quantity | quoted | replayed | source | tolerance | replay row |
|---|---|---|---|---|---|
| integrated power-free classes, loops 3..7 | 5,16,76,395,2298 | [5, 16, 76, 395, 2298] | `P/inputs/manifest.json` (counts), `inputs/inventory.json` (primitive flags) | exact | `n.classes_free` |
| seven-loop classes: nonprimitive + primitive | 2254 + 44 | 2254 + 44 | `P/inputs/manifest.json` (counts), `inputs/inventory.json` (primitive flags) | exact | `n.classes_prim` |
| integrated power classes, loops 3..7 | 1,3,20,107,590 | [1, 3, 20, 107, 590] | `P/inputs/manifest.json` (counts), `inputs/inventory.json` (primitive flags) | exact | `n.classes_power` |
| kernels in all | 3,511 | 3511 | `P/inputs/manifest.json` (counts), `inputs/inventory.json` (primitive flags) | exact | `n.kernels` |
| denominators and weights unchanged from the 2D inventory (all kernels checked) | 3,511 checked | passed, 3511 | `P/reference/verification/dimension_checks.json` | exact | `n.structure` |
| b_{2,5} | 26.0214190551330710 | 26.0214190551 | `P/inputs/two_loop.json` (B2[5]) | half a unit of the last printed digit | `n.b25` |
| b_{2,5} digits (Decimal) | 26.0214190551330710 | 26.0214190551330710 | `P/inputs/two_loop.json` (B2[5]) | exact | `n.b25_digits` |
| two 65-digit evaluations, radii 0.04, 0.07, 64 and 80 Cauchy nodes | 0.04/64, 0.07/80 | [('0.04', 64), ('0.07', 80)] | `P/reference/verification/two_loop_checks.json` | exact | `n.b2_contours` |
| the two evaluations agree to | 3.3e-57 | 3.25175698462e-57 | `P/reference/verification/two_loop_checks.json` | half a unit of the last printed digit | `n.b2_agree` |
| agreement with the sixth-order input | 1.3e-54 | 1.31585423799e-54 | `P/reference/verification/dimension_checks.json` | half a unit of the last printed digit | `n.b2_c6` |
| independent Cauchy evaluations of the Gamma factors | 30 | 30 | `P/reference/verification/dimension_checks.json` | exact | `n.gamma_n` |
| Gamma-factor agreement | 8.3e-54 | 8.31788494544e-54 | `P/reference/verification/dimension_checks.json` | half a unit of the last printed digit | `n.gamma` |
| exact rational cases test the assembly | 64 | 64 | `P/reference/verification/assembly_checks.json` | exact | `n.assembly64` |
| C7(3) contains (3 c_{7,0} - b_{7,0})/6561 (Jacobian of the production assembly) | -1/6561, 3/6561 | -0.000152415790276, 0.000457247370828 | Jacobian of `tools/assemble.py` (4de9412) at the run1 means | exact | `n.c7_const` |
| three-loop power graph closed form -16 pi/15 | -16*pi/15 | -16*pi/15 | `P/reference/verification/dimension_checks.json` | exact | `n.b3_exact` |
| -16 pi/15 | -3.3510322 | -3.35103216383 | `dimension_checks.json` and -16*pi/15 computed | half a unit of the last printed digit | `n.b3_value` |
| production b_3^p(0) | -3.3510653 | -3.3510652602 | `R/groups/{a,b}_power_L3/merged.json` (column 0); closed form from `dimension_checks.json` | half a unit of the last printed digit | `n.b3_prod` |
| its sampling SE | 0.0000262 | 2.6214371623e-05 | `R/groups/{a,b}_power_L3/merged.json` (column 0); closed form from `dimension_checks.json` | half a unit of the last printed digit | `n.b3_prod_se` |
| pull from -16 pi/15 | -1.26 | -1.26252786143 | `R/groups/{a,b}_power_L3/merged.json` (column 0); closed form from `dimension_checks.json` | half a unit of the last printed digit | `n.b3_pull` |

###### Section 29.3 The 2026 production

| quantity | quoted | replayed | source | tolerance | replay row |
|---|---|---|---|---|---|
| production worker byte-identical to the previous calculation (src/ = reference/src/) | identical | identical | `P/src/` vs `P/reference/src/` (sha256) | exact | `n.worker` |
| promotion thresholds 1e-9 (binary128) and 1e-23 (GMP) | 1e-9, 1e-23 | found in src/kernel.hpp | `P/src/kernel.hpp` line 166 | exact | `n.thresholds` |
| archived production rows replayed (job 566411) | 168,528 | 168528 | `results/C7_3/evidence/replay_report.json` (job 566411); rerun: `make -f public.mk archived-replay` | exact | `n.replay_rows` |
| share reproduced bit for bit, % | 96 | 96.1525681192 | `results/C7_3/evidence/replay_report.json` (job 566411); rerun: `make -f public.mk archived-replay` | half a unit of the last printed digit | `n.replay_bitwise` |
| largest normalized difference of the rest | 1.0e-11 | 1.01457341013e-11 | `results/C7_3/evidence/replay_report.json` (job 566411); rerun: `make -f public.mk archived-replay` | half a unit of the last printed digit | `n.replay_max` |
| identical promotion counts (20 groups) | identical | identical | `results/C7_3/evidence/replay_report.json` (job 566411); rerun: `make -f public.mk archived-replay` | exact | `n.replay_prom` |
| rebuilt previous estimator vs published | -227.61810947469922 vs -227.61810947469945 | -227.61810947469922 vs -227.61810947469945 (= verification/C7_full_result.json) | `results/C7_3/evidence/replay_report.json` (job 566411); rerun: `make -f public.mk archived-replay` | exact | `n.replay_c7` |
| independent high-precision reimplementation reproduced 13 archived rows, L3-L7, both sectors | 13 rows | CITED | `results/C7_3/REVIEWS.md`; rows can be rechecked with `make -f public.mk indep-rows` | not recomputable from shipped files | `n.indep13` |
| 64 vs 16 threads: rows, mismatches, binary128 and GMP promotions | 5,776 rows identical; 255,396 / 20,511 | THREADCHECK rows=5776 mismatches=0 quad=255396 mp=20511 | `results/C7_3/evidence/buildtest-566376.out` (THREADCHECK line) | exact | `n.threads` |
| AMD vs Intel: same rows and identical promotion counts | identical promotion counts | AMD64-vs-INTEL20 rows=5776 mismatches=5452 quad=255396 mp=20511 | `results/C7_3/evidence/intelcheck-566410.out` | exact | `n.cpu_counts` |
| AMD vs Intel: largest normalized difference | 2.0e-11 | CITED | `results/C7_3/CAMPAIGN.md` ("AMD vs Intel identity") | not recomputable from shipped files | `n.cpu_max` |
| 2.0e-11 relative to SE//C7/ (about 1e-7) | 1e-7 | 1.3850583711e-07 | derived: 2.0e-11 / (SE/abs(C7)) | order of magnitude | `n.cpu_rel` |
| 64 randomized replicates for every loop and sector | 64 | all 64 | `R/manifest.json`, `groups/*/config.json`; `P/inputs/inventory.json`, `reference/inputs/allocation.json` | exact | `n.reps` |
| campaign a: 52-bit nets, rate .8; b: 60-bit nets, rate .7 | 52/.8, 60/.7 | all groups | `R/manifest.json`, `groups/*/config.json`; `P/inputs/inventory.json`, `reference/inputs/allocation.json` | exact | `n.bits_rates` |
| frozen per-graph allocation of the previous calculation x 2^12, powers of two | x 2^12 | multiplier 4096 | `R/manifest.json`, `groups/*/config.json`; `P/inputs/inventory.json`, `reference/inputs/allocation.json` | exact | `n.alloc` |
| at least 64 points per stratum (before x 2^12) | 64 | 64 | `R/manifest.json`, `groups/*/config.json`; `P/inputs/inventory.json`, `reference/inputs/allocation.json` | exact | `n.alloc_min` |
| 44 seven-loop primitive classes at 2^22 points each per replicate (flat, 1024 x 2^12) | 2^22 | [4194304], primitive_points 1024 | `R/manifest.json`, `groups/*/config.json`; `P/inputs/inventory.json`, `reference/inputs/allocation.json` | exact | `n.prim` |
| one fresh base seed (delivered arithmetic offsets) | fresh | 4805754955154533039 | `R/manifest.json`, `groups/*/config.json`; `P/inputs/inventory.json`, `reference/inputs/allocation.json` | exact | `n.seed` |
| kernel samples in the two campaigns | 867,784,720,384 | 867,784,720,384 | `R/manifest.json`, `groups/*/config.json`; `P/inputs/inventory.json`, `reference/inputs/allocation.json` | exact | `n.samples` |
| 14 AMD and 14 Intel nodes | 14 + 14 | 14 + 14 | `R/lanes/node-*.out` | exact | `n.nodes` |
| completed on 1 October 2026 | 1 October 2026 | 2026-10-01T03:51:23-04:00 | `R/lanes/node-*.out` | exact | `n.completed` |
| campaign a | -220.3220 | -220.32200204 | A | half a unit of the last printed digit | `n.ca` |
| campaign a SE | 0.0431 | 0.0430751080241 | A | half a unit of the last printed digit | `n.ca_se` |
| campaign b | -220.3870 | -220.386958907 | A | half a unit of the last printed digit | `n.cb` |
| campaign b SE | 0.0468 | 0.0468431355199 | A | half a unit of the last printed digit | `n.cb_se` |
| first half stream | -220.3207 | -220.320681443 | A | half a unit of the last printed digit | `n.h1` |
| second half stream | -220.3883 | -220.388279503 | A | half a unit of the last printed digit | `n.h2` |
| combined | -220.3545 | -220.354480474 | A | half a unit of the last printed digit | `n.comb` |
| combined SE | 0.0318 | 0.031818800575 | A | half a unit of the last printed digit | `n.comb_se` |
| campaigns differ by (combined SE) | 1.02 | 1.02073092511 | G | half a unit of the last printed digit | `n.ab_pull` |
| error of C7 from free L=3 | 0.0000 | 4.17859712275e-05 | A | half a unit of the last printed digit | `n.err_free_L3` |
| error of C7 from free L=4 | 0.0006 | 0.000561789284622 | A | half a unit of the last printed digit | `n.err_free_L4` |
| error of C7 from free L=5 | 0.0034 | 0.00340837425533 | A | half a unit of the last printed digit | `n.err_free_L5` |
| error of C7 from free L=6 | 0.0119 | 0.0118620162592 | A | half a unit of the last printed digit | `n.err_free_L6` |
| error of C7 from free L=7 | 0.0248 | 0.0247981210591 | A | half a unit of the last printed digit | `n.err_free_L7` |
| error of C7 from power L=3 | 0.0000 | 1.56940104241e-05 | A | half a unit of the last printed digit | `n.err_power_L3` |
| error of C7 from power L=4 | 0.0002 | 0.000166116852874 | A | half a unit of the last printed digit | `n.err_power_L4` |
| error of C7 from power L=5 | 0.0014 | 0.00144226564532 | A | half a unit of the last printed digit | `n.err_power_L5` |
| error of C7 from power L=6 | 0.0058 | 0.00575832761904 | A | half a unit of the last printed digit | `n.err_power_L6` |
| error of C7 from power L=7 | 0.0145 | 0.0144769180295 | A | half a unit of the last printed digit | `n.err_power_L7` |

###### Section 29.4 Checks

| quantity | quoted | replayed | source | tolerance | replay row |
|---|---|---|---|---|---|
| C3(3) by-product | -0.3535806960 | -0.353580695987 | G | half a unit of the last printed digit | `n.C3` |
| C3(3) sampling SE | 3.59e-7 | 3.59147894386e-07 | G | half a unit of the last printed digit | `n.C3_se` |
| C3(3) pull (reference -0.3535815204331724) | +2.30 | 2.29556065445 | G | half a unit of the last printed digit | `n.C3_pull` |
| C4(3) by-product | 1.2280727249 | 1.22807272492 | G | half a unit of the last printed digit | `n.C4` |
| C4(3) sampling SE | 8.52e-6 | 8.52384937029e-06 | G | half a unit of the last printed digit | `n.C4_se` |
| C4(3) pull (reference 1.2280635453276232) | +1.08 | 1.07693033118 | G | half a unit of the last printed digit | `n.C4_pull` |
| C5(3) by-product | -5.8503454757 | -5.85034547566 | G | half a unit of the last printed digit | `n.C5` |
| C5(3) sampling SE | 1.52e-4 | 0.000151754506044 | G | half a unit of the last printed digit | `n.C5_se` |
| C5(3) pull (reference -5.85035142075) | +0.04 | 0.0391757368838 | G | half a unit of the last printed digit | `n.C5_pull` |
| C6(3) by-product | 33.5738672 | 33.5738671978 | G | half a unit of the last printed digit | `n.C6` |
| C6(3) sampling SE | 0.0019782 | 0.00197818806385 | G | half a unit of the last printed digit | `n.C6_se` |
| C6(3) pull (reference 33.57542664131543) | -0.79 | -0.786907371165 | G | half a unit of the last printed digit | `n.C6_pull` |
| power correction at order 4 | 2.0e-6 | 2.01681068024e-06 | A | half a unit of the last printed digit | `n.pd4` |
| its SE | 2.1e-6 | 2.08277854548e-06 | A | half a unit of the last printed digit | `n.pd4_se` |
| power correction at order 5 | 4.0e-5 | 3.98275503821e-05 | A | half a unit of the last printed digit | `n.pd5` |
| its SE | 6.4e-5 | 6.43855836049e-05 | A | half a unit of the last printed digit | `n.pd5_se` |
| power correction at order 6 | -3.7e-4 | -0.000369881639912 | A | half a unit of the last printed digit | `n.pd6` |
| its SE | 10.2e-4 | 0.00101995121608 | A | half a unit of the last printed digit | `n.pd6_se` |
| order-3 power difference at rounding level | rounding level | -1.1e-16 +- 6.1e-15 | A | exact | `n.pd3` |
| seventh-order power correction | 0.018 | 0.0178768920536 | A | half a unit of the last printed digit | `n.pd7` |
| its SE | 0.016 | 0.0156478322911 | A | half a unit of the last printed digit | `n.pd7_se` |
| bootstrap replicate resamples | 4,096 | 4096 | A | exact | `n.boot_n` |
| bootstrap SE | 0.03204 | 0.0320400823926 | A | half a unit of the last printed digit | `n.boot` |
| covariance SE | 0.03182 | 0.031818800575 | A | half a unit of the last printed digit | `n.boot_cov` |
| previous power correction | -3.836223 | -3.83622337598 | `P/reference/verification/C7_full_result.json` | half a unit of the last printed digit | `n.prev_pc` |
| its SE | 2.007117 | 2.00711725703 | `P/reference/verification/C7_full_result.json` | half a unit of the last printed digit | `n.prev_pc_se` |
| distance in previous SE | 1.92 | 1.92021679577 | A; `P/reference/verification/C7_full_result.json` | half a unit of the last printed digit | `n.prev_pc_dist` |

###### Section 26.7 (C6(3) section) by-product sentence

| quantity | quoted | replayed | source | tolerance | replay row |
|---|---|---|---|---|---|
| C6(3) by-product of the C7(3) production | 33.57387 | 33.5738671978 | G | half a unit of the last printed digit | `n.s26_c6` |
| its sampling SE | 0.00198 | 0.00197818806385 | G | half a unit of the last printed digit | `n.s26_c6_se` |
| combined SE from the C6(3) estimator | -0.79 | -0.786907371165 | G | half a unit of the last printed digit | `n.s26_pull` |

###### Note README (lines 45, 67, 79)

| quantity | quoted | replayed | source | tolerance | replay row |
|---|---|---|---|---|---|
| estimator | -220.35448 | -220.354480474 | A | half a unit of the last printed digit | `r.est` |
| sampling SE | 0.03182 | 0.031818800575 | A | half a unit of the last printed digit | `r.se` |
| power-free | -220.37236 | -220.372357366 | A | half a unit of the last printed digit | `r.pf` |
| power-free SE | 0.02771 | 0.0277073251594 | A | half a unit of the last printed digit | `r.pf_se` |
| power correction | +0.01788 | 0.0178768920536 | A | half a unit of the last printed digit | `r.dp` |
| power correction SE | 0.01565 | 0.0156478322911 | A | half a unit of the last printed digit | `r.dp_se` |
| previous estimator | -227.618 | -227.618109475 | `P/reference/verification/C7_full_result.json` | half a unit of the last printed digit | `r.prev` |
| previous SE | 3.83 | 3.82739687566 | `P/reference/verification/C7_full_result.json` | half a unit of the last printed digit | `r.prev_se` |
| samples | 8.68e11 | 867784720384 | `R/manifest.json`, `groups/*/config.json`; `P/inputs/inventory.json`, `reference/inputs/allocation.json` | half a unit of the last printed digit | `r.samples` |

##### The two CITED rows

- **13 archived rows reproduced by an independent mpmath re-implementation** (Sec 29.3). The code review ran
  `indep_rows.py` (now `P/public/indep_rows.py`, reference path made relative) on 13 rows across L3-L7 and both sectors:
  free rows to 1e-17-1e-19, power rows to <= 9e-13 (`results/C7_3/REVIEWS.md`). The list of the 13 rows was not
  archived. `make -f public.mk indep-rows ROWS='[...]'` rechecks any rows (hosted records needed); on 2026-10-13 three
  rows gave 9.1e-13 (power L3), 5.7e-18 (free L4) and 3.4e-19 (free L3) (`replay_local_run.txt`).
- **AMD vs Intel: at most 2.0e-11 normalized** (Sec 29.3). From `results/C7_3/CAMPAIGN.md` ("AMD vs Intel identity",
  job 566410) and the code review. The shipped log `evidence/intelcheck-566410.out` confirms the 5,776 rows and the
  identical promotion counts (255,396 binary128, 20,511 GMP), but the per-row comparison output was not archived.
  `make -f public.mk smoke` repeats this kind of comparison against run1's own checkpoints.

##### Specialist targets that recompute cited evidence (cluster node; not part of `replay`)

| evidence | shipped record | command | node, runtime | tolerance |
|---|---|---|---|---|
| archived-stream replay (Sec 29.3: 168,528 rows, 96% bitwise, rest <= 1.0e-11, identical promotions, -227.61810947469922) | `results/C7_3/evidence/replay_report.json` (job 566411) | `make -f public.mk fetch-data records archived-replay` | x86-64 Linux, 64 cores; 95 s at 64 threads on AMD EPYC 7532 | same rows; identical promotion counts; max normalized difference <= 1e-10; rebuilt C7 and SE within 1e-10 relative |
| thread identity (5,776 rows, 0 mismatches, 255,396/20,511 promotions) | `results/C7_3/evidence/buildtest-566376.out` | not rerun by a target (the delivered thread check used a plan of job 566376); `tests/validate.py` of `make test` checks 1 vs 4 threads | - | - |
| re-verification of run1 by data identity, incl. `graph_replicates.csv` | `results/C7_3/run1_report_bb9d2ca.json` | `make -f public.mk fetch-data reverify` | any machine, Python >= 3.10; about 1 min, 0.6 GB disk | `public/compare_report.py`: identical identity fields; C7, SE, coefficients within 1e-12; gates within 1e-8 |
| production slice (rerun job indices 0, 320, 192 of run1) | run1 checkpoints in the hosted tarball | `make -f public.mk fetch-data smoke` | 64-core x86-64 node with the test toolchain and SciPy 1.17.1; about 2-3 min | `public/compare_smoke.py`: identical task coordinates and promotion counts; values bitwise or within 1e-10 normalized |

##### Section 33 paths

`section33_row.tex` gives the public row. Every path it names exists in the export: `results/C7_3/run1-20260930-m4096/`
(C7_result.json, manifest.json, groups/*/config.json, groups/*/merged.json), `results/C7_3/CAMPAIGN.md`,
`results/C7_3/evidence/replay_report.json`, `results/C7_3/REVIEWS.md`, `code/LRI_C7_D3_HPC/` (4de9412),
`code/LRI_C7_D3_HPC/reverify_a6ce987/tools/report.py`, `code/LRI_C7_D3_HPC/reference/`, and the hosted
`data/C7_3/run1-20260930-m4096_full.tgz` and `data/C7_3/reference_records.tar.gz` (`make fetch-data`).

## Full C8(1), C8(2), C8(3) and the independent checks

### `LRI_C8_HPC`

Folder: `code/LRI_C8_HPC/`.

#### C8(1): quoted numbers -> record, command, tolerance (C71d, 2026-10-13)

Every row is a check of `public/verify8.py` (run by `make -f public.mk replay` in `GFF/code/LRI_C8_HPC`).
Quoted values are from the condensed note at fa71533 (abstract, Section 1 table, Section 30) and from
`GFF/results/C8_1/2026-10_ext1/REPORT.md`.
- **Recomputed from:** the replayed records in `.work/c8_hpc/results/`. F = `C8_final_A3/C8_final.json` (K = 14),
  A1 = `C8_A1_close/combination/C8_interim.json`, K4 = `C8_final/C8_final.json`.
- **Tolerance:** a rounded quote passes when the recomputed value rounds to it (half a unit of its last digit). The
  Section 1 full-precision values pass at 1e-6 absolute.
- **Result:** 122 checks PASS on a personal desktop, symmetry AMD and the Mac (note at 97dd353).

| Quoted (where) | Value | Record field | Tolerance |
|---|---|---|---|
| estimator, SE (Sec 1 table) | 8059766.723129955, 4209.576151 | F `C8_full`, `sampling_se` | 1e-6 abs |
| C8(1), allowance (abstract, Sec 30.1) | 8059767, +-17000; (8.060 +- 0.017)e6 | F `C8_full`, `allowance.headline_2sf` | 0.5; exact |
| SE, bootstrap (Sec 30.1) | 4210, 4140 | F `sampling_se`, `bootstrap_se` | 5 |
| batches, range, SE range, chi2 (Sec 30.1) | 14; 8041935-8089624; 15090-16343; 8.49/13 | F `batches.per_batch`, `chi2_about_combined`, `dof` | 0.5; 0.005 |
| allowance candidates (Sec 30.1, REPORT) | 4SE 16838.3 (largest), half split 4316, R8 524, R9 499, L5 step 5.5 | F `allowance.candidates` | 0.05 (4SE), 0.5 |
| ratio C8/C7 (Sec 30.1) | -25.0 | F `C8_full` / C7 reference -322549.9 | 0.05 |
| loop-5 contribution, last step (Sec 30.2) | -1297392.1, +2.8 | F `loop5_exact` | 0.05 |
| composition table (Sec 30.4) | 10 means and 9 SEs (free 7879086.8 +- 790.7 ... check -113.3 +- 68.1) | F `free_level`, `power_levels`, `check_levels` | 0.05 |
| K (Sec 30.4 table) | 1531302.35 | `data/C8_1/c8_hpc/analysis/v1/full_affine8.json` `K[8]` | 0.005 |
| resolution sequence (REPORT) | 8429541, 8064559, 8059969, 8059943, 8059740, 8059767 | F `resolution_sequence` | 0.5 |
| controls (Sec 30.4) | uncontrolled 8048689 +- 23730; correction +11078 +- 24734; per loop -663+-316, +2506+-4037, -12920+-24400; SE ratio 5.6 | F `raw_uncontrolled`, `zero_pole_control` | 0.5 |
| pole columns (Sec 30.4) | 30 columns, max abs z 2.18, four above 2 (L7 12/13, L8 1/9), sum z^2 39.8 | F `spurious_pole_checks` | 0.005, exact |
| half splits (Sec 30.4) | 8055451, 8064082 | F `half_splits` | 0.5 |
| lower orders (Sec 30.2, 30.4) | C3 -1.3e-12, C4 1.1e-9, C5 -731.140052 (-5.8e-4), C6 14332.8222 +- 2.52 (+0.45), C7 -322495.6 +- 74.4 (+0.72), 0.4 combined standard errors vs truncation-aware -322524 +- 38 (1 sigma 18.6) | F `lower_order_checks` | last digit |
| vendor split (Sec 30.3, REPORT) | AMD 8063282 +- 5975, Intel 8056245 +- 5918, difference 7037 +- 8410 | F `batches.per_batch` (b1-b4, b12-b14 AMD) | 0.5 |
| HT comparison (REPORT) | -5700, -0.88 sigma | F `C8_full` vs external 8.0655(50)e6 | 50; 0.005 |
| coverage (REPORT) | 21143 active L8 classes | F `coverage` | exact |
| K = 4 result (Sec 30.3) | 8066723 +- 8015, allowance 33000 | K4 | 0.5 |
| A1 result (Sec 30.3) | 8061480 +- 5300, allowance 22000, b5-b9 included | A1 | 0.5; 50 (2 s.f.) |
| inventory (Sec 30.2) | 26540 classes, 7231 power, 248 primitive and power free, 3908 zero, 2507176 terms | `inputs8/L8_coord.txt` (from the .xz), `exact_zero_L8.txt` | exact |
| affine checks (Sec 30.2) | C2 exact, C3 -1.3e-12, C4 1.1e-9, channel ratio -3 | `full_affine8.json` | last digit |
| loop-5 degree sequence (Sec 30.2) | C5 - exact: -0.94, -0.13, -0.019, -0.0032, -5.8e-4 at N = 6..14 | recomputed: K + J5 . v5(N) from `runs/exact8_L5/exact_L5/merged/N*.json` | last digit |
| pilot hazard (Sec 30.3) | C7 production value 16372.8; pilot campaigns (64 points per graph, 16 replicates) A -16793.9 +- 9359.6 and B -13230.8 +- 7406.2, 33166.7 and 29603.7 below, 3.5 and 4.0 of their own SEs; repetition of A with 4096 points per graph (32 replicates) 16838.1 +- 724.1 (the agreement of 16838.1 with the 4SE candidate 16838.3 is a coincidence; the note says so) | `runs/pilot8/tprod{A,B}_L7` and `runs/tailtest_L7/tprodA_L7` via the production `design8.per_graph`; C7: `GFF/results/C7_1/.../C7_final.json` aggregates tprodA_L7 + tprodB_L7 | 0.05; replicates exact |
| kernel validation (Sec 30.3) | power bitwise (0 mismatches), QMC 8e-17, binary128 L8 2.5e-17 | `validation/expanse_2026-10-02/c8_vs_c7_T1-T5_job54592375.json` | last digit |
| cost model (Sec 30.2) | 5, 14 core-hours (degrees 6, 7); 32, 67 at 8, 9 are PLAN.md extrapolations (INFO) | `validation/expanse_2026-10-02/bench8_job54591957.json` | 0.5 |
| core-hours (Sec 30.3) | about 9e4 physical (1.4e5 as charged) | Slurm accounting (`<PAPER>/notes/compute_accounting_2026-10-13_c8ext.md`); not replayed (INFO) | |
| identity (REPORT Files) | K14 sha256 115d614f..., K4 4d4d1865..., A1 62ca9cb0... | replayed files vs `GFF/results/C8_1/` | bitwise or 1e-12 rel |

### `LRI_C8_D2_HPC`

Folder: `code/LRI_C8_D2_HPC/`.

#### Results map: C8(2) (note Sections 1, 28 and 31; paper at f496d39a: `\CeightTwo` in Table tab:pt, perturbation.tex l.27; `\PTorderTwoThreeD` and `\CeightTwoIndepPull` are defined in numbers.tex, not printed)

Command for every row: `make -f public.mk replay` in `GFF/code/LRI_C8_D2_HPC` (about 10 s; Python 3.10+, numpy; no
hosted data), which prints one PASS/FAIL row per number and writes `public/out/replay.json`. Rows marked (tails) are also
recomputed from the full group tables by `make -f public.mk replay-tails` (after `fetch-data`). Last run: macOS arm64,
Python 3.10.11, numpy 1.23.5: 192 PASS, 0 FAIL, 3 SKIP.

Abbreviations: F = `GFF/results/C8_2/C8_final.json`; R = `GFF/data/C8_2/prod1-2.5e-4-ddmp256-20261006-ba68f401e46e/`;
P = `GFF/results/C8_2/pilot/C8_result.json`; A = `GFF/results/C8_2/production/analysis.json`;
T = `GFF/results/C8_2/tailcheck/`; E = `GFF/code/LRI_C8_D2_HPC/benchmarks/symmetry_2026-10-c8/`.
Tolerance "printed digits": the recomputed value, printed at the digits the note shows, equals the note's text.

| Quoted (note line at fa71533) | Value | Record, field | How replay gets it | Tolerance | Status |
|---|---|---|---|---|---|
| Estimator, SE (l.130; `\CeightTwo`) | 45990.00263614446, 8.216820958 | F `C8_full`, `sampling_standard_error` | the 24 merged groups of R recombined with tools/combine.combine_batches (K = 1) and compared with F in all 484 fields; F also with tools/verify_result.py | fields: rel 1e-12 headline, 1e-7 others, abs 1e-9 rounding-level gate residuals (max seen 7e-16, 2.5e-9, 9e-12); the 17-digit estimator is quoted from F (recombined value agrees to 2e-16) | PASS |
| C8_result.json of the batch | (assembly, 4,096 draws) | R `C8_result.json` | tools/assemble.combine on the same groups, all 537 fields | as above | PASS |
| Allowance +-33 (l.65, 104, 137-141, 11591-11596) | 4 sigma = 32.87 > half-stream deviations 2.39; ceil = 33 | F `half_streams[*][8]` | arithmetic | exact | PASS |
| Sec 31.1 table | pf 45991.2684796 +- 7.6797436; Delta_p -1.2658435 +- 2.9224044 | F `power_free_C8/se`, `power_correction/se` | recombined | printed digits | PASS |
| Pilot | 45620 +- 214; 1.73 sigma; campaigns 0.64; pulls <= 2.11 at C6; 227 core-h; 8 x 4,096; shares 71%/2.4%, 18%/71% | P; E`pilot/analysis/pa.570669.0/{sacct.txt, pa_analysis.json}`; R `design_bundle/design_meta.json` | verify_result on P; scheduler records; arithmetic | printed digits | PASS |
| Ratios -11.86, -5.77, -7.69, -9.33, -10.70 | | F `lower_order_checks[*].reference`, `GFF/results/C6_2/C6_result.json`, `GFF/results/C7_2/C7_result.json` | arithmetic | printed digits | PASS |
| b_{2,6}, contours 3.1e-66, 7.7e-68; L = 2 control 1.22 SE | | `inputs/two_loop.json`, `inputs/verification/two_loop_extension8.json`, `benchmarks/expanse_2026-10-c8/stage3/s3val3.54637264.0/l2_control.json` | read | printed digits | PASS |
| Assembly: 64 cases, 7.0e-16; gates 6e-16 | 6.97e-16; 5.9e-16 | `vendor/c8_assembly/exact_check_results.json`; F `gates.loop7.rel_deviation` | read; recombined | printed digits | PASS |
| Inventory table (L = 3..8), 2,254 / 3,886 / 15,816 / 248 / 4,336, L7 2,397/44/709, 24,173 kernels, 4,032 / 280, 2,511 / 2,340, 1,091 / 7,231, 144, 11,254,373 | | `LRI_C8_shared/inventory/inventory8_d2/{inventory_L7,inventory_L8,selection}.json`, `gates/`; `inputs/inventory.json`; the C7(2) reference `power_mass/inputs/L*/inventory.json` | counted | exact | PASS |
| Design: 128 replicates, >= 4,096 points, 2.5e-4 of 4.6e4, 11.50, 1.5, 7.67, >= 32,768 free L8 points, 779,836,456,960 samples, route (b) 0.37 | | R `design_bundle/design_meta.json`, `groups/*/config.json` | read, summed | exact / printed digits | PASS |
| Numerics gate F1/F2/F4/F5: 153,600 points, 5.2e-12, 1.4e-11; 4 x 256, 193,384 tasks, **4.2e-16** (note: 4.3e-16, erratum), 0.062, 5.6e-14; 1,600 + 400 sample, about 2.5x; 1/8/16/64 threads | | E`s6fix4/s4flag.570574.0/jflag_dd+mp256/numerics_flags.json` (sha256 42e6d2d8…, pinned by the design bundle); `tests/numerics_flags.py` `BOUND_DC8` | read | printed digits | PASS (erratum listed) |
| Exact-path replays (3,773 kernels bit for bit, 2^32 operand pairs) | | native validation runs | not recomputable without the native build | — | SKIP (CLUSTER_CHECKS: `make test-full`) |
| Production: 8 + 6 nodes, 22.4-23.0 h, 4.4-5.6 h, 1,129 / 6,192,256 / 24,848, 28.7 h, 13,454 core-h, 0.93, EPYC 7543, one runtime identity | | E`production/result/prres.571287.0/sacct.txt`; R `manifest.json` `scale`, `groups/*/merged.json` `blocks`, `thread_seconds_sum`, `cpu_vendor.json`, `runtime_identity.json`; `GFF/results/C8_2/production/accounting.json` | scheduler records summed as tools/accounting.py does (64 cores per AMD node) | exact / printed digits | PASS |
| About 1.6e4 core-h with development | | development accounting (plan log, not shipped) | — | — | SKIP |
| Campaigns 45993.58 +- 12.15, 45986.42 +- 11.06, 0.44; half streams 45987.61, 45992.39; combined 45990.00 +- 8.22 | | F `campaigns`, `half_streams` | recombined | printed digits | PASS |
| SE by loop (12 entries) | | F `error_by_loop` | recombined | printed digits | PASS |
| Realized/predicted 1.07; per stratum 0.98-1.32 (tails) | | F; R `design_meta.json` `predictions`; A `variance.strata.*.predicted_variance_from_pilot_sigma` | arithmetic (prediction read from A; replay-tails recomputes A) | printed digits | PASS |
| Tail rule: k = 16, >= 32,768 points, mean xi > 0.44; 4,832 = 4,631 + 201 confirmed (tails) | | `tools/design.py` constants; `GFF/results/C8_2/production/tails.csv.gz` (decompressed sha256 8039682a…) | recounted from the tail table | exact | PASS |
| 27.6% of the variance (tails); <= 0.08% per graph-campaign | 0.2758; 0.0008 | A `tails.threat` | read (replay-tails recomputes) | printed digits | PASS (note prints 27.5%: erratum) |
| Verification: 3,959,753 subsets, 24,173 kernels, 4 primes x 2 points, < 1e-53, 9 controls, margins 0.1/0.05/0.6/0.55, 17 unbounded legacy kernels, median terms 128 vs 16 | | T`cert_summary.json`, `cert_check.json`, `negctl_check.json` | summed / read | exact | PASS |
| Hill slopes -0.34 to -0.17; nested -0.018 [-0.051, +0.030] (16 graphs), -0.062 [-0.110, +0.060] (8 graphs) | | T`nested_joint.json` `classes` | read | printed digits | PASS |
| Double lift: 380 graphs, 0.058%, 16 largest = 52%, x18.9/x45/x335 -> SE 8.26/8.32/8.97 | | T`dl_targeted.json` | SEs recomputed: SE sqrt(1 + (k-1) share) | printed digits | PASS |
| Lower-order table (C3..C7 estimates, SEs, pulls), sum 4.78; references | | F `lower_order_checks` | pulls recomputed from estimate and both SEs; C6, C7 references equal GFF/results/C6_2, C7_2 | printed digits; references exact | PASS |
| Power null rows (orders 4-7), max 0.47; order 3 exactly 0; correction -1.27 +- 2.92 | | F `power_null_checks`, `power_correction` | recombined | printed digits | PASS |
| Bootstrap 8.09 (4,096) | | R `C8_result.json` `bootstrap.full_se[8]` | recombined (fixed seed) | printed digits | PASS |
| C7(2) by-product -3875.55 +- 0.29, +0.97 (Sec 28 l.11220-11222, Sec 31.6) | | F `coefficients[7]`, `standard_errors[7]`, `lower_order_checks` | recombined | printed digits | PASS |
| Independent check 46006.1 +- 13.4, +1.03 (Sec 1, 31.7; `\CeightTwoIndepPull`) | | — | unit C8_2_check | — | not here |

### `LRI_C8_shared`

Folder: `code/LRI_C8_shared/`.

_same as the section above (one text for the whole unit)._

### `LRI_C8_D2_HPC_optimized`

Folder: `code/LRI_C8_D2_HPC_optimized/`.

#### Results map: independent check of C8(2)

Command for every row: `make -f public.mk replay` in `GFF/code/LRI_C8_D2_HPC_optimized` (65 rows; all PASS on numpy
1.23.5 and 2.3.5). "Printed digits" means the recomputed value, rounded to the digits the note prints, equals the quoted
text. R = `GFF/results/C8_2_check/prod1/C8_result.json`, P = `.../pilot1/C8_result.json`, D = `GFF/data/C8_2_check/prod1/`,
O8 = `GFF/results/C8_2/C8_final.json`, O7 = `GFF/results/C7_2/C7_result.json`. Note lines at HEAD fa71533.

| Quoted (note) | Where | Source | Tolerance | Status |
|---|---|---|---|---|
| C8(2) = 46006.1 +- 13.4 | l.155, 11570, 11900ff | R `C8_full`, `sampling_standard_error`; recombined from D groups/*/merged.json | field: 1e-12 rel; quote: printed digits | final |
| table: campaigns 46012.55 +- 19.70, 45999.73 +- 18.23; half streams 46008.16, 46004.11; combined 46006.14 +- 13.42 | §31.7 table | R `campaigns`, `half_streams[*][8]` | printed digits | final |
| campaigns differ by 0.48 combined SE | §31.7 | from R `campaigns` | printed digits | final |
| bootstrap SE 13.38 (4,096 resamples) | §31.7 | R `bootstrap.full_se[8]`, `.replicates` (seed 70530413) | printed digits | diagnostic |
| power-free 46004.84 +- 12.90; power correction +1.29 +- 3.71 | §31.7 | R `power_free_C8`, `power_free_se`, `power_correction`, `power_correction_se` | printed digits | final |
| variance shares 78% (free L8), 14% (free L7) | §31.7 | R `error_by_loop` squared over SE^2 | printed digits | final |
| no single graph above 0.2% of the variance | §31.7 | `results/.../prod1_analysis/inspect.json` (needs graph_replicates.csv, hosted) | recorded | recorded |
| lower-order pulls -0.01, +1.75, +0.57, -1.18, +1.04; sum of squares 5.88 | §31.7 | R `lower_order_checks` | printed digits | final |
| power null rows at orders 4-6, max pull 0.76 | §31.7 | R `power_null_checks` | printed digits | final |
| C7(2) by-product -3875.47 +- 0.35, +1.04 combined SE from C7(2) | l.11214 | R `coefficients[7]`, `standard_errors[7]`; O7 | printed digits | final |
| difference from the reported estimator +16.1 +- 15.7 = +1.03 combined SE | l.155, 11570, §31.7 | R and O8 | printed digits | final |
| power-free parts differ by 0.90, power corrections by 0.54 combined SE | §31.7 | R and O8 | printed digits | final |
| pilot 46178 +- 417, 32 replicates per campaign | §31.7 | P; data/C8_2_check/pilot1 configs | printed digits | final |
| allocation 28,500 kernel core-hours, 64 replicates, forecast SE 14.97 | §31.7 | D `allocation.json` (`target_core_hours`, `replicates`, `model_only_standard_error_forecast`) | printed digits | final |
| at least 8,192 / 4,096 points per replicate for every free / power L8 graph | §31.7 | D `allocation.json` `counts` | exact | final |
| 24,173 kernels: 16,064 free and 4,336 power at L8, 3,150 at L7 | §31.7 | D `allocation.json` `counts` | exact | final |
| 342 work indices, each run once without a failure; 11 nodes, 16.3-20.1 h each | §31.7 | D `attempts/*.jsonl` | exact / printed digits | final |
| 207 node-hours, 26,526 core-hours | §31.7 | D `attempts` spans: 207.1 node-h (the quoted 207.2 is the scheduler's elapsed time, which includes about 30 s of runner start-up per node) | 0.5 node-h; 0.3% | final |
| 96.5% kernel time | §31.7 | `prod1_analysis/kernel_util.txt` (25,585.3 kernel core-h) over the attempt spans; recomputed from the hosted checkpoints by `remerge` | printed digits | final |
| 52 frozen fixtures reproduced bit for bit | §31.7 | `make -f public.mk fixtures` (science digest 366421b2…); gate records in `verification/site_gates/` | exact | final |
| merged records equal a fresh merge of the checkpoints | (supports all) | `make -f public.mk remerge` after fetch-data | byte-identical | verified 2026-10-13 |

### `LRI_C8_D3_HPC`

Folder: `code/LRI_C8_D3_HPC/`.

#### C8(3): results map (every number the condensed note quotes for C8(3) -> file, command, tolerance)

Note edition fa71533 (`GFF/LRI_condensed_note/long_range_ising_condensed.tex`): abstract (line 65), Section 1 tables (lines 104, 131) and
allowance text (lines 157-165), Section 32 (`app:C8d3`, lines 12007-12253), Section 33 row "Full $C_8(3)$". The note README
(lines 48, 54, 56, 480 ff.) repeats the Section 1 numbers. Sections 32.8 and 33 quote paths only (see `section33_row.tex` and
`section32_replacements.md`).

**Command for every row:** `make -C GFF/code/LRI_C8_D3_HPC -f public.mk replay` (`public/replay_c8_3.py`; 1 core, about 20 s,
40 s with the hosted tables). The row id is the id in `.public_out/replay/REPLAY.md`. Paths are relative to `GFF/`; `prod1/` is
`code/LRI_C8_D3_HPC/benchmarks/symmetry_2026-10-c8/production/prod1/` and `pilot/` its sibling `.../symmetry_2026-10-c8/pilot/`.

**Tolerances and why.** A printed decimal is checked to half a unit of its last printed digit, because the note rounds the
record: a tighter test would test the rounding rule, a looser one would let a wrong digit pass. Counts, seeds and sizes are
exact. "Logical" rows test a stated property (a sign, a bound, a status). The recomputation rows (step A) use the
package's own re-verification tolerance, relative 1e-10, and 1e-12 for C8 and its SE: the merged batches are float64 and
the assembly is the same code, so only BLAS rounding can differ (measured 2.8e-16 for C8 and 0 for the SE on macOS arm64).
The independent check (1600.98 ± 3.97, pull −0.40) is mapped in the C8_3_check draft.

Local outcome (macOS arm64, Python 3.10.12, NumPy 1.24.4, 2026-10-13): 214 PASS, 0 FAIL, 1 KNOWN, 2 ERRATUM, 1 INFO
with the hosted `graph_replicates.csv`; without them 3 rows are NOT RUN. See `replay_local_run.txt`.

##### 1. Integrity and recomputation (steps P, R, A, T, H)

| step | check | outcome | source | tolerance |
|---|---|---|---|---|
| P | SHA256SUMS (4fbd1bae) of every shipped file | PASS | SHA256SUMS | sha256; absent only under the export excludes (NOT_EXPORTED) or public/dropped_paths.txt |
| P | merged notes not shipped (public/dropped_paths.txt) | INFO | SHA256SUMS | reference/reference/C7_d2_complete.tex, one TeX note per direction (2026-10-16) |
| P | evidence files of 6dd4a75a | PASS | public/SHA256SUMS.evidence_6dd4a75a | sha256 |
| R | SHA256SUMS.symmetry | PASS | results/C8_3/SHA256SUMS.symmetry | sha256 |
| R | result -> manifest.json | PASS | C8_result.json source_manifest_sha256 | sha256 |
| R | result -> 24 merged.json | PASS | C8_result.json merged_sha256 | sha256 |
| R | manifest -> 24 config.json | PASS | manifest.json groups[].sha256 | sha256 |
| R | manifest -> cost_model.json | PASS | manifest.json cost_model_sha256 | sha256 |
| R | manifest/result -> design bundle | PASS | manifest.json allocation.meta_sha256 | sha256 |
| R | merged.json: complete, self-hash, plan and config binding, shape | PASS | groups/*/merged.json | exact |
| R | scientific identity of every group | PASS | C8_result.json science_sha256 | exact |
| P | tools/assemble.py is the production tool | PASS | C8_result.json tool_sha256 | sha256 |
| P | tools/report.py is the production tool | PASS | C8_result.json tool_sha256 | sha256 |
| P | tools/production.py is the production tool | PASS | C8_result.json tool_sha256 | sha256 |
| P | tools/common.py is the production tool | PASS | C8_result.json tool_sha256 | sha256 |
| P | vendored assembly module | PASS | C8_result.json assembly | sha256 |
| P | vendored HANDOFF | PASS | C8_result.json assembly | sha256 |
| P | POWER_PROTOCOL.md | PASS | C8_result.json power_protocol | sha256 |
| P | inputs/manifest.json is the plan's | PASS | manifest.json inputs_manifest_sha256 | sha256 |
| P | inputs/two_loop.json | PASS | C8_result.json two_loop_sha256 | sha256 |
| P | references/lower_order_d3.json | PASS | C8_result.json references_sha256 | sha256 |
| P | inputs/ files against inputs/manifest.json | PASS | inputs/manifest.json sha256 | sha256 |
| A | assemble.combine on the 24 merged batches = C8_result.json (every field) | PASS | tools/assemble.py combine (vendored order-8 assembly) | rel 1e-10, abs floor 1e-13 |
| A | hard-gate rounding diagnostics below their gate thresholds (stored and recomputed) | PASS | C8_result.json hard_gates | top-slot/loop-7 1e-12, affinity 1e-10 |
| A | C8_full reproduced | PASS | assemble.combine | rel 1e-12 |
| A | sampling_standard_error reproduced | PASS | assemble.combine | rel 1e-12 |
| A | power_free_C8 reproduced | PASS | assemble.combine | rel 1e-12 |
| A | power_correction reproduced | PASS | assemble.combine | rel 1e-10 |
| A | estimator digits as printed in Sec 1 | PASS | C8_result.json | repr equality |
| A | tools/verify_result.py C8_result.json (file mode) | KNOWN | tools/verify_result.py | exit 0 on the production CPU class |
| T | tail_ntrend/ntrend.py rerun = committed ntrend.json | PASS | tail_ntrend/ntrend.json | exact (JSON equality) |
| T | prod_tails.csv reproduces the tail monitor's listed rows | PASS | ntrend.py cross_check_vs_tail_monitor | < 1e-12 |
| H | graph_replicates.csv pins | PASS | merged.json graph_replicates_sha256 | sha256 |
| H | ab_split.py rerun = committed report.txt | PASS | prod1/ab_split/report.txt | byte-identical text |
| H | tail monitor variance shares recomputed | PASS | C8_result.json tail_monitor.listed[].share | rel 1e-10 |

##### 2. Quoted numbers (step N)

| id | where (note) | quoted | record value | file (source) | tolerance | outcome |
|---|---|---|---|---|---|---|
| S1.1 | abstract, Sec 1 table, 32.1 box | 1602.6 | 1602.60522297 | results/C8_3/C8_result.json | /x-q/ <= 0.05 | PASS |
| S1.2 | abstract, Sec 1 table, 32.1 box: allowance = 4 SE rounded up to 0.1 | 3.9 | 3.9 | results/C8_3/C8_result.json (4 x sampling_standard_error) | /x-q/ <= 1e-09 | PASS |
| S1.3 | Sec 1 estimator table | 1602.6052229663408, 0.9516489064 | 1602.6052229663408, 0.9516489064069612 | results/C8_3/C8_result.json | repr / 10 digits | PASS |
| S1.4 | 32.1: 4 SE | 3.81 | 3.80659562563 | results/C8_3/C8_result.json | /x-q/ <= 0.005 | PASS |
| S1.5 | 32.1, Sec 1 allowance text: half-stream deviations | 0.046 | 0.0460983606424 | results/C8_3/C8_result.json half_streams[*][8] | /x-q/ <= 0.0005 | PASS |
| S1.6 | Sec 1, 32.1 | 4 SE exceeds both half-stream deviations | 4 SE 3.8066 > 0.0461 | results/C8_3/C8_result.json | logical | PASS |
| S1.7 | 32.1: the record quotes | 1.0 | 0.951648906407 | results/C8_3/C8_result.json | /x-q/ <= 0.05 | PASS |
| S1.8 | paper `\CeightThree` (PDG rounding of 4 SE) | 1603 ± 4 | 1603 +- 4 (4 SE = 3.8066) | results/C8_3/C8_result.json | string equality | PASS |
| 32.1a | 32.1 table | 1601.9999290 | 1601.99992896 | results/C8_3/C8_result.json | /x-q/ <= 5e-08 | PASS |
| 32.1b | 32.1 table | 0.7279030 | 0.727903027027 | results/C8_3/C8_result.json | /x-q/ <= 5e-08 | PASS |
| 32.1c | 32.1 table | 0.6052940 | 0.605294004705 | results/C8_3/C8_result.json | /x-q/ <= 5e-08 | PASS |
| 32.1d | 32.1 table | 0.6129303 | 0.612930299236 | results/C8_3/C8_result.json | /x-q/ <= 5e-08 | PASS |
| 32.1e | 32.1 table | 1602.6052230 | 1602.60522297 | results/C8_3/C8_result.json | /x-q/ <= 5e-08 | PASS |
| 32.1f | 32.1 table | 0.9516489 | 0.951648906407 | results/C8_3/C8_result.json | /x-q/ <= 5e-08 | PASS |
| 32.1g | 32.1, 32.3: pilot | 1619 | 1619.27306524 | pilot/evidence/pilot_report.json cost_table.c8_pilot | /x-q/ <= 0.5 | PASS |
| 32.1h | 32.1, 32.3: pilot SE | 16 | 15.7874093179 | pilot_report.json cost_table.c8_pilot_se | /x-q/ <= 0.5 | PASS |
| 32.1i | 32.1: pilot vs production (combined SE) | 1.05 | 1.05385516084 | pilot_report.json + results/C8_3/C8_result.json | /x-q/ <= 0.005 | PASS |
| 32.1j | 32.1: C8(3)/C7(3) | -7.27 | -7.27285063376 | results/C8_3/C8_result.json + references/lower_order_d3.json (C7(3) estimator) | /x-q/ <= 0.005 | PASS |
| 32.1k3 | 32.1: C3/C2 | -1.95 | -1.95109831658 | references/lower_order_d3.json; C2 = coefficients[2] (exact input) | /x-q/ <= 0.005 | PASS |
| 32.1k4 | 32.1: C4/C3 | -3.47 | -3.47321190266 | references/lower_order_d3.json; C2 = coefficients[2] (exact input) | /x-q/ <= 0.005 | PASS |
| 32.1k5 | 32.1: C5/C4 | -4.76 | -4.76388330474 | references/lower_order_d3.json; C2 = coefficients[2] (exact input) | /x-q/ <= 0.005 | PASS |
| 32.1k6 | 32.1: C6/C5 | -5.74 | -5.73904441402 | references/lower_order_d3.json; C2 = coefficients[2] (exact input) | /x-q/ <= 0.005 | PASS |
| 32.1k7 | 32.1: C7/C6 | -6.56 | -6.56296888876 | references/lower_order_d3.json; C2 = coefficients[2] (exact input) | /x-q/ <= 0.005 | PASS |
| 32.1l | 32.1, Sec 1, Sec 32.7 | independent code 1600.98 +- 3.97, -0.40 | covered by GFF/code C8_3_check (other package) |  | logical | INFO |
| 32.2a.free3 | 32.2 integrated classes | 5 | 5 | results/C8_3/groups/a_*/config.json counts (b equal: True) | exact | PASS |
| 32.2a.free4 | 32.2 integrated classes | 16 | 16 | results/C8_3/groups/a_*/config.json counts (b equal: True) | exact | PASS |
| 32.2a.free5 | 32.2 integrated classes | 76 | 76 | results/C8_3/groups/a_*/config.json counts (b equal: True) | exact | PASS |
| 32.2a.free6 | 32.2 integrated classes | 395 | 395 | results/C8_3/groups/a_*/config.json counts (b equal: True) | exact | PASS |
| 32.2a.free7 | 32.2 integrated classes | 2,441 | 2441 | results/C8_3/groups/a_*/config.json counts (b equal: True) | exact | PASS |
| 32.2a.free8 | 32.2 integrated classes | 16,064 | 16064 | results/C8_3/groups/a_*/config.json counts (b equal: True) | exact | PASS |
| 32.2a.power3 | 32.2 integrated classes | 1 | 1 | results/C8_3/groups/a_*/config.json counts (b equal: True) | exact | PASS |
| 32.2a.power4 | 32.2 integrated classes | 3 | 3 | results/C8_3/groups/a_*/config.json counts (b equal: True) | exact | PASS |
| 32.2a.power5 | 32.2 integrated classes | 20 | 20 | results/C8_3/groups/a_*/config.json counts (b equal: True) | exact | PASS |
| 32.2a.power6 | 32.2 integrated classes | 107 | 107 | results/C8_3/groups/a_*/config.json counts (b equal: True) | exact | PASS |
| 32.2a.power7 | 32.2 integrated classes | 709 | 709 | results/C8_3/groups/a_*/config.json counts (b equal: True) | exact | PASS |
| 32.2a.power8 | 32.2 integrated classes | 4,336 | 4336 | results/C8_3/groups/a_*/config.json counts (b equal: True) | exact | PASS |
| 32.2b | 32.2 | 24,173 | 24173 | group configs; = inputs/manifest.json kernels | exact | PASS |
| 32.2b2 | 32.2 (inputs) | 24,173 | 24173 | inputs/manifest.json | exact | PASS |
| 32.2c | 32.2 | sixteen propagators, 31-dimensional nets, 350-digit GMP | emax 16, dimmax 31, mp_digits10 350 | results/C8_3/C8_result.json build | logical | PASS |
| 32.2d | 32.2 | order 7 bit for bit with the C7(3) worker on the L2 graph and the 3,511 C7(3) kernels | J-VAL-2 570904 on the final code: passed, G-C7 exact over 3773 L<=7 kernels (the 3,511 C7(3) ones and the 262 new L7 ones) + L2 | benchmarks/symmetry_2026-10-c8/stage6_a914db2/val2/validate_full.json | logical | PASS |
| 32.2e | 32.2 | replays the archived seventh-order production | 168528 rows, C7 rebuilt rel 1.0e-15 | benchmarks/symmetry_2026-10-c8/stage5_3cbe7a4/run1/archived_stream_replay.json | logical | PASS |
| 32.2f | 32.2 | AMD vs Intel at most 2.0e-11 normalized | symmetry job 566410 as recorded | docs/NUMERICS.md "CPU dependence (measured)" | logical | PASS |
| 32.2g | 32.2 | every production job on one processor model (AMD EPYC 7543) | cpu_vendor.json vendor amd; the CPU pin (slurm/site.sh c8_cpu_guard, EPYC 7543) and prod1/README.md | results/C8_3/cpu_vendor.json | logical | PASS |
| 32.2h | 32.2 | b_{2,6}(3) = -29.258124480916806558671227221989158045345... | -29.25812448091680655867122722198915804534567 | inputs/two_loop.json B2[6] | printed digits | PASS |
| 32.2i | 32.2: two contours at 65 digits agree to | 2.7e-56 | 2.68e-56 | vendor/c8_assembly/inputs_d3/checks.json | /x-q/ <= 5e-58 | PASS |
| 32.2i2 | 32.2 | the contours are at 65 digits; reference at 95 digits | dps 65, reference dps 95 | checks.json settings | logical | PASS |
| 32.2j | 32.2: reference confirms stored entries to | 1.7e-57 | 1.72e-57 | checks.json | /x-q/ <= 5e-59 | PASS |
| 32.2k | 32.2 | 42 Gamma jets correctly rounded, two contours at 100 digits | 42 jets, two Cauchy contours of log G (radius/nodes [('0.041', 128),  | checks.json gamma.cauchy_check | logical | PASS |
| 32.2l | 32.2 | b_3^p(0) = -16 pi/15 | -16 pi/15 | results/C8_3/C8_result.json | logical | PASS |
| 32.2m | 32.2: b_3^p(0) estimate | -3.3509158 | -3.35091579742 | results/C8_3/C8_result.json | /x-q/ <= 5e-08 | PASS |
| 32.2n | 32.2: its SE | 0.0000894 | 8.94323335792e-05 | results/C8_3/C8_result.json | /x-q/ <= 5e-08 | PASS |
| 32.2o | 32.2: its pull | +1.30 | 1.30116705581 | results/C8_3/C8_result.json | /x-q/ <= 0.005 | PASS |
| 32.2p | 32.2 | dC8/d(b,c)_{L,8-L} = (-1,3)/3^(L+1) | six rows | results/C8_3/C8_result.json hard_gates.top_slot | logical | PASS |
| 32.2q | 32.2: top-slot gate holds to | 4e-16 | 4.00131588019e-16 | results/C8_3/C8_result.json | /x-q/ <= 5e-17 | PASS |
| 32.2r | 32.2: A_3 = -b_{2,0}/6 | 1.6309960686 | 1.63099606865 | results/C8_3/C8_result.json hard_gates.loop7 | /x-q/ <= 5e-11 | PASS |
| 32.2r2 | 32.2: A_3 from inputs/two_loop.json | 1.6309960686 | 1.63099606865 | inputs/two_loop.json B2[0] | /x-q/ <= 5e-11 | PASS |
| 32.2s | 32.2 | loop 7 enters through (-16 A3, 42 A3)/19683 | expected [-0.0013258109586140225, 0.0034802537663618095] | results/C8_3/C8_result.json | logical | PASS |
| 32.2t | 32.2: loop-7 gate holds to | 8e-16 | 8.17765282027e-16 | results/C8_3/C8_result.json | /x-q/ <= 5e-17 | PASS |
| 32.2u | 32.2: response to loops 5-8 linear to | 3e-13 | 2.92210700081e-13 | results/C8_3/C8_result.json | /x-q/ <= 5e-14 | PASS |
| 32.2v | 32.2 | the three hard gates pass | gates block | results/C8_3/C8_result.json | logical | PASS |
| 32.3a | 32.3: screen graphs | 2,732 | 2732 | pilot/campaigns/pilotA2-s6-20261007/subset_summary.json (graphs over both campaigns / 2) | exact | PASS |
| 32.3b | 32.3: screen points per replicate | 4,096 | 4096 | pilotA2 manifest.json allocation | exact | PASS |
| 32.3c | 32.3 | full pilot: 8 replicates of 4,096 points, 16 for power L8 | {"source": "pilot", "points": 4096, "replicates": 8, "group_replicates": {"power:8": 16}, "graphs": null} | pilotF manifest.json allocation | logical | PASS |
| 32.3d | 32.3: confirmation graphs | 710 | 710 | pilotC subset_summary.json | exact | PASS |
| 32.3e | 32.3: cap a quarter of the full pilot L8 cost | 0.25 | 0.25 | pilot_report.json pc_cap | /x-q/ <= 0 | PASS |
| 32.3e2 | 32.3 | the confirmation stayed within its cap | used 226200 s of 226209 s | pilot_report.json pc_cap | logical | PASS |
| 32.3f | 32.3: the pilot used | 422 | 421.72 | prod1/c8d3_prod1_budget.txt (pilot line) | /x-q/ <= 0.5 | PASS |
| 32.3g | 32.3: replicates per group | 128 | 128 | group configs (all 24 equal: True) | exact | PASS |
| 32.3h | 32.3: at least points per graph | 4,096 | 4096 | group configs counts | exact | PASS |
| 32.3i | 32.3: predicted SE | 0.87 | 0.872423967607 | prod1/production/design_freeze.json | /x-q/ <= 0.005 | PASS |
| 32.3j | 32.3: with the safety factor 1.5 | 1.31 | 1.30863595141 | design_freeze.json x 1.5 | /x-q/ <= 0.005 | PASS |
| 32.3k | 32.3: estimated cost (core-h) | 15,492 | 15492.128679 | design_freeze.json | /x-q/ <= 0.5 | PASS |
| 32.3l | 32.3: target SE | 1 | 1 | design_prod/design_meta.json | /x-q/ <= 0 | PASS |
| 32.3l2 | 32.3: about 6e-4 of C8(3) | 6e-4 | 0.000623983989113 | target / C8 | /x-q/ <= 5e-05 | PASS |
| 32.3m | 32.3 | the cheapest of three power-of-two designs | A 15492.1, B 21130.8, C 30984.3 core-h | production/price/*.json (last row of each) | logical | PASS |
| 32.3n | 32.3 | campaigns a, b: rates x0.8, x0.7; 52- and 60-bit nets | {'a': ('.8', 52), 'b': ('.7', 60)} | group configs rate, net.bits | logical | PASS |
| 32.3o | 32.3 | fresh base seed (not a pilot seed) | seed 7204841255549554256 | manifest.json seed; pilot manifests | logical | PASS |
| 32.3p | 32.3: kernel samples in the design | 365,441,318,912 | 365441318912 | group configs samples (sum) | exact | PASS |
| 32.4a | 32.4 | 9 to 12 October 2026 | 2026-10-09T01:26:16 .. 2026-10-12T04:27:54 | prod1/jobs_sacct.psv | logical | PASS |
| 32.4b | 32.4: lanes of threads | 8 | 8 | manifest.json threads | exact | PASS |
| 32.4c | 32.4: at most nodes at a time | 8 | 8 | jobs_sacct.psv (overlapping lane jobs, one whole node each) | exact | PASS |
| 32.4d | 32.4: nodes in all | 10 | 10 | jobs_sacct.psv NodeList | exact | PASS |
| 32.4d2 | 32.4 | whole nodes (64 CPUs) of the AMD partition |  | jobs_sacct.psv | logical | PASS |
| 32.4e | 32.4: work indices | 1,941 | 1941 | manifest.json jobs | exact | PASS |
| 32.4f | 32.4: checkpoint blocks | 25,714 | 25714 | manifest.json jobs[].blocks | exact | PASS |
| 32.4g | 32.4 | all indices and blocks completed | 24 groups merged | prod1/c8d3_prod1_status.txt | logical | PASS |
| 32.4h | 32.4: lane core-hours | 14,970 | 14969.6177778 | jobs_sacct.psv (ElapsedRaw x AllocCPUS) | /x-q/ <= 0.5 | PASS |
| 32.4i | 32.4: of the design estimate | 0.97 | 0.966272491533 | jobs_sacct.psv / design_freeze.json | /x-q/ <= 0.005 | PASS |
| 32.4j | 32.4: merges (core-h) | 106 | 105.902222222 | jobs_sacct.psv | /x-q/ <= 0.5 | PASS |
| 32.4k | 32.4: production in all (core-h) | 15,102 | 15101.56 | prod1/c8d3_prod1_budget.txt (production line) | /x-q/ <= 0.5 | PASS |
| 32.4l | 32.4 table | 1604.684 | 1604.68386994 | results/C8_3/C8_result.json | /x-q/ <= 0.0005 | PASS |
| 32.4m | 32.4 table | 1.239 | 1.23922060035 | results/C8_3/C8_result.json | /x-q/ <= 0.0005 | PASS |
| 32.4n | 32.4 table | 1600.527 | 1600.52657542 | results/C8_3/C8_result.json | /x-q/ <= 0.0005 | PASS |
| 32.4o | 32.4 table | 1.445 | 1.44460197743 | results/C8_3/C8_result.json | /x-q/ <= 0.0005 | PASS |
| 32.4p | 32.4 table | 1602.651 | 1602.65132133 | results/C8_3/C8_result.json | /x-q/ <= 0.0005 | PASS |
| 32.4q | 32.4 table | 1602.559 | 1602.55912488 | results/C8_3/C8_result.json | /x-q/ <= 0.0005 | PASS |
| 32.4r | 32.4 table | 1602.605 | 1602.60522297 | results/C8_3/C8_result.json | /x-q/ <= 0.0005 | PASS |
| 32.4s | 32.4 table | 0.952 | 0.951648906407 | results/C8_3/C8_result.json | /x-q/ <= 0.0005 | PASS |
| 32.4t | 32.4: campaigns differ by (combined SE) | 2.18 | 2.18425854458 | results/C8_3/C8_result.json | /x-q/ <= 0.005 | PASS |
| 32.4u | 32.4: linearized a - b | 4.16 | 4.15729451356 | replay (ab_split.py method: j8 . batch means) | /x-q/ <= 0.005 | PASS |
| 32.4v | 32.4: its SE | 1.90 | 1.90329781281 | replay | /x-q/ <= 0.005 | PASS |
| 32.4w | 32.4: total exact a - b | 4.16 | 4.15729451356 | results/C8_3/C8_result.json | /x-q/ <= 0.005 | PASS |
| 32.4x | 32.4: power-free L8 | +1.36 | 1.36339437822 | replay | /x-q/ <= 0.005 | PASS |
| 32.4y | 32.4: power L8 | +1.39 | 1.38658386219 | replay | /x-q/ <= 0.005 | PASS |
| 32.4z | 32.4: power-free L7 | +0.90 | 0.89687232737 | replay | /x-q/ <= 0.005 | PASS |
| 32.4aa | 32.4: power-free L5 | +0.19 | 0.191440694729 | replay | /x-q/ <= 0.005 | PASS |
| 32.4ab | 32.4: its SE | 0.10 | 0.0957269798462 | replay | /x-q/ <= 0.005 | PASS |
| 32.4ac | 32.4 | no term above two of its own SEs (to the printed 2.00) | largest /pull/ 1.9999 (free L5; ab_split/report.txt prints +2.00) | replay | logical | PASS |
| 32.4ad | 32.4: chi2 per graph, 16,064 power-free | 0.994 | 0.994 | prod1/ab_split/report.txt (recomputed by step H when the hosted graph_replicates.csv are fetched) | /x-q/ <= 0.0005 | PASS |
| 32.4ae | 32.4: chi2 per graph, 4,336 power | 1.010 | 1.01 | prod1/ab_split/report.txt (recomputed by step H when the hosted graph_replicates.csv are fetched) | /x-q/ <= 0.0005 | PASS |
| 32.4af | 32.4: ten largest carry (free) | +0.19 | 0.1902 | prod1/ab_split/report.txt (recomputed by step H when the hosted graph_replicates.csv are fetched) | /x-q/ <= 0.005 | PASS |
| 32.4ag | 32.4: ten largest carry (power) | -0.07 | -0.0696 | prod1/ab_split/report.txt (recomputed by step H when the hosted graph_replicates.csv are fetched) | /x-q/ <= 0.005 | PASS |
| 32.4ah.free3 | 32.4 error table | 0.001 | 0.00119093569226 | results/C8_3/C8_result.json error_by_loop | /x-q/ <= 0.0005 | PASS |
| 32.4ah.free4 | 32.4 error table | 0.011 | the record gives 0.0104766; corrected text 0.010 checked next. Sec 32.4 error table, power-free L=4: error_by_loop.free.4.se = 0.010477 | results/C8_3/C8_result.json error_by_loop | logical | ERRATUM |
| 32.4ah.free4* | 32.4 error table, corrected | 0.010 | 0.010476588168 | results/C8_3/C8_result.json error_by_loop | /x-q/ <= 0.0005 | PASS |
| 32.4ah.free5 | 32.4 error table | 0.048 | 0.0478634899231 | results/C8_3/C8_result.json error_by_loop | /x-q/ <= 0.0005 | PASS |
| 32.4ah.free6 | 32.4 error table | 0.160 | 0.160083738697 | results/C8_3/C8_result.json error_by_loop | /x-q/ <= 0.0005 | PASS |
| 32.4ah.free7 | 32.4 error table | 0.362 | 0.361978284952 | results/C8_3/C8_result.json error_by_loop | /x-q/ <= 0.0005 | PASS |
| 32.4ah.free8 | 32.4 error table | 0.609 | 0.609020743696 | results/C8_3/C8_result.json error_by_loop | /x-q/ <= 0.0005 | PASS |
| 32.4ah.power3 | 32.4 error table | 0.000 | 0.000392680690257 | results/C8_3/C8_result.json error_by_loop | /x-q/ <= 0.0005 | PASS |
| 32.4ah.power4 | 32.4 error table | 0.003 | 0.00311875940086 | results/C8_3/C8_result.json error_by_loop | /x-q/ <= 0.0005 | PASS |
| 32.4ah.power5 | 32.4 error table | 0.018 | 0.0183457342831 | results/C8_3/C8_result.json error_by_loop | /x-q/ <= 0.0005 | PASS |
| 32.4ah.power6 | 32.4 error table | 0.079 | 0.0788859447547 | results/C8_3/C8_result.json error_by_loop | /x-q/ <= 0.0005 | PASS |
| 32.4ah.power7 | 32.4 error table | 0.220 | 0.220161679036 | results/C8_3/C8_result.json error_by_loop | /x-q/ <= 0.0005 | PASS |
| 32.4ah.power8 | 32.4 error table | 0.566 | 0.566243408549 | results/C8_3/C8_result.json error_by_loop | /x-q/ <= 0.0005 | PASS |
| 32.4ai | 32.4: realized SE / design prediction | 1.09 | 1.0908101356 | results/C8_3/C8_result.json + design_freeze.json | /x-q/ <= 0.005 | PASS |
| 32.5a | 32.5: listed eight-loop graphs | 10,034 | 10034 | results/C8_3/C8_result.json tail_monitor | exact | PASS |
| 32.5b | 32.5: largest variance share (%) | 1.65 | 1.64921975145 | results/C8_3/C8_result.json | /x-q/ <= 0.005 | PASS |
| 32.5c | 32.5: flagged above 3% | 0 | 0 | results/C8_3/C8_result.json | exact | PASS |
| 32.5d | 32.5: listed share of power-free L8 variance (%), campaign a | 62 | 62.1862034906 | results/C8_3/C8_result.json (campaign b: 63.1) | /x-q/ <= 0.5 | PASS |
| 32.5e | 32.5: listed share of power L8 variance (%), campaign a | 99.5 | 99.547778899 | results/C8_3/C8_result.json (campaign b: 99.4) | /x-q/ <= 0.05 | PASS |
| 32.5f | 32.5: rates re-derived on graphs | 48 | 48 | production/margin_probe{1,2}/margin_report_*.json | exact | PASS |
| 32.5g | 32.5: the two controls (per sector) +  | 4 | 4 | margin_report_571479.json roles (2 per sector) | exact | PASS |
| 32.5h | 32.5: power L8 graphs whose xi did not fall | 16 | 16 | margin reports (14 in probe 2, the others in probe 1) | exact | PASS |
| 32.5i | 32.5: apparent deficits | 5 | 5 | margin_report_571479.json deficits | exact | PASS |
| 32.5j | 32.5 | crossovers t^1.5 -> t^1.0 with a zero in between; asymptotic exponent 1.0 | 31 deficit levels: start 1.500000..1.500000, end 0.999999999999..1.000000000001, sign changes 1..2 | production/margin_ladder/ladder_571518.json | logical | PASS |
| 32.5k | 32.5: confirmed possible infinite-variance graphs | 441 | 441 | pilot_report.json action2_confirm | exact | PASS |
| 32.5l | 32.5: of them power-free | 246 | 246 | pilot_report.json | exact | PASS |
| 32.5m | 32.5: power | 195 | 195 | pilot_report.json | exact | PASS |
| 32.5n.free | 32.5: pilot exponent PF->PC (free), "about N^-0.23" | -0.23 within the two campaigns' medians | medians over the confirmed graphs: a -0.229, b -0.258 (pilot log: "-0.23 (a)") | ntrend.json summary.piv_*.beta_pf_pc (pilot PF 4,096 -> PC 32,768) | logical | PASS |
| 32.5n.power | 32.5: pilot exponent PF->PC (power), "about N^-0.18" | -0.18 within the two campaigns' medians | medians over the confirmed graphs: a -0.176, b -0.194 (pilot log: "-0.18 (a)") | ntrend.json summary.piv_*.beta_pf_pc (pilot PF 4,096 -> PC 32,768) | logical | PASS |
| 32.5o | 32.5: interpolation medians / trend, low | 0.996 | 0.996379220867 | ntrend.json summary.*.new_n.by_n | /x-q/ <= 0.0005 | PASS |
| 32.5p | 32.5: high | 1.031 | 1.03123929293 | ntrend.json | /x-q/ <= 0.0005 | PASS |
| 32.5q | 32.5: above the pilot 32,768 value, low (%) | 13 | 12.6265427835 | ntrend.json | /x-q/ <= 0.5 | PASS |
| 32.5r | 32.5: high (%) | 38 | 38.4019336998 | ntrend.json | /x-q/ <= 0.5 | PASS |
| 32.5s | 32.5: graph-campaigns at 65,536 | 13 | 13 | ntrend.json | exact | PASS |
| 32.5t | 32.5: their medians / xi(32,768), low | 0.82 | 0.822996715804 | ntrend.json | /x-q/ <= 0.005 | PASS |
| 32.5u | 32.5: high | 0.88 | the record gives 0.874755; corrected text 0.87 checked next. Sec 32.5 "to medians of 0.82 to 0.88": the three extrapolated medians are 0.... | ntrend.json | logical | ERRATUM |
| 32.5u* | 32.5: high, corrected | 0.87 | 0.874755116332 | ntrend.json | /x-q/ <= 0.005 | PASS |
| 32.5v | 32.5: / extrapolated trend, low | 0.94 | 0.936227965799 | ntrend.json | /x-q/ <= 0.005 | PASS |
| 32.5w | 32.5: high | 1.02 | 1.01956855826 | ntrend.json | /x-q/ <= 0.005 | PASS |
| 32.5x | 32.5: free campaign shift at matched length, low | +0.03 | 0.0336352841581 | ntrend.json ab_shift_free (production lengths) | /x-q/ <= 0.005 | PASS |
| 32.5y | 32.5: high | +0.05 | 0.0488927445073 | ntrend.json ab_shift_free | /x-q/ <= 0.005 | PASS |
| 32.5z | 32.5 | opposite in sign to the rate-limited prediction | observed [0.0488927445072912, 0.03363528415810296], model [-0.042627876397252615, -0.0637843613637756] | ntrend.json | logical | PASS |
| 32.6a3 | 32.6 table: C3 estimate | -0.3535809354 | -0.353580935359 | results/C8_3/C8_result.json lower_order_checks | /x-q/ <= 5e-11 | PASS |
| 32.6b3 | 32.6 table: C3 SE | 1.38e-6 | 1.37589022903e-06 | results/C8_3/C8_result.json | /x-q/ <= 5e-09 | PASS |
| 32.6c3 | 32.6 table: C3 pull | +0.43 | 0.425233092746 | results/C8_3/C8_result.json | /x-q/ <= 0.005 | PASS |
| 32.6a4 | 32.6 table: C4 estimate | 1.2280445577 | 1.22804455769 | results/C8_3/C8_result.json lower_order_checks | /x-q/ <= 5e-11 | PASS |
| 32.6b4 | 32.6 table: C4 SE | 3.88e-5 | 3.88047052061e-05 | results/C8_3/C8_result.json | /x-q/ <= 5e-08 | PASS |
| 32.6c4 | 32.6 table: C4 pull | -0.49 | -0.489312811879 | results/C8_3/C8_result.json | /x-q/ <= 0.005 | PASS |
| 32.6a5 | 32.6 table: C5 estimate | -5.8499922821 | -5.84999228209 | results/C8_3/C8_result.json lower_order_checks | /x-q/ <= 5e-11 | PASS |
| 32.6b5 | 32.6 table: C5 SE | 4.86e-4 | 0.000486107844077 | results/C8_3/C8_result.json | /x-q/ <= 5e-07 | PASS |
| 32.6c5 | 32.6 table: C5 pull | +0.74 | 0.73880448633 | results/C8_3/C8_result.json | /x-q/ <= 0.005 | PASS |
| 32.6a6 | 32.6 table: C6 estimate | 33.5763740 | 33.5763740486 | results/C8_3/C8_result.json lower_order_checks | /x-q/ <= 5e-08 | PASS |
| 32.6b6 | 32.6 table: C6 SE | 0.0050853 | 0.00508534976732 | results/C8_3/C8_result.json | /x-q/ <= 5e-08 | PASS |
| 32.6c6 | 32.6 table: C6 pull | +0.19 | 0.186250695673 | results/C8_3/C8_result.json | /x-q/ <= 0.005 | PASS |
| 32.6a7 | 32.6 table: C7 estimate | -220.3847628 | -220.38476283 | results/C8_3/C8_result.json lower_order_checks | /x-q/ <= 5e-08 | PASS |
| 32.6b7 | 32.6 table: C7 SE | 0.0528950 | 0.0528950376867 | results/C8_3/C8_result.json | /x-q/ <= 5e-08 | PASS |
| 32.6c7 | 32.6 table: C7 pull | -0.49 | -0.490578912352 | results/C8_3/C8_result.json | /x-q/ <= 0.005 | PASS |
| 32.6d | 32.6 | no pull above three |  | results/C8_3/C8_result.json | logical | PASS |
| 32.6e4 | 32.6: power correction at order 4 | 8.6e-6 | 8.58510894997e-06 | results/C8_3/C8_result.json power_differences | /x-q/ <= 5e-08 | PASS |
| 32.6f4 | 32.6: its SE | 7.3e-6 | 7.31360491968e-06 | results/C8_3/C8_result.json power_difference_errors | /x-q/ <= 5e-08 | PASS |
| 32.6e5 | 32.6: power correction at order 5 | 9.2e-5 | 9.22732928554e-05 | results/C8_3/C8_result.json power_differences | /x-q/ <= 5e-07 | PASS |
| 32.6f5 | 32.6: its SE | 13.1e-5 | 0.000131164896368 | results/C8_3/C8_result.json power_difference_errors | /x-q/ <= 5e-07 | PASS |
| 32.6e6 | 32.6: power correction at order 6 | 3.3e-4 | 0.000328123300015 | results/C8_3/C8_result.json power_differences | /x-q/ <= 5e-06 | PASS |
| 32.6f6 | 32.6: its SE | 19.5e-4 | 0.00195351557992 | results/C8_3/C8_result.json power_difference_errors | /x-q/ <= 5e-06 | PASS |
| 32.6e7 | 32.6: power correction at order 7 | 0.009 | 0.00912234792338 | results/C8_3/C8_result.json power_differences | /x-q/ <= 0.0005 | PASS |
| 32.6f7 | 32.6: its SE | 0.024 | 0.0243073132171 | results/C8_3/C8_result.json power_difference_errors | /x-q/ <= 0.0005 | PASS |
| 32.6e8 | 32.6: power correction at order 8 | 0.61 | 0.605294004705 | results/C8_3/C8_result.json power_differences | /x-q/ <= 0.005 | PASS |
| 32.6f8 | 32.6: its SE | 0.61 | 0.612930299236 | results/C8_3/C8_result.json power_difference_errors | /x-q/ <= 0.005 | PASS |
| 32.6g | 32.6 | order 3 difference at rounding level | 0.0 | results/C8_3/C8_result.json | logical | PASS |
| 32.6h | 32.6: bootstrap resamples | 4,096 | 4096 | results/C8_3/C8_result.json | exact | PASS |
| 32.6i | 32.6: bootstrap SE | 0.940 | 0.940337212307 | results/C8_3/C8_result.json | /x-q/ <= 0.0005 | PASS |
| 32.6j | 32.6: covariance SE | 0.952 | 0.951648906407 | results/C8_3/C8_result.json | /x-q/ <= 0.0005 | PASS |
| 32.6k | 32.6: bootstrap SE (replayed) | 0.940 | 0.940337212307 | replay (assemble.combine, seed 70530413) | /x-q/ <= 0.0005 | PASS |

##### 3. Notes on particular sources

- **Abstract and Section 1, "1602.6 ± 3.9"** (rows S1.1–S1.6): 1602.6 is the estimator rounded; 3.9 = ceil(4 × 0.95165 / 0.1) × 0.1;
  the paper (`\CeightThree`) rounds the same 4 SE = 3.8066 by the PDG rule (leading digits 381: one significant digit)
  to 1603 ± 4 (row S1.8). The note keeps one more digit.
  "Exceeds both half-stream deviations (0.046)" uses `C8_result.json` `half_streams`. The rule was fixed after the result
  and confirmed by the author (`public/REVIEWS.md`, section 4).
- **"1.05 combined standard errors" (pilot):** (1619.273 − 1602.605) / sqrt(15.787² + 0.952²), with the pilot values of
  `pilot/evidence/pilot_report.json` `cost_table` (the pilot result file is not shipped; the report binds its sha256).
- **C8/C7 = −7.27 and the preceding ratios:** C2 from `C8_result.json` `coefficients[2]` (an exact input), C3..C7 from
  `code/LRI_C8_D3_HPC/references/lower_order_d3.json` (special-function values and the C6(3), C7(3) production estimators).
- **Section 32.2 worker statements** (3,511 kernels bit for bit; the archived production replayed; ≤ 2.0e-11 across CPU types):
  J-VAL-2 570904 on the final code (`benchmarks/symmetry_2026-10-c8/stage6_a914db2/val2/validate_full.json`; it covered the
  3,511 C7(3) kernels and the 262 new L7 kernels), J-RUN1 570390 (`stage5_3cbe7a4/run1/archived_stream_replay.json`: 168,528
  rows, C7(3) rebuilt to 1.0e-15) and `docs/NUMERICS.md` "CPU dependence (measured)" (symmetry job 566410; its raw rows are
  not shipped). `make -f public.mk test-native` and `test-replay` rerun the first two on a cluster node.
- **Section 32.4 per-graph statements** (χ²/graph 0.994 and 1.010; the ten largest carry +0.19 and −0.07): read from
  `prod1/ab_split/report.txt`; step H reruns `ab_split.py` on the hosted `graph_replicates.csv` and requires identical text.
- **Section 32.4 costs** (lanes 14,970, merges 106, total 15,102; 8 at a time, 10 nodes, 9–12 October): recomputed from
  `prod1/jobs_sacct.psv` (ElapsedRaw × AllocCPUS) and `prod1/c8d3_prod1_budget.txt` (the production line, which adds the plan
  job and the rate probes). The pilot's 422 core-hours: the pilot line of the same budget file.
- **Section 32.5 tail statistics:** the tail monitor (10,034 listed, largest share 1.65%, none flagged; 62% and 99.5% are campaign
  a's shares, campaign b 63.1% and 99.4%) from `C8_result.json`; the N-trend numbers from `prod1/tail_ntrend/ntrend.json`, which
  step T regenerates exactly from `pilot/evidence/pilot_report.json`, `prod1/tail_ntrend/prod_tails.csv` and the result.
  `prod_tails.csv` was computed from the L8 `graph_tails.csv` (2.1 GB, optional hosted tier); step T checks it against the
  result's tail monitor (10,034 rows to 2.2e-16). "About N^-0.23" is campaign a's median (b: −0.258); the replay accepts a
  value inside the two campaigns' range.
- **Section 32.5 rate probes** (48 graphs, 5 apparent deficits, crossovers t^1.5 → t^1.0, asymptotic exponent 1.0):
  `production/margin_probe1/`, `margin_probe2/` (reports) and `margin_ladder/` (31 deficit levels).
- **ERRATUM rows:** Section 32.4 error table, power-free L = 4 (printed 0.011, record 0.0105) and Section 32.5 "0.82 to 0.88"
  (record maximum 0.875). Corrections in `section32_replacements.md`; the corrected values are checked strictly (rows with *).
- **KNOWN row:** `tools/verify_result.py` stops, off the production CPU class, at the rounding-level affinity-gate diagnostic
  (stored 3.0e-14, here 1.4e-13; threshold 1e-10). The note's "linear to 3e-13" is the production value; step A checks that
  stored and recomputed diagnostics lie below the gate thresholds and compares every other field.

### `LRI_C8_D3_OPT`

Folder: `code/LRI_C8_D3_OPT/`.

#### Results map: independent check of C8(3) (C8_3_check, 2026-10-13)

Every number the condensed note (`GFF/LRI_condensed_note/long_range_ising_condensed.tex` at fa71533) quotes for this
check (the final paper, f496d39a, prints none of them: its macro `\CeightThreeIndepPull` = 0.40 in `paper/numbers.tex`
is defined but not used), with its record, the replay row that recomputes it, the tolerance and
why. Command for all rows: `make -f public.mk replay` in `GFF/code/LRI_C8_D3_OPT` (rows R7 need `fetch-data` and
`make -f public.mk replay-full`). Record paths are relative to `GFF/`. All values were recomputed locally on
2026-10-13 (`replay_local_run.txt`) and agree with the note.

| where quoted | number | record (field) | replay row | tolerance | why |
|---|---|---|---|---|---|
| Sec 1 (l.163), Sec 32.1 (l.12037), Sec 32.7 (eq., l.12233) | C8(3) = 1600.98 +- 3.97 (sampling SE) | `results/C8_3_check/runs/prod1/C8_result_54838171.json` (`C8_estimate` 1600.9770046710833, `sampling_standard_error` 3.967937252893955) | R1 (recomputed from `means`, `input_covariances` with `rg.coefficients`, `rg.jacobians` and the propagation of `assemble.calculate()`), R2 (`assemble.calculate()` on moment-matched replicates), R3 (rounding) | R1 rel 1e-12 / 1e-10; R2 rel 1e-11 / 1e-8; R3 2 decimals | same float64 code on the stored inputs, only BLAS order differs (observed 3e-16, 0); R2 rebuilds covariances by eigen-decomposition (observed 3e-15, 4e-10) |
| Sec 1 (l.164), Sec 32.1 (l.12039), Sec 32.7 (l.12235); paper macro `\CeightThreeIndepPull` = 0.40 (not printed at f496d39a) | -0.40 combined standard errors from the estimator | this record and the main record `results/C8_3/C8_result.json` (`C8_full` 1602.6052229663408, `sampling_standard_error` 0.9516489064069612; sha256 `b0776258...`) | R5: (C8 - main)/hypot(SE, SE_main) = -0.3990 | 2 decimals | the main record is checked by hash and against the note's Sec 32.1 values; without it the replay uses those values and marks the record row SKIP |
| Sec 32.7 (l.12235-12236) | campaigns 1603.53 +- 4.91 and 1598.42 +- 6.24 | `individual_campaigns.a/b` | R4: values recomputed to first order from `runs/prod1/graph_statistics_54838171.json` (per-graph projected means), compared with the stored ones; SEs read from the record | values abs 1e-4 (observed 1.4e-6); 2 decimals | the campaign SEs need the per-replicate matrices (native outputs, not archived) |
| Sec 32.7 (l.12236) | differ by 0.64 combined standard errors | `campaign_difference_pull` 0.6441848 | R4 (assemble.py formula on the stored campaign values) | abs 1e-12; 2 decimals | arithmetic |
| Sec 32.7 (l.12237-12238) | lower-order coefficients within 1.73 standard errors | `lower_order_checks` (C3 -1.405, C4 -1.546, C5 -0.102, C6 +1.728, C7 -0.207; references `tools/assemble.py REFERENCES`) | R1 (each pull, abs 1e-9), R3 (max |pull| = 1.73) | 2 decimals | the C6, C7 references are the main package's C6(3), C7(3) productions (33.57542664 +- 1.19e-4, -220.35448 +- 0.0318) |
| Sec 32.7 (l.12238-12239) | sixth- and seventh-order by-products 33.599 +- 0.014 and -220.40 +- 0.19 | `coefficients[6,7]`, `standard_errors[6,7]` | R1, R3 | 3 and 2 decimals | |
| Sec 32.7 (l.12219-12220) | integrates the same 24,173 kernels | `manifest.json` groups (18,997 power-free + 5,176 power-containing per campaign) = `GFF/code/LRI_C8_D3_OPT/inputs/inventory.json` | R6 | exact | also: manifest graph hashes = inventory hashes |
| Sec 32.7 (l.12222) | rates multiplied by 0.8 and 0.7 | manifest groups `rate` (a 0.8, 52 bits; b 0.7, 60 bits) | R6 | exact | |
| Sec 32.7 (l.12227) | a fresh base seed | manifest `base_seed` 1546835505427890396 vs the delivered pilot's 7736323638330945148 (`inputs/pilot_design.json`) and the README example | R6 (+ the 48 group seeds = `campaign.derive_seed`) | exact | |
| Sec 32.7 (l.12227-12228) | an allocation of about 2,000 core-hours of its development host | `results/C8_3_check/allocations/prod1_2000.json` (sha256 `fccf8969...`, bound by the manifest) | R7: `tools/allocate.py` on the pilot's `graph_statistics.json` (hosted) with 2,000 core-hours and 16 replicates reproduces the file byte for byte; estimate 1999.99 core-hours | exact | needs the pilot bundle; SKIP in `replay`, required in `replay-full` |
| Sec 32.7 (l.12228-12229) | 16 replicates per campaign, at least 4,096 points per graph | manifest `replicates`, groups' `points` (= allocation) | R6 | exact | |
| Sec 32.7 (l.12230) | 1,994 jobs | manifest `jobs`; result `streaming_assembly.jobs` | R6 (recounted from the allocation by the planner's rule: blocks of 32 graphs, 262,144-point chunks) | exact | |
| Sec 32.7 (l.12230) | 3.7 x 10^10 evaluations | manifest and result `evaluations` 37,121,687,552 | R6 (= 2 x 16 x sum of points; = sum of per-graph points in the graph statistics) | exact | |
| Sec 32.7 (l.12229-12231) | ran on 10 and 11 October 2026 on six whole AMD EPYC 7742 nodes, about 9,800 service units | `results/C8_3_check/README.md` (Slurm accounting: lanes 6 x 45,814 s, tail 0.19 node-h, shared jobs about 0.11 node-h); manifest `created_utc` 2026-10-10T21:00:28Z | D: 76.66 node-h x 128 SU = 9,812 SU (arithmetic); dates and nodes documented | rounds to 9,800 | accounting is not recomputable from the science records; the logs and sacct output are not shipped |
| Sec 33 row (Independent check of C8(3)) | paths | see `section33_row.tex` | | | |

Further numbers in the production README (not in the note), also replayed: power-free 1602.61 +- 2.96 and correction
-1.63 +- 2.64 (R1, R3); half streams 1599.79 and 1602.17 (record lookup, R4). Not replayed: the bootstrap SE 3.78
(needs the replicate matrices); the README's comparison with the main package's pilot (1619 +- 16, -1.09) belongs to
the main package.

Related statements in Sec 1 (l.160-162) and Sec 32.7 (l.12214-12227): "shares the method and the seventh-order
integrator", "regenerates the graph inputs at every loop ... derives its own low-loop inputs": descriptive; backed by
the package (`docs/GRAPH_GENERATION.md`, `tools/generate_graphs.py`, `tools/prepare_low.py`, `verification/`) and by
`inputs/two_loop.json` (sha256 `2abf1322...`), a different file from the main package's (`6c31bf7f...`).
