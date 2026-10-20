# Cluster continuation: configurable resources, unchanged physics

This folder adds **launching, cache management, indexing, and planning tools**.
It does not change a matrix element, denominator, counterterm, tail coefficient,
or physical conversion in the scientific solver. It does not establish a new
value or additional digits of C2. The scientific result remains approximately
**C2 = -4.07**, with systematic extrapolation uncertainty.

No scheduler, CPU count, memory amount, wall-time limit, account or partition is
required to read or validate the package. Configure those at submission time.
The default worker count is serial, not a recommendation for production.

**On SDSC Expanse or Perimeter's symmetry use the multi-site layer**
([`sitekit/`](sitekit/README.md) with the site folders [`expanse/`](expanse/README.md)
and [`symmetry/`](symmetry/README.md)): pinned environments, tarball staging
with checksums, grid and row jobs on node-local scratch, a submit driver with
resource checks per site, collection and cross-site merging, and the
re-prioritised site-neutral plan `production_plan.json` (PILOT, P1 at N=768,
P2 at N=1024). It was exercised with N=12 smoke chains on both sites and an
N=512 pilot on Expanse; see `results/expanse/` and `results/symmetry/`. The
generic adapter below remains for other Slurm sites.

## Files and status

| File | Role | Status |
|---|---|---|
| `extension_plan.json` | Nine proposed task groups: three regulator families at each of N=512, 768, 1024 | **Not run**; planning input, not data; kept for reference, superseded by `production_plan.json` |
| `production_plan.json` | Site-neutral PILOT / P1 / P2 rows and science rules | PILOT run on Expanse; P1/P2 not run |
| `smoke_plan.json` | A tiny N=12 task testing the wrapper and cache | Validation only; not a physical coefficient |
| `run_task.py` | Validate/list tasks, prepare one coefficient grid, run one task in isolated directories; optional plan keys `tail_cutoff` (leading-tail sidecar cutoff, default 2048) and `stage` | Unit-tested and small-task-tested; used by the Expanse jobs |
| `resource_estimate.py` | Exact sizes of two known arrays using the installed FFT padding rule | Tested; not peak memory or runtime |
| `collect_records.py` | Preserve all raw records and compare finite-box overlaps without hard-coded N=384 routing | Tested; not a continuum analysis |
| `slurm_array.sh` | Optional scheduler adapter using caller-supplied environment/resources | Shell-syntax checked; not submitted to a cluster |
| `test_cluster.py` | Nine tests of plans (including the optional keys), locks, grid metadata, indexing, dry runs, allocation formulas and shell syntax | Rerun in this revision |
| `sitekit/` | Site-independent jobs, driver, monitor, receipts, collection, merging; see its README | Unit-tested; used on both sites |
| `expanse/`, `symmetry/` | Site profiles, environments, wrappers, tests | Smoke chains run on both; pilot on Expanse |

The existing complete numerical reproduction is still documented in the main
README and uses `scripts/run.py`. Its historical `full-hamiltonian` plan is
separate from the **proposed** extension plan in this folder.

## 1. Scientific strategy and acceptance criteria

Evaluate the fourth-order coefficient at physical delta=0. The useful limits are

```text
h0 = limit(lambda -> 0+) limit(N -> infinity) h_N(lambda)
C2 = -pi**2/(4*b0) + h0/b0**2
b0 = 1.26840430893914254379...
```

These are deterministic sums. Repeating the same calculation longer does not
reduce statistical noise: increase the cutoffs, reduce the regulator, and test
the numerical method instead. Use more regulator points than fit parameters.
The prior four-parameter fits for two regulator families had only four points;
a zero residual in such an interpolating fit is not accuracy evidence.

A proposed progression is N=512 first, then 768, then 1024 only after checking
resource use and convergence. The plan groups several lambda values in one task
so the same Ising grid is reused. Grid arrays are independent of the regulator
order and lambda. A sufficiently large N*lambda helps suppress regulated tails,
but is not by itself an error certificate. Smaller lambda can increase the
cancellation between large intermediate contributions.

First acceptance target: an independently controlled absolute error in C2 of
1e-3; next target: 1e-4. These are **targets, not forecasts**. They require errors
in h0 of approximately 1.61e-3 and 1.61e-4, respectively, and usually tighter
errors at each fixed lambda because extrapolation amplifies input errors.
Report separately spectral tails, mixed/collapsed/tail-constant cutoffs,
Cauchy-grid errors, roundoff, and regulator-model dependence. Model half-spreads
are not standard deviations or rigorous bounds.

