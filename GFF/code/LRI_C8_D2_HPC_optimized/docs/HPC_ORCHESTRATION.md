# HPC scheduling, bounded work blocks, and node-local staging

The optimized frontend changes placement, checkpoint boundaries, and temporary I/O. It preserves the native task's UID, replicate, graph, point interval, total normalization, seeds, and sampling precision. Complete groups are still reduced in the original sorted `(replicate, graph, begin)` order using the same 50-digit Decimal accumulator.

## Planning many independent jobs

New plans use `--task-order graph` by default. The planner sums the estimated cost of all tasks for each graph, assigns whole graphs to shards with longest-processing-time-first placement, and keeps their tasks adjacent. Consequently a graph is loaded once per checkpoint block that contains it, instead of being repeatedly loaded for scattered replicates.

`--shard-policy cost` remains the default policy for the *number* of shards per group: `--shards` specifies the most expensive group and cheaper groups receive proportionally fewer shards. `--shard-policy uniform` requests the same maximum shard count for every group. In graph mode, the number of nonempty shards cannot exceed the number of active graphs. Each shard is a separate array element and uses the planned `--threads` CPU cores.

This arrangement requires no cross-node communication during native integration. Nodes share immutable inputs and publish independent, atomically committed checkpoints. Slurm submission still splits large job counts into offset windows; `C8_THROTTLE` limits concurrency **per submitted array window**, not across all windows combined.

### The graph-indivisibility limit

A whole graph stays on one shard. That saves parsing and graph-preparation work but makes the largest graph bundle a lower bound on the longest shard. Increasing `--shards` cannot distribute one such bundle over multiple nodes. If a few extremely expensive graphs dominate a future campaign, compare `--task-order legacy`: it retains the previous per-task LPT placement and can spread a graph's existing replicate/chunk tasks across shards, at the cost of more graph loads. OpenMP still parallelizes the tasks inside either kind of shard.

Neither placement policy changes the sample allocation. Changing `--chunk-points` also preserves point identities and normalization, but changes floating-point summation boundaries; validate the resulting rounding differences at the required tolerance. The workflow regression compares split and unsplit chunks explicitly.

## Independent checkpoint limits

Graph mode stores explicit checkpoint descriptors in each group's frozen `tasks.sqlite`. These descriptors are covered by the existing task-database SHA-256 and group/manifest hashes. Execution, restart, status, merge, and pilot timing all read the same descriptors. Historical plans without the descriptor table retain their original fixed-size cuts.

| Option | Meaning |
|---|---|
| `--checkpoint-tasks N` | Hard maximum existing native tasks per block; default 512, maximum 100,000. |
| `--checkpoint-graphs G` | Optional hard maximum distinct graphs loaded in a block. This bounds graph memory independently of replicate/chunk count. |
| `--checkpoint-seconds S` | Optional target for **summed estimated kernel core-seconds** per block, requiring a supplied `--cost-model`. It is not a measured wall-time bound. |
| `--chunk-points N` | Maximum points in one indivisible native task. This controls the smallest work unit available to checkpointing and OpenMP. |

Complete graph bundles remain together when they fit all limits. Oversized bundles are cut only between existing tasks. One native task can itself exceed the time target; it is retained unchanged and counted in `checkpoint_layout.indivisible_tasks_above_time_target`. Reduce `--chunk-points` in a **new plan** if such tasks make restart latency unacceptable. No time target can certify actual run time, because the cost model is approximate and promotion rates can vary across sampled regions.

For example, after measuring a representative pilot with the intended optimized executable, backend, hardware, and thread configuration:

```bash
python3 tools/make_cost_model.py runs/pilot cost_model.json
python3 tools/production.py plan runs/high_precision \
  --seed NEW_UNUSED_INTEGER --backend gmp --purpose production \
  --allocation allocation.json --replicates 64 \
  --cost-model cost_model.json --shards 256 --threads 8 \
  --task-order graph --checkpoint-tasks 512 \
  --checkpoint-graphs 8 --checkpoint-seconds 120
```

