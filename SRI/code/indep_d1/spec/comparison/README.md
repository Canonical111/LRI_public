# spec/comparison: sealed archive data and comparisons

**Everything in this directory comes from the archive.** These numbers are for comparison
only, after our own values exist.

* Production code never reads this directory. That covers `spec/scripts`, the framework, the
  engine and direct production paths.
* `check_sealing.py` verifies this for the spec pipeline with a runtime file-access audit.

The compendium is only read. These scripts never call the archive's integration engine
(hyperlog_core, moment_series, run_moment, periods_gmp and the rest). Archived `series/*.expr`
files are evaluated by our own string-to-mpmath evaluator, using the archived period tables.

| file | content |
|---|---|
| `archive_comparison.json` | **The single sealed comparison file.** See the key list below. |
| `archive_inputs.json` | The 25 archived inputs and the derived values C6, T3, B_old, C7, D4, B_old^{D4}, with source paths. |
| `archive_raw_coefficients.json` | Archived raw [eps^p l^k] coefficients for every needed atom and every archived power, to 60 digits. |
| `archive_normalized_atoms.json` | The archived normalized atoms. |
| `spec_selftest.json` | Our definitions evaluated on archived normalized atoms, and normalized atoms rebuilt from archived raw coefficients using the tight windows. |
| `comparison_report.json` | Pass/fail summary of `compare_with_archive.py` (`ALL_PASS`). |
| `sealing_report.json` | Result of `check_sealing.py` (`PASS`). |
| `SHA256SUMS` | Hashes of the sealed files. |

Keys of `archive_comparison.json`:

* `archive_inputs`, `archive_derived_values`, `note_quoted_decimals_archive_origin`;
* `C6_terms_from_archive_inputs`, `D4_terms_from_archive_inputs`;
* `raw_coefficients_needed`, `normalized_atoms`, `period_tables_used`;
* `archive_derived_validation_predictions`, `archive_finite_cutoff_values`;
* `superseded_records`;
* `comparisons`, which holds the algebra, invariants, targets, two-kink, independent-value,
  finite-cutoff, assembler, tight-bound and self-test comparisons.

## Scripts (`scripts/`)

Run them in this order, after the archive-free pipeline in `../scripts`:

1. `archive_values.py`. Extracts the archived inputs and evaluates the archived series with the
   archived periods (203,420 words, 0 conflicts), then runs the spec self-tests. About 30 s.
2. `compare_with_archive.py`. Runs every comparison and writes `archive_comparison.json`,
   `comparison_report.json` and `SHA256SUMS`. About 20 s. It feeds archive data to the
   production assembler `../../scripts/assemble_from_raw.py` in the tight, safe and both modes.
3. `check_sealing.py`. The hygiene check. About 10 s. It:
   * reruns the archive-free pipeline in a scratch copy under an audit hook;
   * checks that no production script contains an archive literal;
   * checks that every number in the spec files that coincides with an archive number has an
     archive-free origin.

`archive_layout.py` holds the archive-layout loader that used to sit inside the production
assembler. It is used by `compare_with_archive.py` and by `../review/cancellation_factors.py`.

## Status (2026-10-02)

`comparison_report.json` has `ALL_PASS: true`, and `sealing_report.json` has `PASS: true`.

## Notes for other components

* `framework/tests/test_archive_pipeline.py` and `framework/make_requirements.py` now look here
  first. The deprecated symlink `spec/out/archive_raw_coefficients.json` was deleted in the gate
  review (2026-10-02); the framework archive test passes without it (rerun in a scratch copy).
* Gate review (2026-10-02): the production assembler's strictness was made order-independent
  (see `../README.md`, "Gate review fixes"). `compare_with_archive.py` was rerun with the new
  assembler and all its outputs are byte-identical. `check_sealing.py` now compares resolved
  paths.
* The archived polynomials omit log powers whose coefficient is zero. `archive_layout.py` fills
  these zeros (k = 0, 1) when the polynomial is complete. A loader that does not do this sees
  them as missing.

## C8 extension (2026-10-03)

The C8 archive values live in the separate sealed directory `../comparison_C8/` (see its README). `scripts/check_sealing.py`
was extended: its runtime audit now reruns the C8 scripts too (`derive_requirements_C8.py` ... `validation_targets_C8.py`
before `build_spec.py`), forbids reads of `comparison_C8/`, requires `out/C8/*.json` to be byte-identical as well, and its
fingerprint scan accepts the tagged archive-free values of `out/C8/validation_targets_C8.json`.

