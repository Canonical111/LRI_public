# HPC runbook

## Deployment

Build the native worker with GCC, OpenMP, libquadmath and Boost headers on the cluster's intended CPU architecture
(`make clean && make`; no binary is shipped). Avoid `-march=native` when login and compute nodes differ. There is no
MPI dependency: shards are independent Slurm array elements, with OpenMP within each. Python >= 3.10 is required.

On SDSC Expanse (verified 2026-09-28): `module load cpu/0.21.2a gcc/13.3.0 boost/1.86.0` plus a venv holding
`requirements.txt`; see `slurm/expanse_env.sh.example`. Campaign directories live on the shared Lustre tier
(`<SCRATCH>/temp_project/...`). Node-local `/scratch/$USER/job_$SLURM_JOB_ID` (`SLURM_TMPDIR`) is
used only for the job-private runtime and merge scratch, and is purged when the job ends. The shared partition
requires `--nodes=1 --ntasks=1`, which the templates set; arrays are limited to indices 0-999 (MaxArraySize=1000).

Use a production directory on a filesystem every worker can reach. Runtime input hashes and scientific identities,
not absolute paths, define checkpoint compatibility. Never rebuild or change the executable or inputs inside an active
campaign: a new binary requires a new plan.

## One full calculation

1. `production.py plan` freezes **eight groups** (campaigns a/b at loops 3-6): counts, Sobol nets, seeds, task
   databases, shard assignment and block positions. It first runs the executable on a tiny self-test task, so a
   binary built for another system is refused before its hash is frozen. It prints and records cost estimates and a
   suggested wall time.
2. A global job index chooses `(group, shard)` from `manifest.json`. `slurm/submit.sh` submits arrays of at most
   `C6_MAX_ARRAY` (default 1000) elements with `C6_INDEX_OFFSET`, then `slurm/merge.sh` with `afterok` on all arrays.
   CPUs per element and wall time default to the plan's `--threads` and suggested time.
3. Each job verifies the tools, the inputs manifest and the executable against the plan, then copies the executable
   and exactly the inputs its shard needs, plus the group's Sobol net, into a job-private directory (mode 0700,
   under `--scratch`/`SLURM_TMPDIR`), verifies every copy, and runs only those copies. It reads at most `checkpoint_tasks` task rows at a time, in the
   frozen cost-descending order, and atomically publishes one checked block per native call. Each checkpoint records
   the digests of the executable that actually ran, of the inputs manifest and of the Sobol net; a checkpoint from
   another executable, input set, net or plan is rejected at restart and at merge.
4. `production.py status` reports committed/total blocks per group and every incomplete job index, with the
   complete `sbatch` lines to resubmit them (`--json` for scripts; `slurm/resubmit.sh` uses it); it exits 0 only when
   every block is committed.
5. `merge` validates every expected record and [0,N) interval coverage, sorts on disk, writes `graph_replicates.csv`
   and stores complete-replicate Taylor vectors in `merged.json`. Groups already merged are validated and skipped; an
   invalid existing `merged.json` is an error and is never overwritten.
6. `assemble.py` verifies the two assembly-only inputs (two-loop B2, primitive reference P10) against the frozen
   inputs manifest, performs the fixed-point and covariance assembly, and publishes `C6_result.json` idempotently: an
   existing identical result is kept, a different one is an error.

The sample set and randomization do not depend on node assignment, thread count or checkpoint boundaries. Changing
the thread count at restart is permitted (at most `checkpoint_tasks` threads). Changing checkpoint boundaries or the
frozen task plan is not a restart: use a new plan.

## Blocks, shards and throughput

Every block is one native process: it loads the block's graphs and (for a_L6) the frozen grid, then runs its tasks
with OpenMP (`schedule(dynamic,1)`, largest first within the block) and ends at a barrier. Blocks within a shard are
consecutive in the frozen position order (estimated cost descending), so each block holds tasks of similar cost and
the barrier idles few threads. Per-block process start-up, graph loading, validation and fsync are amortised by large
blocks: use `checkpoint_tasks` of at least 16-32 times the thread count (`run` warns below 16x and refuses more threads
than tasks per block). `--shards` sets the shard count of the most expensive group; other groups get proportionally
fewer shards, so no array element is a few seconds long. Measured utilisation on Expanse is in
`docs/PERFORMANCE.md`.

## Restart, recovery and integrity

Checkpoints are published with a same-filesystem atomic hard link and are never overwritten. A worker crash loses at
most the uncommitted block. Re-running an index verifies existing checkpoints (identity, runtime digests, payload
hash, task coordinates) and skips them. Native failures publish a failure log under the group's `logs/`.
`run --max-blocks N` stops after N new blocks (time slicing).

With `afterok`, a failed element leaves the merge pending forever. Recovery (same environment as `submit.sh`):

```bash
python3 tools/production.py status "$C6_RUN"      # incomplete indices and the complete sbatch lines
scancel <pending merge job>
slurm/resubmit.sh                                  # resubmits exactly those indices + a merge with afterok on them
```

