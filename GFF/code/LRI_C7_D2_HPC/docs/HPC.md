# Cluster runbook

> Delivery note: earlier benchmark numbers below are retained records.
> Fresh packaging checks and rebuilt benchmark fixtures are documented in
> `delivery/DELIVERY.md` and `delivery/fresh_checks.json`.

## Execution model

A scientific stratum is (campaign, sector, loop, graph, replicate). Its full
power-of-two Sobol net may be partitioned into arbitrary nonoverlapping sample
intervals for execution. The scheduler assigns intervals, not new replicates.
The resulting scientific stream is independent of rank, thread and node IDs.

Twenty groups cover two campaigns x two sectors x loops 3--7. Slurm arrays run
independent shards with OpenMP inside each process. MPI is not required.
There is no shared mutable counter/random stream or central worker-server in
the hot integration path. All filesystem publication is checkpoint-level.

The planner uses a disk-backed SQLite table. It sorts tasks by estimated work
and greedily assigns the longest first to the lightest shard. Each native
invocation handles at most `--checkpoint-tasks` tasks. It schedules longer
native tasks first with OpenMP dynamic scheduling. Graph metadata, products and
importance tables are immutable and shared among threads; scratch is per-thread.

## Build and pin the environment

Load the site's GCC, Boost and GMP modules as needed. `make` builds the original
300-digit arithmetic backend; `make gmp` builds the opt-in 350-digit backend.
Run `make test` and `make test-full` on the target CPU/environment before a long
campaign. Do not change the compiler flags or linked-library environment in the
middle of a run. New executable bytes require a new plan.

The local benchmark used four available CPU cores. No multi-node benchmark,
NUMA tuning study, GPU test or arbitrary-architecture portability claim is made.

## Plan, submit and assemble

```bash
export C7_PACKAGE=/path/to/LRI_C7_D2_HPC
export C7_RUN=/scratch/$USER/c7-d2-run1
cd "$C7_PACKAGE"
source .venv/bin/activate
python3 tools/production.py plan "$C7_RUN" \
  --seed 2026093002 --backend gmp --replicates 64 \
  --multiplier 4 --primitive-mode recompute --primitive-points 65536 \
  --shards 32 --threads 8 --chunk-points 65536 --checkpoint-tasks 32
NJOBS=$(python3 -c 'import json,os; print(len(json.load(open(os.environ["C7_RUN"]+"/manifest.json"))["jobs"]))')
JID=$(sbatch --parsable --array="0-$((NJOBS-1))%32" slurm/run_array.sh)
sbatch --dependency="afterok:$JID" slurm/merge.sh
```

Account, partition, memory and walltime in the templates are examples. The
array `%32` is a site concurrency cap, not the number of statistical replicates.
Clusters with a smaller MaxArraySize can split the array into several submissions
and export `C7_ARRAY_OFFSET` for subsequent blocks. Their final merge must depend
on successful completion of **all** submissions. Some federated Slurm sites
append a cluster suffix to `--parsable` output; adapt dependency handling to
the site. Log in with the same Python environment or activate it in the wrapper.

The manual completion is:

```bash
python3 tools/production.py merge "$C7_RUN" --scratch /path/to/local/scratch
python3 tools/assemble.py "$C7_RUN" --bootstrap 4096
```

Each group can be merged independently with `merge --group NAME`, allowing
parallel group merges and smaller serial I/O tails. Assembly reads only completed
replicate totals, not every point or native checkpoint.

## Resumption and failure behavior

Resubmit the same unfinished array index. Checkpoint hashes and scientific
identity are validated before completed work is skipped. Atomic hard-link
publication avoids overwriting an existing checkpoint; a duplicate execution
must produce matching scientific rows. An interruption loses at most the
currently uncommitted native work block, not the whole shard.

Missing tasks, duplicates, gaps, overlapping point intervals, wrong dimensions,
changed numerical backends, changed hashes and malformed jets cause errors.
A damaged checkpoint must be investigated; do not silently replace its contents
or accept an incomplete merge as zero. Remove only the invalid checkpoint after
keeping an audit copy, then rerun that same planned job.

The checkpoint method uses POSIX hard links on the target filesystem. Test that
this works on the site's scratch/shared filesystem. It is not an object-store
protocol. A single writer creates a group merge; simultaneous attempts fail
without overwriting data. The native runtime is not a signal-aware MPI service;
checkpoint-sized work blocks are the restart granularity.

## Memory and filesystem behavior

Kernel packs replace thousands of independent shared-filesystem graph opens with
indexed reads from one pack per sector/loop. Per-block staging reads and hashes
only required members and materializes their unchanged text on local scratch.
No entire pack is loaded into Python RAM. The largest pack is about 207 MiB
(seven-loop power-free) and is stored on disk.

Default memory is bounded by the chosen native task block, its distinct graphs,
per-thread arithmetic scratch and a small task result array. Growth in point
count increases runtime and checkpoint/disk output, not a stored point array.
Within a graph, exact importance tables still require O(2^(2L)) entries; the
code is supported through L=7 and does not remove the intrinsic complexity of
higher-loop graph inventories. Planning/merging use an 8 MiB SQLite cache plus
Python graph/group metadata and the final O(replicates x jet_width) arrays.

If many blocks reuse the same large group pack, `C7_STAGE=1` stages that group's
pack, binary and Python runtime into local scratch once per array job. Otherwise
the default seeks the shared pack directly. Copying 207 MiB for a short job can
be slower; staging is opt-in. Reuse node-local caches at the site level only if
they are keyed by input checksums and are immutable after publication.

## Tune on the actual cluster

1. Run `tools/profile.py --output /scratch/profile-new` and
   `tools/benchmark.py --output /scratch/benchmark-new`. Their graph subsets and
   counts are fixed, and both original/optimized samples match.
2. Start with one process per NUMA domain, `OMP_PROC_BIND=close`, `OMP_PLACES=cores`,
   and no BLAS oversubscription. Compare 1,2,4,... threads locally; do not assume
   the four-core VM measurements predict your sockets.
3. Choose chunk sizes large enough that graph loading and subprocess startup are
   small compared with integration. Choose checkpoint blocks small enough for
   memory and walltime-loss tolerance, but large enough to occupy all threads.
4. A pilot's actual per-graph costs can improve shard balance:

```bash
python3 tools/make_cost_model.py /scratch/completed-pilot /scratch/costs.json
python3 tools/production.py plan /scratch/new-run \
  --seed 481771 --backend gmp --replicates 64 --multiplier 4 \
  --cost-model /scratch/costs.json
```

The cost model affects placement only. It never changes estimator weights,
sample counts, random points or covariance units. Freeze new sample allocations
from independent pilots rather than adapting production counts to final outputs.
The delivered allocation is the retained pilot plan, not claimed optimal for
all clusters or the optional backend. Keep a pilot independent of production.

## Remaining limits

There is no global runtime work-stealing across nodes. Precomputed balanced
shards and dynamic within-process scheduling handle variable work; the slowest
shard still determines completion. Tasks and checkpoints grow with total samples
at fixed chunk size. Final shard sorting/merging is disk-backed, not O(1) disk.
The arithmetic fallback can still be costly at rare severe cancellations.
The supplied code does not lower precision to avoid that cost.

Official Slurm array documentation:
https://slurm.schedmd.com/job_array.html
