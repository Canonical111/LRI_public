# results_map: indep_d1

Every quoted number this package reproduces: the macro of the paper's numbers.tex, its text as printed, the record it is
recomputed from, the rule, the command (from SRI/) and the tolerance. Tolerance of every macro row: the recomputed
value, rounded half-up to the digits the macro prints, equals the printed value (verify/sri_lib.py). The claims are
the paper's eq:sr-closed and eq:sr-C8 (results/quoted_numbers.json, "equations"), evaluated with mpmath at 50 digits.

| Macro | Printed | Status | Record | Rule | Command |
|---|---|---|---|---|---|
| `\SRCeightIndep` | `242.8\pm2.4` | note only (the paper quotes \SRCeightMag, package integ_d1, instead, since paper e89a94a0; INFO row) | `code/indep_d1/RESULTS_C8_independent.json` /step1/outputs/C8 {value, sigma}, recomputed by `assembly/run_assembly_C8.py` step1() from `engine/runs/prod_6digit/framework_input_final.json` + `engine/runs/c8tiersABC/framework_input_final.json` (201 raw scalars, R = 6) and `public/pooled_sector_record.json` | C8 = 8 T4 (strict, per replicate, 50 digits) +- the quoted error = max(sigma_cov, sigma_rep, sigma_pool) = sigma_pool | `make -C code/indep_d1 -f public.mk replay` |
| `\SRCeightPull` | `1.9` | note only (the paper's sentence was removed in c9adefbf; INFO row) | as above; claim eq:sr-C8 (= the archive record of `spec/comparison_C8/archive_C8_values.json` to < 1e-25) | |C8 - claim| / sigma = 1.92 (below the claim) | same |
| `\SRCeightPullMax` | `4.0` | note only (the paper's sentence "1.9 to 4.0 standard errors below the claimed value depending on the error estimator" was removed in c9adefbf; INFO row) | `code/indep_d1/RESULTS_C8_independent.json` /step1/outputs/C8 {value, sigma_cov, sigma_rep, sigma_pool} (recomputed by `assembly/run_assembly_C8.py` step 1) | largest \|C8 - eq:sr-C8\| / sigma over the three estimators: replicate spread (sigma 1.15) 3.98; linear propagation (1.37) 3.32; sector-pooled (2.37, the quoted one) 1.92 | `make -C code/indep_d1 -f public.mk replay` |
| `\SRindepPullMax` | `0.9` | note only (the paper does not print it; INFO row) | `code/indep_d1/RESULTS_independent.json` (recomputed by `assembly/run_assembly.py` main() from `engine/runs/prod_6digit/framework_input_final.json`) against the sealed 100-digit archive values `spec/comparison/archive_comparison.json` | max over the 25 inputs of C5..C7 of |value - archive| / sigma = 0.915 (Omega); the coefficients C5..C7 themselves reach 0.78 (C6, INFO row) | rounded half-up to one decimal |

Cited checks (PASS rows of the same replay; values as printed in RESULTS.md and RESULTS_C8.md):

| Check | Value | Record | Rule |
|---|---|---|---|
| C5, C6, C7 independent | 29.237811563 +- 1.35e-7 (pull -0.13); -58.66569861 +- 1.45e-6 (-0.78); 51.0689860 +- 3.14e-5 (-0.08) | RESULTS_independent.json /step1/outputs | recomputed value at the printed digits, sigma to 3 digits, pull to 2 decimals |
| D4 independent | -2.53463048 +- 7.85e-6 (pull -0.09) | same; claimed closed form from `framework/lri_framework.closed_forms` | same |
| eq:sr-closed = claims tested | C5, C6, C7 agree to < 1e-25 | RESULTS_archive_comparison.json /claims_vs_closed_forms | the paper's closed forms are the ones compare_archive.py tests |
| inputs of C5 to C7 (SRI note Sec. 2.6) | 25 inputs: rms pull 0.34, none above 1 (largest 0.915, Omega) | RESULTS_independent.json vs `spec/comparison/archive_comparison.json` (sealed 100-digit values) | rms rounds to 0.34 and max < 1; the max is \SRindepPullMax (0.9) |
| J9 | -291.9 +- 9.5 against -273.72, pull -1.92 | RESULTS_C8_independent.json /step1/outputs/J9; archive record | as printed |
| A9[eps^0 l^1] tension | ours - archive = -20.4 +- 9.3 (-2.19 sigma, 3.3e-5 relative) | /step1/sub_pieces/A9_1; archive record | as printed |
| "traces to a single input integral" | A9_1 -2.19; Z8_1 +0.14, (EA7)_0 +0.95, (EZ6)_0 -0.24, D9_lower -0.71; U +0.27, Kv -0.27; C8 - J9/4 -0.20 | sub_pieces, outputs, RESULTS_C8_archive_comparison.json | |pull(A9_1)| > 2 while every other piece of J9, U, Kv and C8 - J9/4 have |pull| < 1 |
| chunk-pooled C8 pull | -2.09 | RESULTS_C8.md (statistics verifier) | INFO, not recomputed |

Also checked by the replay: RESULTS.md and RESULTS_C8.md regenerate byte-identically (RESULTS_C8_tierA.md up to its
hand-added status note); RESULTS_independent.json (13,602 leaves), the C8 step-1 results and both comparison files
regenerate within the stated tolerances (values 1e-24, linear and replicate errors 1e-12, sector-pooled errors 1e-6 of
the quoted error, per-job diagnostics 1e-2 of it). The C8 records are published in their re-pinned form
(RE-PINNED.json: the personal desktop's name removed, no number changed); the JSON pointers are unchanged. `make test`: snapshot and recorded sha256 values, the framework tests, the engine rebuilt and four
production chunks rerun.
