# spec: what must be computed for an independent C6/C7 (and C8) re-derivation

This directory holds the specification for an independent re-derivation of the C6/C7
beta-function inputs in the compendium
`<PROJECT>/LRI_SRI_research_compendium`, extended on 2026-10-03 to the ten
new inputs of C8. The compendium was only read; nothing was written there.

## C8 extension (version 3, 2026-10-03)

C8 = 8 T4 (note Secs. 14-18, l.1100-1460). The ten new inputs are W = b3_ddd/6, S = b5_dd/2, U = b7_d,
J9 = b9, L3 = -2/3 h4_vvv, M21 = -2 h4_vvd, M12 = -2 h4_vdd, N2 = -2 h6_vv, Ndelta = -4 h6_vd and
Kv = -4 h8_v, all at (v, delta) = (1, 0).

**Where it is.** `spec_definitions.json -> C8_EXTENSION` (new block; every C6/C7 block, `spec.json` and every
`out/*.json` are byte-identical to version 2), the archive-free files in `out/C8/`, section 10 of `spec.md`, and the
sealed archive side in `comparison_C8/`. `spec_definitions.json` (version 3) has SHA-256 `26cad552...4afa`
(`SHA256SUMS`, which now also lists `out/C8/*.json`).

**Open items (C8).** (1) lambda6 is still an extrapolation of the note (now in K, Kv and J9), supported by the CS
derivation and the note's F3 split. (2) Of the six inherited inputs only W is confirmed independently; S, L3, M21, M12,
N2 and the packages U, J9, Kv, Ndelta need engine data (targets: K4-jet closed-form logs for L3, M21, M12; RG formulas
for C5_dd, K6_vv, K6_vd, C7_d, C9, K8_v). (3) The data-dependent RG checks of the new jets need the E jets EC3_1, EC5_1,
EC7_1, EK4_1, EK6_1, i.e. the same eps windows as their [eps^0 l^0] versions with log powers 0..1. (4) The raw leading log
-2362/315 of d_delta A7 is taken from the note; it is not derived here (raw, not normalized).

| file (`out/C8/`) | content | script |
|---|---|---|
| `input_definitions_C8.json` | all 35 inputs in normalized atoms; per-input tight/safe raw windows; lambda6 dependence | `scripts/derive_requirements_C8.py` |
| `normalized_atoms_C8.json` | 100 normalized atoms (31 new): Leibniz expansion in raw atoms, windows | same |
| `raw_requirements_C8.json` | C8 tight set 309 scalars in 104 atoms (114 beyond C7, 29 new atoms), safe set 324 (12 below-bound zeros, 3 genuine extras) | same |
| `definition_chain_C8.json` | C9, K8, EC7 normalization (generating function = note = explicit product rule), recurrence through b9 with j7 and lambda6, note F1-F4 structure checks | same |
| `two_kink_exact_C8.json` | Z2_*, Q2_* (incl. ddd, vvvv, vvvd, vvdd) exact; EZ2_*, EQ2_* exact, their eps^0 constants as MZVs (PSLQ, checked at 100 digits) | `scripts/two_kink_exact_C8.py` |
| `invariants_C8.json` | T4 and C8 = 8 T4 from eq:C8F/eq:C8H with a leak test; eq:C8assembly coefficients and the appendix B_old (61 terms) reproduced exactly; C8 has no D5 | `scripts/derive_invariants_C8.py` |
| `rg_logs_C8.json` | Callan-Symanzik higher-log predictions at general (v, delta) (derivation in the script docstring) | `scripts/rg_logs_C8.py` |
| `poles_C8.json` | pole-cancellation targets of the 74 normalized jets (28 new) and the raw negative powers they need | `scripts/poles_C8.py` |
| `budget_C8.json` | exact dC8/dx for the new non-exact scalars (e.g. A9[eps^0 l^1] +1/4, Q8_v -1/8, Q6_vd -1/2, A7_d +3/4) | `scripts/budget_C8.py` |
| `validation_targets_C8.json` | all archive-free C8 targets with provenance tags | `scripts/validation_targets_C8.py` |

