# Precision refinement of C6(2) and C6(3)

This archive refines the full numerical coefficient in the existing long-range
Ising calculation, with epsilon = 2s - d. It does not rederive the common graph
inventory, the finite-forest subtraction, or the previously audited power-sector
compensation. The original note is retained under `provenance/previous_note.tex`.
The current values, estimated sampling errors and empirical reporting allowances
are in `verification/reported_values.json` and
`verification/precision_d[23]_prod_a_prod_b.json`.

The reporting allowance is four estimated sampling standard errors rounded
upward to 0.1 at d=2 and to 0.05 at d=3. It is an empirical numerical convention,
not a rigorous interval, a guaranteed confidence level, or an estimate of the
error in truncating the epsilon series. Extra digits in JSON outputs are not
certified physical digits.

## What is new

Each graph is a separate stratum with a frozen power-of-two sample count.
Independently randomized Sobol nets replace random graph selection and
independent point sampling. Two production campaigns, each with 64 independent
replicates at each of loops 3, 4, 5 and 6, use separate seeds and two exactly
equivalent maps for selecting a complete edge ordering. Campaign A uses
52-bit digital coordinates; B uses 60-bit coordinates. Their jet means are
combined with weights 1/2, 1/2, fixed before production. No lower physical
coefficient is imposed as a constraint or fitted control.

The two-dimensional 76-kernel contribution is retained once, with its common
sampling error 0.1373774929550988. Those graphs are not counted as independent
new measurements in the reported estimate. Raw minimal diagnostics for them
remain in the graph-level arrays but are excluded from final analysis. Full
old C6 estimates, pilots and validation runs are not included in the final
estimator. The earlier power-containing correction is retained, not rerun.

## Reassemble without running integrals

Requirements: Python 3, NumPy, SciPy, mpmath, SymPy and NetworkX. The final
analysis needs only NumPy and mpmath plus the shipped coefficient data.
Run these commands from the archive root:

```sh
python code/final_analysis.py
python code/extra_checks.py
python code/check_structure.py
```

The first command rebuilds the full physical coefficient from all raw production
replicate vectors, including beta/mass and epsilon-Taylor covariance. It never
fits to the known C3--C5 checks. The second performs an independent finite
Lagrange expansion and a replicate bootstrap (including the common d=2
input once per bootstrap). The third verifies the exact sector-order mapping
and the dimension-correct Gamma normalization.

## Rebuild the integrators and independent pointwise check

Requirements: C++17, GCC/OpenMP, libquadmath, Boost multiprecision headers.

```sh
sh code/build.sh
python code/check_kernels.py
```

Production uses long double, with binary128 and 300-decimal fallback when
cancellation triggers it. The optional `FAST_INITIAL` macro was a separate
same-point replay experiment; it is OFF in all production binaries built by
`build.sh`. Optional same-point experiment binaries can be built with
`sh code/build.sh --with-fast`; they are not used by the production driver.

The independent reference check constructs Kirchhoff cofactor determinants
rather than the integrator's spanning-tree monomial masks. It includes all
493 kernels (one two-loop control plus loops 3--6), in both dimensions, and
extreme endpoints. It does not certify an interval for the integrals.

## Reproduce or extend the production sampling

All actual settings are in `inputs/production_plan.json`; execution records and
individual manifest files supply the per-loop counts, seeds and elapsed times.
The full binary direction matrices are shipped, avoiding a dependence on a
future SciPy internal representation. To replay them directly, run
`python code/run_from_saved_inputs.py prod_a 2 6 fresh_replay`; this preserves
the shipped points rather than regenerating a new scramble. The driver additionally reconstructs
public SciPy points and checks them exactly whenever generating a new matrix.

```sh
python code/run_precision.py new_a --d 2 --loops 3,4,5,6 \
  --replicates 64 --budget 1048576 --seed 8017391 \
  --bits 52 --allocation production --rate 0.8 --encoding original
python code/run_precision.py new_b --d 3 --loops 3,4,5,6 \
  --replicates 64 --budget 1048576 --seed 9099113 \
  --bits 60 --allocation production --rate 0.8 --encoding single
```

These examples give the same nominal budget to every loop; the delivered
production plan instead allocates smaller budgets to lower loops. A fresh tag
is required: the driver refuses to overwrite an existing output. The final
analysis script by default expects the two delivered `prod_a` and `prod_b`
tags; it also accepts two new full campaign tags as command-line arguments.
Never add new streams without accounting for any shared retained input.

Both the ordinary edge-order map and the compressed one-coordinate map
implement the identical normalized Hepp-sector importance distribution.
The integer coordinate is converted to a midpoint before logarithms. Variation
of bit depth checks but does not rigorously bound digital discretization bias.

## Files

- `long_range_ising_complete.tex/pdf`: complete updated scientific note.
- `C6_d2_d3_precision.tex/pdf`: standalone precision appendix.
- `C6_precision_appendix.tex`: the exact addition to the full source.
- `records/prod_[ab]_d[23]_L[3-6].json`: full independent replicate vectors,
  graph-level contributions, counts and arithmetic fallback records.
- `inputs/production_*`: frozen allocations and campaign plan.
- `inputs/*_net.bin`: the actual randomized direction matrices.
- `records/pilot_*`, `records/validation_*`, `records/sector_test_*`: allocation
  training and validation only, excluded from the final coefficients.
- `baseline/`: the minimal retained graph, normalization and subtraction inputs,
  plus the previous power-sector/result audits. Unrelated historical code and
  historical full PDFs are not duplicated.
- `verification/`: all new comparisons, statistical checks and source audit.
- `source.diff`, `provenance/previous_note.tex`: preservation evidence.

## Rebuild the note

```sh
python code/make_note.py
pdflatex -interaction=nonstopmode -halt-on-error long_range_ising_complete.tex
pdflatex -interaction=nonstopmode -halt-on-error long_range_ising_complete.tex
pdflatex -interaction=nonstopmode -halt-on-error C6_d2_d3_precision.tex
pdflatex -interaction=nonstopmode -halt-on-error C6_d2_d3_precision.tex
```

Source creation is local and deterministic given the saved results. It does
not execute integrations. Every previous displayed mathematical block remains
verbatim and in order. Historical numerical values are retained as history;
the new appendix and abstract state the current precision.
