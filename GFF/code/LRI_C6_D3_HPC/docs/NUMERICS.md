# Numerical contract: C6(3)

## Mathematical identity

The spatial dimension is fixed at 3, with epsilon=2s-3. The finite forest kernel is

```
K_G(x) = sum_F sign(F) * sum_{e in root(F)} x_e / ( S(x) * U_F(x)^(3/2) ),
S(x) = sum_e x_e.
```

At z=0 the edge measure is product x_e^(-1/4). The sampled ordered-sector
exponent uses `3*|S|/4-alpha[S]`, and shifting a homogeneous degree-L Symanzik
polynomial by exp(shift) entails the multiplier exp(-3*shift/2).
Both are different from the two-dimensional worker.

The retained Gamma factor is

```
G_L(z) = Gamma(1+L*z/2)
         * [Gamma(3/2+z/2)/Gamma(1+z/2)]^L
         / Gamma(3/4+z/4)^(2L).
```

The native normalization is `2*(-1)^(L+1)*G_L(0)`. The input table stores the
ordinary Taylor coefficients of `log(G_L(z)/G_L(0))`. Their normalization was
independently differentiated at 80 decimal working digits, with maximum
absolute disagreement below 3.5e-54 for the stored decimal values.

The two-loop data use `b2(0)=-6*(2+4*log(2)-pi)` and `c2(z)=b2(z)/6`.
Loops L=3,4,5,6 retain regulator orders 3,2,1,0 respectively. The fixed-point
solver keeps those jets before setting z=epsilon, and adds the canonical
term 3/2-epsilon/2. The exact last-loop sensitivity is

```
d C6 / d b6(0) = -1/2187,
d C6 / d c6(0) =  3/2187.
```

This is not an application of a regulator-independent MS formula to
regulator-dependent finite-MOM coefficients.

## Precision is not reduced

The reference precision hierarchy is retained:

- `long double`, at least 64 significant binary bits and extended exponent range;
- GNU binary128 when the cancellation ratio is below 1e-9;
- Boost 300-decimal arithmetic when its binary128 ratio is below 1e-23.

`U^(3/2)` is evaluated as `U*sqrt(U)` at all three levels. The fallback
log-sum/exponential expressions and thresholds match the original d=3 code.
No float64 first-pass shortcut, approximate inverse square root, lower
precision fallback, changed endpoint cutoff or discarded forest term is used.

The build uses `-O3 -std=c++17` (user-adjustable `CXXFLAGS`) followed by the non-overridable
`-fopenmp -ffp-contract=off -fno-fast-math` (Makefile `C6_REQUIRED`, and `tools/common.py` for every test and
benchmark build), so an environment `CXXFLAGS` cannot drop them. The only test hook in the kernel, `C6_FORCE_LEVEL`
(forced promotion for `tests/force_levels.py`), is compiled only when defined; production builds do not define it,
and the production binary built from this revision is byte-identical to the one built from the delivered sources
(personal desktop, Ubuntu GCC 13.3: sha256 e22809aa...; Expanse GCC 13.3: 2f897044..., job 54510646).
A compile-time check rejects `__FAST_MATH__`, and static assertions enforce
long-double precision. Never use `-Ofast` or architecture flags that narrow
long double. GCC's optimization contracts are documented at
https://gcc.gnu.org/onlinedocs/gcc/Optimize-Options.html .

Final fixed-point/covariance analysis uses NumPy float64, as in the reference
analysis. This is **not** a new reduction in analysis precision. Merging task
partials uses 50-digit Decimal arithmetic before conversion to replicate jets.
If sampling precision eventually approaches that arithmetic floor, a separate
high-precision assembly audit is required.

## Rounding-order changes

Shared denominator prefixes preserve each individual ordered addition chain.
The default nevertheless uses compensated accumulation **within a task**,
followed by a deterministic `(replicate, graph, interval)` merge. Changing chunk
boundaries changes rounding order relative to a single naive original sum.
Bitwise equivalence to the original global sum is not promised.
`--sum-mode legacy` exists for matched-stream reference checks.

The measured comparison norm is `abs(new-old)/max(1,abs(old))`, not a relative
error claim at a cancelled zero. Tested differences:

- 492 graph classes at loops 3--6, two 64-point replicates per graph, legacy
  mode: maximum normalized difference < 9e-20; fallback counts matched.
- Arbitrary 23-point execution chunks reconstructing complete 64-point nets:
  difference < 1.6e-17. Fixed chunks on one vs four threads produced identical
  tested scientific rows.
- Matched production-style benchmark sums: < 3e-18.
- 516 independent Kirchhoff-cofactor point checks at 70 or 650 working digits, now by **relative** error (the bridge
  returns long-double decimal strings, so scaled values down to 1e-396 are compared as values; a zero or negated
  value fails, which the test demonstrates). 515 of 516 meet relative 1e-9 (maximum 3.6e-13 on a personal desktop). The
  previous record used `max(1,|ref|)` normalization, which was vacuous for all 48 scaled checks (|ref| <= 1.4e-62).