**Results of the archive-free checks.**
* Definitions: the 25 old inputs, their normalized atoms and windows are regenerated identically. All 35 expansions equal
  the framework's independent J0 beta = R1 formulas (`review/crosscheck_framework_C8.json`). On synthetic data the spec
  C8 assembler and the framework module agree on all 35 inputs and C5..C8 to 3e-35
  (`review/crosscheck_framework_C8_assembly.json`).
* Trace: eq:C8assembly and the appendix B_old polynomial are reproduced exactly; 22 generic higher monomials do not enter T4.
* Recurrence: the l^0 part of the Callan-Symanzik identity reproduces the recurrence of all 35 inputs, including j7, b9 and
  lambda6. lambda6 is still not written in the note; it now enters K, Kv and J9. The note's F3 split
  (Kv = -4 P8 + 16 X_vv - 8 X_E + S3) has the coefficients this lambda6 implies.
* Note structure: the leading raw coefficients of Ndelta (-4 P6, +16 (Q4_vvd)_0, -8 (EQ4_vd)_0), U, Kv and J9, the 13
  Leibniz terms of D_norm and (lambda4)_vd all match the note.
* Higher logs: every log of every C3 jet (10 jets incl. d_delta^3, up to l^10) agrees with the independent three-kink code to
  1.3e-28; the note's C3, d_v C3, d_delta C3, A3_dd/2 and K4 logs are reproduced exactly; the general formulas pass 79
  checks on the phase-2 engine data (K4 jets all logs, C5/C7/K6/K8 jets l^2..top+1; rms pull 0.76, max 2.6;
  `review/rg_logs_vs_engine_phase2.json`).
* W = -37.7081115149525551125885600025 (independent three-kink code, ~1e-25; `review/three_kink_C8.py`).
* Exact two-kink endpoint atoms agree with the framework's quadrature to 9e-38.
* Requirements: the tight list, pruned of scalars that only multiply exact zeros, is the framework's list of 201 minus
  EZ4_base [eps^-2 l^0], which the spec places below the tight bound (safe set, must vanish).

**Validation targets for the engine** (`out/C8/validation_targets_C8.json`): the note's [eps^0 l^8] d_delta A7 = -2362/315
and [l^9] = 0 (raw); exact EZ2/EQ2 constants; closed-form higher logs of all C3 and K4 jets (e.g. C3[ddd] l^2 = 3 gamma,
K4[vvv] l^3 = 12A - 8a - 4f + 48 z2 + 32 z3); [l^(top+1)] = 0; pole cancellation; data-dependent second- and higher-log
formulas for C5_dd, C7_d, C9, K6_vv, K6_vd, K8_v (they need the extra E jets EC3_1, EC5_1, EC7_1, EK4_1, EK6_1);
finite-cutoff cross-check quantities.

**Sealed comparison** (`comparison_C8/`, see its README): the sealing script hashes the archive-free results
(`comparison_C8/sealing_record.json`) before it reads any archive value. Our algebra on the archived inputs reproduces the archive B_old
(5e-88), B_done, C8 (2e-98) and C_fixed - P6/2; our coefficients with the archive rational projections give pi_0 C8 = 88;
our independent W equals the archived W to 6e-28. W is the first of the six inherited inputs confirmed independently.

**How to run the C8 part** (after the phase-1 pipeline below; each step a few seconds, `rg_logs_C8.py` about 30 s,
`rg_logs_vs_engine_phase2.py` about 1 min; all local):

```bash
cd scripts
python3 derive_requirements_C8.py && python3 two_kink_exact_C8.py && python3 derive_invariants_C8.py
(cd ../review && python3 three_kink_C8.py)          # W and the C3_ddd logs; read by rg_logs_C8.py
python3 rg_logs_C8.py && python3 poles_C8.py && python3 budget_C8.py
(cd ../review && python3 rg_logs_vs_engine_phase2.py && python3 crosscheck_framework_C8.py)   # read the engine/framework
python3 validation_targets_C8.py && python3 test_assembler_C8.py
(cd ../review && python3 crosscheck_framework_C8_assembly.py)
python3 build_spec.py && python3 make_spec_md.py    # build_spec.py also reads the review/*C8*.json results
python3 assemble_from_raw_C8.py mine.json --fill-two-kink-exact --out result.json   # integration teams
cd ../comparison_C8/scripts            # sealed step, only after the above
python3 seal_and_compare_C8.py && python3 ../../comparison/scripts/check_sealing.py && python3 check_sealing_C8.py
python3 seal_and_compare_C8.py         # refreshes SHA256SUMS (the sealing record gets no new entry if nothing changed)
```

