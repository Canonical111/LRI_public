# 2D dressed-window HT: performance/HPC candidate 0.2.0rc1

This package optimizes the **latest 2D total-bath-level, dressed-zero-mode,
self-consistent full-vacuum-window calculation**. It is not the factorizing-UV
perturbative/source project. No fitting tails, selected-tail eigensolver, new
counterterm, angular buffer, thermal target, or reduced floating-point precision
is introduced. The physical equations are in `docs/ORIGINAL_METHOD.md`.

**Read `PERFORMANCE.md` for measured results and their scope.** The code is a
locally tested HPC candidate, not a release already validated on symmetry.
Distributed execution is across independent parameter/cutoff jobs; an individual
ARPACK solve remains within one node. The exact Fock-space growth is not removed.

## Contents

| Path | Purpose |
|---|---|
| `code/ht2d/` | Optimized numerical modules, exact sparse factorization, ranked basis, window, local basis, diagnostics |
| `code/hpc_run.py` | One-writer point driver, checksums, safe-boundary checkpoints and restart |
| `code/run.py` | Compatibility spelling; maps old diagnostic flags to the restartable driver |
| `cluster/` | Immutable array manifests, one item per process, Slurm template and deployment instructions |
| `benchmarks/` | Independent-process timings, original-versus-new comparisons, profiling and summary generation |
| `tests/` | Original 16 numerical cases plus new operator/ranking/cache/restart/manifest tests |
| `reference/code/` | Unchanged input 2D port, used as the comparison oracle |
| `reference/results/` | Original 66-run records and teacher artifacts; **not new optimized outputs** |
| `upstream/d2dressed/` | Earlier independent circle implementation used by original tests |
| `inputs/` | Original Newton seed data |
| `results/benchmarks/` | New complete timing records, settings, spectra and runtime information |
| `results/tables/` | New benchmark summaries and numerical comparison tables |
| `results/figures/` | Benchmark chart in PNG/SVG; regenerate with `benchmarks/plot.py` |
| `validation/` | Actual local validation, environment, source hashes and development caveats |
| `docs/` | Exact algebra and preservation of the original model |

## Install and validate

Python 3.10+, NumPy, SciPy, Numba, threadpoolctl, pytest. Matplotlib is retained
only for the original reference scripts; it is not used by the solver. Runtime
versions are recorded in the validation artifacts, with optional exact pins in
`requirements-tested.txt` for the observed Python 3.13.5 environment. No C++ compiler, GPU, MPI, or
external service is needed for this release.

```bash
python -m pip install -r requirements.txt
export OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 OMP_NUM_THREADS=1
export NUMBA_NUM_THREADS=4
python tests/verify_manifest.py
python -m pytest tests/test_port.py tests/test_optimized.py tests/test_hpc.py -q
python tests/validate_benchmarks.py
python benchmarks/analyze.py
```

Allow four Numba threads for the test that deliberately compares 1 and 4 threads.
The single-job `--threads` option sets the actual thread count. Keep BLAS at one
thread when using multiple Numba workers. `NUMBA_NUM_THREADS` is an upper limit
set before import; do not set it to one and then request four.

The manifest describes the distributed files. Run its check before tests or
analysis that intentionally rewrite validation/summary outputs. Those scripts
must not be mistaken for immutable input data.

## Numerical backends

* `--backend tensor`: store projected bath vertices W1--W4, but never a many-body
  Kronecker matrix. Optimized sparse/dense contractions improve this existing path.
* `--backend gram`: store exact sparse annihilation images and their Gram factors.
  No full projected quartic W4 and no full-bath ladder work vectors are needed
  during matvecs. All compatible intermediate angular states are retained.
* `--backend ladder`: exact legacy algebra retained for comparison, not the default
  recommendation for large spaces.
* `--backend auto`: tensor through L=12, gram above L=12. Small vacuum sublevels
  through L=8 can use tensor even when the top operator uses gram. These are
  algebraically equivalent backends, not different physical cutoffs.

The crossover is a conservative memory/performance policy, **not a universal
machine-dependent optimum**. Benchmarks include both tensor and gram. On some
sizes tensor is faster but uses more operator storage. Override explicitly after
calibration. Set `HT2D_SPARSE_PARALLEL_MIN_WORK` to adjust the sparse work threshold
(default 250000); the HPC result configuration records it.

## One point using an existing optimized local basis

