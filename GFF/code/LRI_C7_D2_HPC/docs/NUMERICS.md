# Numerical contract and validation

> Delivery note: earlier benchmark numbers below are retained records.
> Fresh packaging checks and rebuilt benchmark fixtures are documented in
> `delivery/DELIVERY.md` and `delivery/fresh_checks.json`.

## Unchanged scientific computation

The dimensional convention is epsilon = 2s - 2. All supplied finite-scheme
kernels, graph weights, mixed local-mass/logarithmic subtractions, projective
importance densities, and regulator Taylor coefficients are unchanged.
At loop L the worker evaluates the jet through order 7-L. In particular the
extra two-loop coefficient needed at seventh order is present. The full
physical assembly evaluates the regulator-dependent fixed point, not a
regulator-independent MS formula applied to finite-scheme constants.

Both sectors are evaluated:

    full = F(free + power)
    correction = F(free + power) - F(free)

The measured power correction is never set to zero. At loops 3--7 there are
2,790 power-free kernel classes and 721 mixed-power kernel classes with required
weights. At seven loops these are 2,298 and 590 respectively. The 44 seven-loop
primitive classes are included in the former. Exact graph/forest zeros remain
excluded according to the unchanged supplied inventory.

## Arithmetic choices

The portable/default optimized executable is `bin/c7d2_decimal`:

| Evaluation stage | Reference and default optimized code |
|---|---|
| First pass | long double, >=64 significant binary bits, exponent range >=16384 |
| Cancellation ratio below 1e-9 | GNU __float128 (binary128) |
| Quad ratio below 1e-23 | Boost cpp_dec_float<300> |

The comparison denominator and tiny floor in the original long-double test are
preserved. No forest term is dropped because it is numerically small.

`bin/c7d2_gmp` is an **explicit backend alternative**, not an invisible switch.
Its first two stages and promotion thresholds are identical. Only the last
stage changes to Boost `gmp_float<350>`, backed by the GMP library. The tested
reference declared 300 decimal digits and stored up to 328 with guard digits;
the alternative declares 350 (372 maximum digits in the tested type metadata).
Thus this option does not reduce arithmetic precision. It does change the
library and rounding/truncation behavior, and cannot promise identical results
for every possible input. Retain the decimal executable for compatibility
replays. Neither backend constitutes interval arithmetic.

All builds end with `-ffp-contract=off -fno-fast-math`; __FAST_MATH__ and
insufficient long-double types are rejected. The test host used GCC 14.2.0.
Rebuild and test on target hardware. Freeze/compiler-pin Boost and GMP versions
for a campaign. A binary checksum protects against mixing executable builds,
but does not magically make dynamically linked libraries identical on different
nodes: the cluster environment/module stack must be held fixed.

## Changes in evaluation order

The shared product DAG and ordered-prefix denominator sums were already present
in the original *long-double* evaluator. This revision applies identical-order
sharing to the expensive binary128 and multiprecision evaluators too. Products
and each denominator/numerator are still evaluated in their original order;
identical subexpressions are cached within the point, not approximated. Scratch
objects are reused by a thread between samples. The discarded final MP error
sum was never read: only its value enters the returned integrand. Quad error
sums remain because they decide promotion.

The scientific values printed by both optimized executables were identical to
the original worker on all delivered matched-graph replay tests. This is an
observed regression result, not a universal bitwise-equivalence theorem for the
GMP option. Arbitrary sample chunks change where compensated partial sums are
combined; deterministic Decimal merging can differ in the last rounding bits
from a single continuous native accumulator. `--sum-mode legacy` disables native
compensation for diagnostic comparisons only.

The merger uses 50-digit Decimal arithmetic on textual native partials, then
converts completed replicate totals to NumPy float64 for the fixed-point,
complex-step Jacobian, covariance and bootstrap calculations. That final
precision boundary matches the existing analysis. It is explicitly not a
claim that all final analysis is 80-bit or multiprecision.

## Random-stream contract

The native point is a function of the frozen direction matrices, seed,
replicate, graph and absolute point index. Thread IDs, node IDs, chunk IDs,
array placement and completion order do not enter the stream. Gray-code seeking
starts directly at each interval's first point; it does not replay earlier
draws. Each stratum retains its original whole power-of-two net with midpoint
open-interval coordinates. The net exporter verifies its direction matrices
against 16 points from the public SciPy API every time it builds a replicate.
It records SciPy's version because the matrix export accesses a private member.

The two sectors, two campaigns and loop orders use independent randomizations.
Within each sector/campaign/loop, graph totals are summed by replicate before
estimating covariance. Chunks and points within a single net are not treated
as independent uncertainty samples. Coupling/mass and Taylor-order covariances
are retained. Campaign weights are fixed at one half, not fitted to final data.

## Retained inputs

Default production recomputes all seven-loop primitives. In optional retained
mode their old scalar contribution is added once to C7, and the old variance
is added once to the full and power-free covariance. It cancels in their
difference. Bootstrap diagnostic draws one shared primitive uncertainty per
resample. Earlier complete C7 values and lower physical coefficients are never
used as fitting constraints. Known one- and two-loop jets remain input data.

## Actual tests

- `benchmarks/full_validation.json`: all 3,511 required classes at loops 3--7,
  56,176 matched samples, both arithmetic backends; printed scientific jets and
  promotion counts matched exactly. This is a finite point set, not exhaustive
  coverage of the integration continuum.
- Arbitrary 23-point chunks reconstruct complete 64-point strata across layouts
  0, 1 and 2. Maximum normalized split/unsplit change is recorded there; one
  versus four threads gives identical tested scientific rows at fixed chunks.
- `benchmarks/point_checks.json`: 140 independent 450-digit point checks per
  backend, including progressively extreme endpoints. Denominators are
  independently evaluated by exponentiating each monomial's log sum rather
  than using the optimized product DAG. Scaled discrepancy is below 1e-280;
  the observed maximum is about 1.85e-302 for decimal and 2.15e-353 for GMP.
  This normalizes by one plus the sum of absolute terms; it is not a relative
  error bound on a nearly cancelled zero.
- 96 synthetic regulator-jet cases: new fixed-point and Jacobian functions agree
  with the original analysis implementation.
- `benchmarks/workflow.json`: both primitive modes, all 20 group types,
  incomplete-coverage rejection, duplicate no-clobber publication, corrupt
  checkpoint rejection, and restart with changed thread counts. Tiny workflow
  subsets explicitly output `C7_full = null`.
- `benchmarks/staging.json`: relocated one-pack runtime and frozen cost model.
- `benchmarks/reassembled.json`: saved-data reconstruction of full, power-free
  and correction means/covariances. Maximum scalar difference from the
  authoritative record is about 9.1e-13; no graph integrations are rerun for
  this reassembly.

Reference replay tolerance: |x-y|/max(1,|x|) <= 1e-13. Chunk tests use 1e-12.
These are documented regression thresholds, not certified errors on C7.
The original physics derivation and graph-generation framework are retained;
this optimization is not an independent field-theoretic validation.

## External documentation

- SciPy Sobol balance and independent randomization:
  https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.qmc.Sobol.html
- GCC floating-point optimization contract:
  https://gcc.gnu.org/onlinedocs/gcc/Optimize-Options.html
- Boost GMP multiprecision backend:
  https://www.boost.org/doc/libs/latest/libs/multiprecision/doc/html/boost_multiprecision/tut/floats/gmp_float.html
