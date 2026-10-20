# Full coefficients and a new-cutoff test, not a completed analytic tail

## Direct answer to the outstanding request

The complete analytic large-Lambda leading polynomials of C6, C7, C8 are still
not obtained. This report does not count another overlap block or a finite
Schur identity as those polynomials.

The calculation has instead been moved to the entire Dconn problem: all even
cutoffs through 44 now have directly evaluated coefficients through order eight.
All vertices, vacuum feedback, primary retuning and normalization are included.
Old-data forecasts were frozen before the new high-order runs. A separate
attempt to extract EVERY coefficient of the proposed leading log polynomial
from full coefficient increments was tried and found unstable. Its outputs are
published as failed asymptotic inference, not new analytic constants.

This is numerical progress and a test of the missing asymptotics, not a claim to
have answered the full analytic request. A larger finite dataset does not by
itself replace the required hard-region integrations.

## 1. New complete finite-cutoff coefficients

The convention is epsilon=2s-1, Delta_sigma=(1-epsilon)/4,
Delta_thermal=1/2-epsilon/6+sum C_n epsilon^n, with frozen E0=N+P/4<=Lambda.
Dconn is the same consistent disconnected-vacuum model as in the supplied files.
Only spin/shadow primary gaps determine couplings. No thermal C_n is a target.

| Lambda | C6(Dconn) | C7(Dconn) | C8(Dconn) |
|---:|---:|---:|---:|
| 24 | 4468.053995119 | -80413.034760592 | 1627790.581001209 |
| 28 | 4756.037720364 | -86553.452234542 | 1772379.886143005 |
| 32 | 5001.245176310 | -91837.142161796 | 1897958.822838242 |
| 36 | 5214.293639728 | -96467.045249231 | 2008830.795999773 |
| 40 | 5402.321788341 | -100582.165342433 | 2107994.839825621 |
| 44 | 5570.353208855 | -104281.776437426 | 2197622.589237355 |

C6,C7 at 30..44 and C8 at 26..44 are new. Smaller values are independent replays,
not a relabelling of inherited records. The values in this table are NOT
continuum coefficients. In particular, 2,197,622.589 is C8(44), not C8(infinity).

## 2. Why the full calculation became practical

A stationary Rayleigh quotient of a wavefunction correct through epsilon^m
reproduces the exact eigenvalue through epsilon^(2m+1). Thus four wavefunction
orders suffice for all eighth-order energies. The new engine stores only the
actual symmetry/energy support of each subcutoff vacuum, and consumes the ladder
powers sequentially in normal ordering. None of these transformations omits a
hard vertex or reduces numerical precision.

At Lambda=44 the calculation contains 2,006,277 auxiliary
Fock states. Stored wavefunction entries are 38,815,700,
versus roughly 1.68 billion entries for a naive nine-order, all-state/all-vacuum
array. The completed run took 144.1 seconds locally,
with peak process RSS 2.390 GiB. This is not
cluster benchmarking, and the input production HPC code is unchanged.

The exact stationarity identity is tested with rational noncommuting matrices.
Independent ordinary full-order HT recursion and rational-coordinate calculations
check the physical coefficients. At Lambda44, degree-seven and degree-eight
calculations have different particle support and wavefunction order but agree
through seventh order to 1.25e-14
scaled discrepancy.

## 3. Forecasts made BEFORE the new high-order data

The prior same-scheme data were used through Lambda118 at orders 3,4,5, through
28 at orders 6,7, and through 24 at order 8. Sixteen model configurations were
frozen and hashed. This is new high-order withholding, not a claim that the
lower coefficients at the future cutoff were unobserved. Analytic C2,C3 and
independent gap exponents are declared controls; C4..C8 continuum targets do not
enter fitting, weighting, design selection or bias removal.

For a fixed representative residual basis A and lower edge 8, the errors at
Lambda44 are:

| Frozen model | C6 prediction minus new data | C7 difference | C8 difference |
|---|---:|---:|---:|
| homogeneous | -0.059611118 | +0.921867912 | -20.261310926 |
| source5 | -0.025727641 | +0.659327130 | -16.261622724 |
| sources567 | +0.022286690 | -0.467858482 | -1.490476764 |
| free_omega | +0.021469795 | -0.486017367 | -0.262909899 |

All 416 forecast comparisons are retained, including
models which do worse. The free-leading model's close C8(44) prediction is NOT a
measurement of its continuum intercept or a proof of its asymptotic hypothesis.
The source model and the old free-exponent alternative remain competing models,
not a calculation of the missing hard coefficients.

## 4. Attempting the WHOLE leading polynomial, not another partial class

I also fitted complete full-model increments to

    F_n(L)=L^-1/2 sum_(j=0)^(n-2) a_nj [log(L/32)]^j + optional residual powers,
    C_n(L+2)-C_n(L) = F_n(L+2)-F_n(L).

This keeps all five, six or seven monomial coefficients of the hypothesized
leading polynomial for C6,C7,C8. It does not impose homogeneous phi6 exponent
relations. New data only through Lambda36 are used to predict Lambda38..44.
The postulated leading power/log form and optional L^-1,L^-3/2 terms are model
assumptions; unresolved nondecaying terms are not claimed absent by proof.

| Leading-polynomial model | c8 intercept | Maximum new-cutoff error |
|---|---:|---:|
| All seven leading logs, no extra power | -5273487.074 | 0.0177821696 |
| All seven leading logs, plus L^-1 | 21329040.259 | 0.000412796045 |

The radically different intercepts coexist with tiny cutoff-prediction errors.
They must not be reported as an envelope of possible physical C8 or as derived
analytic tails. The input-noise sensitivity is also large in some models. All
successful and sample-count-rejected designs are retained. No favorable subset
is picked using a desired thermal result.

This test directly shows that 'include all leading monomials and fit them' does
not finish the requested task over the present range.

## 5. What remains uncomputed

The higher hard-region Wilson coefficients and overlap/counterterm terms must
still be evaluated uniformly and combined. The previous two-vertex formulas and
completed phase-response block do not determine the new six-, seven- and eight-
interaction amplitudes. The finite data here contain their effects but do not
uniquely identify their asymptotic residues.

Even the highest-log-only approximation has the wrong shell-increment sign in
this cutoff range under the old homogeneous hypothesis. Its derivative changes
sign at exp(2d), d=4,5,6. Those turning points are NOT required cutoffs for a full
polynomial fit; they simply explain why retaining the highest monomial alone
is not an adequate approximation now.

The result of this continuation is therefore a full-model numerical benchmark
and a real new-cutoff test, not the complete analytic tails. No additional
physical counterterm, OPE calculation, or tuned high-order continuum prediction
has been introduced.

## 6. Validation and reproducibility

- Raw independent HPC-array comparison: maximum scaled difference
  2.38e-14.
- Corrected finite C2..C5 versus the prior exact/closed-sum data: largest absolute
  difference 1.24e-11.
- Old complete higher-order Dconn records: largest scaled difference
  8.82e-15.
- Independent Fraction and ordinary full-order tests are in
  results/independent_validation.json.
- Nine exact stationary-quotient cases test both its valid order and a missing-
  wavefunction negative control.

Memory-exhausted developmental runs are recorded, not accepted as data. The
successful final path was replayed in independent processes. Source input files
and supplied production code are not changed. README maps commands to outputs;
docs/METHOD.md gives the exact recursion and the limits of each inference.
