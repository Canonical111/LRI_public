# Results map: integ_d1

Every number the package publishes, where it lives, and how `make -f public.mk replay` (run from `SRI/code/integ_d1`)
checks it. Paths are relative to `SRI/code/integ_d1/`; JSON pointers follow RFC 6901.

Rules: **byte** = the record rebuilt by the verbatim tool has the frozen sha256; **round** = the recomputed value,
rounded half-up to the printed precision, equals the printed text; **exact** = the printed decimal equals the record's
string; **order** = "to 10^-n" holds if the value lies in [10^(-n-1/2), 10^(-n+1)); **trunc** = the record begins with
the printed digits; **int** = count equals. Superseded records are marked "superseded, cited by App. I.7".

## Paper

| number | printed | record, pointer | check | rule |
|---|---|---|---|---|
| \SRCeightMag (Sec. 3.2 "Checks") | 247.38\pm0.13 | `results/C8_record_v2.json` `/C8` = 247.3811797457894848, `/C8_error` = 0.131 | `c8_assemble.py --verify` (byte) then sri_lib `T.quoted` against `../../results/quoted_numbers.json` | round (half-up to 2 decimals) |
| \SRintegClosedDev (Sec. 3.2 "Checks") | 7\times10^{-26} | max over n = 3..7 of the relative difference between the scheme's C_n and the closed form, printed by `c8_assemble.py --verify` from the unrounded 40-digit assembly (6.65e-26, n = 6); not from the 25-digit strings of `/C3_C7` | the same run, then `T.quoted` | round (half-up to 1 digit) |
| \SRCeightMagDiff (Sec. 3.2 "Checks") | 2.5\times10^{-5} | abs(`/C8` - 247.3812048049935), the record value of eq:C8num (2.506e-5) | `c8_assemble.py --verify`, then `T.quoted` (absolute) | round (half-up to 2 digits) |

## Records (App. I.8)

| record | sha256 | check | rule |
|---|---|---|---|
| `results/C8_record_v2.json` | 0d463b29...ec0c | `c8_assemble.py --verify` | byte |
| `results/M2_flow_coefficients.json` | 33cc2e1e...e833 | `m2_gate.py <source> --stage2 --expect-sha` | byte (+ sidecar) |
| `results/M3_flow_coefficients.json` | 4328cab9...1bce | `m3_gate.py results/m3_runs/s3 --stage2 --expect-sha` | byte (+ sidecar) |
| `results/M4A_flow_coefficients.json` | 584562ca...1048 | `m4a_gate.py n3d2_B n3d2_A --dry` (would-be sha256) | byte |
| `results/M4B_flow_coefficients_v2.json` | 90542a62...9899 | `m4b_gate.py F C --fine-dd Fdd --coarse-dd Cdd --radius R --radius-dd Rdd --dd-sample Vdd --dd-sample2 Vdd2 --verify` | byte (+ sidecar) |
| `results/M4B_cx_check_v2.json` | 66287b2a...f1fb | `m4b_cx_check.py cxA cxB --amended --verify` | byte |
| `results/M3_sector_check_*.json` (3) | 8097a48a..., df1a3528..., 80b18816... | `m3_sector_check.py ... --verify-record` | byte |
| `results/M4B_cx_check.json` (superseded, cited by App. I.7) | ca86bbc1...0666 | registry sha256; `m4b_cx_check.py cxA cxB --dry` fails on K_B as recorded | sha256; values equal |
| `results/C8_record.json`, `M4B_flow_coefficients.json` (superseded, cited by App. I.7) | d9b3be4e..., 9a16f1a9... | registry sha256 | sha256 |

## App. I.7: gates and results

