# 3D dressed Hamiltonian truncation with a consistent vacuum window

This is a **new direct 3D computation**, porting the agreed 1D/2D prescription to
spherical oscillators: total bath-level truncation, dressed zero mode, original
Gaussian normal ordering, the full self-consistent vacuum window, and optional
state-averaged local functions. Standard dense/ARPACK eigensolvers are retained.
There is no selected-tail solver, angular buffer, fitted energy scale, kinetic
counterterm, individual-mode UV parent, or cutoff-tail fit.

Read `REPORT.md` for the measured curve and its limitations; `docs/METHOD.md` gives
the mode, angular, window, and local-basis conventions. The window is an explicitly
defined approximation, not a proved complete physical effective Hamiltonian.

## Directory map

```
code/ht3d/          spherical basis/vertices, local projection, window, solver, diagnostics
code/run.py        one restartable numerical point (same entry as hpc_run.py)
code/hpc_run.py     single-node scalar solve plus optional angular diagnostics
campaign.py        complete three-cutoff scan, raw replays, and nested local checks
refinement.py      selected L=12 points and independently enlarged local spaces
analyze.py         checksummed saved results -> tables, no continuum fits
plot.py            measured curves, endpoint drift, and candidate descendant plot
inputs/            old raw couplings/data used as seeds; independent benchmarks
results/curve/     52 accepted window curve records, including 15 teacher artifacts
results/raw/       15 new raw L=10 replay spectra
results/local/     15 nested-size checks and four independent local refinements
results/probes/    initial probes/replays, separate from the 86-record main inventory
results/tables/    curve, comparison, local tests, candidates, and benchmarks
results/benchmarks/operator-only performance measurements
results/logs/      scan/refinement command journals and logs
validation/        actual tests, numerical checks, provenance and limitations
benchmarks/        separate original/tensor/Gram operator comparison programs
tests/             independent matrix, symmetry, window, offline workflow tests
cluster/           frozen independent Slurm-array requests; not an MPI eigensolver
reference/         original 3D oracle, source inputs, and selected port templates
```

All reported local counts are **per field parity**. The spacetime dimension is 3;
`dimension` inside result JSONs means the combined scalar matrix dimension, whereas
`spacetime_dimension` is the physical dimension.

## Dependencies and precision

Python 3.10+, NumPy, SciPy, Numba, threadpoolctl, SymPy (independent exact shell
tests), pytest, and Matplotlib. Exact tested versions are in
`validation/ENVIRONMENT.json`. All Hamiltonian calculations use float64. There is
no fast-math, precision reduction, amplitude pruning or perturbative particle cap.

```
python -m pip install -r requirements.txt
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
export OMP_NUM_THREADS=1
export NUMBA_NUM_THREADS=4
export MPLBACKEND=Agg
export MPLCONFIGDIR="$PWD/.mplconfig"
```

The Numba maximum must allow four threads for tests explicitly comparing one and
four. Individual scan processes used one thread; parameter points were run in
separate processes. Scan timings are not isolated speed benchmarks.

## Verify the supplied results

Verify the immutable distribution first. Some scripts intentionally regenerate
validation records or tables, so use a writable working copy afterward.

```
python tests/verify_manifest.py
python -m pytest tests/test_port.py tests/test_hpc.py -q
python tests/validate_physics.py
python tests/validate_numerics.py
python tests/validate_saved.py
python analyze.py
python plot.py
```

The first pytest command runs 27 cases. `validate_physics.py` checks the covariance,
rotations, exact second-order shell sum, and original normal ordering through an
independent oracle. `validate_numerics.py` compares larger original/tensor/Gram
matrices and weak-coupling spectra. `validate_saved.py` checks every complete main
record and all auxiliary comparisons without requiring physical Ward errors to
vanish. None of these is a target-cluster validation receipt.

## Run a point and train a basis

The intended interacting scan is approximately 0.518148806 < x < 0.75. The operator
positivity guard is the wider x>0.5, not an assertion of physical criticality below
the short-range crossover. Only the primary gaps x and 3-x are tuned.

```
# Learn local functions at a small bath cutoff. The thermal state is not a target.
python code/run.py --L 6 --x .6 --nz 24 --osc 192 \
  --window vacuum --window-mode consistent --train-keep 20 \
  --diagnostics first --backend tensor --threads 1 \
  --output reproduced/teacher_x06.json

# Continue first to L=8, then L=10; every new vacuum and both couplings are recomputed.
python code/run.py --L 8 --x .6 --nz 16 --window vacuum \
  --basis reproduced/teacher_x06.json --seed reproduced/teacher_x06.json \
  --diagnostics all --backend tensor --threads 1 \
  --output reproduced/window_L8_x06.json --resume

python code/run.py --L 10 --x .6 --nz 16 --window vacuum \
  --basis reproduced/teacher_x06.json --seed reproduced/window_L8_x06.json \
  --diagnostics all --backend tensor --threads 1 \
  --output reproduced/window_L10_x06.json --resume

# Independent raw comparison in the original 3D convention.
python code/run.py --L 10 --x .6 --nz 20 --osc 160 --window none \
  --diagnostics first --output reproduced/raw_L10_x06.json
```

