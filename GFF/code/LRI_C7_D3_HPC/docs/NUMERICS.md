# Numerical contract

Dimension 3, epsilon=2s-3, complete C0--C7 finite-scheme assembly. The forest
kernel contains U_F^(3/2), the critical edge measure x^(-1/4), r(3,z), and all
regulator Taylor coefficients through z^(7-L). No power correction is assumed zero.
The original graph and local-subtraction construction is an inherited scientific
assumption; these software checks are not an independent field-theory derivation.

Default arithmetic exactly retains d=3 production: long double with >=64
significant binary bits and exponent range >=16384, GNU binary128 promotion
at 1e-9, Boost GMP350 promotion at 1e-23. The optional decimal300 compatibility
build has LOWER final-tier precision than the default; use it only deliberately.
Both backends passed the supplied tests. No threshold is relaxed.

The production kernel.hpp and native driver are byte-identical to the original
d=3 implementation. Quotient reuse passed numerical tests but showed no
consistent timing benefit, so it is retained only as a documented experiment.
The speculative exponential-scale cache is not included.

Task accumulation is compensated, and checkpoint partials are deterministically
merged with 50-digit Decimal arithmetic. Rechunking may change last rounding
bits; bitwise identity for arbitrary chunking is not promised. --sum-mode legacy
is provided for reference comparisons. Fixed chunks must be thread-independent.
Final fixed-point/covariance analysis deliberately retains original NumPy float64.

Reference-replay tolerance: |new-old|/max(1,|old|) <=1e-13; split-stream tolerance
1e-12. These are absolute floors at cancelled zeros. Promotion counts must agree.
Independent 450-decimal point checks compare original polynomial evaluation with
both backends, scaled by 1+sum(abs(forest terms)); this is not a global error bound.
Read benchmarks/full_validation.json, point_checks.json, workflow.json,
staging.json and reassembled.json for the measured outcomes.

Complete randomized graph-summed replicates, not chunks or individual Sobol
points, are statistical units. Preserve complete power-of-two nets. All mass,
coupling and Taylor-order covariance is retained; optional retained primitive
uncertainty is counted once, not averaged away between campaigns.

Build on the target cluster. GNU C++17/OpenMP, Boost, libquadmath and GMP are
required for the default. Strict flags are -ffp-contract=off -fno-fast-math;
fast-math is rejected. Tested locally on x86-64 Linux; wider portability is not
claimed. Changing executable or inputs requires a new run plan.
