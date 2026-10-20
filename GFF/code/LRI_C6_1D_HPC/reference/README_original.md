# One-dimensional long-range Ising: numerical C6

Convention: epsilon = 2s - 1 and Delta_E = 1/2 - epsilon/6 + ... + C6 epsilon^6.

**Result: C6(1) approximately 14331.8, with a conservative empirical uncertainty of about 0.5.**
The fitted-control estimate is 14331.77074704865; its estimated sampling standard error is 0.1434434494. The extra digits document arithmetic, not certified accuracy. The uncertainty is not a rigorous interval or a probability guarantee.

This is a direct six-loop graph calculation with deterministic singular-sector refinement and paired Monte Carlo corrections for smoother interpolation-degree differences. It is not a Pade/large-order prediction from C0--C5.

## Documents

- `C6_numerical_calculation.pdf`: five-page standalone derivation and numerical audit.
- `long_range_ising_complete.pdf` and `.tex`: complete project note, with the new sixth-order appendix. The general-dimensional result remains fifth order.
- `C6_numerical_appendix.tex`: additions alone.
- `verification/C6_result.json`: rounded result and evidence scope.
- `verification/C6_stratified_analysis.json`: full estimator, covariances, raw cutoff results, independently seeded checks and degree-12 diagnostic.

The two unadjusted cutoff estimates are 14331.773460287906 (maxgap) and 14331.755117787689 (span), with sampling standard errors 0.1683856282 and 0.1520987957. Their difference is 0.0183425002 +/- 0.0409223331 (sampling standard error). These values are not forced to agree by a control variate.

## Reanalyze saved data

The `reproduction` directory is self-contained for the numerical reassembly. It does not need a compiler, the graph binary, network access, or a known C6.

```sh
cd reproduction
python -m pip install numpy mpmath sympy
bash run_reproduction.sh
```

This reruns exact coefficient assembly, the RG higher-pole predictions, the multilevel/covariance analysis, and the independent five-loop-input control. `additional_checks.json` already records the exhaustive integer-weight audit; rerunning that audit requires generating the graph binaries.

Arrays `samples_*.bin` are native little-endian float64 in this record. The companion JSON gives sample count, stride (12), and an overall factor of -662287500. Columns are maxgap Laurent powers -6 through -1 followed by span powers -6 through -1. Multiply each stored row by the JSON factor before forming physical residues. A common seed reuses the same graph/ordering at both interpolation degrees. Features are int32, 10 columns: graph index, number of pole axes, count with 2a=-3, count with 2a<=-4, count with 2a=-1, and the five b_j values. The hard stratum has at least two pole axes or an a_j<-1; its Monte Carlo correction is set to zero because it is summed deterministically.

All degrees, counts, features, lower-loop arrays, and subtraction constants actually used are saved. Higher-degree samples with seed 135799 overlap; the degree-12 diagnostic is not treated as independent statistical evidence in the variance of the principal estimate.

## Regenerate the integration

A full rerun requires a C++17 compiler, OpenMP, and an AVX-512-capable x86-64 processor. The implementation actually used g++ 14.2.0, an AMD EPYC 9V74, four CPU cores, binary64 vector kernels and long-double final reductions. Weights are generated at 80 decimal working digits; Laurent assembly is high precision. This is **not** an entirely extended-precision integration kernel. Floating-point reduction order can change small last digits. Several gigabytes of free memory are required.

```sh
cd reproduction
bash run_reproduction.sh --integrate
```

The script runs sequentially to limit peak memory. It regenerates `graphs6.bin` and `graphs7.bin` (the latter contains 2,427,005 labeled six-loop graphs), all required quadrature weights, deterministic integrals and matched sample sets. Large graph binaries, generated caches and machine-specific executables are deliberately not shipped.

The expensive estimator is:

`H(all,N6) + H(hard,N10) - H(hard,N6) + sample(light,N8-N6) + sample(light,N10-N8)`.

N8 hard data is retained as a degree control. Sampling consists of 30,000 + 20,000 independent draws at the 8-minus-6 level and 3,000 draws at the 10-minus-8 level, not 2,137,415 independent direct high-resolution graph integrals. All nonzero graphs are included in the baseline and hard-stratum sums.

## Assembly

Let J5 = [epsilon^0](8 B5 - 3 A5), and H6 = [epsilon^-1](3 B6 - A6), for one common cutoff. Then

`C6 = R6 + (4/243) J5 - (2/729) H6`.

R6 uses the two-loop amplitude through epsilon^3, three-loop through epsilon^2, four-loop through epsilon^1, and five-loop poles. The lower-degree checks, five-loop finite-part control and five-loop regression are in the standalone note. The two cutoffs have different R6, J5 and H6; mixing their raw amplitudes is invalid.

The five-loop retained pole inputs originate from the precision-corrected previous project calculation; their file names and contents are preserved under `reproduction/lri_numerical_resolution/verification/records/`. The helper source from that calculation is included only for lower-loop integration and Laurent arithmetic. No fifth- or sixth-order special-function value is read by the new six-loop graph code.

## Scope

Sampling standard errors, interpolation-degree changes and cutoff/pole consistency tests are empirical numerical checks. They do not prove a rigorous error enclosure, an independent field-theoretic determination, a symbolic sixth-order identity, or accuracy of the truncated epsilon series away from epsilon=0. The sixth-order extension is one-dimensional only. Earlier d=1,2,3 and general-dimensional formulas in the full note are retained, not revalidated by this computation.
