# results_map: dual_d1

Every quoted number and displayed result of the paper that this package reproduces: the macro of the paper's
numbers.tex (or the equation or table cell), its text as printed, the record it is recomputed from, the rule, the
command (from SRI/) and the tolerance. Tolerance of every macro row: the recomputed value, rounded half-up to the digits
the macro prints, equals the printed value (verify/sri_lib.py); "note only" = defined in numbers.tex but not printed
(INFO row); "literature" = a published value, cited, not recomputed (INFO row). Paths below are in `code/dual_d1/`.
All rows are produced by `make -C code/dual_d1 -f public.mk replay` (the rows marked T also by `test`).

| Macro / item | Printed | Status | Record | Rule | Tolerance |
|---|---|---|---|---|---|
| `\SRCthree` (T) | `5.72737` | printed | eq:sr-closed = `data/coefficients.json` n = 3 | 39/16 + 2 zeta(2) with mpmath at 50 digits | rounding |
| `\SRCfour` (T) | `-12.1962` | printed | n = 4 | 4 - 4 zeta(2) - 8 zeta(3) | rounding |
| `\SRCfive` (T) | `29.2378` | printed | n = 5 | eq:sr-closed | rounding |
| `\SRCsix` (T) | `-58.6657` | printed | n = 6 | eq:sr-closed | rounding |
| `\SRCseven` (T) | `51.0690` | printed | n = 7 | eq:sr-closed | rounding |
| `\SRCeight` (T) | `247.381` | printed (tab:sr cell `\ptConj`: conjectured closed form eq:sr-C8) | `data/archived/C8_zeta_candidate/result.json` `C8_assembled_without_candidate` (the numerical record, = Cfixed - P6/2) | the record; also recomputed from its 36 inputs with the verbatim `full_jacobian.py` | rounding; recomputation within 1e-95 |
| `\SRorderword` (T) | `eight` | printed | `data/coefficients.json` | number word of the highest order with a value | equal |
| `\SRorder` (T) | `8` | note only | same | highest order | INFO |
| `\SRclosed` (T) | `7` | note only | same | highest order whose status is not "numerically supported candidate" | INFO |
| `\SRorderLitword` (T) | `two` | printed, literature | Benedetti:2024wgx, Benedetti:2025nzp | cited; the registry marks n = 1, 2 "published baseline" | INFO |
| `\SRorderLit` (T) | `2` | note only, literature | same | same | INFO |
| C^SR_1 = -2, C^SR_2 = 1/2 (text; tab:sr `\ptPub` cells) (T) | `-2`, `1/2` | literature | same | cited; registry values -2, 1/2 | INFO |
| eq:sr-closed (T) | TeX in `results/quoted_numbers.json` | printed | `data/coefficients.json` (expressions in pi and odd zetas), the compendium's eq:thermal-main (`public/compendium_extract.json`, verbatim block of its TeX source, which is not shipped), `data/archived/C6_closed_form/input_expressions/C6_candidate.expr`, the candidate string of `code/archived/C7_closed_form_proof/code/verify_input_map.py` | the TeX parsed into exact rational coefficients of zeta products; zeta(2k) = r_k pi^(2k) | exact equality of every coefficient; rational parts equal the registry's |
| eq:sr-C8 (T) | TeX | printed | `data/coefficients.json` n = 8, the compendium's eq:C8-candidate-main (`public/compendium_extract.json`), `result.json` `candidate_coefficients` | as above | exact |
| "It is conjectured: it agrees with the numerical value of C^SR_8(1) to about 85 digits" (T) | text | printed | `result.json` and its inputs (`C8_zeta_candidate/inherited/*`, `P6_eval100.json`) | eq:sr-C8 at 120 digits minus the record = 3.085e-86; the record's printing floor: sum over the 35 decimal inputs of the exact change of C8 for half a unit in the last printed digit (`beta_c = -16.0` exact) | \|residual\| <= printing floor (about 2e-85, 87 significant digits; INFO row for the floor, which is not an interval bound) |
| "a second evaluation of one input cross-checks about 57 decimal places" (SRI note; the paper quoted it until 1ab2ea1c and no longer does) (T) | text | note only | `data/archived/C8_P6_exact_sources/P6_full/P6_eval70.json`, `P6_eval100.json` (the 100-digit value is `result.json` `P6_fresh`) | C8 = Cfixed - P6/2 from each evaluation; places = round(-log10 \|dC8\|) (\|dC8\| = 2.2e-57, the precision of the 70-digit run; only P6 is cross-checked) | equal (57) |
| "reproduces its rational term, 88, which is computed exactly" (T) | text | printed | `data/archived/C8_rational_completion/result.json`, `.../R8_work/prior_inputs/T4_rational_reduction.json` | rational part of eq:sr-C8; the record (C8 = 88, T4 = 11); the verbatim `full_jacobian.py` on the 35 rational beta inputs; the two independent rational sums of `run_checks.py` | exact |
| "Through C^SR_7 ... proved" | text | printed | the certificates | C5 (D3) and C6 certificates, C6 and C7 input maps, C7 certificate weights 2..5 (`replay`); complete `reproduce.py --task certificates` (`replay-full`, after `fetch-data`) | exit 0 = exact zero residual; input-map reports equal the consolidation's records |
| tab:sr, d = 1 row (T) | `\ptPub{-2} \ptPub{1/2} \ptClosed{\SRCthree}..\ptClosed{\SRCseven} \ptConj{\SRCeight}` | printed | `results/quoted_numbers.json` `tab_sr`, registry status | each cell holds the macro of its C_n and the marker of its status (published, analytic reduction, conjectured closed form = registry "numerically supported candidate"; \ptConj prints blue with a section sign) | equal |

Also checked (replay): the compendium's `run_checks.py`, `reproduce.py --task c8-saved` (the 64-bucket P6 sum, the
decimal Jacobian, the integer-relation recognition of eq:sr-C8 at 115 digits with its 1e-80 test) and `--task
c8-rational-algebra` (the regenerated registry, tables and `summary_algebra.json` equal the shipped ones) and
`--task low-integrals`; the regenerated `exact_P6_replay.json`, `new_full_Jacobian.json` and
`candidate_validation.json` equal the shipped records. replay-full adds `--task c8-positive-check` and `--task
c8-numerical` (fresh 70- and 100-digit evaluations of the P6 expression).

Values published for other folders: `maint/sr_values_dual_d1.json` (C^SR_1..C^SR_7 decimals and expressions in
`data/coefficients.json`, the C8 record in `result.json`, the 31-digit C8 string in `data/current_status.json`).