**Independence disclosure (C8).** The note (including its C8-era decimals) was read for the definitions. While locating
the sealed values, the archive's numerical JSON records were opened after the archive-free C8 definitions, requirements,
two-kink, trace, RG and pole outputs and the independent W existed (later archive-free steps only collect and format
them); no archive number entered any archive-free file (fingerprint scan,
`comparison_C8/sealing_report_C8.json`). No archive code, `*.expr`, `*_negative.json`, `*_audit.json` or raw Laurent table
was used.


**Version 2 (2026-10-02).** The phase-1 critique fixes are in. The specification is now split
into two parts:

* a definitions-only part that contains no archive numbers;
* a sealed comparison part that production code never reads.

## Layout

| path | what it is | archive numbers? |
|---|---|---|
| `spec_definitions.json` | **The specification.** Integration teams and production code read this file. Blocks: `CLAIMS_UNDER_TEST`, `CONVENTIONS`, `DEFINITIONS`, `EXTRAPOLATIONS`, `RAW_MOMENT_REQUIREMENTS` (tight and safe windows), `VALIDATION_TARGETS` (closed-form or independent, each with a provenance tag), `SPEC_CHECKS_ARCHIVE_FREE`, `AMBIGUITIES_AND_DISCREPANCIES`. SHA-256 is in `SHA256SUMS`. | none |
| `spec.md` | Readable version of `spec_definitions.json`, generated from it. | none |
| `spec.json` | **Deprecated.** The same definitions in the phase-1 key layout, kept for backward compatibility. `VALUES_ARCHIVE_COMPARISON_ONLY` is now a stub that points to the sealed file. | none |
| `out/` | Archive-free generated intermediates (listed below). | none (see the symlink note) |
| `scripts/` | The archive-free pipeline and the reference assembler. | none |
| `comparison/` | **Sealed.** Holds every archive-derived number and every comparison with the archive (`comparison/README.md`). | yes |
| `review/` | The phase-1 reviewer's checks (`review/README.md`). Two of them are sizing aids that read sealed data. `three_kink_independent.py` and its `.json` also hold the archive values of V, alpha, beta and gamma, typed in for comparison after computing; `validation_targets.py` reads only the script's own values. | sizing and comparison only |
| `out/C8/` | Archive-free C8 extension outputs (table above). | none |
| `comparison_C8/` | **Sealed** C8 archive values, the sealing record and the C8 comparisons (`comparison_C8/README.md`). | yes |
| `SHA256SUMS` | Hashes of `spec_definitions.json`, `spec.json`, `out/*.json` and `out/C8/*.json`. | none |

**Symlink removed (gate review, 2026-10-02).** The deprecated symlink
`out/archive_raw_coefficients.json` was deleted. `framework/tests/test_archive_pipeline.py` and
`framework/make_requirements.py` look in `spec/comparison/` first; the framework archive test was
rerun in a scratch copy without the symlink and passes. `out/` now holds no archive data at all.

## What the specification says, in brief

1. **Claims under test.**
   * C6 = 26 - 38z2 + 104z3 - 80z4 - 272z5 + 112z2z3
   * D4 = 13 - 179/8 z2 + 47/2 z3 - 493/8 z4 + 289z5 - 130z2z3 + 499/4 z6 - 76z3^2
   * C7 = 4D4 - T3 - T2^2 + C3C5/2

   We evaluated each of them to 60 digits ourselves.
2. **Definitions.** Each of the 25 inputs (a, p, A, E, c, f, b, G, q, k, V, R, J, L, M, N,
   alpha, beta, gamma, Phi, Psi, Omega, Q, P, K) is a Taylor coefficient of b3, b5, b7, h4, h6
   or h8 (note eq:subtraction plus the h8 line of the note, l.1150-1151).
   * Each input is expanded in 69 normalized atoms, for example `C3_1[v1d0]` = [eps^0 l^1] of
     d_v C3 at (v,delta) = (1,0).
   * Each normalized atom is a Leibniz sum of products of 75 raw atoms, for example `A5_vd`.
   * The exact integrand of every raw atom is in `DEFINITIONS.raw_atoms.*.integrand_at_v1_delta0`.
