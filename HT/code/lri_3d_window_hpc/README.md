# 3D dressed-window HT: L18/L20 repair candidate 0.2.1rc1

Read **FIX_L18_L20.md** for patch installation into the Expanse site checkout,
new-manifest/new-receipt requirements, and staged large-cutoff probes. Read
**REPORT_L18_L20.md** for the fresh results and their limits. The attached site
status report describes an Expanse installation not included in this standalone
ZIP. Use the surgical patch there; do not overwrite its site-layer files.

This release adds a verified gesvd retry after a failed default gesdd projector
SVD, lower-overhead assembly, exact sizing, and failure diagnostics. It does not
change the physical model, cutoffs, precision, window equations, or eigensolver.
Largest actual L18 species blocks were tested in isolation; no full L18 or L20
curve point is claimed. L20 preflight/isolated sparse assembly are not full setup.

The older performance measurements and scientific outputs below remain preserved
**historical** evidence, not new benchmarks for the changed source. Their audit
uses a pinned source snapshot and additionally requires fresh current checks.

---

# 3D dressed-window HT: performance candidate 0.2.0rc1

This package optimizes the **latest supplied 3D window code**, without changing its
Hamiltonian, physical cutoff, Gaussian normal ordering, local basis, scalar
vacuum-window prescription, two primary targets, float64 arithmetic, or final
acceptance thresholds. It does not introduce fitting tails, a selected-tail
solver, an individual-mode UV parent, or additional Ward calibration.

Read **PERFORMANCE.md** for measured speed/memory results and their scope.
`docs/OPTIMIZATION.md` derives the exact rotational-trace and subcutoff identities.
This is a locally validated HPC candidate, **not** a target-cluster validation
receipt, a precision continuum result, or an MPI-distributed eigensolver.

## What changed

* Scalar vertex integration is exactly a north-pole evaluation; fixed spin J uses
  a trace over its 2J+1 magnetic components. Original quadrature remains an oracle.
* Species-block SO(3) projection is ranked/compiled, preserving the old column order.
* All lower vacuum-cutoff bare vertices are exact restrictions of the top ones.
* Newton calibration requests only one even and two odd eigenpairs. Final validation
  still requests five per parity; optional angular checks still request six.
* Large threaded local contractions use contiguous output layouts; the measured
  faster original serial local contraction remains at one thread.
* Optional immutable graph/projector/bare-vertex caching permits reuse across
  independent x/local-size/cutoff campaigns without caching changed-coupling vacua.

Tensor remains the default. The quadrature-expanded Gram backend is retained for
checks, not selected as a performance default in 3D. The optimized local teacher
and density selection are unchanged; teachers still exclude the thermal state.

## Directory map

```
code/ht3d/           optimized numerical modules and restartable point driver
code/run.py          ordinary point entry (same entry as hpc_run.py)
scripts/prepare_cache.py  optional static precomputation; no spectrum solved
benchmarks/          serial independent-process workers, summaries and plotting
results/benchmarks/  actual final benchmark records with module/runtime hashes
results/tables/     generated timing and numerical comparison CSVs
results/figures/    generated performance plots
results/development/ separately labelled intermediate implementation evidence
reference/baseline/ latest supplied 3D code, inputs and saved curve (unaltered oracle)
reference/d3original/ earlier independent mathematical/normalization oracle
inputs/             original default seeds and endpoint references (not targets)
tests/              inherited and new algebra, numerical and workflow tests
validation/         actual validation outputs, environment, provenance and caveats
cluster/            frozen independent Slurm-array workflow and site runbook
docs/OPTIMIZATION.md exact identities, cache semantics and complexity
```

No new physical curve is claimed. Historical spectra in `reference/baseline/results`
remain historical, with original checksums. They are not rewritten to masquerade
as new performance or continuum results. The original curve/figure drivers remain
inside that reference; root performance analysis does not mix them with new data.

## Dependencies and numerical threading

Python 3.10+; install the dependencies in requirements.txt. Exact tested versions,
BLAS, affinity and CPU quota are recorded in the benchmark/validation records.
Numba maximum threads must be set **before** importing Numba. The actual point
thread count must not exceed it. BLAS is kept single-threaded to avoid nesting.

```bash
python -m pip install -r requirements.txt
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
export OMP_NUM_THREADS=1
export NUMBA_NUM_THREADS=4
export MPLBACKEND=Agg
export MPLCONFIGDIR="$PWD/.mplconfig"
```

For read-only installations put Numba's compiled-code cache in a separate writable
location using `NUMBA_CACHE_DIR`. That compiler cache is different from the optional
**numerical static cache** passed as `--cache-dir`. No platform-specific JIT binaries
are shipped.

## Validation

Verify the untouched distribution before running tests that write new evidence.

```bash
python tests/verify_manifest.py
python -m pytest -q
python tests/validate_physics.py
python tests/validate_numerics.py
python tests/validate_large.py
python tests/validate_benchmarks.py
```

