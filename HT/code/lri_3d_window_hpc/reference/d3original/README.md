# Direct nonperturbative 3D long-range Ising curve

This package extends the previous dressed-circle calculation to S^2 using the
correct generalized-free radial and angular modes. It computes finite-cutoff
thermal gaps directly, not by evaluating the epsilon series. It is a **research
prototype**, not a complete physical effective Hamiltonian or an MPI/HPC release.

## Scope and completed work

- 80 primary scan points: bath levels L=4,6,8,10,12, on the common 16-point x grid
  from 0.5182 through 0.7499, where x=Delta_sigma.
- Eight independent local-basis refinements, to 28 dressed states per parity
  and 224 auxiliary oscillator functions.
- Untuned spin-one and spin-two diagnostics at six x values, for L=8 and 10.
- Independent angular, normal-ordering, free-endpoint and Jacobian tests.
- Independent rational second-order shell coefficients and a continuum integral.
- Twelve weak-limit spectral checks at L=4,6,8 and epsilon=.02,.01,.005,.002.

The two tuning conditions are E_sigma-E0=x and E_chi-E0=3-x. Delta_E is the
untuned first excited even scalar gap. Known thermal coefficients and both
endpoint benchmarks are comparisons only.

**Main caveat:** the numerical eigenproblems are well converged, but the raw
product-regulator Hamiltonian has substantial untuned descendant discrepancies.
No continuum curve, matching completion, or physical uncertainty band is claimed.

## Layout

```
code/d3dressed/   spherical Fock basis, rotational projection, vertices, solver
code/scan.py     direct curve driver with per-point atomic JSON and resume gates
code/diagnostics.py  untuned rotational-sector calculations
code/check_second_order.py  independent exact rational oscillator-shell sums
code/second_order_analysis.py  shell table and continuum integral
code/analyze.py  verifies accepted records and builds CSV/tables/summary
code/plot.py     generates all three figures from saved records
inputs/         published benchmark values (never thermal tuning inputs)
results/L*/     accepted primary point records, including spectra and couplings
results/refine_L*/  independently refined local basis calculations
results/        validation records, weak tests, diagnostics, combined CSV
figures/        finite-cutoff curve, untuned errors, second-order comparison
texts: REPORT.md and docs/METHOD.md
```

The `delta` key and legacy CLI option `--deltas` denote **x=Delta_sigma**, not
epsilon or 1-s. Each output also records s=3-2x and epsilon=3-4x explicitly.

## Dependencies

Python 3.10 or newer; NumPy, SciPy, mpmath, Matplotlib. The tested runtime is
recorded in `results/ENVIRONMENT.json`. NumPy/SciPy version or BLAS changes can
alter last digits and iteration counts. No reduced physical precision is used.

```
python -m pip install -r requirements.txt
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
export OMP_NUM_THREADS=1
export MPLBACKEND=Agg
export MPLCONFIGDIR="$PWD/.mplconfig"
```

Each point is independent after providing a root seed. Continuation is used for
speed but supplies no thermal target. Separate processes can distribute cutoffs
or parameter subsets. This prototype has no reviewed cluster dispatcher, solver
lock layer, single-point MPI solver, or checkpoint inside an eigenvalue solve.
Do not launch concurrent writers to the same output item.

## Recreate figures and tables without rerunning spectra

```
python tests/verify_manifest.py
python code/analyze.py
python code/plot.py
```

`analyze.py` rejects incompatible numerical-source fingerprints and failed gates.
`results/curve_points.csv` includes all primary and refinement points; the
`group` column identifies them. Plots show only actual completed points. The
bootstrap endpoint is marked separately and is not inserted into the numerical
curves.

## Reproduce the validation

```
python tests/validate.py
python tests/validate_response.py
python tests/weak_limit.py
python code/second_order_analysis.py
```

`validate.py` tests the spherical covariance against Gegenbauer polynomials,
quadrature refinement, rotational matrix equivalence at different M, original
normal ordering, Hermiticity, and second-order matrix versus rational shell sums.
`validate_response.py` compares the moving-subspace Jacobian with independent
full spectral differences and checks the Gaussian endpoint. No source C2 is
used in either side of the finite-cutoff matrix/shell comparison.

## Reproduce a main scan

```
python code/scan.py --bath-cut 8 --nz 20 --osc 160 \
  --root-tol 2e-11 --output-dir reproduced/L8 --resume
```

The default grid is

```
.7499 .749 .745 .74 .725 .7 .675 .65 .625 .6 .575 .55 .535 .525 .52 .5182
```

The release uses (nz,osc)=(16,128) at L=4 and (20,160) at L=6,8,10,12. To rerun
larger cases using saved coupling seeds (not saved thermal answers):

```
python code/scan.py --bath-cut 12 --nz 20 --osc 160 \
  --seed-dir results --root-tol 2e-11 \
  --output-dir reproduced/L12 --resume
```

To reproduce selected local refinements:

```
python code/scan.py --bath-cut 12 --nz 28 --osc 224 \
  --deltas .7 .6 .5182 --seed-dir results --root-tol 2e-11 \
  --output-dir reproduced/refine_L12 --resume
```

To reproduce untuned angular tests:

```
python code/diagnostics.py --inputs results/L10 \
  --deltas .745 .7 .65 .6 .55 .5182 --spins 1 2 \
  --output reproduced/diagnostics_L10.json
```

The thermal/descendant role of levels is assigned by weak-coupling continuation.
This is not a complete operator identification at strong coupling.

## Cutoff and implementation details

The sphere mode labels are (radial n,ell,m), with energy x+2n+ell and squared
weight `(x)_(n+ell)*(x-1/2)_n/(n!*(3/2)_(n+ell))`. All positive-level Fock states
with N<=L are enumerated, without an additional particle cap. Scalar states are
true SO(3) singlets, not just M=0 occupations. Intermediate ladders keep all M.

The bath bounds and dressed local bounds define a **product regulator**, not
N+3P/4. Existing frozen-energy vacuum-window shifts are not inserted. Both this
regulator and the 2D product regulator require their own high-state analysis.

The basis guard permits at most 400,000 full bath states (L=12 has 341,241).
The L=12 scalar bath has 1,285 states; with nz=20 the pair of field-parity
matrices has 51,400 states, or 71,960 at nz=28. The implementation uses explicit
bath vertices and dense local blocks with matrix-free global actions. A larger
cutoff needs new memory/performance assessment; raising the guard is not a
validated HPC scaling strategy.

## Reproducibility and provenance

`MANIFEST.sha256` covers the release files. Accepted point JSONs additionally
record a SHA-256 of `code/d3dressed/*.py`, the Python version, root history,
spectral and rotational residuals, couplings, local/bath edge weights, and
cutoffs. Edge weights are warning diagnostics, not error estimators. Timing
fields are observations of local processes and do not support cluster-speed
claims.

`local.py` and the spectral/tuning scaffold were adapted from the earlier
user-conversation package `lri_2d_nonperturbative_curve.zip`. The spherical
basis, SO(3) projection and integration, new shell checks, and 3D results were
implemented for this release. No earlier 1D/2D output is relabelled as 3D data.

No fitted continuum extrapolation or unseen high-cutoff result is included.
The modest finite-cutoff thermal discrepancy near the endpoint must be read
alongside the substantially larger untuned spin-one and spin-two discrepancies.
