# Reproduce: SRI

Environment: Python >= 3.10 with numpy, scipy, mpmath, sympy, matplotlib and threadpoolctl (`requirements.txt`). Tested
with Python 3.12.9, numpy 2.3.5, scipy 1.17.1, mpmath 1.3.0, sympy 1.14.0, matplotlib 3.11.2, threadpoolctl 3.7.0 on
the symmetry cluster (Intel Xeon Gold 6148 and AMD EPYC 7532 nodes), unpacked in node-local storage. Also needed:
g++ with OpenMP (C++17, x86-64-v3) for the engine rows of `indep_d1` test (SKIP without it) and for `integ_d1` test
(its cluster engine and sector checker are built from source; bash too); a C++17 compiler with
OpenMP and the GMP/GMPXX headers for `dual_d1` replay-full; gcc with libquadmath for the Monte Carlo targets of
`c2_closed_d2`. Run `dual_d1` in a case-sensitive work directory (any Linux file system): the compendium has two
input files whose names differ only in case, and on macOS or Windows defaults its C6/C7 input maps report SKIP.
No cluster is needed except for production reruns.

| Step | Command (from SRI/) | Cost | What |
|---|---|---|---|
| 1 | `make test` | 12 min | every package's fast tests (below) |
| 2 | `make replay` | 17 min | every quoted number from the shipped records (PASS/FAIL table per package), then `make check-values` |
| 3 | `make fetch-data ZIP=<absolute path>` | seconds | the hosted inputs (below); without them `dual_d1` replay-full fails its certificate row |
| 4 | `make replay-full` | 35 min | the heavier reruns: `dual_d1` 9 min (after step 3), `c2_cylinder_d2` 10 s, `c1_d3` 25 min; `indep_d1` and `integ_d1` print their production reruns |
| - | `make note` | seconds | the note's check (PDF current, no private names); `make note-pdf` rebuilds the PDF in `.work/` |

`make <target> PKG="dual_d1 c1_d3"` runs a subset; `make -C code/<pkg> -f public.mk help` lists a package's own targets.
A failing package does not stop the others; the run exits non-zero if any failed. Measured times (seconds; Intel
Xeon Gold 6148 / AMD EPYC 7532; `docs/<pkg>/TESTS_<pkg>.md`):

| Package | test | replay | replay-full | also |
|---|---|---|---|---|
| `dual_d1` | 23 / 26 | 65 / 70 | 544 / 556 (0.5 GB work copy) | - |
| `indep_d1` | 258 / 308 (8 cores) | 229 / 264 | prints the production rerun | `replay-raw RAW=<dir>` 349 (raw outputs not yet hosted) |
| `integ_d1` | 249 / 249 (8 cores) | 78 / 85 | prints the production rerun | - |
| `c2_closed_d2` | 4 / 4 | 39 / 41 | - | `rerun-mc-smoke` 24, `mc-batch-check` 169 |
| `c2_cylinder_d2` | 170 / 152 | 3 / 3 | 10 / 9 | - |
| `c1_d3` | 16 / 14 | 469 / 484, plus 66 (Intel) for the two re-implementations | 1474 / 1486 | - |

What `replay` checks, per package:
- `dual_d1`: the paper's Eqs. eq:sr-closed and eq:sr-C8 parsed into exact rational coefficients of zeta products and
  compared exactly with the compendium's registry, its closed forms (TeX blocks in `public/compendium_extract.json`), C8 record and the closed forms its input maps prove; C^SR_3..8
  at 50 digits against the macros; the C8 record, its printing floor and the residual of eq:sr-C8; the rational part
  88 three ways; the compendium's own tasks verbatim on a work copy (the 64-bucket P6 sum, the C8 Jacobian assembly
  and integer-relation recognition, the regenerated registry, the C5 and C6 certificates, the C6 and C7 input maps, the
  C7 certificate at weights 2..5), each regenerated report against the shipped record.
- `indep_d1`: the verbatim assembly scripts on the 116 + 201 raw scalars (the raw per-sector outputs replaced by
  their exact sufficient statistics); RESULTS.md and RESULTS_C8.md regenerate byte for byte; the C5..C8 values, pulls,
  the 25-input rms pull and the A9 tension against the paper's equations.
- `integ_d1`: the verbatim gates rerun in a work copy (a git stand-in answers their git queries from the committed blob
  ids): every record from M2 to C^SR_8 rebuilt from the shipped engine outputs and compared byte for byte with the
  frozen one (the M4B gate, the confirmatory check under the original and the amended criterion, the sector checks,
  the C8 assembly), the comparison stage rerun, every number of the note's Appendix I (112 numbers and 114 printed
  strings), and \SRCeightMag (247.381179745789 +- 0.131 -> 247.38\pm0.13).
- `c2_closed_d2`: the study's eight-stage runner rerun and compared; every constant of the appendix cf:sec:cr2 at 50
  digits; the verbatim `summ.py` on the 142 Monte Carlo chunks against the production logs, and the recombination to
  -4.075 +- 0.019; the d = 2 row of tab:sr.
- `c2_cylinder_d2`: the 154 regulator fits, 84 joint variants, the outcome table, every error component and
  C2 +- dC2 from the shipped points, with the verbatim functions and with an independent implementation; the c_2 row
  of tab:htpert (the C^SR_2(2) row) and its caption.
- `c1_d3`: the package's 20-stage workflow rerun from scratch, its 23 regression checks, every output against the
  shipped full run, the regenerated summary tables, the d = 3 row of tab:sr, the inputs S, E_SR, and the note's "two
  independent implementations agree to 10^-12" (\SRthreeConeImplDev, note only; a bound): the review's two re-implementations (`review_indep/`, neither imports
  the package) rerun on the shipped spectrum, |delta c_1| <= 1e-12 against the package and between the two. The
  package's own two integrated forms are reported separately (INFO: a same-domain consistency check).
