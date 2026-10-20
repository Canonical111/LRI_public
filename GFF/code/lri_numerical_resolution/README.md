# LRI C5: numerical offset resolution and self-contained note

This is an additive revision of the **polygamma coefficients + proved Kappa**
note. All 262 previously displayed equation/align/gather environments and
143 unnumbered displays are preserved byte-for-byte. The original TeX and earlier proof-level verification
records are retained under `previous/`. This revision adds Appendix H and
updates the abstract, main result, numerical-check section, and status pointers.

## Result and meaning

The analytic expression is unchanged:

    C5 = -731.1394766245398258538691265825272306624788975443600036...

The historical printed span result was -731.1394766152787. Its signed difference
(old minus closed) is +9.2611258538691265825e-9.

The highest completed fresh raw graph calculation uses interpolation degree
**24**, fresh degree-32 lower-loop data, and the exact combined channel:

| Cutoff | Forward-reassembled C5 | New minus analytic expression |
|---|---:|---:|
| Total span | -731.13947662453918918697817 | 6.3666689095762e-13 |
| Largest gap | -731.13947662453680571273417 | 3.0201411349529e-12 |

These long decimal strings are arithmetic outputs, **not certified digits**.
The old 9.26e-9 offset is removed down to the residuals above. The note does
not claim a rigorous interval enclosure or a new independent physical
five-loop derivation. No correction is fitted to C5 or to any raw amplitude.

## Diagnosis and controls

The old C++ kernel used binary64 `double` for the quadrature rows, tensor
weights, smooth integrand values and within-group sums. Only the outside
accumulation used `long double`. Extending an outer sum cannot recover
rounding errors already created inside a signed finite-part functional.
The old Python path additionally narrowed some stored and assembled values
through `float`.

A full scalar control at degree 18 promotes **all** original kernel arithmetic
to `long double` (64 significand bits on the tested platform), and includes
all 59,145 ordered graphs in both channels. At fixed degree and fixed lower
inputs it moves C5 by about -7.96e-9. A second implementation performs the
exact cancellation 3*w_mass-w_coupling before integration. Its 49,605 nonzero
graphs and 335 exponent groups contain no derivative-residue a=-2 sector.
At degree 18 it agrees with the full extended control within 1.7e-12.
Raising the degree then suppresses the residual interpolation error.

The direct combined engine uses vectorized double-double regular contractions;
its upstream nodes, weights, kernel factors and endpoint contractions are
extended precision. This is **not** a claim that the whole integral has
106-bit accuracy. The original extended engine and combined engine have
independent contraction structures but share the mathematical sector rules.
The regular Laurent tensor contribution is shared by both cutoffs, explaining
why a small historical cutoff difference could miss a common bias.

The exact identity controlling propagation is

    delta C5 = (5/729) delta [z^(-1)](3 B5 - A5).

The detailed signed ledger separately accounts for old finite-precision assembly/output,
lower-loop input changes, the corrected five-loop integral, and the remaining
new-minus-closed residual. It is forward bookkeeping, not a fitted adjustment.

## Files

`long_range_ising_complete.tex` is standalone and compiles without external
figures or data files. `long_range_ising_complete.pdf` is its compiled version.
The new appendix is also extracted in `additions/numerical_resolution.tex`.
`source_diff.patch` records every change against the preserved latest note.
`verification/records/` contains raw amplitudes, complete reassembly results,
exact algebra and graph checks, the runtime environment, and actual run logs.
`verification/source/` contains the original, scalar extended, and combined
C++ kernels plus the original graph-enumeration/lower-loop Python module.
The latter is imported by the new drivers; use the drivers rather than running
its preserved historical command-line interface directly.

The original residue certificate (26 four-loop and 92 retained five-loop
rows) is supplied under `verification/inputs/`, together with the historical
numerical record. The symbolic expressions for b4, c4 and the D5 remainder
are checked exactly against that certificate. The **symbolic forest residues
were not freshly regenerated** in this investigation; the raw numerical graph
integrals were regenerated and use no analytic periods as inputs.

## Fast audit (saved raw data; usually seconds)

From this folder, after installing the Python dependencies:

```sh
python verification/symbolic_audit.py
python verification/exact_decimal_audit.py
python verification/audit.py
```

The final command reconstructs Laurent counterterms, beta/gamma coefficients
and the fixed-point expansion at 80 decimal working digits without converting
raw inputs through binary64. Use `--refresh-reference` to reevaluate the gamma
integral and the wheel functions; this can take longer. It never adjusts a raw
integral to agree with that reference.

## Full integral regeneration

Requirements: Python 3.10 or later, NumPy, mpmath, SymPy, a C++17 compiler with
OpenMP, and several gigabytes of RAM. `requirements.txt` lists the exact Python
package versions used here. The `combined-simd` method requires AVX-512F/FMA;
the driver checks this. On other hardware use `scalar` on a platform whose
`long double` has at least 64 significand bits; it is substantially slower.
The stored binary caches are not required or distributed: they are regenerated
locally in the appropriate floating-point layout.

```sh
python verification/run_lower.py 32
python verification/regenerate_graph_audit.py
python verification/enumeration_audit.py
python verification/run_sector.py --method scalar --order 18 --threads 4
python verification/run_sector.py --method combined-simd --order 18 --threads 4
python verification/run_sector.py --method combined-simd --order 22 --threads 4
python verification/run_sector.py --method combined-simd --order 24 --threads 4
cp verification/work/scalar/amplitude5_*.json verification/records/
cp verification/work/combined-simd/combined5_*.json verification/records/
python verification/audit.py --refresh-reference
```

Each new sector run evaluates both cutoffs. The optional `original-double`
method reconstructs the historical arithmetic path at a chosen degree, but
its original saved numerical rows, not a newly repeated binary64 run, are
used as the historical comparison in this revision. Reproduction commands
can overwrite the corresponding record files; retain the supplied package
as a baseline. Hardware, libm and thread reductions can change low-order bits.

The old kernel's diagnostic log label `W MB` assumes eight-byte scalar storage;
the extended variants still print that inherited label. Actual `long double`
storage was 16 bytes, so that particular W-only log estimate is half the
allocation size. `environment.json` records the actual type sizes. This
cosmetic diagnostic is left untouched in the exact source used for the runs.

## Rebuilding the note

```sh
python build_note.py
python make_readme.py
pdflatex -interaction=nonstopmode -halt-on-error long_range_ising_complete.tex
pdflatex -interaction=nonstopmode -halt-on-error long_range_ising_complete.tex
pdflatex -interaction=nonstopmode -halt-on-error long_range_ising_complete.tex
```

The builder reads the completed numerical records and the preserved previous
TeX. It refuses to publish the intermediate degree-18 result as the resolution.
The final PDF is compiled and visually inspected; its final preflight record
is included. All mathematical formulas in the previous displayed environments
are protected by an exact preservation check. A SHA-256 manifest records the
files actually delivered (the manifest itself is excluded).
