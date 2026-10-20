# Spin–boson NRG: compatibility-first HPC optimization

This package optimizes the spin–boson solver supplied in
`lri_extended_comparison_study.zip`, including its corrected critical-root selector
and analytic alpha tangent. It is separate from `lri_dressed`, `lri_hpc`, and the
coefficient/effective-Hamiltonian campaigns. It does not alter those installations.

## Scope and numerical contract

The physical problem remains the unbiased spin–boson Hamiltonian

```
H = -Omega sigma_x/2 + sum_j omega_j b_j^dagger b_j
    + sigma_z sum_j lambda_j (b_j + b_j^dagger)/2,
rho(omega) = 2 alpha omega^s,  0 < omega < 1.
```

We keep the exact original one-mode-per-logarithmic-bin chain coefficients,
`nb` local oscillator states, and `keep` states **per field-parity sector**.
`nsites` is the infrared depth. `Lambda` is the frequency-discretization ratio,
not the old dressed-phi4 bath cutoff. All physical arithmetic is float64.
No `fastmath`, mixed precision, amplitude pruning, changed counterterms, or new
bosonic basis is used. No thermal coefficient is supplied to the solver.

The default `ordered` backend preserves the original parity-basis ordering and
all forward projected-operator associations. It constructs only one parity
Hamiltonian at a time, specializes the oscillator annihilation action, and
reassociates the *linear tangent* contractions to avoid cubic products that are
unnecessary. The entire discarded eigenspace remains in that derivative.

A more aggressively reordered backend (`dense`) and a banded experiment are
provided, but **are not the default**. Reordered floating-point sums moved late
critical trajectories in testing despite tiny local spectral differences. Do not
reuse a reference critical coupling with those backends without a new tuning and
window analysis. Banded, ARPACK, LOBPCG, and projected-CG alternatives did not
outperform the accepted default in the tested configurations; some were rejected
for accuracy. See `docs/ALGORITHM.md` and `PERFORMANCE.md`.

This release accelerates the finite numerical map. It does not improve physical
mass-flow errors, retained-state completeness of correlation functions, the
bath-discretization limit, or the extraction of high-order physical coefficients.

## Symmetry cluster

For symmetry (amdq), use `docs/SYMMETRY.md` and `cluster/symmetry/`. The templates in `slurm/` are generic examples
and are not for symmetry: there every CPU partition allocates whole nodes and BeeGFS `flock` is node-local. The
symmetry tools add packed lanes, cross-node item ownership and a persistent stop file. `review/CODE_REVIEW.md` has the
review and explains why the LRI window correction does not apply to this NRG.

## Installation

Python 3.10 or later; NumPy >=1.24, SciPy >=1.11, threadpoolctl >=3.1.
The tested versions and BLAS libraries are recorded with the benchmarks.
Validation additionally needs pytest and mpmath. Linux/POSIX is required for the
HPC locking, directory fsync, and signal handling.

```
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[validation]'
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
export OMP_NUM_THREADS=1
python scripts/validate_release.py --output validation/local.json
```

There is no JIT compilation phase. The `threads` setting controls the native BLAS
pool during a trajectory. Run one solver per process; do not call differently
threaded solver instances simultaneously from Python threads because native
thread-pool limits are process-global.

## Quick runs

A fixed-alpha ordinary trajectory:

```
python -m lri_spin flow --s .8 --Lambda 3 --keep 64 --nb 10 --nsites 65 \
  --alpha .43976978933704 --threads 1 --memory-limit-gib 4 \
  --output-dir results/fixed --resume
```

Its exact finite-map derivative with respect to alpha:

```
python -m lri_spin flow --s .8 --Lambda 3 --keep 64 --nb 10 --nsites 65 \
  --alpha .43976978933704 --tangent --threads 1 --memory-limit-gib 4 \
  --output-dir results/tangent --resume
```

Those alpha values are example *finite-discretization* couplings, not universal
critical constants. For changed resolutions or a changed BLAS/runtime, retune:

```
python -m lri_spin critical --s .8 --Lambda 3 --keep 64 --nb 10 --nsites 65 \
  --bracket .3 .6 --threads 2 --memory-limit-gib 4 \
  --output-dir results/critical --resume
```

The terminal target is the original fraction (default 0.3) of the same numerical
free-chain gap. Bisection returns the **final bracket midpoint**, never a historical
smallest terminal residual. Intermediate trials omit observers that do not feed
back into the Hamiltonian; the final flow and tangent retain all observers.
A bracket that exhausts the iteration limit is not accepted as converged.

The tangent window audit uses the original formulas and thresholds. It reports
`number_of_quality_windows` and all windows, even when no acceptable physical
plateau is detected. Numerical acceptance is not a claim of physical convergence.

## Output and restart

Each run has an exclusive `.claim.lock`. It is held by the process doing the
actual solve; locks are never unlinked. A fixed trajectory writes:

* `state.npz`: retained energies/operators, derivative state if needed, and records;
* `result.json`: checksummed identity and numerically gated payload.

A critical search additionally writes `tuning.json`, validated trial subfolders,
`final_flow/`, and `tangent/`. Successful prior alpha trials are reused; no trusted
trajectory is interpolated. `result.json` at the search root contains the final
flow, tangent, and target-free window audit.

Records and checkpoints pin production-source hashes, physical/numerical options,
Python, NumPy, SciPy, BLAS version/architecture, and thread budget. A mismatch or
corruption is rejected, not silently reused. Keep immutable copies of the release
on the cluster; do not edit or git-pull a shared code directory during a run.

`--checkpoint-every 8` is the default. SIGUSR1, SIGTERM, and SIGINT request a stop
at the next completed NRG iteration; exit status 75 indicates a saved interruption.
If `LRI_SPIN_STOP_FILE` names an existing file, the solver does no work (exit 75), and
it polls that file after every iteration; lanes use it instead of signalling children.
LAPACK calls are not interruptible at an arbitrary safe point: send warning signals
well before wall expiry. An abrupt node loss can discard the work since the last
checkpoint. Restart never requires storing the large enlarged-space eigenbases.
A complete state checkpoint can be finalized without another eigensolve.

All filesystem durability and locking guarantees require the target filesystem to
support the used POSIX semantics. Local tests are not an Expanse/Lustre validation.
`seconds` in a resumed result describes that invocation, not all earlier attempts.
Use scheduler accounting for total resource use.

## Resource planning

```
python -m lri_spin plan --keep 256 --nb 16 --nsites 120 --threads 2
```

At saturation a parity block has dimension `D = keep * nb`. The default still
uses dense eigensolvers: asymptotic time is O(nsites D^3), while working memory is
O(D^2 + D keep). The number of stored observable records is linear in nsites.
The optimization reduces constants and removes avoidable cubic tangent products;
it does not remove dense spectral decomposition's cubic scaling in keep/nb.

The planner's memory envelope includes margin and process overhead, but is not a
cluster RSS guarantee. Calibrate it on the actual compute nodes before increasing
keep/nb substantially. A user-specified memory budget is checked before allocation.

## Multiple nodes

Different s, Lambda, keep, nb, infrared depths, and independent error checks are
separate jobs. One trajectory is sequential in NRG iteration; it is **not MPI- or
GPU-distributed**. Multi-rank launches are rejected to avoid replicating an
allocation unexpectedly. Native BLAS threading is the tested within-process path.
For moderate blocks, many one-/two-thread jobs may use the allocation better than
one large thread team. Do not assume 32-/64-/128-thread speedups.

1. Run `slurm/validate.slurm` on a compute node (set account/partition there).
2. Edit `inputs/example_items.json` for the intended resolutions.
3. Freeze it against the compute-node validation receipt:

```
python scripts/make_manifest.py --items inputs/example_items.json \
  --receipt validation/compute_node.json --output campaign/manifest.json
```

