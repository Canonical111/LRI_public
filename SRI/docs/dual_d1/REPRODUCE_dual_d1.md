# Reproduce dual_d1

Environment: Python >= 3.10 with mpmath (>= 1.3) and sympy (>= 1.12; the compendium used 1.14.0)
(`requirements_dual_d1.txt`); standard library otherwise. `replay-full` also needs a C++17 compiler with OpenMP and the
GMP/GMPXX development headers (`g++`, `gmp.h`, `gmpxx.h`), which the compendium's period evaluator compiles at run
time. All targets run from `SRI/code/dual_d1/` and write only into `$(WORK)` (default `.work/`).

**Use a case-sensitive work directory** (any Linux file system). The compendium has two input files whose names differ
only in case (`a_check_symbolic.expr`, `A_check_symbolic.expr`); the repository ships the lower-case one under another
name and the work copy restores it only where both can coexist. On a case-insensitive file system (macOS, Windows
defaults) the C6 and C7 input maps report SKIP and `replay-full` cannot run the complete certificate task; set
`WORK=<case-sensitive directory>`.

1. `make -f public.mk test` (about 25 s on one core): the snapshot sha256 list; every shipped file against the
   compendium's own `reproduction/MANIFEST.json`; the paper's Eqs. eq:sr-closed and eq:sr-C8 parsed into exact
   rational coefficients of zeta products and compared exactly with `data/coefficients.json`, the compendium's closed forms (`public/compendium_extract.json`), the
   C8 record and the candidates the C6/C7 input maps prove; C3..C8 at 50 digits against the quoted macros; the d = 1 row
   of Table tab:sr; the C8 record, its printing floor and the candidate residual; pi_0 C8 = 88 three ways; the
   compendium's `run_checks.py` (verbatim, on the work copy).
2. `make -f public.mk replay` (about 1 min on one core): `test` plus the compendium's tasks, verbatim on the
   work copy: `reproduce.py --task c8-saved` (all 64 P6 terminal outputs summed exactly; the decimal full-Jacobian
   assembly; the integer-relation recognition of the C8 candidate at 115 digits and its 1e-80 test), `--task
   c8-rational-algebra` (`reproduce_summary.py`; the regenerated registry, tables and `summary_algebra.json` must equal
   the shipped ones), the commands of `--task certificates` one by one (C5 = D3 certificate, C6 certificate, C7 input
   map), the C6 input map, the C7 certificate at weights 2 to 5, and `--task low-integrals`. Each regenerated report is
   compared with the shipped record.
3. `make -f public.mk fetch-data`: downloads the hosted weight-6 C7 certificate (`SRI__dual_d1__C7.w6.certificate.txt`
   in the project's Zenodo data record; 57,283,795 bytes, sha256 in `public/HOSTED.json`), checks it and places it in
   `$(WORK)/hosted/`. `URL_BASE=<url>` points it at a mirror; `ZIP=<LRI_1d_full_research_bundle.zip>` or
   `DIR=<unpacked archive>` takes it from the compendium's original archive instead.
4. `make -f public.mk replay-full` (about 9 min; 0.5 GB): `replay` with the complete `reproduce.py --task
   certificates` (588,878 certificate rows, exact zero residual at every weight; about 6 min on one core),
   `--task c8-positive-check` (a fresh 90-digit evaluation of the P8 positive-weight divergence difference) and
   `--task c8-numerical` (two fresh evaluations, at 70 and 100 digits, of the complete 66,404-term P6 expression;
   each must agree with the record to 10^-(digits-15)).

Measured on symmetry (TESTS_dual_d1.md): test 24 s, replay 63 s, replay-full 553 s on an Intel Xeon 6148 node; 26 s,
69 s and 558 s on an AMD EPYC 7532 node.

## What cannot be reproduced from this package (or from the original archive)

**Regeneration is broken.** The raw integrals behind C^SR_3..C^SR_8 cannot be recomputed from this package or from the
original archive: 21 stage programs are missing. What we offer instead is (i) the replay of every quoted number from
the shipped records, (ii) the exact certificate checks (C5, C6, C7; the C7 weight-6 part after `fetch-data`) and the
input maps that tie them to the archived beta inputs, and (iii) the independent re-derivation of the inputs of
C^SR_5..C^SR_8 with separately written code, in package `indep_d1`.

- **Details.** The archive omitted 21 ordered-integration "stage" programs
  (among them `run_mixed_stage2.py`, `chunked_stage4.py`, `run_B8_stage4.py`, `parallel_stage5.py`; listed in
  `reproduction/omitted_files.json` as "regenerable ordered-integration stage", although they are programs, not
  outputs), so the documented raw P6 and R8 regenerations stop at the first missing stage. The `p8-source` workflow of
  `prepare_workflows.py` does not recreate the `old_C7` and `rational_stages` paths that the P8 programs expect. The F2
  coverage metadata names 258 intermediate files that are not in the archive.
- **Six inputs of C^SR_8 are numerical records only.** W, S, L3, M21, M12 and N2 enter the C8 assembly as
  decimal values from one recorded 100-digit evaluation (`six_new_inputs.json`); the archive holds no exact expression
  and no second evaluation of them. The
  record's precision rests on them; no interval bound exists for any input.
- **No C8 certificate exists.** The C8 zeta expression is recognised numerically (integer relation at 115 digits,
  tested against a second evaluation); a proof would need all C8 inputs as exact expressions in one regularized-period
  convention and a complete weight-7 certificate.
- The dropped raw stages (about 1.9 GB) are in the original archive only; nothing in `test`, `replay` or `replay-full`
  needs them.

## Decisions you must not make

- The C8 expression is CONJECTURED. Do not relabel it proved because the residual is small; the replay tests the
  residual against the record's printing floor, not against a proof.
- The tolerances: exact equality of every rational coefficient; the candidate residual must not exceed the printing
  floor; the compendium's own thresholds (1e-80 for the candidate test, 10^-(digits-15) for fresh P6 evaluations,
  1e-65 for the P8 divergence difference) are part of its verifiers and are not to be loosened.
- The physical assumptions (hard-core regulator, matched finite-tail couplings, closure of the two couplings) are
  those of the archived prescription; the certificates prove period identities of that calculation, not the duality.
- Do not "repair" the archive's omissions by writing new stage programs and presenting the result as a replay.