A keep20 artifact supports nested nz12/16/20. It does not support nz24. A basis
fixes its primitive scale/auxiliary dimension and x. Two-dimensional artifacts,
cross-x reuse, and requests exceeding its retained capacity are rejected.
Increasing the teacher/auxiliary dimensions requires new training. The embedded
artifact in every optimized result is retained for audit.

`--diagnostics first` checks six roots in spin one; `all` adds spin two and mixed
scalar trace candidates. Omitting diagnostics does not change scalar tuning, but
it does not count as a complete spectral check. Candidate assignments are flagged
when their free-translation overlap is below 0.5 or a trace selects the primary
itself. No candidate is forced to have integer spacing.

## Reproduce the complete scan

The root drivers use the supplied `results/` location. To recompute rather than
reuse the shipped records, make a fresh working copy and move `results/` aside:

```
mv results published_results
mkdir -p results/curve results/raw results/local results/logs results/benchmarks
python campaign.py --workers 2
python refinement.py --workers 1
python benchmarks/run.py
python analyze.py
python plot.py
```

The 15-point grid is .7499, .745, .74, .725, .7, .675, .65, .625, .6, .575, .55,
.535, .525, .52, .5182. Each point has an L6 teacher24/192 (keep20), L8 and L10
window density16, L10 density12, and L10 raw20/160. Seven points have window L12.
At x=.6 and .5182 there are additional independent moving-local L10(32/256) and
L12(24/224) checks. Default seeds come from the included old raw 3D calculation;
thermal dimensions and endpoint numbers never determine a solve.

Historical output records bind their original source hashes, input byte hashes,
paths and runtime. The final auto-backend policy was clarified after the scan;
it leaves every saved L<=12 calculation on the same tensor path. This change is
recorded in `validation/final_source_changes.json`, not hidden by rewriting the
old records. `tests/validate_saved.py` audits their internal identities. Reuse
through the CLI is intentionally stricter: a different path/runtime/source or
configuration gets a new output, not an incompatible old completion.

## Performance and large cutoffs

The ranked spherical Fock graph is numeric and avoids the old all-state tuple
list/dictionary. Angular projection nevertheless requires species blocks and
nullspaces, which remain a cost. Four exact projected bath vertices are retained
in the default tensor backend and applied with compiled sparse/local contractions.

Unlike 2D, the quadrature-expanded `gram` backend was **much slower and larger**
at the measured L10/12 sizes. It is available for correctness/comparison tests,
not selected by `auto`. In 3D, auto now means tensor at all sizes. There is no
claimed optimal automatic crossover beyond the measured range.

At L12 the measured one-/four-thread tensor applications are about 2.63/1.29 ms.
This is operator-only timing. Complete-window speedups against the old raw 3D
solver are not claimed: they are different physical prescriptions. The default
basis-state and memory limits reject oversized problems instead of silently
lowering caps. The RSS estimate is heuristic; monitor actual peaks on the target
cluster. A single ARPACK problem remains on one node.

## Restart, safety and deployment

`--resume` accepts only identical requests and complete checksummed results or a
compatible Newton-boundary checkpoint. Couplings are checkpointed; every window
is solved again after restart. SIGUSR1/TERM/INT request a stop at a safe boundary,
not inside an active LAPACK/ARPACK call. Exit 75 is a checkpointed stop, 73 means
another owner holds the output claim. A hard crash leaves a claim **fail closed**.
Verify the owner job/process is dead before offline removal; do not delete live
claims. The array wrapper freezes input contents and code hashes in addition to
paths. There is no online distributed lease reclamation in this research port.

See `cluster/README.md` for target-site validation and independent Slurm arrays.
The code has not been submitted to symmetry, does not inherit a 1D validation
receipt, and does not distribute one eigenproblem across nodes. Obtain a new
review and site tests before a large production campaign.

## Interpretation

The curve is a sequence of finite-window prescriptions, not a controlled physical
continuum band. The near-SRI sequence rises through the known endpoint value and
continues upward. Some first-descendant candidates improve dramatically, but
several assignments become ambiguous and scalar traces remain problematic. Small
local/eigenvalue residuals do not remove these physical issues. This release does
not compute new C4-C6, fit cutoff tails, or determine precision OPE coefficients.