- `check-values`: every entry of `results/sr_values.json` resolved at its file and JSON pointer; the digits must be
  equal.

Tolerance of every quoted-number row: the recomputed value, rounded half-up to the digits the paper prints, equals the
printed text (`verify/sri_lib.py`; "note only" and literature macros give INFO rows). The tolerances of the regenerated
records are in each package's `docs/<pkg>/results_map.md`.

## Hosted data

Two inputs exceed what the repository ships; they are in the project's Zenodo data record,
https://doi.org/10.5281/zenodo.23466766 (`DATA.md`). `make fetch-data` downloads and checks both (`URL_BASE=<url>` for a
mirror).
- `dual_d1`: the weight-6 C7 certificate (`SRI__dual_d1__C7.w6.certificate.txt`, 57,283,795 bytes, sha256 in
  `code/dual_d1/public/HOSTED.json`), placed in `code/dual_d1/.work/hosted/`; needed only by `replay-full`. It can also be
  taken from the compendium's original archive: `make -C code/dual_d1 -f public.mk fetch-data ZIP=<absolute path>` (or
  `DIR=<unpacked copy>`).
- `indep_d1`: the raw per-sector engine outputs (`SRI__indep_d1__raw_engine_outputs.tar.gz`, 30,749,940 bytes; 293 files,
  131 MB), unpacked into `code/indep_d1/.work/raw` and checked file by file against `public/RAW_SHA256SUMS.txt`; then
  `make -C code/indep_d1 -f public.mk replay-raw RAW=.work/raw`. `replay` does not need them.

## What cannot be reproduced

The raw integrals of C^SR_3..C^SR_8 cannot be regenerated, from this folder or from the compendium's original archive:
21 ordered-integration stage programs are missing from the archive, so the documented raw regenerations stop at the
first missing stage. What is offered instead: the replay of every quoted number from the shipped records, the exact
certificate checks of C^SR_5..C^SR_7 (the weight-6 part of C7 after `fetch-data`), and the independent re-derivation
of every input of C^SR_5..C^SR_8 (`indep_d1`). Do not write new stage programs and present the result as a replay.

## Production reruns (cluster; not needed for any replay)

| Package | Rerun | Cost |
|---|---|---|
| `dual_d1` | not possible (above) | - |
| `indep_d1` | the shipped `.cfg` chunks of the eleven production runs, then `replay-raw` on the new outputs | about 22k core-hours (symmetry `amdq`) |
| `integ_d1` | the engine runs of M2 to M4B from the shipped inputs and designs with the shipped templates (`public/REPLAY_FULL.md`), then `replay` on the new outputs | about 1.6e4 core-hours of engine time (2.7e4 allocated; symmetry) |
| `c2_closed_d2` | the Monte Carlo (`mc/prod.sbatch`, `mc/prodC.sbatch`; three configurations) | about 135 core-hours |
| `c2_cylinder_d2` | the N = 768 and 1024 records, extraction checks and auxiliary inputs with the shipped launch layer | about 1.5 node-hours on symmetry, 470 SU on SDSC Expanse, and the D1 completion rows on symmetry |
| `c1_d3` | none beyond `replay`, which reruns the whole workflow from scratch | 9 min |

Each package's `docs/<pkg>/REPRODUCE_<pkg>.md` gives the commands.

## Other folders

`Resummation/` imposes the short-range data at the far end of its windows and reads them from
`results/sr_values.json` at stable pointers: `/d1/C/1` .. `/d1/C/8` (C^SR_n), `/d2/c2/closed` (c_2), `/d3/c1/value` and
`/d3/c1/range` (c_1 and its estimated range), `/d3/S` and `/d3/E_SR` (the d = 3 inputs). Its input check compares its
frozen copies with these values; `code/c2_closed_d2/outputs/summary.json` is byte-identical to its frozen copy. Do not
move or rename these pointers. Within this folder, two framework tests of `indep_d1` read files of `code/dual_d1/`
(SKIP when it is absent).

## Decisions you must not make

- The prescription of the dual (hard-core regulator, matched couplings, closure of the two couplings) and the status
  words: "proved" never extends beyond the prescription; eq:sr-C8 is conjectured, however small its residual.
- `indep_d1`: the quoted error is the largest of three estimators, fixed before the comparison (for C^SR_8 the
  sector-pooled one). The magnetization-scheme value (`integ_d1`; SRI note, Sec. 2.7) agrees with the record,
  which indicates that the low C^SR_8 of indep_d1 is the one in error (its own input comparison locates the
  difference in A9); whether it is a fluctuation or a systematic error needs an
  independent run of A9.
- `integ_d1`: the uncertainty 0.131 is the linear sum fixed in the plan (3/4 x sigma(f_301) + 2 x sigma(f_202) + the
  rest), an empirical numerical uncertainty: do not combine it in quadrature or call it a standard deviation. The two
  check criteria amended after their data were seen (A and B) are disclosed; the first records ship frozen and must
  not be presented as passing. `docs/integ_d1/REPRODUCE_integ_d1.md`.
- `c2_closed_d2`: the Monte Carlo cut Lambda > -15, the inverse-variance combination of the three configurations and
  the map from the integral to c_2.
- `c2_cylinder_d2`: the analysis rules (`meta.rules` of every output), the pre-declared outcome table and the linear
  sum E. Do not quote another branch or a per-order value, and keep "not a standard deviation".
- `c1_d3`: the gap hypotheses, the box of twice the quoted input errors, the chosen allowances and the outward
  rounding of the estimated range; do not present the range as a confidence interval.
- The rounding rule of the quoted numbers and the tolerances of every replay. If a comparison fails, report the numbers.