- **The one listed point beyond the 300-digit tier (shared with the original code).** At L6G160 with the six scaled
  edge variables at 1e-130, the forest terms have magnitude A = 0.78 while the true value is 9.24e-396: a
  cancellation of 394.9 digits, beyond 300-digit arithmetic. The kernel returns rounding noise, -1.46e-316
  (1.86e-316 A). The original d=3 code has the identical promotion path and returns the identical value. For this
  listed point only, `tests/check_points.py` requires level 2, a measured depth > 300 digits, |value| <= 1e-290 A,
  and a value bit-identical to the ORIGINAL code's (through a bridge to `reference/code/kernel.hpp` built with
  `-DSPATIAL_D=3`); any other failure, or the listed point not being encountered, fails the test. The strict
  relative criterion is therefore **not** met by every point; the exception is a property of the numerical
  contract, not of this optimization, and the regime cannot be reached by production samples.
- Forced precision tiers (`tests/force_levels.py`): with promotion forced to binary128 and to 300 digits at every
  point (test-only hook in the new worker; a patched temporary copy of the original header), the new worker and the
  original d=3 code agree to normalized <= 1e-15 at every loop, and every point is counted at the forced level.
- **Archived production replay** (`make test-replay`): all eight archived fresh d=3 streams, 385,744,896 samples, on their
  archived nets and seeds. Fallback counts equal the archive in every stream; per-graph jets agree to <= 2.2e-13 and
  replicate batches to <= 1.6e-15 (the archived code summed `prob*v/n` per point); the fresh-only C6(3) rebuilt from
  the replayed batches equals the published 33.560840352429125 (bitwise on a personal desktop).
- 96 independent regulator-dependent Lagrange extractions agree to normalized
  tolerance 1.2e-14 on the tested synthetic data. A further 64 synthetic
  comparisons with the archived fixed-point implementation are bitwise equal
  in the tested environment.

The records `benchmarks/final_validation.json`, `point_checks.json`, `dimension_checks.json` and
`matched/benchmarks.json` were produced by the delivered (earlier) test versions and are kept unchanged as evidence.
Records of this revision are in `benchmarks/expanse_2026-09/`. Tests write only into temporary directories or an
explicit `--output`; they never rewrite shipped evidence.

The native worker cannot tell a d=2 from a d=3 Gamma table (same format). The d=3 identity is guarded in Python:
the job-private runtime copies only `gamma_d3.txt`, verified against the frozen d=3 inputs manifest, and plans,
checkpoints and merges carry and check `dimension == 3`.

## Randomization and complete coverage

Scientific stream identity is campaign/loop/replicate/graph/sample index.
Threads, nodes and scheduler placement never seed the stream. Native code seeks
using the Gray code of the global index. The final graph net must be a complete
power-of-two interval `[0,N)`; chunks may be of arbitrary positive size only
because all pieces must be rejoined before statistical analysis.

SciPy's LMS-scrambled Sobol direction matrices are frozen into hashed files.
Every newly generated net is checked against SciPy's public `random_base2`
output before export; the package records the SciPy version. The export reads
private direction arrays, so a future SciPy change may require adapting that
checked exporter rather than assuming compatibility. Runtime integration reads
the frozen integer matrices and does not require SciPy. See
https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.qmc.Sobol.html .

Covariance is estimated between independent graph-summed randomized replicas.
Points within a net, or chunks belonging to the same net, are not counted as
independent measurements. Coupling, mass and Taylor-order correlations are
retained. The two campaigns have equal jet weights fixed before production.
Every primitive kernel is sampled, so no inherited Monte Carlo offset is used.

## Power-sector and evidence boundary

The local finite kernels integrate the power-free sector of the established
calculation. Their identification with the full physical coefficient uses the
retained d=3 analytic compensation, including the unknown-core cancellation.
Those audits are preserved in `reference_d3/verification/` and in the original
note. This delivery **does not independently redo that analytic derivation**.
It does not remove power graphs on the unsupported assumption that each one
vanishes.

Reassembling original data with the archived analysis code reproduces C6(3)=33.56819679857058 and sampling SE
0.02418403846814063 (relative 1e-12; bitwise where the NumPy build matches). The new assembly (`tools/assemble.py`)
reproduces the archived fresh-only, previous, per-campaign and four-campaign results from the archived records
(`tests/archived_assembly.py`, relative 1e-15). That is a regression
check; no new physics production has been pooled with the accepted data.

Sampling errors, lower-loop controls and point checks do not certify shared
systematic errors in the graph inventory, forest construction or analytic
compensation. The new result writer leaves an empirical accuracy allowance
unset until a user evaluates convergence and independent diagnostics.

The 28 six-loop graphs whose frozen target is zero have wa = 3 wb, so their C6 weight is exactly zero; they still
receive 4 x multiplier points, which leaves C6 unaffected but makes the individual six-loop jet components (and
their covariance) differ from the archive's. The lower-order C3-C5 pulls are diagnostics, not gates: the archived
fresh C3 pull was +2.42, and at higher statistics they become far more stringent.