3. **Extrapolation beyond the note (stated explicitly).** The note writes `+lambda6` in h8 but
   defines only lambda2 and lambda4 (l.430-431). The spec uses the pattern extension
   `lambda6 = -2 K6_0 - 4 v d_v K6_0 + 2 v EK6_0`. Equivalently, the note's Jacobian is
   extended by one order: J21 += sqrt2 b0 6 K6_0 g^5, J22 += lambda6 g^6 and
   R1_2 += sqrt2 b0 K8_1 g^8. This reproduces the h8 line (`review/recurrence_from_jacobian.py`).
   * It affects only K = -4 h8, which enters D4 with weight -3/128.
   * It does not affect C6 or any other input.
   * See `EXTRAPOLATIONS` in `spec_definitions.json`.
4. **Raw requirements.** Both window sets are published.
   * **Tight set:** 195 scalars [eps^p l^k], with p from -2 to +2 and k = 0 or 1.
   * **Safe set:** 204 scalars, i.e. 9 extras.
     * 6 extras lie below the tight bound and must vanish: EQ2_base, EZ2_base, EZ2_d and EZ2_v
       at eps^-1, and Q4_base at eps^-2 (k = 0, 1).
     * 3 extras are genuine positive-power coefficients that multiply those: EZ2_base and
       Z4_base at eps^+2.
   * The tight bounds rest on a power-counting argument, which is written out in
     `RAW_MOMENT_REQUIREMENTS.tight_bounds_argument`.
   * 56 of the tight scalars belong to Z2_* and Q2_* and are known exactly
     (`out/two_kink_exact.json`).
5. **Matching.** No fugmatch (Y-factor) term enters any single-log input. Finite delta acts only
   through the moments, j1 = -2/(1+delta), j3, j5, the lambda_n and the explicit factors of v.
   * In the three-kink sector this is confirmed against the note's closed forms of a, p, A, E
     and c.
   * The b check is not independent here: EA3_base [eps^0 l^0] = -26 + 10z2 is solved from the
     note's b (target `EA3.0.l0`), so b's definition is tested only when a project route
     computes that scalar.
   * For the 4- to 8-kink inputs it is not tested against any note closed form (open item).

## Validation targets (archive-free)

The targets are in `out/validation_targets.json` and are mirrored in
`spec_definitions.json -> VALIDATION_TARGETS`. Each carries one of these provenance tags:

* `note`: stated in the note, with the line number.
* `note-closed-forms`: a lower-flow relation evaluated with the note's closed forms of a, A, p, E.
* `derived-here-exact`: derived exactly in this directory.
* `note-implied`: fixed by a note closed form through our own definitions. For example,
  EA3_base [eps^0 l^0] = -26 + 10z2 follows by solving our definition of b against the note's
  closed form of b.
* `independent-numeric`: a project-internal number, not exact. Examples are V, alpha, beta and
  gamma from `review/three_kink_independent.py` (about 1e-26), and the scipy and mpmath
  finite-cutoff values.

The targets themselves:

* the old inputs a, c, p, b, f, A, E;
* the combination calR = 2G + k + 2q - 2b - f (note l.632-634);
* D2, T2, C3, C4, D3, C5;
* P4, R4, S5;
* the low-order log coefficients of C3, K4, C5, d_v C3 and d_delta C3. The single log of
  d_delta C3 is p - 4, with p in closed form;
* the endpoint finite parts;
* the A3_dd/2 higher logs, which use the note's closed forms of a, A, p, E;
* the note's higher-log predictions for C7, d_delta C5, d_v C7 and K8.

**Archive-derived predictions are not in the spec.** They are sealed in
`comparison/archive_comparison.json`:

* [l^7] and [l^3] of C7;
* [l^7], [l^3] and [l^2] of d_delta C5;
* the second-tail logs of K4;
* the archived finite-cutoff values.

## How to run

The archive-free pipeline takes under 10 s on the Mac and must run in this order:

