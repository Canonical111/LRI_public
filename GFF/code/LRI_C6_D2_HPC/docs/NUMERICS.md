# Numerical contract

## Scientific scope

The optimized executable evaluates exactly the supplied **d=2 power-free finite
forest kernels**, retaining z-dependent b_L(z), c_L(z) through z^(6-L). Final
assembly substitutes z=epsilon and solves the finite-order fixed-point equation.
Two-loop data and the previously audited power-sector compensation are supplied
from the reference calculation. This delivery does not redo the field-theoretic
power correction or establish a rigorous interval for the physical coefficient.

All required loop groups (3,4,5,6) and both campaigns must be merged before a full
new result is assembled. No old physical C6 value is used as a control, and no
C3–C5 reference is fitted. The numerical lower-order outputs are checks, not
replacements for the previously more precise special-function evaluations.

## Precision retained

* `long double` must have >=64 significant binary bits and extended exponent
  range (tested: x86-64 80-bit format in 16-byte storage).
* First cancellation promotion: GNU binary128, at the unchanged threshold 1e-9.
* Second promotion: Boost `cpp_dec_float<300>`, at unchanged threshold 1e-23.
* No `FAST_INITIAL`, `double` shortcut or fast-math. Builds fail if fast-math is
  enabled. `-fopenmp -ffp-contract=off -fno-fast-math` are appended to every build
  (Makefile `C6_REQUIRED`, and `tools/common.py` for test and benchmark builds), so an
  environment `CXXFLAGS` cannot drop them.
* The only test hook in the kernel, `C6_FORCE_LEVEL` (forced promotion for
  `tests/force_levels.py`), is compiled only when defined; production builds do not
  define it. With GCC 13.3 on Expanse the production binary built from this revision is
  byte-identical to the one built from the delivered sources (sha256 5818340b...).
* Promoted paths still form the original ordered log sums and exponentials.

These are the C6 thresholds and 300-digit fallback, NOT the different C7 defaults.
The precision classes should not be silently interchanged between packages.

## Rounding changes explicitly flagged

The shared-prefix and numerator kernels retain each polynomial's addition order.
The default per-task accumulation is compensated, rather than the original naive
sum. Different sample chunking changes where sums are grouped. The deterministic
merge uses Decimal at 50 digits on the serialized extended-precision contributions
before the original float64 fixed-point analysis. Consequently, bitwise equality
with the old naive global sum is not promised. `--sum-mode legacy` is available
for matched-reference checks; it does not remove split-task rounding differences.

## Fresh checks supplied

Normalized differences below use `abs(new-ref)/max(1,abs(ref))`. This scale floor
matters near exact cancellations and is not a claim of relative accuracy for zero.

* 492 graph classes (5+16+76+395), 64 points in each of two replicates: maximum
  legacy-mode normalized jet difference 8.76e-20. All fallback counts match.
* Arbitrary 23-point chunks reconstruct the full 64-point nets; after compensated
  reduction the maximum normalized difference is 4.69e-17. The tested one- and
  four-thread rows are identical for fixed chunks.
* Frozen-map matched replay: maximum normalized difference 5.44e-20. Endpoints
  of that saved map are retained, not silently renormalized.
* Longer matched benchmark: maximum normalized jet difference 2.15e-18; the
  28 five-loop and 421 six-loop binary128 promotions match the original counts.
* 516 independent Kirchhoff-cofactor checks at 70 or 650 working digits. The bridge
  returns long-double decimal strings, so the scaled configurations (references down
  to 1e-395) are compared as values. Criterion: relative error <= 1e-9 (the level-0 path
  accepts cancellation down to the 1e-9 promotion threshold); a zero or sign-flipped value
  fails, which the test demonstrates. On Expanse, 515 of the 516 checks meet it (max
  relative error 2.8e-15). The strict criterion is NOT met by the one point below, which
  is the only permitted, explicitly listed exception. (The
  original record, `benchmarks/point_checks.json`, used `max(1,|ref|)` normalization,
  which was vacuous for every scaled case.)