| number | printed | source | rule |
|---|---|---|---|
| C3 (M1, absolute) | 2e-38 | `m1_gate.py` output `difference` | round |
| two bubbles, delta^0 vs Bethe ansatz | 4e-32 | `results/M2_flow_coefficients.json` `/delta0_vs_BA_max_rel` | round |
| two bubbles, number of relations | 36 | relation checks printed by `m2_gate.py` | int |
| two bubbles, relations | 10^-28 | `/relations_max_rel` (M2) | order |
| f_101 | -36.49853744243762... | `/flow_coefficients/f_1_0_1` (M2) | trunc |
| C4, C5 (M2, absolute) | 3e-28, 10^-26 | `m2_gate.py` output `diff` | round, order |
| three bubbles vs exact cluster, real / complex v | 10^-23, 10^-28 | `cluster_check.py 3` on `results/m3_runs/g2g3/*_L2.out` | order |
| three bubbles, relations | 10^-27 | `results/M3_flow_coefficients.json` `/relations_max_rel` | order |
| C6, C7 (M3, absolute) | 4e-24, 2e-24 | `m3_gate.py` relative difference x |C_n| | round |
| f_202: delta^0 vs BA; delta^1 vs M3; delta^2 relations (count, max) | 4e-23; 9e-24; 12, 4e-24 | `results/M4A_flow_coefficients.json` `/checks/delta0_vs_BA_max_rel`, `/checks/delta1_vs_M3_max_rel`, `/checks/delta2_relations_max_rel_fine`; count from `m4a_gate.py` | round, int |
| f_202 and its error | 172415.83018563 +- 1.7e-7 | `/flow_coefficients/f_2_0_2`, `/errors/f_2_0_2_two_grid` (M4A) | round |
| f_301 double-double overrides | 8 at 0.2, 14 at 0.3 | `results/M4B_flow_coefficients_v2.json` `/dd_sectors` | int |
| f_301: delta^0 vs exact cluster; delta^1 relations (count, max) | 4e-11; 12, 7e-12 | `/checks/delta0_vs_BA_max_rel/fine`, `/checks/delta1_relations_max_rel/fine` (M4B v2); count from the gate report | round, int |
| confirmatory check K_A, K_B | 1.7e-14, 1.6e-12 | `results/M4B_cx_check_v2.json` `/results/0/rel_diff`, `/results/1/rel_diff` | round |
| roundoff sample sizes | 56 = 16 + 24 + 16 | `/dd_validation_sample/rows` (M4B v2; stratum, old/new) | int |
| roundoff ratios: top 16 + top decile; decile 9; any sector | 2.5e-3; 1.3e-2; 0.41 | `/dd_validation_sample/strata/*/ratio_max` | round |
| bound share of top 16 + top decile | about 98% | `results/m4_inputs/fix3b_design.json` `/stratum_bound` (98.44%) | round |
| f_301 | -514275.75 +- 0.17 | `/flow_coefficients/f_3_0_1`, `/errors/f_3_0_1_total` | round |
| f_301 error budget | 0.174 = 0.016 + 0.022 + 0.137 | `/errors/f_3_0_1_two_grid`, `/errors/f_3_0_1_radius_diff`, `/errors/roundoff_estimate_fine` | round |
| C3..C7 (assembly; table) | 25 digits each | `results/C8_record_v2.json` `/C3_C7/C3` ... `/C3_C7/C7` | exact |
| C3..C7 closed forms (table) | 25 digits each | the note's Eq. (closed), mpmath at 40 digits | round |
| C3..C7 relative differences (table) | 3e-39, 2e-29, 3e-28, 7e-26, 4e-26 | `c8_assemble.py --verify` output `rel` | round |
| C8 | 247.381179745789 +- 0.131 | `/C8`, `/C8_error` (C8 v2) | round |
| C8, quoted | 247.38118 | `/C8` | round |
| uncertainty components | 0.13, 3.3e-7, 3.6e-15 | `/components/0.75*sigma_f_3_0_1`, `/components/2*sigma_f_2_0_2`, `/components/other_inputs` | round |
| inputs (Table tab:integ:inputs) | 29 values, 25 digits | `/inputs/f_i_j_k` (C8 v2) | exact; count int |
| C8 and C3..C7 reassembled from the printed inputs | 247.381179745789; 10^-25 to 2e-22 | `mscheme_numeric.C_numeric` on the printed table, mpmath 40 digits | round, order |
| compute | about 2.7e4 core-hours | cluster accounting (not in the records) | INFO |

## App. I.7: comparison and disclosures

| number | printed | source | rule |
|---|---|---|---|
| Delta vs the record; Delta / 0.131 | -2.506e-5; -0.0002 | `/C8` (C8 v2) - 247.3812048049935 | round |
| independent value | 242.825 +- 2.371 | `../indep_d1/RESULTS_C8_independent.json` `/step1/outputs/C8/value`, `/sigma` (SKIP if indep_d1 is absent) | round |
| Delta vs independent; / 0.131; / 2.371 | +4.556; +34.8; +1.92 | `/C8` and the independent value | round |
| Delta vs 242.83 (comparison stage) | +4.551 | `c8_assemble.py --compare --expect-sha 0d463b29...` output; same text as `results/C8_comparison.txt` | round; text equal |
| first version (superseded, cited by App. I.7) | 247.38118 +- 0.077 | `results/C8_record.json` `/C8`, `/C8_error` | round |
| A: K_B difference, criterion, own bound, rerun cost, amended criterion | 1.6e-12, 10^-12, 1.7e-9, 1.7e4, 10^-11 | `results/M4B_cx_check.json` `/results/1/rel_diff`, `/threshold`; `M4B_cx_check_v2.json` `/results/1/roundoff_bound_rel`, `/threshold`; `results/m4_inputs/cx_v2_design.json` `/dd_rerun_core_h_model` | round |
| B: roundoff and uncertainty under the original rule | 21.3; about 16 | `results/M4B_gate_v2_dry.txt` (superseded, cited by App. I.7): 4.11 x 5.184, total 21.3; 0.75 x 21.3 | round |
| B: non-sampled bound before the held-out sample | 5.184 | `fix3b_design.json` `/stratum_bound` total minus `fix3_design.json` `/fine_bound_eps_B` of the 40 first samples (equals the dry run's) | round |
| B: held-out sample within the margin | - | new max ratio <= 10 x old max in deciles 9, 10; stop strata <= 0.1 | PASS/FAIL |

With the note present (`../../note/sri_short_range.tex`), `replay` also requires each printed TeX string of these rows
to occur in its Appendix I.