```bash
cd scripts
python3 derive_requirements.py   # definitions -> out/input_definitions.json, normalized_atoms.json, raw_requirements.json
python3 two_kink_exact.py        # exact Z2_*/Q2_* expansions -> out/two_kink_exact.json
python3 derive_invariants.py     # fixed point, T, D, conversion; note formulas and closed forms -> out/invariants.json
python3 check_closed_forms.py    # exact consistency of the closed forms -> out/closed_form_consistency.json
python3 sanity_finite_cutoff.py  # scipy cubature at eps=1/8 (our values) -> out/sanity_finite_cutoff.json
python3 validation_targets.py    # archive-free targets -> out/validation_targets.json
python3 build_spec.py            # -> spec_definitions.json, spec.json (deprecated), SHA256SUMS
python3 make_spec_md.py          # -> spec.md
python3 test_assembler_modes.py  # assembler window-mode regression test (synthetic data, ~1 s; exit 0 = pass)
```

The sealed comparison step is separate. Run it only after the pipeline above has run; it
takes about 1 min:

```bash
cd comparison/scripts
python3 archive_values.py        # archived inputs/series/periods -> comparison/archive_*.json, spec_selftest.json
python3 compare_with_archive.py  # -> comparison/archive_comparison.json, comparison_report.json, SHA256SUMS
python3 check_sealing.py         # independence hygiene -> comparison/sealing_report.json
```

The scripts need Python 3.10 or later, SymPy 1.12 and mpmath 1.3. The finite-cutoff check also
needs scipy.

## For the integration teams

Write your raw coefficients as `{"A3_base": {"-1": {"0": "...", "1": "..."}, ...}, ...}`, then run:

```bash
python3 scripts/assemble_from_raw.py mine.json --out result.json \
        [--windows both|tight|safe] [--zero-tol 1e-10] [--agree-tol 1e-8] [--fill-two-kink-exact]
```

The assembler returns all 25 inputs, D2, T2, D3, C5, T3, C6, D4 and C7, and their differences
from the claims. Its behaviour:

* **`--windows both`** is the default and is strict.
  * Every tight scalar and the 6 below-bound scalars must be supplied.
  * The 3 genuine positive-power extras (EZ2_base [eps^2 l^0], Z4_base [eps^2 l^0, l^1]) need
    not be supplied. They multiply only below-bound scalars, so they are looked up only when
    such a partner is non-zero, and then a missing one is reported in `safe_assembly_error`.
  * The below-bound scalars must vanish within `--zero-tol`.
  * Tight and safe assemblies must agree within `--agree-tol`.
  * If a check fails, the exit code is 1.
* **Missing coefficients.** A missing coefficient is always an error, never zero. All missing
  scalars are listed at once.
* **`--fill-two-kink-exact`** fills absent Z2_* and Q2_* coefficients from the exact table. It
  also reports how far your own values of them deviate from it.
* **Archive layout.** The assembler refuses the archive layout. The loader for that layout now
  lives in `comparison/scripts/archive_layout.py`.

Validate against `VALIDATION_TARGETS` first. Compare with the archive only at the end, by
running the comparison step.

**Error budget (sizing aid).** `review/sensitivities.json` lists dC6/dx and dD4/dx for all 25
inputs and the absolute accuracy each needs for a 1e-10 test of C6 and D4. Examples:
|dK| < 4e-9, |dOmega| < 3e-9, |dP| and |dN| < 1.6e-9, |dR| < 1e-10, |dV| < 5e-11. These were
evaluated at archive input values, which is used for sizing only. Finite-cutoff cubature checks
integrand conventions; it cannot isolate the [eps^0 l^1] single logs of the 6-8 kink atoms.

## Gate review fixes (2026-10-02, after fix round 1)

* **Assembler strictness made order-independent** (`scripts/assemble_from_raw.py`). Before,
  the default `--windows both` failed with exit 1 on exactly the documented required set, i.e.
  all tight scalars plus the 6 below-bound scalars at zero, with no genuine extra supplied. The
  reason: the safe assembly looked up `EZ2_base [eps^2 l^0]` before seeing that its below-bound
  partner was zero, and the error message wrongly blamed a non-zero below-bound scalar. The
  archive test passed only because the archived data contain that coefficient. Now a product
  is zero if any factor is exactly zero. A missing coefficient is an error only when every
  other factor of its product is non-zero, i.e. when its value could change the result.
  * On the full archived data, outputs are byte-identical before and after the fix; the sealed
    comparison step was rerun and every `comparison/*.json` is unchanged.
  * New `scripts/test_assembler_modes.py` (archive-free, synthetic data) covers all window modes,
    the non-zero below-bound paths, missing scalars, `--fill-two-kink-exact` and the
    archive-layout refusal. It fails 3 checks on the old assembler and passes on the new one.