The original teacher files are included as explicit input artifacts. They are
usable for regression and pilots; their retained size is not certified adequate
at arbitrary larger cutoffs. Use adjacent-cutoff seeds to stay on the intended
branch when the primary tuning equations have multiple roots.

```bash
python code/hpc_run.py \
  --L 10 --x .25 --nz 16 --backend auto --threads 1 \
  --window vacuum --window-mode consistent \
  --basis reference/results/teacher_L6_x0.250.json \
  --diagnostics all --memory-limit-gib 8 \
  --output runs/L10_x025.json --resume
```

The calculation retunes only the spin and shadow gaps and recomputes changed-
coupling windows. It returns the same five scalar levels and, with `all`, six
roots per angular sector for the original first/second descendant diagnostics.
`--diagnostics first` omits level-two diagnostics explicitly; `none` is useful for
an isolated solve benchmark, not a complete spectrum audit.

For a new teacher and transfer:

```bash
python code/hpc_run.py --L 6 --x .3 --nz 24 --osc 192 \
  --window vacuum --train-keep 20 --diagnostics none --threads 1 \
  --output runs/teacher_x030.json
python code/hpc_run.py --L 10 --x .3 --nz 16 --window vacuum \
  --basis runs/teacher_x030.json --backend auto --threads 1 \
  --output runs/L10_x030.json --resume
```

An artifact with 20 functions per parity supplies nested 12/16/20 spaces, not a
24-state space. Its primitive scale and auxiliary dimension are authoritative.
The thermal state is not used to select the basis. The optimized-basis mode is
restricted to the consistent vacuum window in the new HPC driver.

## Restart semantics and output integrity

The configuration binds the source/default-seed-table hash, input contents, runtime versions,
cutoffs, precision/tolerances, backend and thread settings. Accepted results have
an additional content checksum. **Old research-port JSONs are not restart
records**; keep them as reference data, use new output paths, and use their
`theta` values only as explicit starting guesses.

SIGUSR1, SIGTERM and SIGINT request a stop at a safe Newton boundary. The next
checkpoint contains the current couplings and iteration history; exit code 75
means a checkpointed stop. The code does not checkpoint inside ARPACK/LAPACK or
inside an unfinished window fixed point. Signal lead time must exceed that work.
A resumed solve reconstructs the operators and re-solves the current point; it
never accepts a stale vacuum table. Resume is tolerance-equivalent, not a promise
of identical warm-vector iteration counts.

Each output has an atomically created `.claim` directory. Concurrent writers fail
with exit code 73. After SIGKILL/node loss the claim remains **fail-closed**. There
is no automatic remote-owner guessing or lease theft. Confirm owner/job death,
archive the owner record, and remove that exact stale claim offline before
resuming. See `cluster/README.md`. This simpler policy is not advertised as the
full reviewed 1D generation-lease integration.

## Memory and numerical safety

The ranked basis computes its exact dimension before allocation, checks integer
range, and uses explicit state/array guards. The point driver assigns one quarter
of its requested GiB budget to each basis-array guard and forwards it to every
sub-cutoff; this is a preflight safeguard, not a total-memory bound. The HPC driver also reports a
conservative **heuristic** memory estimate after operator construction and refuses
an insufficient requested budget. This is not a proved peak-RSS bound and does
not replace Slurm/cgroup memory enforcement. Tensor construction itself can be
large: prefer auto/gram for larger L. No resource guard silently reduces L, nz,
precision, residual thresholds, or the requested roots.

The physical spectrum is still finite-cutoff. Better numerical speed does not
remove the self-consistent window model's known matching errors or resolve every
strong-coupling branch ambiguity.

## Reproduce measurements

```bash
# Serial isolated child processes, repeated and alternating implementation order.
# Existing named records are skipped. Move them aside to run a fresh campaign.
python benchmarks/run.py --group all
python benchmarks/analyze.py
MPLBACKEND=Agg python benchmarks/plot.py

# One new explicitly named warmed profile; not used as a wall-time benchmark.
python benchmarks/worker.py --implementation optimized --task solve \
  --L 10 --x .25 --backend tensor --threads 1 --profile \
  --output runs/profile_L10.json
```

The benchmark worker warms relevant numerical signatures before timing. Full-
solve timings include basis/operator setup, all vacuum fixed points, coupling
retuning and five-root scalar validation; they exclude imports, JIT warmup, local
teacher training and the optional cross-sector descendant calculation. Operator
benchmarks are matvec timings only. Peak RSS is process high-water usage, including
warmup/imports; operator-array bytes are a separate metric. See `PERFORMANCE.md`.
