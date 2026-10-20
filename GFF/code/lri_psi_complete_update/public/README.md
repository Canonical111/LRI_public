# lri_psi_complete_update: public targets

This folder and `../public.mk` were added for the public edition (2026-10-13). Everything else in
`GFF/code/lri_psi_complete_update/` is the package as delivered in the September 2026 research bundle, byte for
byte (checked against `public/bundle_sha256.txt`, the lines of the bundle's `MANIFEST.sha256` for this package; the package has no checksum list of its own). Its `README.md` is the final
report; it mentions files that are not exported here (the note copies `long_range_ising_complete.*` and
`previous/`, the TeX additions `additions/`, `source_diff.patch`, `update_note.py`, the unexecuted Wolfram file
`CoefficientsPsi.wl`, and the note-build records `verification/pdf_checks.json`, `preservation_checks.json`).
The proof of the polygamma evaluation of K is Section 8 of `GFF/note/`; the C0..C5 forms are its Sections 1.1 and 4.

## What the package checks

* Exact SymPy certificate (`verification/symbolic_checks.py`): the telescoping certificate of the contiguous
  relation, the bilinear Taylor relation, the reduction of K to fixed polygamma values, and every C0..C5 and L
  rewriting between the original and the reflected-quarter bases.
* `verification/coefficient_values.py` (70 digits): C0..C5(1), K, L, P4, P5 in both bases. P4 and L reuse the
  240-digit 4F3(1) values in `verification/wheel_inputs.json` (from the bundle package `Fpm_simplification`, not
  exported); P5 is a fresh Gamma quadrature. The other two replays recompute P4 from scratch.
* `verification/numerical_checks.py` (110 digits): the endpoint-subtracted original master integral for K
  against the polygamma value (residual about 6e-109), the elementary u and sigma coefficients, and 75-digit
  finite-parameter tests of the six-3F2 master and of the bilinear identity; `complex_check.py` repeats the
  complex-parameter bilinear test at 130 digits.

## Targets (run from `GFF/`)

    make -C code/lri_psi_complete_update -f public.mk test     # ~2 s: symbolic, coefficient values, complex test
    make -C code/lri_psi_complete_update -f public.mk replay   # ~15 s: test + numerical_checks.py

One core, Python >= 3.10 with `public/requirements.txt`. The scripts run unchanged in a fresh copy under
`.work/pkg/` (they overwrite their records). Each regenerated record is compared with the shipped one (exact for
the symbolic record; 1e-55 relative for the 70-digit record, 1e-45 for the mixed 110/75/50-digit record, 1e-90
for the 130-digit record), and C2..C5(1), K, P4, P5 with `GFF/results/closed_forms_1/C5_1_quoted.json`.
Observed residuals quoted by the README (6.387e-109, 2.673e-51, 1.39e-102, 9.28e-69) pass if the recomputed
residual is at most ten times the quoted one. Table: `.work/VERIFY_<target>.md`.

The package README's closing remark that the old graph estimate's 9.26e-9 discrepancy "remains unresolved"
predates `lri_numerical_resolution`, which resolves it (note Section 14).