* **`comparison/scripts/check_sealing.py`** now compares resolved paths
  (`/var` vs `/private/var` on macOS). Before, its local-file listing and its scratch
  `comparison/` clause silently missed paths when `TMPDIR` was a symlinked path. The
  compendium and `comparison/` clauses were already absolute and unaffected.
* **Deprecated symlink `out/archive_raw_coefficients.json` removed** (see Layout).
* **Wording fix in `AMBIGUITIES_AND_DISCREPANCIES.matching-wording`**: the b check is circular
  in the archive-free spec (see point 5 above). Only that string changed, so
  `spec_definitions.json` now has SHA-256 `9679237c...375e` (was `24c6c8e1...8426`). Every
  `out/*.json` is unchanged.

## Results of the checks (2026-10-02)

Archive-free checks, all passing:

* Normalization: from generating functions, C3..C7, K2..K8, EC3, EC5 and EK2..EK6 equal the
  note.
* Algebra (`derive_invariants.py`):
  * the symbolic content is byte-identical to phase 1;
  * D2, T2, D3, B_old(C6) and the new-input coefficients of C6 and D4 equal the note;
  * no generic higher term leaks into T3 or D4;
  * the conversion was checked by direct eigenvalue expansion;
  * the note's closed forms of a, c, p, b, f, A, E and calR give the boxed D2, T2 and D3
    exactly.
* The note's closed forms of C3, C5 and the C7 polynomial are mutually consistent under the
  conversion formulas.
* Two-kink table:
  * the insertions re-derived from the exponent equal the insertion table;
  * Z2 = 1/eps + l - 1 and Q2 = -l - 1 + eps hold (note l.388);
  * the supports are Z2 in {-1,0} and Q2 in {0,1}.
* Our definitions with the note's atoms give c = -16 exactly, and they fix
  EA3_0 = -26 + 10z2 from the note's b.
* EQ2_0 and EZ2_0 are derived analytically and confirmed numerically. The note's integral
  representations of A and E agree with their closed forms to 1e-39.

Sealed comparison, all passing (`comparison/comparison_report.json`):

* Our algebra is identical to the archived `trace_symbolic.json` and `D4_algebra.json`.
* The archived 100-digit inputs, put through our polynomials, give C6, D4 and C7 minus the
  claims of about 1e-83.
* All 64 comparable archive-free targets agree with the archived series to better than 1e-40.
* The exact two-kink table equals the archived series in all 73 files, with difference exactly
  0.
* The 12 archive-derived predictions match the archived series.
* The independent V, alpha, beta and gamma agree with the archive to at most 8e-27.
* The scipy A3_d and Z4_d agree with the archive to 3e-15.
* The production assembler on archived raw coefficients passes in all three modes (tight, safe,
  both). C6 minus the claim is 4e-56, the limit of the 60-digit data, and tight and safe agree
  exactly.
* All 26 archived series below the tight bounds are exactly zero.
* `check_sealing.py` passes. The pipeline, rerun in a scratch copy with a file-access audit hook,
  opens nothing in the compendium or `comparison/`, and its outputs are byte-identical. No
  production script contains an archive literal. Every number in the spec files that has 12 or
  more digits and coincides with an archive number is one of our own: a re-evaluated closed
  form, or a value tagged independent.

## Files in `out/` (archive-free)

* `input_definitions.json`, `normalized_atoms.json` and `raw_requirements.json`: the
  definitions and the tight and safe windows.
* `invariants.json`: symbolic T, D and fixed point, B_old, the conversion, the claims to
  60 digits.
* `two_kink_exact.json`: exact Z2_* and Q2_* expansions.
* `closed_form_consistency.json`.
* `validation_targets.json`.
* `sanity_finite_cutoff.json`.

The phase-1 `archive_*.json`, `spec_selftest.json` and
`selftest_assembler_on_archive_raw.json` were moved to `comparison/`; the last of these is
superseded by `archive_comparison.json -> comparisons.assembler_on_archive_raw`.
`scripts/archive_values.py` moved to `comparison/scripts/`.
