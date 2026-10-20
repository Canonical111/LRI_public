# dual_d1: the d = 1 dual series C^SR_1..C^SR_8 at the short-range end

Near the short-range end of the long-range Ising chain (s -> 1, d = 1) the weakly coupled dual of Benedetti, Lauria,
Mazac and van Vliet gives

    Delta_eps = 1 + sum_n C^SR_n Delta_sigma^(n/2),        Delta_sigma = (1 - s)/2.

C^SR_1 = -2 and C^SR_2 = 1/2 are published (Benedetti:2024wgx, Benedetti:2025nzp); this package cites them and does not
recompute them. C^SR_3 to C^SR_8 were computed by another AI system, OpenAI GPT-6 astra (via ChatGPT), whose
computational compendium was supplied by the author; we reviewed the calculation (REVIEWS.md). This package ships that
compendium as a pruned dated snapshot (archive of 2026-10-02) and replays every number the paper quotes from it. The
raw regeneration of the integrals is broken (21 stage programs are missing from the archive); what the package offers
is the replay, the exact certificate checks and, in package `indep_d1`, the independent re-derivation. Paper: Sec. 3.2 "Near the short-range end" (Eqs. eq:sr-closed,
eq:sr-C8, Table tab:sr, d = 1 row). Derivations: the SRI note, Appendices A to C (the model, regulator and
finite-response renormalization; the third to sixth orders; the certificates and the seventh and eighth orders).
The compendium's own note (`note/LRI_perturbation_compendium.tex` and PDF) is not shipped since 16/17 October 2026 (author: one TeX note per direction and nothing else); its derivations are in the SRI note, Appendices A to C. The four TeX blocks that the checks parse (its closed forms eq:thermal-main and eq:C8-candidate-main for the replay; eq:C8assembly and the old-input polynomial for `indep_d1`'s self-test) are kept verbatim, at their original line numbers, in `public/compendium_extract.json`; `public/NOT_SHIPPED.txt` records the original's sha256 and a map from its labels and sections to the SRI note. The scripts that only build notes are not shipped either, and three verbatim files whose text pointed to the note (README.md, Makefile, documentation/SCRIPT_OUTPUT_MAP.md) are edited and re-pinned (`public/RE-PINNED.json`).

| Result | Value | Status |
|---|---|---|
| C^SR_1, C^SR_2 | -2, 1/2 | PUBLISHED (cited) |
| C^SR_3 .. C^SR_7 | rational combinations of zeta values, eq:sr-closed: 5.72737, -12.1962, 29.2378, -58.6657, 51.0690 | PROVED within the archived matched two-coupling prescription (exact period certificates for C5, C6, C7; C3, C4 by analytic low-order evaluation) |
| C^SR_8 | 247.381204804993548407355074766099998652... (record; about 85 digits) | NUMERICAL (no interval bound) |
| pi_0 C^SR_8 (rational part) | 88 | EXACT (completed rational integration and independent trace assembly) |
| eq:sr-C8 (weight-7 zeta expression for C^SR_8) | matches the record to 3.1e-86, below the record's printing floor (about 2e-85) | CONJECTURED, not proved (no C8 certificate exists) |

Every coefficient above C^SR_2 assumes that the two couplings of the dual close under renormalization (the archived
"matched hard-core two-coupling" prescription); two formal arguments (SRI note, Appendix D; checks in package `closure_d1`) support it. No calculation in
this package tests that assumption; the comparison with the nonperturbative descriptions in the paper does. An
independent re-derivation (package `indep_d1`) confirms every input of C^SR_5..C^SR_7 within 0.92 standard errors (the
coefficients within 0.78) and gives C^SR_8 = 242.8 +- 2.4, 1.9 to 4.0 standard errors below the record depending on the
error estimator; that tension traces to a single input integral, A9[eps^0 l^1]. A third calculation, in a scheme
defined by the magnetization at the integrable point s = 1 (SRI note, Sec. 2.7 and Appendix I; package
integ_d1), shares no input with either, gives C^SR_8 = 247.38118 +- 0.13 (empirical numerical uncertainty, not a
standard deviation), 2.5e-5 from the record, which indicates that the low value of the re-derivation is the one in error.

## Layout (code/dual_d1/)

| Path | What |
|---|---|
| `README.md`, `run_checks.py`, `Makefile`, `requirements*.txt` | the compendium's own entry point, default check and targets (verbatim) |
| `code/` | all of its programs: `reproduce.py` (named tasks), `reproduce_summary.py` (coefficient registry and algebra), `prepare_workflows.py` (rebuilds the original layouts from `reproduction/layout.json`), and `code/archived/` (every surviving program of the calculation: kink integrators, period algebra, certificate verifiers, GMP period evaluator) |
| `data/coefficients.json`, `data/current_status.json` | the registry: C1..C8 expressions, 70-digit decimals, rational parts, status words |
| `data/archived/` | the stored inputs the replayed checks read (pruned; see DATA_dual_d1.md): the C8 records, P6 exact expression and its 64 terminal outputs, the full-C8 exact expressions (P8, Kv, J9, ...), the 25 C7 beta inputs and the C7 proof target and certificates of weights 2..5, the C6 inputs, target and certificate rows |
| `outputs/` | the regenerated tables, the consolidation's verification records, and the C8 candidate records |
| `public/compendium_extract.json` | the four TeX blocks of the compendium's (unshipped) note that the replay and `indep_d1`'s self-test parse, verbatim at their original lines, with the original's sha256 |
| `reproduction/` | `layout.json` (virtual original paths -> stored copy), `MANIFEST.json` (sha256 of all 8,560 distributed files), `omitted_files.json`, `source_archives.json`, `environment.json` |
| `public.mk`, `public/` | new: replay and fetch tools, the snapshot list, the hosted-file list, the restored lost file |

## Targets (from code/dual_d1/)

`make -f public.mk test` (about 25 s), `replay` (about 1 min), `fetch-data` (the hosted 57 MB C7
certificate), `replay-full` (about 9 min). See REPRODUCE_dual_d1.md; every quoted number and its rule is in
results_map.md.
