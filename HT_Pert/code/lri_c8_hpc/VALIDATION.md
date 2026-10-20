# Validation of the optimized C8 implementation

## What is unchanged

The frozen energy cutoff N+P/4<=Lambda, the full eighth-order support P<=19,Q<=16,
normal ordering, the sphere parity projection after complete vertices, the two
primary-gap conditions and float64 precision are unchanged. `vacuum_only` retains
exactly the original isolated g(epsilon)^2 D(epsilon), not Dconn. The implementation
changes the evaluation of the same coefficients; it does not change the physical
renormalization prescription or improve the continuum extrapolation.

## Completed local tests

`benchmarks/VALIDATION_RECEIPT.json` records a successful **39-test suite**. The
receipt fingerprints `src/lri_c8/`. It is local evidence, not a compute-node or
Expanse acceptance receipt. Tests cover:

- Independent original-SciPy full eighth-order recursion at cutoffs 2,4,6,8,12,
  for both raw and vacuum-only prescriptions.
- Saved exact-rational coefficients and a freshly executed rational calculation
  at cutoff 4.
- Packed vertices against original full vectors for both field parities; physical
  reflection projection occurs only at the end of the complete vertex.
- Exact core/full rank embedding, state counts and edge counts.
- Stored and on-demand ranked outer operators, one-/two-thread agreement, actual
  int64-index kernels on small allocated arrays. No billion-state run is implied.
- Complete independent-reference assembly against an ordinary four-reference run.
- Numerical gates, bad cutoff/cap/input rejection, and memory guards.
- Checksum corruption, incompatible configuration/source rejection, CLI run/resume,
  assembled results and legacy-format export.
- Scalar checkpoint recovery, safe-boundary stopping, completed-checkpoint finalization
  without basis allocation, exclusive solver-owned claims, and a supervisor killed
  while the numerical child continues to own its lock.
- Local frozen-campaign manifest and lane-driver integration.

## Full saved-grid replay

All **38** supplied C8 records were replayed: 25 raw even cutoffs 2..50 and 13
vacuum-only cutoffs through 50. No supplied inputs were changed. The maximum absolute
differences from those saved arrays are:

| Array | Maximum absolute difference |
|---|---:|
| `C` | 2.095475793e-08 |
| `r` | 8.833012544e-09 |
| `g` | 3.597233444e-08 |
| `energies` | 1.885928214e-08 |

Thus the largest checked coefficient or coupling difference is about 3.60e-8.
`benchmarks/REGRESSION_GRID.json` retains every comparison and diagnostic. The
reported decimal differences are not bounds for an arbitrary larger calculation.

Regression comparisons use

    abs(new-reference) <= 1e-7 + 2e-11*abs(reference).

This permits floating-point regrouping from the residual formula and parity-packed
reductions. No fastmath or precision reduction is used. The numerical gates are
independent C2 shell residual <=1e-10, low-order residual <=1e-7, and final tuning
residual <=1e-6, plus finite arrays and metadata checks. Passing those checks does
not certify the new C8 coefficient independently at every larger cutoff.

## Benchmark correctness

Every repeated benchmark point through cutoff 50 compares all energy, coupling,
and thermal arrays with the appropriate supplied reference. The raw cutoff-56
capacity run passes its internal gates, but no saved cutoff-56 C8 existed to
supply an independent reference comparison.

## Remaining validation responsibilities

Before production on a cluster, regenerate the validation receipt with its actual
CPU, threading layer, BLAS/LAPACK, Python and compiler environment, and replay larger
reference points. Calibrate memory and threading separately. Cross-platform bitwise
equality is not claimed. Test the local filesystem's lock/rename semantics and the
scheduler's signal policy before relying on long-running checkpoints.

None of these implementation checks measures the missing physical matching or
cutoff-extrapolation error. The symbolic residual identity is exact for the stated
finite-dimensional Hamiltonian and perturbative support; it is not a determination
of a physical continuum C8.

## Fresh-extraction check

After creating the release archive, it was extracted to a separate directory. All
152 then-manifest-listed files passed SHA-256 verification, and all 39 tests passed
again there. `benchmarks/FRESH_VALIDATION_RECEIPT.json` records this separate run.
This final receipt and documentation are included in the rebuilt manifest; the
validated numerical source fingerprint is unchanged.

## Symmetry defq port (2026-10-03)

The deployment layer was changed for symmetry `defq` (see `docs/SYMMETRY.md`): batch
scripts, environment, validation receipt, campaign manifest, lane supervisor, owner
files, export signature, threadpoolctl guards and a residual support assertion. The
source digest therefore differs from the one in `benchmarks/*RECEIPT.json` and
`BUILD_INFO.json`, which document the original local build only. Local checks of the
port, before any cluster run:

- 55 tests pass on an emulated symmetry stack (Python 3.11.4, numpy 1.24.3, numba
  0.57.0, scipy 1.10.1, threadpoolctl 2.2.0), on pip wheels with threadpoolctl 2.2.0
  and suffixed OpenBLAS (which crashed the unguarded original), and on Python 3.13 /
  numpy 2.3.5 / numba 0.65.1; each with a fresh Numba cache.
- C, r, g, energies and every F/M/V/K component are bitwise identical to the original
  source at L=20, 28, 40, 44 (raw and vacuum_only, stored and ranked).
- The 38-point saved-grid replay reproduces every C8 of `benchmarks/REGRESSION_GRID.json`
  bitwise on the emulated stack; the original solver agrees at L=24 within atol 1e-7.

The binding evidence is the compute-node receipt written by `slurm/submit_defq.sh validate`.