`validate_large.py` includes L14 matrix comparisons and freshly retuned scalar and
angular replays; it is more costly than the quick pytest suite. `validate_benchmarks`
audits the shipped measured records, not newly run timing estimates. Source changes
invalidate its strict provenance comparisons. The original physical saved-data audit is preserved in the baseline snapshot;
this release's acceptance claims concern the explicitly executed new checks.

Local tests do not certify a particular cluster scheduler, shared filesystem,
account allocation, memory envelope or scaling beyond the measured thread counts.

## Run a physical point (same finite model)

Use an explicit prior-cutoff seed at branch-sensitive points. The example uses
the included original teacher and preceding-cutoff window record:

```bash
python code/hpc_run.py \
  --L 12 --x .6 --nz 16 \
  --basis reference/baseline/results/curve/teacher_L6_x0.6.json \
  --seed reference/baseline/results/curve/window_L10_x0.6.json \
  --window vacuum --window-mode consistent \
  --backend tensor --threads 4 --diagnostics all \
  --cache-dir runs/static-cache --memory-limit-gib 8 \
  --output runs/window_L12_x06.json --resume
```

Omit `--cache-dir` for an uncached solve. It has no effect on the mathematical
Hamiltonian. A changed cache directory is still a changed request identity in the
strict point driver; use a fresh output rather than forcing incompatible reuse.
No old-source completion or checkpoint is accepted as a new-source result.

To train a new basis (same exclusion of the thermal target):

```bash
python code/run.py --L 6 --x .6 --nz 24 --osc 192 \
  --window vacuum --train-keep 20 --diagnostics first --threads 1 \
  --cache-dir runs/static-cache --output runs/new_teacher_x06.json
```

A keep20 artifact supports nested 12/16/20 spaces, not 24. The artifact fixes its
primitive scale/auxiliary resolution. Cross-x and wrong-dimensional artifacts are
rejected. Increase teacher/local resolution explicitly; no automatic cap reduction.
Default full-bath guard is 2,000,000 states; increasing it requires an appropriate
memory allocation. The planner's RSS estimate is a heuristic, not an allocator bound.

## Optional static precomputation

```bash
python scripts/prepare_cache.py \
  --L 10 12 --x .6 .5182 --spins 0 1 2 \
  --cache-dir runs/static-cache --threads 1 \
  --max-bath-states 2000000 --max-basis-gib 2 \
  --output runs/cache_preparation.json
```

This builds no vacuum or coupled spectrum. Completed arrays are published
atomically, content verified and loaded read-only. Cache entries bind exact x,
cutoff/spin, projector gauge, relevant source contents and dependency versions.
Corruption is an error, not a reason to silently reuse data. Concurrent equivalent
builds are safe under the tested local atomic-rename semantics but duplicate work;
precompute once per group, then share read-only arrays to avoid a cluster stampede.
No coupled-state cache is shared between different couplings or numerical cores.

## Reproduce benchmarks

Every worker uses a fresh process. The driver runs them **serially** and alternates
old/new implementation order for full solves and setup. Do not concurrently run
other compute-intensive jobs when measuring these benchmarks.

```bash
python benchmarks/run.py --group solve
python benchmarks/run.py --group operator
python benchmarks/run.py --group setup
# For genuinely cold creation, use a fresh runs/benchmark_cache directory:
python benchmarks/run.py --group cache
python benchmarks/run.py --group profile
python benchmarks/analyze.py
python benchmarks/plot.py
```

The full-solve timing includes graph/vertex setup, all sub-vacua, nonlinear primary
retuning and final five-root scalar checks. It excludes imports/JIT warmup, teacher
training and optional angular diagnostics. Cache experiments separately show cold
construction and warm verified reuse. Times from these different scopes must not
be added or averaged as though they were one repeated experiment.

The existing final records will be replaced unless `--resume` is used; preserve a
published copy before recomputing. Logs, source hashes, settings, achieved residuals,
peak RSS and all timing batches are retained. This is not a benchmark against a
different physical raw Hamiltonian or a slower deliberately selected Gram backend.

## HPC deployment boundary

See **cluster/README.md**. One eigensolve remains on one node; independent points
and local-size checks scale through Slurm arrays. Staged cutoffs should depend on
finished lower-cutoff seeds. Shared static geometry/vertices reduce repeated setup,
not distributed-vector storage. Calibrate total runtime, training and RSS on the
actual nodes before a large allocation. Report strong and throughput scaling
separately; four-thread measurements do not establish 64/128-core efficiency.

Original claim directories, atomic results and Newton-boundary restart are retained.
A hard crash leaves ownership fail-closed. Confirm the remote job/process is dead
before offline recovery. Do not clear a live output claim or numerical-cache entry.
The new release needs its own review and on-cluster validation; a 1D or previous
3D receipt does not validate it.