4. Set `LRI_SPIN_ROOT`, `LRI_SPIN_MANIFEST`, `LRI_SPIN_RECEIPT`, `LRI_SPIN_OUTPUT`
   to absolute paths and submit `slurm/array.slurm`. Adjust the array length,
   concurrency cap, memory, CPU count and time limit. All examples use one task per
   process. Site-specific account, partition, QOS and retry rules are not hardcoded.

A lane can also execute selected item indices sequentially with
`scripts/run_lane.py`. The child process owns the numerical lock if the lane
supervisor dies. Graceful lane signals are forwarded to the child, requesting a
safe checkpoint; the lane then stops rather than launching another item.
There is no automatic unbounded retry or automatic reduction of
numerical tolerances. Site accounting and bounded requeue policy should be added
in the reviewed campaign repository.

The Slurm templates are syntax-checked. They have not been submitted to Expanse.
This package does not claim to include later private changes to the Expanse layer
in the earlier coefficient campaign.

## API and old analysis scripts

```
from lri_spin import Config, run, run_tangent
cfg = Config(s=.8, Lambda=3, keep=64, nb=10, nsites=65, threads=1)
trajectory = run(alpha, cfg)
derivative = run_tangent(alpha, cfg)
```

These low-level functions have no filesystem lock or allocation budget; the CLI
and `workflow` entry points supply them. Optional adapters in `adapters/` allow
old code importing `nrg` and `nrg_tangent` to use the new numerical kernel. They do
not retrofit operational safeguards into an old critical/campaign script.

For old plotting/analysis tools:

```
python scripts/export_legacy.py results/critical/result.json \
  --output-dir exports
```

This emits plain `critical.json` and `tangent.json` with lineage metadata. They
are analysis exports, not resumable, accepted production records. Arbitrary archived
source versions require explicit `--allow-other-source`. A general gated list export
is also available as `python -m lri_spin export ... --output list.json`.

## Directory map / reproduction

| Path | Purpose / generated outputs |
|---|---|
| `src/lri_spin/compat.py` | Default exact-parity, reference-order flow and full-projector tangent |
| `src/lri_spin/solver.py`, `blocks.py` | Explicitly experimental reordered/banded implementations |
| `src/lri_spin/workflow.py`, `io.py` | Critical search, checkpoints, claims, acceptance, provenance |
| `src/lri_spin/validation.py` | Numerical gates and unchanged target-free window extraction |
| `reference/` | Unmodified supplied solver/root/analyzer for regression; not new code |
| `tests/` | Numerical, independent dense, derivative, integrity, restart, signal and lock tests |
| `scripts/` | Validation receipts, manifests, lane execution, gated legacy exports |
| `slurm/` | Portable examples requiring target-site customization |
| `inputs/` | Example item manifest and archived critical-coupling provenance |
| `benchmarks/benchmark.py` | One complete fixed-alpha flow/tangent measurement in a fresh process |
| `benchmarks/run_suite.py` | Sequential repeated benchmarks; writes `benchmarks/raw/` |
| `benchmarks/summarize.py` | Validates benchmark pairing and writes `SUMMARY.json` and performance tables |
| `benchmarks/long_regression.py` | Full-depth reference comparisons; writes a long-flow regression record |
| `benchmarks/profile_reference.py` | Recreates source bottleneck profiles |
| `benchmarks/rejected_alternatives.py` | Optional one-block alternative-eigensolver probe |
| `docs/ALGORITHM.md` | Mathematical equivalence, scaling, numerical reproducibility limits |
| `PERFORMANCE.md` | Measured results and limits, not projected cluster speedups |
| `MANIFEST.sha256.json` | Distribution integrity (not a scientific error certificate) |

Run `python tests/verify_manifest.py` to check the extracted distribution,
then `python -m pytest -q` or `scripts/validate_release.py` for numerical validation.
The shipped validation receipt records a **local** test only; generate a new
receipt on the compute node before a campaign. Benchmark scripts can
overwrite their generated raw outputs; use a copy of the package to preserve the
shipped evidence. The benchmark source fingerprint distinguishes releases.