Replace `NEW_UNUSED_INTEGER` with a fresh integer in `[0, 2**63)` and supply a complete independently planned allocation file. The example's limits illustrate the separate controls; they are not a universal optimal configuration. The time model should be regenerated after changing the native implementation or machine. Inspect the frozen per-group `checkpoint_layout` and shard estimates before submitting.

Graph-count bounds limit the number of graph objects, not the size of one graph. A single large kernel must still fit in a worker process. Within Python, plan generation now keeps only one SQLite connection/page cache open at a time; coordinate validation streams the replicate-by-graph table, and task/checkpoint readers keep only a bounded block in memory. The task tables and final graph-replicate data remain disk backed.

## Optional shared node-local pack cache

Ordinary execution already seeks only the graph members needed by each block. Full-pack staging is optional. If many array elements reuse the same node, avoid a complete pack copy for every element by enabling the cache:

```bash
export C8_STAGE=1
export C8_PACK_CACHE="/site/node_local_storage/$(id -un)/c8-pack-cache"
```

The path must identify a real node-local directory shared by this user's jobs on that node, outside job-private staging directories, owned by that user and without group/other write permission. A job-private `SLURM_TMPDIR` usually cannot provide reuse across different array elements; follow the site's scratch layout.

The cache key is the frozen pack's SHA-256. A per-key `flock` allows only one publisher. A new copy is hashed in full, made read-only, and published atomically. A cache hit checks a receipt bound to the file's device, inode, size, nanosecond modification time and change time. Changed entries are rehashed or replaced from the verified source. Every graph member is separately hashed before native work, including on cache hits. Set `C8_REVERIFY_PACK_CACHE=1` to force a full-pack hash on every hit as well.

Job stages contain links to cached packs. Removing a completed/interrupted job's stage does not remove the cache. Cache entries are intentionally not evicted automatically: remove a cache only after all jobs using it have finished. Without `C8_PACK_CACHE`, `C8_STAGE=1` retains the original full-copy behavior.

## Affinity and merge parallelism

The launcher sets `OMP_DYNAMIC=FALSE` and defaults `OMP_PLACES=cores`, `OMP_PROC_BIND=close`. Explicit environment values for `OMP_PLACES` and `OMP_PROC_BIND` are preserved, allowing site-specific comparisons such as `OMP_PROC_BIND=spread` without editing the script.

To merge up to four independent groups at once:

```bash
python3 tools/production.py merge runs/high_precision \
  --scratch /site/node_local_storage --workers 4
```

For submitted workflows set `C8_MERGE_WORKERS=4`. The submission helper validates/caps this count to the number of groups and requests the same number of CPUs for the merge job. The merge launcher refuses to exceed its CPU allocation. Each process owns a separate temporary SQLite database; increase scratch capacity and requested RAM when increasing merge workers. Within every group, insertion batching and disposable-database I/O settings leave Decimal accumulation order unchanged. Serial merge remains the default.

All new plans pin `task_schedule.py`, `stage_runtime.py`, and `slurm_submit.py` alongside the existing production/assembly helpers. Staged execution copies all these modules and rechecks the pinned copies. Old plans continue to enforce their original tool-hash set. Editing code inside an existing campaign still triggers its original provenance guards; use a new plan for optimized production work.

## Verification scope

`tests/hpc_scheduler.py` checks exact task/cost identities, legacy and explicit layouts, hard graph/task limits, time-target exceptions, corrupt-layout refusal, streamed coordinate validation, and concurrent/interrupted/corrupt cache publication. `tests/cluster_graph_tasks.py` compares actual native scientific rows and deterministic merged output before and after rescheduling. `tests/workflow.py` checks restart, missing/corrupt checkpoints, native execution from a cached stage, stage cleanup, serial versus parallel merge bytes, and chunk-rounding tolerance.

These are local correctness and workflow checks, not a claim of measured multi-node scaling. Cluster throughput and shared-filesystem behavior must be measured on the target system with its scheduling, NUMA topology, and scratch facilities.