* **Resolution limit of the 300-digit tier (found by the relative check; shared with the
  original code).** At the most extreme test point, L6G160 with the six scaled edge variables at 1e-130, the forest terms have magnitude A = 9.0 while
  the true value is 4.7e-395: a cancellation of 395 digits, beyond 300-digit arithmetic.
  The kernel returns rounding noise, 2.1e-320 (2.3e-321 A). The original code has the
  identical promotion path (on sampled points with every evaluation forced into this tier,
  the forced-tier test finds the two codes bitwise equal), so
  this is a property of the numerical contract, not of this optimization. The error is
  bounded by about 1e-300 of the point's own term magnitude, far below any value that
  affects an integral. For this listed point only, the test requires level 2, a measured
  depth > 300 digits, |value| <= 1e-290 A, and a value identical to the ORIGINAL code's at
  the same point (evaluated through a bridge to `reference/code/kernel.hpp`); any other
  point failing the relative criterion fails the test.
* Forced precision tiers (`tests/force_levels.py`): both the new worker and a patched
  copy of the original code are built with every point promoted to binary128, and
  then to the 300-digit tier, and compared on matched points of every loop (including
  the most expensive six-loop graphs): normalized jet difference <= 1e-15 and every
  point counted at the forced level by both codes. Ordinary replays never reach the
  300-digit tier, so this is its only matched test.
* End to end (`tests/e2e_reference.py`): a small campaign run through plan, shards,
  chunks, cost-ordered checkpoint blocks and merge agrees with one run of the original
  binary per group (all 8 groups, frozen grid included): batches and per-graph jets
  <= 1e-15 normalized, equal fallback counts.
* 64 independent synthetic-jet fixed-point comparisons agree exactly with the
  archived Python assembly.
* The new assembly (`tools/assemble.combine`) applied to the archived fresh-campaign
  records in retained mode reproduces the archived fresh-only result
  362.4401566755939 +/- 0.19630967690795775 and both per-campaign results to relative
  <= 1e-12 (`tests/archived_assembly.py`; observed 7e-16).
* The archived analysis code (`tools/reassemble_reference.py`) reproduces
  362.3489137997967 and SE 0.15264446036381157 to relative 1e-12; the last bits
  depend on the NumPy/BLAS build (bitwise on the original environment, 6e-16 relative
  on Expanse NumPy 1.26.4).

See the machine-readable files in `benchmarks/` and rerun `make test` and
`python tests/check_points.py` after changing compiler/architecture.

## Sampling and common-reference covariance

A scientific replicate contains all graph strata at that loop order. Its complete
Taylor vector is the statistical observation. Direction matrices, shifts, maps,
counts and seeds are fixed before production. Direct Gray-code seeks permit work
splitting without dropping or thinning points. The merger requires full
nonoverlapping coverage [0,N) for every N=2^m stratum.

The two campaigns receive equal fixed weights on RG Taylor data. All Taylor and
coupling/mass covariance within each replicate is retained. Independent loops
and campaigns contribute covariance with squared weights. Bootstrap replicates
resample full Taylor vectors, not individual components.

`--primitive-mode recompute` (default) measures all ten primitive graphs anew;
it uses no retained primitive variance. Their budget (`--primitive-points x
--multiplier` per primitive on average) is split by a frozen Neyman table,
`inputs/primitive_allocation_d2.json`: per-point standard deviations of the
C6-projected integrand h=(-v0+3v1)/2187 from the four archived paired d2 L6 records
(auxiliary method-study data used by no estimator), counts rounded to powers of two,
total cost within 1.1x of the uniform split. Every primitive remains an independent
stratum, so the estimator is unbiased for any allocation; `plan` records the counts
and a projected block SE (MC scaling). `--primitive-allocation uniform` restores the
equal split; `--points` overrides every stratum. `--primitive-mode retained` excludes
those ten graphs and adds their prior finite-MOM contribution once. Its variance
is a shared uncertainty, not reduced by the number of campaigns or workers.
The formerly retained 66 nonprimitive graphs are always integrated in a new run.
Do not substitute an MS partial sum for this finite-MOM reference.

Assembly uses the two-loop B2 and the primitive reference P10 only after their
digests match the inputs manifest frozen by the plan, and records those digests in
`C6_result.json`.

Seeds: group seeds are SHA-256 functions of (user seed, campaign, loop, role) by
default. The archived driver arithmetic (`--seed-scheme legacy`) regenerates the
archived fresh campaign-a L6 net byte for byte (`tests/archived_replay.py`) and is kept
for such replay tests; it refuses the archived production base seeds.

Final outputs report sampling error and leave `empirical_allowance` null.
Independent run agreement, resolution/rate checks and the retained analytic
audits must be reviewed before assigning additional physical digits. No sampling
calculation here bounds a shared graph/renormalization implementation error.
