# Numerical contract and verification scope

## Physical target

The observable is the thermal dimension in dimension three, with
`epsilon=2s-3`. The constant and linear coefficients are `3/2` and `-1/6`.
The finite-scheme beta and mass jets remain functions of the regulator until
the fixed-point series is solved. These inputs are not constant
minimal-subtraction RG coefficients.

Every loop L carries Taylor terms through `z^(8-L)`. The high-order RG
assembly uses nine coefficients, including C0. Missing loops or short jets
are errors. The analytic two-loop series is computed through z^6 and the
Gamma logarithmic factors through order six.

## Integrand and arithmetic

The mixed forest uses a denominator `U_F^(3/2)` for each term before the
signed sum. The edge measure is `x_e^(-1/4+z/4)`. The root numerator removes
only logarithmic forest edges. A proper power subgraph contributes its
zero-momentum local mass subtraction without changing the root interaction
order. Exact denominator groups and integer numerator coefficients are
combined before floating-point evaluation.

The C7 arithmetic contract is retained:

- Long double is the first tier, with at least 64 binary significand bits.
- A cancellation ratio below `1e-9` promotes to IEEE binary128.
- A ratio below `1e-23` in that tier promotes to GMP with 350 decimal digits.
- No endpoint, signed forest term or precision promotion is dropped.
- Task accumulation is compensated and chunk accumulation uses 50-digit
  Decimal arithmetic. Complete randomized replicates are converted to
  float64 for the inherited fixed-point/Jacobian covariance formulas.
- The build includes `-O3 -std=c++17 -fopenmp -ffp-contract=off
  -fno-fast-math`, with conflicting arithmetic flags refused.

The C8 extension increases storage limits to 16 edges, 31 Sobol coordinates,
seven scalar regulator coefficients, and 14 output values at the largest
beta/mass jet width. It preserves the forest summation order on shared
C7 inputs.

## Independent verification

The detailed machine-readable evidence is under `verification/`.

- Analytic jets: two independent Cauchy contours for the two-loop input;
  independent Gamma-factor Cauchy checks; comparison of every overlapping
  old two-loop jet with the supplied C7 values.
- Fixed point: 64 exact rational comparisons with independent bivariate
  Lagrange inversion; exact top-loop weights; affine high-loop response;
  explicit regression for a seven-loop zero-channel graph that affects C8.
- Graphs: enumeration reproduces all class counts through L8; independent
  nauty canonicalization checks the L8 isomorphism classes and
  automorphism-derived rational weights; every supplied nonzero C7 kernel
  at L3–L7 is reproduced after graph/edge alignment.
- Non-induced subgraphs: every proper edge subset is independently checked
  in all power-containing graph classes through L8, and every unreduced
  mixed-forest map agrees with the induced-subgraph construction.
- Native regression: 2,432 identical-point evaluations reproduce every
  shared C7 jet and precision counter exactly, including both sectors.
- Native boundaries: largest Taylor/edge/Sobol limits, all three layouts,
  random-access splitting and thread counts are checked with synthetic
  inputs that never enter a scientific run.
- Independent 450-digit arithmetic: actual L8 free, primitive and power
  graphs are tested at ordinary and extreme parameter configurations.
- Campaign tests: beta/mass correlation, nonlinear power correction,
  covariance identities, complete-net summation and rejection of omitted,
  duplicated, stale or altered scientific inputs.

Matching sampled point arithmetic is not a bound on integration error.
Matching lower-loop kernels does not independently prove the inherited
finite-scheme field-theory construction at arbitrary loop order. The exact
non-induced cancellation argument and exhaustive graph checks address
specific extension risks, rather than making that broader claim.

## Statistical treatment

SciPy exports independently scrambled Sobol direction matrices. The first
1,024 points are reconstructed against its public API, and every leading
generator block is checked for nonsingularity over GF(2). Columns beyond
that public-API check, and bits below float64 resolution, are not compared
point by point with the public API.

Each scientific stratum has independent matrix and digital-shift seeds
derived from the frozen base seed, campaign, sector and loop. Per-graph
digital shifts remain deterministic functions of replicate and graph IDs.
The two campaign means have weights 1/2; their covariance matrices of the
mean therefore enter with weights 1/4. Covariance between all beta/mass and
regulator slots of a graph-summed replicate is retained.

If J and Jf are the Jacobians of the full and power-free coefficient maps,
the power correction uses the derivative J-Jf for the free sector and J
for the power sector. The cross covariance between the free coefficient
and its power correction is retained. The code verifies that the complete
covariance equals the free covariance, correction covariance and both
cross terms. A separate whole-replicate bootstrap checks the delta-method
standard errors and estimates plug-in nonlinearity bias diagnostically.

References for C3–C7 are comparison controls only. The C7 value comes from
the supplied study's completed high-statistics run, not the older archived
pilot. No reference is used to tune the output coefficient or force a
power correction to vanish.
