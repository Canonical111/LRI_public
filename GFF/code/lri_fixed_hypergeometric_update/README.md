# LRI: a finite, derivative-free ordinary-hypergeometric value for P5

## Current result and note

The current standalone source is `long_range_ising_complete.tex`; the compiled
PDF has 83 pages. The finite formula is on page 7, equations (4)--(6). Its
analytic proof is Section 8.12, pages 32--35. Section 8.13 states which of the
retained representations to use.

For r in {1,2,3,5,7}, set

    Y[r] = (r/8) [Gamma((r+2)/8)/Gamma((r+6)/8)]^7
           * 9F8(1,1+r/8,((r+2)/8)^7 ; r/8,((r+6)/8)^7 ; -1).

With c = cos(pi/8) and s = sin(pi/8),

    P5 = 16*pi^(3/2) * {
            -35*Y[2]
            + (22*sqrt(2)-13)*(c^7*Y[3]-s^7*Y[5])
            + (22*sqrt(2)+13)*(c^7*Y[1]+s^7*Y[7]) }.

Here exponent 7 in a parameter list means seven repeated parameters, not a
power of the parameter. The r=2 upper/lower parameter 1 cancels at fixed
parameters, leaving an 8F7. Therefore the result uses four fixed 9F8(-1)
values and one fixed 8F7(-1) value. All parameters are positive rational
numbers and every series has parametric excess 3/2. The final evaluation
contains no parameter derivative, Taylor coefficient, limiting process,
extra summation, multivariate function, or Meijer G.

## Analytic proof, not integer-relation fitting

The function

    f(z) = (z+1/4) [Gamma(z+1/2)/Gamma(z+1)]^7

is summed bilaterally with alternating signs. Gamma reflection, absolute
convergence, removable poles, and a vertical growth bound imply that

    Xi(t) = cos(pi*t)^7 sum_{n in Z} (-1)^n f(n+t)
          = alpha*cos(2*pi*t) + beta*sin(4*pi*t) + gamma*cos(6*pi*t).

The finite harmonic space is proved before its coefficients are recovered.
The exact samples at t=0,+/-1/8 determine the three coefficients. Splitting
the bilateral sum produces precisely the five ordinary hypergeometric
values above. This eliminates the derivatives that appeared in the earlier
local residue representation. It is not a finite-difference approximation
and makes no minimality or elementary-evaluation claim.

`fixed_hypergeometric_main.tex` and `fixed_hypergeometric_proof.tex` are
convenient excerpts. Their contents are already incorporated verbatim in
the main source; no external TeX input files are required.

## Fresh reproducible verification

The new verifier requires mpmath and sympy:

    python code/verify_fixed_hypergeometric.py --digits 100 \
      --output verification/fixed_hypergeometric_checks.json

The saved complete run uses 100 decimal working digits and a 125-digit
control with changed gamma quadrature breakpoints. It computes all five
literal fixed-parameter hypergeometric values and independently recomputes
the positive-real-axis gamma integral. It also checks an alternative exact
sixth-grid representation, the trigonometric identity at real and complex
points, and exact symbolic transformations of the original three-G formula.
No stored period values, parameter derivatives, Cauchy coefficients, or
parameter limits are used as inputs or evaluation procedures.

The recorded gamma-integral-minus-fixed-hypergeometric residual is
-9.3633527093844e-97 at 100 working digits, and +3.6305549201712e-121 at
125 working digits. These are numerical consistency checks, not interval
error bounds. The analytic proof does not depend on these checks.

`code/P5FixedHypergeometric.wl` translates the same finite expression to
Wolfram Language. This file has not been executed in a Wolfram kernel in
this revision; the Python verifier is the executed implementation.

## Preservation and evidence boundary

The immediately preceding main source is preserved as
`history/hypergeometric_derivative_note.tex`. Its README is preserved in
`history/README_hypergeometric_derivative.md`.

`changes_fixed_hypergeometric.diff` is the source diff for this revision.
All 282 displayed equation/align/gather/multline blocks in the immediately
preceding note remain byte-for-byte in the new source. The original Meijer
formula, parameter-Taylor presentation, all C0--C5 formulas, the K and L
proofs, and the preceding numerical graph audit remain available. Prose
identifying the preferred representation and the current result has been
updated. The original uploaded source was not modified in place.

No graph, counterterm, or fixed-point computation was rerun in this
period-level revision. P5 and the physical coefficients are unchanged.
Historical records retain their historical working precisions and scope.
In particular, agreement of special-function expressions is not a new
independent five-loop graph calculation or a rigorous interval certificate.

The inherited root manifest was an older historical artifact; its bytes
are preserved in `history/manifest_inherited_before_fixed_update.json`.
Only the newly generated root `sha256_manifest.json` describes the bytes
of this current package. Check them with

    python verify_manifest.py

The historical `changes.diff`, older note-builder scripts in `history/`,
and records in `previous/` are provenance, not current rebuild commands.
Do not run an old note-builder script over the present main source.

## Compilation

From the revision root:

    latexmk -pdf -interaction=nonstopmode -halt-on-error long_range_ising_complete.tex

Alternatively run pdflatex three times. The note uses a self-contained
bibliography, has no external figure dependencies, and requires no Wolfram
installation for compilation or Python verification. The checked PDF has
no unresolved references or overfull boxes; an inherited underfull text
line is harmless. New result/proof pages were rendered and visually checked.