## 2. Inspect before computing

Run from the package root, in the Python environment installed from the main
README:

```bash
python cluster/run_task.py list
python cluster/resource_estimate.py --cutoff 384 512 768 1024 --oversample 4
python cluster/test_cluster.py --output outputs/cluster_tests.json

# No scratch arrays are created by a dry run.
python cluster/run_task.py run --task-index 0 \
  --work-root work/cluster --output-root outputs/cluster --dry-run
```

The resource estimator reports **array storage**, not requested RAM. With
K=N+1 and even M chosen by the implementation's `next_fast_len` rule:

```text
stored real grid bytes = 48 * K**3
temporary complex grid bytes = 96 * (M//2 + 1) * K**2
```

At oversampling four, the stored/temporary sizes are about 2.74/10.97 GB for
N=384, 6.48/26.02 GB for 512, 21.83/87.48 GB for 768, and 51.69/207.67 GB for
1024 (decimal GB). FFT work arrays, per-process temporaries, convolutions,
other caches, filesystem paging and operating-system overhead are additional.
There is no universal wall-time prediction. Record the actual peak RSS and
scratch use of a pilot job before selecting a production allocation. The exact
FFT length can depend on the SciPy version; the estimator records that version.

## 3. Shared-grid workflow

Choose paths visible to the relevant jobs. A scratch cache may be local to a
node or shared; it must actually be accessible wherever it is consumed. An
output root should persist after the allocation ends. Replace the example path
values below with your cluster's paths, and set LRI_WORKERS for your allocation.
No memory or CPU allocation is embedded in the plan.

```bash
export LRI_GRID_ROOT=/path/to/persistent/grid_cache
export LRI_WORK_ROOT=/path/to/scratch/task_work
export LRI_OUTPUT_ROOT=/path/to/persistent/results
# Set LRI_WORKERS to an appropriate local worker count before a production run.

# In one allocation, prepare the N=512 grid once.
python cluster/run_task.py prepare-grid \
  --cutoff 512 --oversample 4 --radius-cost 4.5 \
  --cache-root "$LRI_GRID_ROOT" --workers "${LRI_WORKERS:?Set LRI_WORKERS}"

# After the grid preparation has completed, run one regulator family.
python cluster/run_task.py run --task-index 0 \
  --work-root "$LRI_WORK_ROOT" --output-root "$LRI_OUTPUT_ROOT" \
  --coefficient-cache "$LRI_GRID_ROOT" --workers "$LRI_WORKERS"
```

Task indices 0, 1, 2 use N=512 and orders 1, 2, 3, respectively. Tasks 3--5 use
N=768, and 6--8 use N=1024. Preparing one grid does not prepare another N or
another oversampling/radius choice. Run only the stage you intend to test.

`prepare-grid` publishes `grid_receipt.json` only after successful generation.
Consumption checks the receipt, scientific-source hashes, array shape/dtype,
file size and metadata. It does not rehash every byte of a multi-gigabyte array
on every read. Keep shared grids immutable during use. Copy the whole grid
folder, including `.npy`, its `.json` metadata and `grid_receipt.json`, when
moving a prepared cache.

The wrapper creates separate work/output directories named from the task ID
and a hash of its configuration and scientific sources. It uses writer locks
to reject concurrent writers. A hard-killed process can leave `.writer.lock`;
remove it only after independently confirming that no process is using that
directory. Do not let two processes run a generator in the same unprotected
working directory. Stale or incomplete arrays without a completed receipt are
not treated as completed shared grids.

Omit `--coefficient-cache` to generate a private grid inside the task work
area. This is safe but can duplicate expensive grids across task groups.
Within a task the lambda values run sequentially and reuse the grid. Task
receipts include inputs, source hashes, worker settings and output hashes.
Use `--skip-completed` to validate a completed task and skip it; otherwise the
wrapper rejects reuse of a completed output. Incomplete tasks rerun the task,
not just the last interrupted lambda. This is not a fine-grained checkpoint
system, and it does not submit background jobs by itself.

## 4. Optional Slurm adapter

On Expanse or symmetry, use `sitekit/` with the site wrappers instead: it
stages a checksummed tarball and the grid into node-local scratch, sizes
workers from the allocation and records peak memory and timing.
`slurm_array.sh` is optional. The Python driver also works with another
scheduler's job arrays or in a normal shell. There is no MPI-distributed grid;
each task needs an appropriate single-node allocation. Do not launch one copy
of the full Python driver per CPU.

