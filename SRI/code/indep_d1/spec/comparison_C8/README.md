# spec/comparison_C8: sealed C8 archive values and comparisons

**Everything numeric in `archive_C8_values.json` comes from the archive.** These numbers are for comparison only, after
our own values exist. Production code never reads this directory (spec/scripts, framework, engine, direct, assembly
production paths); `scripts/check_sealing_C8.py` verifies this for the spec.

| file | content |
|---|---|
| `sealing_record.json` | SHA-256 of every archive-free C8 result of the spec (spec_definitions.json, spec.md, out/C8/*.json, review/*C8*.json), written by `seal_and_compare_C8.py` BEFORE it reads any archive number. Entries are appended when a result changes, never overwritten. |
| `archive_C8_values.json` | The C8-era archive numbers: the ten inputs (W, S, L3, M21, M12, N2 from the 100-digit inherited record; U, Kv, J9 from their records; Ndelta = F1_known - 4 P6), A9_1, Z8_1, (EA7)_0, (EZ6)_0, D9_lower, A7_d_1, D_known, P6, P8, F3_known, the 25 old inputs used by the archive assembly, B_old, B_done, C_fixed, C8 (and the archive's candidate value), D_ct, the superseded P6 runs; the note-only decimals (X_vv, X_E, S3, D_norm and its products, (Q4_vvd)_0, (EQ4_vd)_0, Q6_vv(1/10), ...); the rational projections and raw rationals; the claims. |
| `comparison_C8_report.json` | Comparisons through OUR algebra (no archive code) and sizing from archive magnitudes. |
| `sealing_report_C8.json` | Result of `scripts/check_sealing_C8.py`. |
| `SHA256SUMS` | Hashes of the files in this directory. |

Not read: `*.expr`, `*_negative.json`, `*_audit.json`, `*.periods.json`, the P6/P8/U/J9/Kv expression files and the raw
Laurent coefficient tables of the archive.

## Scripts

1. `scripts/seal_and_compare_C8.py` (about 1 s): sealing record, archive extraction, comparisons, SHA256SUMS.
2. `../comparison/scripts/check_sealing.py` (about 1 min): reruns the whole archive-free pipeline (phase 1 and C8) in a
   scratch copy under an audit hook; fails on any read of the compendium, `comparison/` or `comparison_C8/`, or on any
   output that is not byte-identical.
3. `scripts/check_sealing_C8.py` (a few seconds): static literal scan, fingerprint scan of the C8 outputs against the C8
   archive numbers, and a read-only scan of the project for references to this directory.
4. `scripts/seal_and_compare_C8.py` again, to refresh SHA256SUMS.

## Results (2026-10-03)

`comparison_C8_report.json` (`ALL_PASS`):
* Our B_old polynomial at the archived 25 inputs minus the archive B_old: -5e-88. B_done (our six-term linear part):
  4e-63 (the archive B_done has 65 digits). C8 from our assembly at the archived inputs minus the archive C8: -2e-98.
  C_fixed - P6/2 minus C8: -6e-109.
* The candidate closed form (our evaluation) minus the archive C8: -3.09e-86, as the note says.
* Our C8 coefficients with the archive rational projections: pi_0 C8 = 1153/6 + sum c_I pi_0(I) = 88; the note's own
  reduction also gives 88 and Ndelta^(0) = -20848.
* The archive identities J9 = A9_1 - Z8_1 + 2 EA7 - 2 EZ6 + D9_lower, U = A7_d_1 + D_known and Kv = -4 P8 + F3_known
  hold to 1e-84 or better; F3_known = 16 X_vv - 8 X_E + S3 with the note's 34-digit decimals to 2e-30.
* **W:** our independent three-kink value minus the archived W = -5.9e-28. This confirms the first of the six inherited
  inputs independently.
* Sizing (comparison only): with the archive magnitudes, a 1e-4 absolute test of C8 needs A9[eps^0 l^1] and Z8 to about
  7e-10 and 4e-8 relative, (EA7)_0 to 1.4e-8, A7_d[eps^0 l^1] to 4e-10, Q8_v[eps^0 l^1] to 4e-9 and Q6_vd[eps^0 l^1] to
  1.6e-7 relative (see the report for the exact list and the 1e-4-relative variant).

## Sealing history

`sealing_record.json` has four entries, all written before the archive values were (re)read by the script:
* 17:30:35 UTC: first sealing.
* 17:37:58 UTC: no definition or value changed. Differences: `out/C8/invariants_C8.json` (a check label corrected from
  "54 terms" to "61 terms"), `out/C8/budget_C8.json` (sigmas rounded to 3 digits, so that float noise such as
  0.00013333333333333334 no longer trips the fingerprint scan), and `spec_definitions.json`/`spec.md` (these two files
  plus the new ASSEMBLER entry and the synthetic framework cross-check).
* third entry: adds the hash of `review/crosscheck_framework_C8_assembly.json`, which the first two entries did not list.
* fourth entry: the RG predictions that vanish are now written as exact `0` instead of the float `0.0`
  (`out/C8/rg_logs_C8.json`, `validation_targets_C8.json`, `review/rg_logs_vs_engine_phase2.json`, `spec_definitions.json`,
  `spec.md`); no value changed.