**One guarded submission path.** `submit.sh`, `resubmit.sh` and the lines printed by `status` (which call
`submit.sh --window OFFSET:ARRAY`) all submit through `tools/slurm_submit.py`. The shell wrappers source
`C6_ENV_SETUP` (if set) and check Python >= 3.10, so they work from a fresh login shell. `slurm_submit.py` then
enforces:
- **Site and extra options.** `C6_SBATCH_ARGS` (one line, shell-lexed) and the extra arguments are each checked,
  separately, against an exact-spelling allowlist, so neither can consume the other's tokens:
  - allowed: `--account --partition --qos --reservation --constraint --mem --mem-per-cpu --time --cpus-per-task --gres
    --tmp --mail-type --mail-user --begin --signal --job-name --exclude --licenses --wckey --requeue --no-requeue
    --hold` and `-A -p -q -C -t -c -J -x -L`; options with optional arguments (e.g. `--nice`) are excluded;
  - refused: everything else, including array, dependency, export, `--export-file`, comment, output, clusters,
    positional words and abbreviations such as `--arr`.
  - Extra arguments may override CPUs and wall time, never the array, tag, offset, output or export.
- **Limits.** `C6_MAX_ARRAY` and `C6_THROTTLE` must be positive integers. `status` sizes its windows by
  `C6_MAX_ARRAY`.
- **Cluster.** Inherited cluster selectors (`SBATCH_CLUSTERS`, `SLURM_CLUSTERS`, `SQUEUE_CLUSTERS`) are refused, so
  queries and submissions address the same cluster.
- **Environments.** Other `SBATCH_*` inputs outside a small allowlist (account, partition, QOS, reservation,
  constraint, memory, time limit, wckey, requeue) are removed from `sbatch`'s environment, and `SQUEUE_*` from
  `squeue`'s.
- **Commands.** Commands are argument lists; nothing is spliced through a shell. `C6_RUN`, `C6_PACKAGE` and the
  window's `C6_INDEX_OFFSET` are set in `sbatch`'s own environment, because with `--export=ALL` an inherited value
  would override an explicit one. Merges carry no offset.

The recovery decision is made by `production.py recover` (pure Python, unit-tested), from a complete snapshot:
`squeue --all --states=all -r -h -u $USER`, with any inherited `SQUEUE_*` filter cleared.
- **Campaign tag.** Every job carries the Slurm comment `<tag>:off=<offset>` (merge: `<tag>:merge`). The tag is
  `c6:` plus a hash of the resolved campaign path and the manifest (`production.py tag`), so even identically planned
  campaigns never see each other's jobs. Do not move a campaign directory while its jobs are queued.
- **Live jobs.** Queued, running, suspended, stopped, held or requeued jobs (including SPECIAL_EXIT) are live. Their
  indices are not resubmitted, and the new merge waits for every live element individually (`afterok` on
  `jobid_taskid`).
- **History.** Finished jobs are ignored.
- **Refusals.** COMPLETING and STAGE_OUT (the outcome is hidden while Slurm cleans up), PREEMPTED (a requeue may
  follow), any unrecognised state, an unexpanded array record and a failed `squeue` all refuse (exit 69; rerun
  shortly). A live merge of the campaign refuses with exit 65: cancel it first.
- **Resubmission.** Missing indices go out in windows of at most `C6_MAX_ARRAY` with `%C6_THROTTLE`, the plan's CPUs
  and wall time, and `C6_SBATCH_ARGS`. If nothing needs resubmission, only the merge is submitted.

The checkpoint hash is an integrity check, not a digital signature against a malicious editor. The merge refuses
missing samples instead of assigning zeros. Do not delete or edit task databases or checkpoints to make a merge pass.

## Memory and I/O

The native memory cap is structural: only the union of graphs in one block, thread-local scratch and a small row
buffer are loaded (about 50 MB measured for an L6 shard at 8 threads). It is not a byte-level allocation guarantee;
promoted precision needs more. Input rate tables still grow exponentially with edge count; this implementation has a
fixed six-loop maximum.

`--chunk-points` balances long graphs against checkpoint rework; chunks need not be powers of two, but complete
stratum totals must be. The task database and merge use file-backed sorting with an 8 MiB SQLite page cache; task
databases are opened read-only by workers. Each job copies at most a few MB of inputs to its private directory.
`tools/stage_runtime.py` can additionally stage the tools and inputs for a whole node.

## Accuracy planning

The default allocation starts from the previous pilot's per-graph counts (times `--multiplier`) plus the frozen
Neyman split of the primitive budget; `plan` prints the projected primitive-block SE (an MC-scaling projection from
archived pilot variances). Prefer at least 16-32 replicates for meaningful uncertainty diagnostics. Inspect per-graph
CSV influences, independent campaigns and the bootstrap. Keep pilot/adaptation data separate from final inference
and freeze adaptation before production. Every campaign needs a fresh seed.

The deployment was tested on Expanse with separate array jobs, split arrays, resumption, failure recovery, complete
merges and assembly (`benchmarks/expanse_2026-09/`). MPI, GPU acceleration and arbitrary loop orders are outside this
package's scope.

## External documentation

* SciPy Sobol: https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.qmc.Sobol.html
* Slurm job arrays: https://slurm.schedmd.com/job_array.html
* GCC optimization options: https://gcc.gnu.org/onlinedocs/gcc/Optimize-Options.html

These sources describe software behavior, not an external validation of the LRI coefficient or of this project's
physical subtraction formula.