For Slurm, prepare the grid first, then set the environment and pass resources
when submitting. For example, the following specifies only the three N=512
array elements; add your site's allocation flags to the sbatch invocation.

```bash
export LRI_COEFFICIENT_CACHE="$LRI_GRID_ROOT"
export LRI_PLAN="$PWD/cluster/extension_plan.json"
export LRI_PYTHON="$(command -v python)"
mkdir -p logs
# Add your chosen CPU, memory, time, partition/account flags to this command.
sbatch --array=0-2 --output='logs/lri-%A_%a.out' cluster/slurm_array.sh
```

The adapter uses `LRI_WORKERS`, otherwise `SLURM_CPUS_PER_TASK`, otherwise serial
execution. It uses `SLURM_ARRAY_TASK_ID` to choose a plan row. Pass
`LRI_FFT_WORKERS` separately to set the solver FFT-worker count. BLAS/OpenMP
threads are limited to one by the wrapper to avoid hidden oversubscription.
Concurrent tasks still consume separate contraction workspaces even when the
coefficient file is shared read-only.

The cluster-readiness revision itself performed no scheduler submission,
multi-node execution, resource guarantee or large-grid benchmark with this
adapter. Later Expanse and symmetry runs used `sitekit/` (see above).

## 5. Collect new records without silently running the old fit selection

```bash
python cluster/collect_records.py --input-root "$LRI_OUTPUT_ROOT" \
  --compare-overlaps --output outputs/new_record_index.json
```

This keeps every `(order, lambda, N, grid)` variant. It records hashes and task
metadata and can compare overlapping raw chain sequences. It does **not**
select the largest N, infer independent error bars, run tail fits, or calculate
C2. The optional `_analysis.json` beside a solver record remains a
fixed-lambda diagnostic from the retained solver.

### Important analysis limitation

The historical final-analysis pipeline remains intentionally frozen:

* `scripts/run.py collect_run` uses the `extended` naming convention only for
  N=384; other arbitrary N values must not be silently routed through it.
* `analyze_extended.py` selects historical windows with Nmin 240 and 288;
  `tail_transseries_fit.py` also uses N=256-specific endpoints.
* `analyze_fine.py` selects mixed-sum fits with Nmin >= 2048 rather than a
  generalized fraction of an arbitrary mixed cutoff.
* `reproduce.py` uses auxiliary leading-tail cutoff 2048 when making its
  diagnostic sidecar unless `--tail-cutoff` (or `LRI_TAIL_CUTOFF`) is given;
  launched tasks take it from the plan key `tail_cutoff`. The historical
  `analyze_extended.py`/`tail_transseries_fit.py` read `LRI_TAIL_CUTOFF`
  (default 2048). The sidecar remains a fixed-lambda diagnostic.
* `scripts/run.py analyze` stages the **preserved** records. It does not discover
  new cluster outputs automatically.

Before using the new records for improved precision, generalize the analysis
explicitly: choose fractional spectral windows (for example 5N/8 and 3N/4),
require enough degrees of freedom and full numerical rank, retain all model
and grid variants, make mixed/tail-constant cutoffs explicit, propagate each
error source, and ensure more regulator points than fitted parameters.
Changing a fit window fraction alone is not proof that the same tail model is
valid for all N and lambda. This analysis refactor and the larger production
runs are **next steps**, not completed results of the packaging revision.

## 6. Reproduce the new small integration test

This uses a regenerable tiny cache, not any bundled numerical array:

```bash
python cluster/run_task.py prepare-grid --cutoff 12 \
  --oversample 3 --radius-cost 4 --cache-root work/test_cache
python cluster/run_task.py run --plan cluster/smoke_plan.json --task-index 0 \
  --work-root work/test_tasks --output-root outputs/cluster_smoke \
  --coefficient-cache work/test_cache
python cluster/collect_records.py --input-root outputs/cluster_smoke \
  --compare-overlaps --output outputs/cluster_smoke_index.json
```

This test checks the new wrapper, metadata and scientific entry point. It
cannot estimate the continuum C2. The tiny recorded JSON output is retained in
`results/revision/cluster_smoke/`; its coefficient arrays and scratch stages
are deliberately excluded.

## References for execution behavior

The main LaTeX note embeds the official SciPy `fftn` and `next_fast_len`
documentation and Slurm job-array documentation in its bibliography. Their
roles are the worker/padding behavior and optional scheduler interface, not
the physics or the claimed accuracy.
