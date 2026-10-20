# Complete numerical C6(3), long-range Ising epsilon expansion

Regulator: epsilon = 2s - 3. Physical coefficient:

**C6(3) = 33.5 +/- 0.6 (empirical numerical allowance).**

The raw pooled estimate is 33.50373572295422; propagated sampling standard
error is 0.1308545241856961. The empirical allowance is not a rigorous
interval, an epsilon-series truncation estimate, or protection against
shared field-theory implementation errors.

## Scope

This archive extends the previously supplied two-dimensional finite-forest
calculation to d=3. It contains new dimension-corrected sampling, three
production runs at each of loops 3--6, independently recomputed two-loop
jets, and a complete MS correction for the power-containing graph target.
The latter is negligible after assembly. Two unknown four-loop core
coefficients cancel **exactly** in the required five/six-loop combination;
they have not been numerically evaluated. Trial assignments to them are
not physical values of individual MS beta/mass sums.

The prior graph inventory and proven master Taylor reductions are reused.
No lower-order physical coefficient, Padé prediction, or C6 from another
dimension was fitted into the production estimator. No omitted graph
remainder is appended to the reported C6(3).

## Documents and data

- `long_range_ising_complete.tex/pdf`: updated full note, Appendix V.
- `C6_d3_complete.tex/pdf`: standalone new calculation and references.
- `C6_d3_appendix.tex`: insertion used in the full source.
- `verification/C6_d3_result.json`: reported result and covariance.
- `records/prod_[abc]_L[3-6].json`: raw independent batch vectors and diagnostics.
- `records/*manifest.json`: actual seeds, settings, and recorded execution times.
  Absolute working paths in these historical command logs document the run;
  use the relative commands below for a relocated copy.
- `records/power_ms_d3_complete.json` and `power_ms_d3_shifted.json`: 75/90 digit
  graph-recursion audits with different trial core assignments.
- `records/correction_power_*.json`: assignment-independent physical correction.
- `inputs/`: graph inventory, forest kernels, sampling exponents, graph allocations.
- `vendor/`: small retained graph-reduction/parser dependencies, copied from
  the preceding supplied calculation, not external packages.
- `provenance/previous_note.tex`, `source.diff`,
  `verification/source_preservation.json`: previous-source preservation.

## Reproduce the final coefficient without running integrals

Requirements: Python 3, numpy, mpmath, sympy, networkx. No network access is
needed after these packages have been installed.

From the archive directory:

```sh
python code/final_analysis.py
python code/check_mom_d3.py
python code/check_unknown_core.py
python code/check_coverage.py
python code/check_gamma_d3.py
```

The first command reconstructs the full coefficient from the shipped batch
arrays using **fixed sample-count weights (0.4,0.4,0.2)** on RG-jet means.
All within-loop beta/mass and Taylor-jet covariance is retained. Independent
loop streams have separate seeds. Known C3--C5 values are comparisons only.
The output is written to `records/C6_d3_result.json`; the copy under
`verification/` records the delivered run. Pilots are not production data.

## Build and run a fresh production stream

C++ requirements: GCC with C++17, OpenMP, libquadmath and Boost headers.

```sh
sh code/build.sh
python code/run_batch.py new_a --samples 16384000 --seed 20260914 --rate 0.8 --allocation refined
python code/run_batch.py new_b --samples 16384000 --seed 740611   --rate 1.0 --allocation refined
python code/run_batch.py new_c --samples 8192000  --seed 922701   --rate 0.8 --allocation target
```

Every command runs loops 3,4,5,6 separately, each with the indicated sample
count, split into 128 batches. `run_batch.py` supplies the dimension-correct
Gamma configuration automatically. Four threads are requested. It refuses
to overwrite existing output files. The actual loop seed is
`base_seed + 2191*L`; each batch then uses the documented sampler offset.
The graphs, density parameters, and allocation files are identical to the
ones used for the delivered results. New platform/library arithmetic may
change insignificant last digits; statistically independent changes should
be compared using sampling uncertainty, not bit-for-bit equality.

The final shipped emergency fallback uses 300 decimal digits. Initial
production used a 100-digit emergency fallback but never called it: all
production `mp_fallbacks` fields are zero. A constructed 10^-120 endpoint
exposed relative cancellation beyond 100 digits; that branch was fixed,
the extreme test rerun, and two same-seed 128000-sample runs compared
batch-for-batch. See `precision_replay.json` and both kernel-check records.
The change does not change any delivered production batch. Quad-precision
fallbacks did occur and are part of the independent pointwise checks.

## Reproduce the analytic power-target audit

```sh
POWER_DPS=75 CORE_U0=0 CORE_U1=0 POWER_OUTPUT=power_replay_75.json python code/power_ms_d3.py
python code/analyze_power.py power_replay_75.json
POWER_DPS=90 CORE_U0=101 CORE_U1=-37 POWER_OUTPUT=power_replay_90.json python code/power_ms_d3.py
python code/analyze_power.py power_replay_90.json
python code/check_core_propagation.py
python code/power_assembly_polynomial.py
```

The audit uses explicit Gamma convolutions and the A/B/T kite Taylor
formulas proved earlier in the note. It rejects unsupported orders. All
31 fifth-loop power classes and all 121 sixth-loop power classes with
nonzero target weight are included. The other 52 sixth-loop power classes
have exactly zero weight `3wB-wA`; this exclusion is checked rationally.
The two non-power fourth-loop reductions rejected by the coordinate tool
are supplied by the finite forest computation, not omitted contributions.

For the extra arbitrary-master consistency check, use
`POWER_Q=7 POWER_P4=11 POWER_KAP=5 POWER_Z=13 CORE_U0=-17 CORE_U1=29` at
65 digits, and pass the same `POWER_Q,POWER_P4` to `analyze_power.py`.
This is an algebraic consistency test, not physical master evaluation.

## Independent numerical and algebraic checks

```sh
python code/check_kernels_d3.py
python code/two_loop_d3.py
```

`check_kernels_d3.py` requires `build.sh` first. Its reference uses direct
Kirchhoff cofactor determinants, not the sampler's monomial masks. Tests
include all 493 kernels and 51 extreme configurations, with 70/650 digit
references. Numerical endpoint valuation files guide proposal choices;
they are not rigorous mathematical error bounds.

## Rebuild documents

```sh
python code/update_note.py
pdflatex -interaction=nonstopmode -halt-on-error long_range_ising_complete.tex
pdflatex -interaction=nonstopmode -halt-on-error long_range_ising_complete.tex
pdflatex -interaction=nonstopmode -halt-on-error C6_d3_complete.tex
pdflatex -interaction=nonstopmode -halt-on-error C6_d3_complete.tex
```

The included TeX sources use standard AMS/LaTeX fonts; no font files are
included. The prior displayed mathematical blocks are preserved verbatim
and in order. The new result is numerical, not a proposed symbolic C6(d).
