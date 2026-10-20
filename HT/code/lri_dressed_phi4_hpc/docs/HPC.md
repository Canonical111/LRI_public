# Cluster deployment and acceptance

## This is a separate direct-spectrum task

Install the package in a new environment/namespace (`lri_dressed`); do not replace
`lri_hpc_Hamitonian` or `lri_eh`. The supplied HPC campaign report describes later
Expanse-specific revisions that were not supplied as source. This release cannot
preserve unknown implementation details by claiming to be that reviewed revision.
Its integration should retain the site's accounting, claim policy, retry policy,
and resource routing after independent review.

Use a compute node, not the login node, to run validation and timing. Account,
partition, reservation, expiry, and QOS limits are intentionally not hardcoded.

## Install and validate

    python -m pip install -e '.[validation]'
    mkdir -p logs validation campaign
    export LRI_BASELINE=/path/to/frozen/e637dfd   # pinned numerical source, checked before any stage
    sbatch --account=YOUR_ACCOUNT --partition=YOUR_PARTITION slurm/validate.slurm

`validation/cluster-receipt.json` is checksummed and identifies the source and
Python/NumPy/SciPy/Numba versions. A lane rejects a stale receipt. The receipt is
an implementation-test result, not evidence of physical cutoff convergence.

## Plan first

    python -m lri_dressed plan --bath-cut 24 --nz 32 --osc 256

The partition and edge counts are exact. The memory envelope includes Krylov
vectors, two parity outputs, full-bath ladder scratch, small local matrices and
runtime reserve. Tensor backend construction uses a deliberately conservative
dense-fill bath bound. Memory numbers are uncalibrated; measure max RSS and time
on progressively larger node-local runs before replacing this conservative
estimate with a reviewed site model. The driver checks the requested GiB and the
visible cgroup remainder. It never lowers a basis cap to fit memory.

## Create parallel continuation lanes

    python scripts/make_campaign.py --bath-cuts 16 20 24 \
      --nz 24 --osc 192 --deltas .24 .225 .2 .175 .15 .125 .1 .075 .05 .025 .01 \
      --out campaign/lanes.json

Each lane is a complete descending-x scan at one physical cutoff. The basis is
reused across its points. All points are independent after their seed is supplied,
so further parallelism can be obtained by making separate manifests for disjoint
parameter subsets. Near x=0, use retained successful continuation seeds and keep
local-basis convergence separate from root residuals.

Export absolute paths, and submit after validation:

    export LRI_MANIFEST="$PWD/campaign/lanes.json"
    export LRI_RECEIPT="$PWD/validation/cluster-receipt.json"
    export LRI_OUTPUT="$PWD/results/cluster"
    export LRI_MEMORY_GIB=8
    export LRI_SEEDS="$PWD/inputs"
    sbatch --account=YOUR_ACCOUNT --partition=YOUR_PARTITION \
      --array=0-2%2 --mem=8G --cpus-per-task=4 slurm/scan_array.slurm

The 8 GiB request is an EXAMPLE, not a validated requirement for the sample grid.
Set it from planning and target-node calibration. More threads need not improve
ARPACK's serial orthogonalization or saturating memory traffic. Measure 1,2,4,8,...
threads at FIXED caps and tolerances; do not assume the largest allocation is best.
A node-local Numba cache avoids repeated compilation within the allocation.

The template launches exactly one solver per item. Single-point multi-rank
`mpiexec`/multi-task srun is rejected. Multi-node scaling here is across independent
scan lanes, not an unmeasured distributed eigensolver.

## Interruptions and restart

A Python solver process owns its item flock throughout computation. The lock is
not held only by a supervisor that might die while the solver continues. Failed
processes release the kernel lock; stale lock files are harmless. Verify flock
semantics on the site's shared filesystem before production.

On symmetry, use `cluster/symmetry/` (README there). BeeGFS flock is node-local, so every claim also takes a
cross-node generation lease (`src/lri_dressed/lease.py`), and the node-packing launcher `scripts/pack_node.py` runs
many items per exclusive node.

USR1/TERM requests are observed at safe Newton boundaries. Coupling coordinates
and root history are checkpointed atomically with source/configuration checksums.
No signal handler allocates large arrays or writes a partial numerical result.
An in-progress ARPACK solve is not serialized and must be repeated on restart.
Continuation bridges before the requested target are not checkpointed separately.
Use `--seed-dir` from accepted scans to avoid expensive repeated bridging.

Run with `--resume` to reuse accepted final results or the last Newton checkpoint.
Final publication, reuse, and export apply the same finite/tuning/eigenvector/
orthogonality checks. A source, runtime, cap, backend, or tolerance change creates
a different configuration fingerprint; old data are never silently relabeled.
Retries are NOT automatic. Inspect the failure, then resubmit with `--resume`;
retain the reviewed site's bounded retry/node-failure handling layer.

## Audit/export

    python -m lri_dressed status --input-dir results/cluster
    python -m lri_dressed export --input-dir results/cluster --output accepted.json

Only checksummed final records in that directory are exported. Failures and
checkpoints are in separate subdirectories. Export never averages duplicate
physical points from different configurations; provenance stays on every row.
The flat result payload retains the old names (Delta_thermal, theta, even_gaps,
odd_gaps, etc.) for downstream analysis. Sector eigenvector layout is changed;
old warm eigenvector files must not be reused without an explicit permutation.

## What has not been tested locally

No job in this release was submitted on Expanse. Slurm templates are syntax
checked and local lane/receipt/restart semantics are tested, not scheduler/QOS or
network-filesystem behavior. Benchmarks use at most four effective CPUs. There is
no validated speedup claim for 32/64/128 cores, GPUs, or a single point over nodes.
