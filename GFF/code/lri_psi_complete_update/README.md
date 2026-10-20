# LRI: reflected-quarter psi coefficients and analytic Kappa proof

## Main files

- `long_range_ising_complete.tex` and `.pdf`: updated complete note.
- `previous/long_range_ising_complete.tex`: unmodified preceding note.
- `source_diff.patch`: exact source difference from that note.
- `additions/psi_coefficients.tex`: added coefficient section.
- `additions/Kappa_analytic_proof.tex`: added analytic proof.
- `CoefficientsPsi.wl`: optional Wolfram Language expressions (not executed here).

The original C2–C5 formulas, the original six-3F2 Kappa definition, its Jhat
and Vr factors, and the original wheel-generating formulas remain in the note.
The preferred added formula has no hypergeometric parameter derivatives.
Q, the two wheel periods, and P5 are still non-polygamma inputs.

## Mathematical result and proof status

The former conjecture is now proved, for the original one-dimensional master:

Kappa = 2 psi_1(1/4)^2 - pi^2 psi_1(1/4)
        + (A/2) psi_2(1/4),
A = psi_0(1/2) + psi_0(1) - 2 psi_0(1/4).

Appendix G gives the full proof. It reduces six elliptic moments to two
3F2 functions, proves a contiguous recurrence with a telescoping certificate,
and proves a bilinear identity using an entire periodic discrete Wronskian.
The polynomial vertical-growth bound, not periodicity alone, forces that
Wronskian to be constant. The bilinear identity eliminates the two higher
Taylor coefficients in exactly the combination entering Kappa.

The appendix does not assume an integer-relation search or the L reduction.
It does not assert a gamma-product evaluation of the whole deformed master.

Section 3 includes a reflected-quarter basis and a sparse alternative for
C0 through C5. It distinguishes the natural arguments d/4, 1-d/4 and d/2
from an unproved arbitrary-dimensional extension of the higher coefficients.
Only the stated known general-dimensional C0–C2 formula is asserted.

## Reproduction

From this directory, with Python, mpmath, SymPy and a standard LaTeX setup:

```sh
python update_note.py
python verification/symbolic_checks.py
python verification/numerical_checks.py
python verification/complex_check.py
python verification/coefficient_values.py
pdflatex -interaction=nonstopmode -halt-on-error long_range_ising_complete.tex
pdflatex -interaction=nonstopmode -halt-on-error long_range_ising_complete.tex
pdflatex -interaction=nonstopmode -halt-on-error long_range_ising_complete.tex
```

The source additions are inserted by `update_note.py`; edit those additions,
not just the merged source, when regenerating the revision.

## Checks actually run

`verification/symbolic_checks.json`: exact checks of the recurrence
certificate, the bilinear Taylor relation, the Kappa reduction, all C0–C5
rewritings, and the equivalence of the reflected and sparse bases. All passed.

`verification/preservation_checks.json`: selected original formulas are
byte-for-byte unchanged, and source hashes are recorded.

`verification/numerical_checks.json`: a fresh 110-decimal-working-digit
endpoint-subtracted original master evaluation differs from the polygamma
value by approximately 6.387e-109. The elementary u and sigma integral
coefficients were recomputed. Finite real and complex parameter tests compare
the original six-function master to the two-function reduction. A separate
mpmath direct-hypergeometric bilinear check at 50 digits has residual 2.673e-51.

The 75-digit complex gamma-ratio-tail test loses digits at higher tail order;
that less accurate record is retained, not silently removed. The follow-up
`complex_bilinear_130.json` increases working precision to 130 digits and has
complex residual of magnitude about 1.39e-102 at t=0.12+0.07i.

`verification/coefficient_values.json`: original and psi coefficient formulas
were compared at 70 working digits. Wheel inputs were reused from the earlier
240-digit record and are included in `wheel_inputs.json`. P5 was freshly
recomputed from its gamma moment. The largest C0–C5 arithmetic residual is
about 9.28e-69. The coefficient begins

C5 = -731.13947662453982585386912658252723066247889754436000...

These are numerical consistency checks, not rigorous interval bounds.
The analytic proof does not depend on their precision. No full graph integral
or independent five-loop renormalization calculation was rerun. The old graph
estimate's approximately 9.26e-9 discrepancy remains unresolved.

The final PDF was compiled and its added coefficient/proof pages rendered
and visually inspected. 
