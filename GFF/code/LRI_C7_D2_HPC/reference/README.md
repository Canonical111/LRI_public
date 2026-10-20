# Full numerical C_7(2): local mass subtraction completion

## Current result

Convention: epsilon = 2s - 2, and Delta_E = 1 - epsilon/2 + gamma_r(g_*, epsilon).

**Full coefficient: C_7(2) = -3950 +/- 310.**

The underlying estimator is **-3953.6336215335396**, with estimated sampling
standard error **76.73103617126334**. The +/-310 is an empirical reporting
allowance: four estimated sampling errors rounded upward (and checked against
half-stream displacement). It is NOT a rigorous interval, a probability
guarantee, or a bound on common errors in the graph/renormalization framework.
Extra digits are for reassembly, not certified physical digits.

This completes the previously missing power-containing correction:

| Component | Estimate | Sampling standard error |
|---|---:|---:|
| Retained power-free coefficient | -3955.3837529230477 | 76.54167996471732 |
| Newly evaluated complete power correction | +1.7501313895081694 | 5.424390147737399 |
| Full coefficient | -3953.6336215335396 | 76.73103617126334 |

The correction is **measured**, not set to zero. Its covariance with the
power-free input is retained. The primitive contribution was already included
in the power-free result; it must not be added a second time.

## What was changed

The old Gamma/kite master routing did not close for 105 seven-loop power
classes. This calculation bypasses that routing. It combines local zero-momentum
subtractions of self-energy insertions with the logarithmic forest terms before
integration. Every nonzero kernel is then integrated directly.

For a compatible mixed forest F, let U_F be the product of the contracted block
Symanzik polynomials. Its numerator is the sum of root-edge parameters after
removing selected LOGARITHMIC blocks only. Selected POWER blocks affect U_F
but do not remove their interaction order from the root amplitude. This
root-weight distinction is essential. See `notes/C7_d2_complete.pdf` for the
construction, normalization, example, and independent checks.

Regulator jets are retained through z^(7-L), at every loop L. Full and
power-free jets are combined in one finite zero-momentum prescription, not by
mixing their constant terms with an MS formula. The fixed point is solved only
after setting z = epsilon in the complete finite jets.

An earlier radial-IBP-only experiment did not implement the required local mass
subtraction and produced divergent regulator derivatives. It was rejected.
Neither those samples nor any pilot samples enter this result.

## Coverage

All 3986 seven-loop graph classes are assigned exactly once:

- 459 zero channel weights;
- 639 exact mixed-forest kernel zeros at nonzero channel weight;
- 44 retained primitive classes;
- 2254 retained power-free nonprimitive classes;
- 590 newly integrated power-containing classes.

There are 1091 power-containing classes. The new mixed kernels are nonzero in
709 of them; 119 of these have zero seventh-order channel weight. The 590
remaining classes, and all required lower-loop coupling/mass jets, are covered.
An independent enumeration over *all edge subgraphs*, not just induced vertex
subgraphs, agrees exactly in all 1301 power-containing classes at loops 3--7
(672192 forest terms before collection).

## Files

- `notes/C7_d2_complete.tex`, `.pdf`: new eight-page full-calculation note.
- `verification/C7_full_result.json`: authoritative result, full covariance,
  component/campaign/error budgets, bootstrap, coverage and input hashes.
- `power_mass/code/`: new builder, native worker, independent forest/point checks,
  frozen allocation, production generator and full statistical assembly.
- `power_mass/inputs/`: all new kernels, inventories, independent Sobol nets and
  the pilot-frozen allocation.
- `power_mass/records/`: raw powerA/powerB productions and excluded, labelled pilots.
- `power_mass/verification/`: exact maps, radial three-loop reference,
  high-precision checks, and production audit.
- `LRI_C7_d2_progress/`: original progress package, with its previous power-free
  and primitive production data, source and note preserved. Its old `null` full
  result is historical and is superseded by the new top-level result.
- `code/reproduce.py`: non-destructive saved-data reassembly and checksums.
- `SHA256SUMS`: SHA-256 of every delivered payload file except this manifest itself.

All earlier C_0--C_6 results are unchanged. The less precise lower-order values
from the present production are checks, not replacements for the retained
special-function and numerical results.

## Numerical design

Two new campaigns use independent seeds and Sobol scramblings, each with 16
replicates per loop. Importance rate multipliers are 0.8 and 0.9. Graph sample
counts were selected from a separate pilot using projected C_7 variance and
cost, then rounded upward to complete power-of-two nets. The new production
uses **25,407,488** kernel evaluations over loops 3--7. Previous power-free and
primitive data are reused rather than rerun.

Covariances retain coupling/mass and regulator-order correlations. The original
power-free input and retained primitive error are shared inputs, not independent
copies in each new campaign. Four thousand ninety-six independent replicate
bootstrap resamples give a full standard error of 75.64234, compared with
76.73104 from covariance propagation. Lower-order reference values and zero
power-correction identities were NOT fitted or imposed as constraints.

Arithmetic is unchanged: long double with >=64 significant binary bits,
GNU binary128 fallback at cancellation threshold 1e-9, Boost 300-decimal
fallback at 1e-23, compensated accumulation, no fast-math.

## Reassemble without running integrations

From this directory, with Python 3.10+ and the dependencies installed:

```bash
python3 -m pip install -r requirements.txt
python3 code/reproduce.py
```

This verifies file hashes, constructs a temporary reassembly tree, recomputes
means/covariances/bootstrap from the old and new raw streams, and compares with
the recorded full result. It does not overwrite the delivery or run new graph
integrations. Reproduction tolerances are stated in the script; floating-point
library/platform changes can affect final rounding bits.

## Rebuild native programs and repeat checks

Requires a GNU C++17 compiler, OpenMP, libquadmath, Boost headers, and a platform
whose long double has >=64 significant bits. No fast-math is allowed.

```bash
make -j4
make checks
```

The exact-check targets write to a new directory under `checks_output/`, leaving
recorded verification files unchanged. `make note` recompiles the TeX source;
LaTeX is not needed for numerical reassembly.

## Rerun integrations deliberately

The supplied plan and independent nets determine the production sample identities.
The production script refuses to overwrite an existing result. To replay the
same experiment, use a *separate copy* of this bundle, move its
`power_mass/records/` aside, create an empty replacement, then run:

```bash
python3 power_mass/code/run_production.py
python3 power_mass/code/assemble_full.py --bootstrap 4096
```

To run genuinely new statistics, first change seeds/replicates and freeze a new
allocation; retain complete nets and independent replicate covariance. Do not
merge execution chunks as though they were independent Sobol replicates.

## Evidence boundary

This is a complete numerical evaluation within the project's common graph
inventory and finite-renormalization construction. It is not an independently
certified seven-loop field-theory calculation or a proof that the seventh-order
power correction is zero. The largest sampling uncertainty is still the retained
power-free seven-loop sector. That sector, rather than the now-small power
correction uncertainty, should be targeted first for greater precision.
