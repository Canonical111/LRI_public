# Further numerical-method and precision study of C6(2), C6(3)

Convention: epsilon = 2s - d. The integral, graph inventory, finite forest
subtraction and previous analytic power-sector compensation are inherited from
the supplied calculation. This is a numerical refinement, not an independent
six-loop field-theory derivation or a rigorous error enclosure.

## Current reported result

- C6(2) = 362.3 +/- 0.7. Underlying estimator 362.3489137997967;
  sampling standard error 0.15264446036381157.
- C6(3) = 33.57 +/- 0.10. Underlying estimator 33.56819679857058;
  sampling standard error 0.02418403846814063.

Reporting allowances are four estimated sampling standard errors, rounded up
in steps of 0.1 for d=2 and 0.05 for d=3. They are empirical allowances, not
probability guarantees, interval bounds, or epsilon-series truncation errors.
The underlying digits document the estimator, not independently certified digits.

The primary estimator is the ORIGINAL preplanned equal-weight combination of
old A/B and fresh A/B RG Taylor vectors. A later dimension-coupled primitive
control is retained as an auxiliary method comparison, NOT selected as the
primary result: it improves that block but gives essentially no improvement in
the full coefficient after its reference uncertainty is included.

## What was actually tested

1. Identical-point kernel optimization: a shared product DAG replaces repeated
   exponentials for overlapping Symanzik monomials. Extended precision and the
   original binary128/300-decimal cancellation fallbacks remain. Identical-point
   speedups were 2.84x and 2.87x on the current four-CPU-quota environment.
2. Matched-budget graph-stratified Sobol versus pseudo-random sampling,
   coordinate reorderings, alternative endpoint powers, and antithetic pairs.
   The smoother endpoint powers and antithetic pairs were not improvements.
3. An independently trained separable importance map, validated on fresh points:
   about 10% variance reduction in d=2; no material gain in d=3. It is VEGAS-
   inspired, not the full VEGAS+ implementation. Only fresh d2 A at L6 uses it.
4. Exact first-edge conditional stratification: no gain per kernel evaluation.
5. Dimension-coupled controls: a separate paired pilot and validation selected
   only the ten-primitive-graph block for further evaluation. Its fixed control
   coefficient comes from that pilot. The control reduced block variance, but
   the full error was not materially improved. No relation between the physical
   C6 values in different dimensions is assumed.

The literature comparison includes tropical integration, VEGAS+, shifted lattice
QMC/pySecDec and global primitive graph sampling. The full VEGAS+ and pySecDec
implementations were NOT benchmarked here. No universal optimal method is claimed.

## Main production and covariance

Fresh primary production comprises 782,893,056 kernel evaluations over loops
3, 4, 5 and 6 for both d=2 and d=3. Each dimension has two campaigns, each with 32
independent randomized nets per loop; point counts are powers of two within
individual graph strata. See inputs/frozen_production_plan.json. Another
34,144,256 d2 auxiliary evaluations replay d3 sample locations for the separate
primitive-control experiment. Method pilots and checks are excluded from the
reported estimator.

The new d2 calculation samples the 66 nonprimitive kernels formerly included in
the shared 76-kernel input. Ten primitive kernels are still retained. Old d2
streams omit all 76, fresh streams omit only ten. For equal campaign weights,
the additive mean is P10 + S66/2, and its covariance is
sigma(P10)^2 + sigma(S66)^2/4. It is included ONCE. The old four-point diagnostics
for excluded graphs are never included as real measurements. All loop-jet
coupling/mass/Taylor covariance is retained. No known C3-C5 value is fitted.

The two-dimensional kernel maps have endpoint roundoff below 8e-16; a same-point
replay with endpoints exactly normalized changes the six-loop mean by about
3e-13. This is a consistency check, not an integral enclosure. Frozen input
maps are supplied for exact replay rather than silently regenerated.

## Reassemble without any new integration

From this directory:

```sh
python code/analyze.py
python code/analyze_control.py
python code/summarize_methods.py
python code/extra_checks.py
python code/structural_checks.py
```

Requirements: Python 3, NumPy, SciPy, mpmath. Independent algebra/integrand checks
also use SymPy and NetworkX. baseline_previous/ contains the minimal previous
calculation tree as delivered, including raw old production replicates, graph
kernels, exact two-loop inputs and known-sector records.

- verification/method_precision_results.json: PRIMARY result, full covariance,
  fresh-only comparison, individual campaigns and diagnostics.
- verification/reported_values.json: rounded reporting convention separately.
- verification/method_benchmarks.json: sampling and runtime comparisons.
- verification/controlled_precision_result.json: auxiliary d3 control result.
- verification/cross_control_budget.json: why the block control is not a major
  improvement for the full coefficient.
- verification/extra_checks.json: independent finite Lagrange, replicate bootstrap
  and nonlinear-bias checks. The bootstrap is an approximate diagnostic.

## Rebuild and replay the integrator

Requires a C++17 compiler with OpenMP, libquadmath and Boost multiprecision:

```sh
bash code/build.sh
python code/check_kernels.py
python code/replay.py new_a 2 4 my_replay --replicates 2
```

A replay reads the shipped binary Sobol direction matrices; it does not rely on
a future SciPy internal direction-number implementation. Outputs are never
overwritten. Full production replay is possible but costly; omit --replicates
to replay a complete stream. Independently seeded fresh streams can be made
using code/driver.py's run function after defining new, frozen allocations.

code/produce.py and code/produce_cross_control.py document the original plans
but intentionally refuse to overwrite delivered production records. To generate
a new study, use new tags and new input/record filenames rather than overwriting
this evidence. Production flags used long double, not the optional fast-double
experiments present in the previous archive.

verification/production_source_hashes.json records the original kernel binaries,
source and frozen inputs. Rebuilding on another compiler/platform can change a
binary hash even with identical source; this is not by itself a mathematical
failure. Python path-only portability edits are retained alongside the original
runtime scripts in provenance/runtime_python/. provenance/setup_v1.py is an
historical prototype, NOT a generator for the final kernel.

The production log retains one launcher error (a missing Python import) that
occurred before any sampling. The corrected valid launch and all successful
production output are separately identifiable in the same log. No incomplete
stream or failed-run samples entered the result.

## Note and preserved history

long_range_ising_complete.tex/pdf is the updated full note. The new Appendix X
is on pages 195-202. C6_numerical_methods.tex/pdf is the eight-page standalone
method appendix with references. All 931 previous displayed mathematical blocks
are unchanged and in order; the new total is 950. Old numerical values remain
as history, while the abstract and Appendix X give the current result.

```sh
python code/make_note.py
bash code/compile_notes.sh
```

The actual integration is not rerun by note creation. Full PDF and layout checks
are recorded under verification/. The previous analytic power compensation is
retained, not rerun or given a new independent certification.
