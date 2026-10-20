# lri_fixed_hypergeometric_update: public targets

This folder and `../public.mk` were added for the public edition (2026-10-13). The rest of
`GFF/code/lri_fixed_hypergeometric_update/` is a subset of the package delivered in the September 2026 research
bundle, byte for byte (checked against `sha256_manifest.json`): `README.md`, `requirements.txt`,
`sha256_manifest.json`, `verify_manifest.py`, `code/verify_fixed_hypergeometric.py` and its record
`verification/fixed_hypergeometric_checks.json`. Not exported: the copy of `lri_numerical_resolution/verification`
that the package carried (shipped in `GFF/code/lri_numerical_resolution`), the earlier Meijer-G and
parameter-derivative evaluators of P5 and their records (superseded representations, nothing quoted), the
unexecuted Wolfram files, the proof excerpts (the proof is Section 10 of `GFF/note/`), `history/`, `previous/`,
the diffs and the note copy. `verify_manifest.py` is strict and lists those files as missing; `make test` checks
the manifest with ignore-missing semantics instead.

## What the package checks

`code/verify_fixed_hypergeometric.py` evaluates the preferred P5 formula of note Sections 1.1 and 4.1, four
9F8(-1) values and one 8F7(-1) value with fixed positive rational parameters, and compares it with a fresh
positive Gamma quadrature at 100 digits and, with changed breakpoints, at 125 digits (residual 3.63e-121). It also
checks the three-Fourier-harmonic identity at five real and complex points, an alternative sixth-grid sample set,
and the exact SymPy transformations from the original three-Meijer-G formula.

Two public-edition checks are added:
* `public/sec11_closed_forms.py`: C2..C5(1), K, L, P4, P5 from the formulas exactly as printed in note
  Section 1.1 (and the unreduced Section 4 formula), with literal mpmath calls at 70 digits;
* `public/kernel_identity.py`: the Barnes kernel identity (fp:eq:kernel) of note Section 10, exactly in SymPy.
  The note refers to "accompanying SymPy code" for it, which is not in the research bundle.

## Targets (run from `GFF/`)

    make -C code/lri_fixed_hypergeometric_update -f public.mk test     # ~3 s (verifier at 40 digits)
    make -C code/lri_fixed_hypergeometric_update -f public.mk replay   # ~6 s (verifier at the recorded 100 digits)

One core, Python >= 3.10 with `public/requirements.txt`. The verifier runs unchanged in a fresh copy under
`.work/pkg/`. Its 100-digit output is compared with the shipped record (1e-85 relative; observed identical), the
quoted P5 to its last digit, and the observed residuals (3.63e-121, 9.36e-97) pass if at most ten times larger.
Table: `.work/VERIFY_<target>.md`.
