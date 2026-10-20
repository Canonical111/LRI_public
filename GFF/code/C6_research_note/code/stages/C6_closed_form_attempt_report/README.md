# C6 residuals: closed-form attempt, not a completed evaluation

## Scope

The requested target is a finite expression using fixed Mathematica built-in special-function values, without explicit sums, integrals, or unevaluated parameter derivatives. No such evaluation of any of the three complete residuals was established in this attempt. The accepted C6 expression is not changed.

## New computations actually executed

1. `spectral_test.py` derives the third-order rational recurrence satisfied by products of two arbitrary solutions of the homogeneous part of the supplied primitive Chebyshev recurrence. It then seeks a rational certificate for telescoping the alternating unweighted product, by solving the scalar adjoint recurrence. SymPy `rsolve_ratio` returned `None`. This is recorded as a failed certificate construction, NOT as a general non-reducibility theorem for the primitive. The inhomogeneous primitive combination is not claimed to have been completely classified.

2. `recognition.py` reads the supplied certified interval midpoints and searches three explicitly listed elementary/gamma candidate bases using PSLQ at 150 decimal working digits, tolerance 1e-125, coefficient bound 10^6, and at most 20,000 steps. It returns no relation for each tested basis. This does NOT show arithmetic independence, or exclude a relation outside these bases or bounds. It does not test every Mathematica special function.

The source certificate is `../C6_three_residual_sums_intervals.json`. A copy is included under `inputs/`; recognition.py supports both the original mounted path and that bundled fallback.

## What was not done

No all-sector reevaluation, no new rigorous interval computation, no new graph/RG proof, no Wolfram-kernel execution, and no proof that a closed form is impossible.

The published Rogers-Dougall and Bailey-Mishev transformations were reviewed; no matching specialization evaluating the complete residuals was established. Existing parameter-derivative and bivariate-function representations are not counted as evaluations in the requested narrower class.

## Reproduce

Requires Python 3, SymPy, and mpmath.

    python spectral_test.py
    python recognition.py

Output paths are relative to this directory. The files are diagnostic results, not a new expression for C6.
