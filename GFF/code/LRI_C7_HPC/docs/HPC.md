# Cluster execution and scaling

## Execution model

One C++ process integrates a bounded checkpoint block with OpenMP. A campaign
consists of many independent, restartable jobs, each integrating a shard of
scientific work units. Each unit is

```
(uid, replicate, graph, sample_begin, sample_end, original_total_samples).
```

Job number and thread number determine only **where** a unit runs, never its
random numbers. There are no MPI reductions, barriers or exchanges on the hot
integration path. Slurm job arrays provide multi-node scheduling; Slurm explicitly
supports independently indexed array elements and concurrency throttling [Slurm].
The same `run --index` command works under another scheduler or a local process
pool, provided each index is dispatched once (or restarted idempotently).

This is real distributed execution support, but **not a measured multinode
scaling result**. The matched speedups were obtained on one VM with a four-core
CPU quota and re-measured single-threaded on one workstation. One complete
archived-design production ran through the Slurm templates on one 24-core node
(PERFORMANCE.md). Measure filesystem load, NUMA effects and straggler tails at
your site.

## Build once, prepare once, freeze once

1. Build on a CPU compatible with your execution nodes. Use strict default flags.
   Do not build separately on every worker. If using `ARCH=-march=native`, all
   execution CPUs must support the emitted instructions. Include paths (for a
   module Boost) go in `CPPFLAGS`; `RPATH=1` embeds the compiler's runtime
   library directory, so a module-GCC binary also runs where that module is not
   loaded. The C++ output records the compiler and Boost versions (`build`).
2. Create byte-offset graph indices once with `make inputs`. Convert native
   weights to portable text before planning if needed. Test the numerical contract
   on the target architecture (`make test`, binary128 replay). With the git
   history, `tests/compare_binaries.py --baseline c21b9e8 --out DIR` also checks
   that this build's kernels give bitwise-identical rows to the delivered source.
3. Create a campaign/production directory on durable shared storage, visible to
   every node and kept after the job ends. Node-local `/scratch` is purged at job
   end on some sites and is suitable only for temporary files. The manifest
   contains source input SHA-256 hashes, executable hash, net hash, frozen sample
   counts, global seeds, task files, paired degrees and numerical settings.
4. Never mutate these inputs in a running campaign. The worker re-hashes the
   executable, every planned input and the net before **each** C++ invocation.
   A new executable or weight file requires a new plan, not mixing checkpoints.

Planning is metadata work only. `--multiplier` increases every active graph's
sample total according to the existing allocation. It must be a power of two for
complete Sobol nets. `--replicate-multiplier` adds independent randomizations.
For a transparent performance comparison, keep counts/replicates fixed.

## Job layout

`cluster/production.slurm` runs a complete-plan job index; `cluster/campaign.slurm`
runs one campaign index. The templates request one node, one process and eight
cores. They use

```
OMP_NUM_THREADS=$SLURM_CPUS_PER_TASK
OMP_DYNAMIC=FALSE
OMP_PLACES=cores
OMP_PROC_BIND=close
```

and single-threaded BLAS for the Python layer. OpenMP placement/binding are runtime
controls, not baked-in thread limits [OpenMP]. Account, partition, limits and
binding defaults remain site-specific.

`srun --cpu-bind=cores` alone does **not** prevent oversubscription. On Slurm
22.05–23.02, `srun` inside a batch job does not inherit the job's
`--cpus-per-task`, so the step received one CPU and all OpenMP threads were
pinned to it. On SDSC Expanse (Slurm 23.02.7) the measured effective parallelism
was 0.99 of 8 threads. The templates therefore launch

```
srun --ntasks=1 --cpus-per-task="$SLURM_CPUS_PER_TASK" --cpu-bind=cores ...
```

Before each C++ launch, `campaign.py run` also compares the number of CPUs the
process may use (`os.sched_getaffinity`) with the thread count:

- fewer allowed CPUs than threads: it refuses to start, with the message
  "CPU affinity n < threads t; launch srun with --cpus-per-task". The explicit
  `--allow-oversubscribe` flag (also on `production.py run`) permits it;
- more allowed CPUs than threads, i.e. the node does not confine CPUs (for example
  a workstation-style Slurm without core confinement): it removes `OMP_PLACES`
  and `OMP_PROC_BIND` from the child environment and prints a note, so that
  concurrent jobs do not all pin their threads to cores 0..t-1;
- equal counts: the binding is kept;
- no affinity API (macOS): no guard, and a note is printed.

The chosen policy is recorded as `binding` in each checkpoint's provenance.

The templates also read three optional variables:

- `C7_ENV_SETUP`: a script sourced with errexit already on (a failing `module load`
  or venv activation aborts the job) but before nounset (`set -u`), e.g. `module
  load` lines and a venv activation. An unreadable file exits with status 64.
- `C7_PYTHON` (default `python3`): the interpreter. A preflight exits with status
  64 and a message if it is missing or older than Python 3.8.
- `C7_INDEX_OFFSET` (default 0): the work index is
  `C7_INDEX_OFFSET + SLURM_ARRAY_TASK_ID`, so a plan larger than the site's `MaxArraySize` can be
  submitted as several arrays with indices 0..MaxArraySize-1.

Empty option arrays are expanded safely on bash older than 4.4. Pass absolute
`--output` log paths on the `sbatch` command line; the `#SBATCH --output`
defaults are relative to the submission directory, and Slurm does not create a
missing log directory.

Start with one process per NUMA domain or a modest core group and benchmark it.
More OpenMP threads share the selected graph inventory but each needs its own
numeric scratch. More processes isolate memory/NUMA traffic but duplicate input
and runtime state. No universal sockets-per-job optimum is asserted.

Use enough shards to expose parallelism, but not a job per individual sample.
The planner estimates work from graph term count, sample count and tensor size,
then assigns longest items first across shards. Each worker similarly schedules
longer items first. This avoids the old limitation of parallelizing only over
replicates. Adaptive numerical sampling allocations are **not** changed during
production.

## Checkpoint granularity and restarting

`--checkpoint-tasks` (default 64) bounds the number of work rows submitted to one
C++ process. Outputs are published by atomic same-filesystem hardlink only after
all rows finish and pass finite-value validation. A result is never overwritten.
Each checkpoint carries a digest of its scientific content inside the same file
(`provenance.payload_sha256`), with the executable digest actually checked before
that invocation and the resolved runtime libraries; see NUMERICS.md for the
integrity model.

A killed running block is rerun; previously completed blocks are skipped only
after verification, digest included. A committed checkpoint that fails
verification is never reused silently: `run`, `merge` and `verify` stop with its
path. After inspection, `campaign.py quarantine DIR IDENTITY --reason TEXT` moves
it to `checkpoints/quarantine/` (logged in `log.jsonl`) and, if the campaign
was already merged, renames `merged/audit.json` to `audit.json.invalidated.N`. The
next `run` recomputes the checkpoint, and the next merge (campaign or production)
reuses the byte-identical merged outputs and republishes the audit. SIGTERM, e.g. at the wall-time limit, unwinds the worker so that
its temporary block directory is removed. `run` needs an explicit `--index` or
`SLURM_ARRAY_TASK_ID`; there is no silent default of 0. The smallest resumable
unit is a checkpoint block, not an arbitrary partially accumulated sample loop.
Use smaller blocks for preemptible queues and larger blocks when process/input
overhead dominates.

`--chunk-points` splits long graph/replicate streams into contiguous intervals.
For QMC, workers reconstruct the state from the global Gray index without
iterating through previous samples. For the power sampler, preserving the
archived MT19937 stream requires O(begin) discard work. Avoid excessively fine
chunks of long power streams; whole graph/replicate units are often preferable.
The full-production default chunks only streams longer than 65,536 points,
which leaves the ordinary power plans effectively unsplit.

Resubmit failed array indices using the **same** manifest and executable. If a
plan exceeds site `MaxArraySize`, submit disjoint ranges with `C7_INDEX_OFFSET`.
`%64` in an array specification caps simultaneous array elements, not total
threads. Submit the merge job with `--dependency=afterany:JOBID` [Slurm], not
`afterok`: with `afterok` a single failed element means the merge never starts.
The merge fails closed if any checkpoint is missing or invalid. After
resubmitting the failed elements, run the merge again. A duplicate element is
safe (the loser of the publication race validates the winner) but wastes CPU.

No asynchronous service is required: the scripts perform foreground worker or
merge work and return nonzero on failure.

## Memory and I/O

The main long-double quadrature tile buffer defaults to 32 MiB **per thread**.
The requested tile is reduced if necessary. Typical 128-node tiles touch much
less, but the process reserves the requested virtual capacity. There are also
small first-order/index vectors, per-term accumulators, graph/trie/proposal data,
thread stacks and allocator overhead. `--scratch-mib` is a principal buffer
budget, **not an exact process RSS limit**.

At L7 the old one-shape geometry alone is about 150.8 MiB at degree 6 and about
2.22 GiB at degree 10. The tiled implementation never allocates either complete
geometry. It still evaluates all their nodes. Raising interpolation degree
therefore increases runtime steeply without the former tensor-sized memory spike.

Only graphs in the current block are loaded, through byte offsets in the original
text inventory. Threads share this immutable data. Worker output has one small
row per work unit, not one row per sample or a mostly-zero full graph table.

For filesystems sensitive to many opens, increase checkpoint block size and stage
the immutable input directory onto node-local storage. The single-campaign worker
accepts `--inputs /node/local/copy` and verifies every planned hash there. It also
accepts `--scratch /node/local/tmp`. Staging inputs is optional; checkpoints must
remain on durable storage. `SLURM_TMPDIR` is used for temporary work files by the
provided scripts when available.

A production directory is self-contained. `production.py plan` copies (never
symlinks) every input file that its campaigns hash into `<production>/inputs/`
(about 20 MB), plus any `--extra-inputs` weights, and plans every campaign
against that snapshot. Manifests store the inputs path relative to the campaign,
and `assembly.json` uses paths relative to the production directory, so the
directory can be moved as a whole. The executable is stored as an absolute path
plus SHA-256; after a move, pass `--executable PATH` to `run`, and the hash must
still match. `production.py run` always uses the snapshot; dispatch
`campaign.py run --inputs` directly to use a node-local copy. File modes follow the umask:
checkpoints, merged outputs and results are no longer forced to 0600.

The full plan uses O(work units) Python metadata. This is not streaming planning
for billions of tiny units. Prefer coarser chunks rather than creating that many
units. The merger uses a disk-backed SQLite uniqueness/join/sort index (16-MiB
cache), loads one bounded JSON checkpoint at a time, and retains only
O(replicates × 14) final totals. Temporary disk space scales with checkpoint data.
Use node-local scratch for the merge database when appropriate.

## Merge and error propagation

A campaign merge refuses missing files, duplicate IDs, malformed rows, seed/
rate/degree mismatch, wrong input provenance, a checkpoint digest mismatch,
overlap, gaps or missing stream tails. It verifies a complete `[0,total)` for
each graph and replicate, and that the set of streams is exactly the manifest's
`{replicate < replicates} × {graph : counts[graph] > 0}`, each at its manifest
total. Missing work is not represented by zero. It sums in canonical order at
50-digit decimal precision and can optionally stream old-format `graph_batches`
to disk. All statistics are computed before anything is published. A rerun
regenerates `merged/N*.json` in temporary files and reuses an existing output
only if it is byte-identical; a difference is an error. `audit.json` is written
last.

`campaign.py verify DIR` re-validates a merged campaign: manifest identity, every
task-file hash, every checkpoint (structure and `payload_sha256`), the merged
outputs against `audit.json`, and audit completeness (`complete: true`, the
work-unit count, and a source list equal to the full expected checkpoint set).
`production.py merge` and `tools/combine.py` call it for already-audited
campaigns.

For paired power degrees, both sides use the same graph counts, seed and replicate
index. Their difference is formed within replicate. The covariance unit is the
**randomized replicate**, not a shard, sample chunk or Sobol point [Sobol].

`production.py merge` gathers all 21 independent campaign groups (plus the
degree-7 check campaigns when planned with `--refine7`) and applies the archived
affine map, zero-pole controls, low-order inputs and one retained primitive
input. It produces sampling SE, covariance, bootstrap and the full set of archived
diagnostics (NUMERICS.md). `C7_result.json` is published atomically; a rerun
recomputes it and must find identical content, so an interrupted or repeated
final merge is recoverable. The merge does not extrapolate the last quadrature
degree. It applies a pre-registered empirical allowance policy mechanically;
that policy is not a rigorous interval. Check each refinement component and
repeat with independent seeds before claiming more digits.

## Independent batches and designs

A batch is one complete production directory with its own seed and `--label`.
Several batches of one frozen design are combined by

```bash
python3 tools/combine.py BATCH_DIR... --output COMBINED_DIR
```

It verifies every campaign of every batch and requires a byte-identical canonical
scientific configuration across batches (ARCHITECTURE.md); only seeds, nets,
absolute paths, timestamps and labels may differ. Batch labels, batch seeds and
per-campaign seeds must all be distinct. Each source enters once, under a
batch-qualified name and with weight divided by the number of batches; the
retained primitive enters once. `C7_final.json` adds per-batch C7 and the
inter-batch χ² about the combined mean.

`tools/design.py` writes a per-campaign `--design` file by a pre-registered
Neyman allocation over campaigns, from the archived components and an
independent pilot production only, never from the batches it will size. A/B
pairs form one group so that their fixed design weights stay valid; per-graph
allocations inside a campaign stay frozen. Freeze the design before the first
batch and do not change it mid-run.

## Limitations to plan around

- Source targets L2 through L7; do not use it for new eighth-loop graphs.
- GNU quadmath/Boost portability, long-double ABI and compiler reproducibility
  must be checked on new architectures. No GPU or non-GNU port was validated.
- Power seeking is linear in the initial sample index; it is not a counter-based
  random generator. Changing generators would change the original samples.
- Default tensor quadrature remains exponential in L-1 and polynomial of that
  degree in N. No optimization here removes the integration's mathematical work.
- A merge interrupted at any point is recovered by rerunning it: merged files
  are reused only if the regenerated content is byte-identical, `audit.json` is
  written last, and a completed audited campaign is re-verified, not trusted by
  hash alone. Never remove valid checkpoints.
- POSIX atomic hardlinks must be supported in checkpoint/output directories.
  Object storage without such semantics requires a different publication layer.

### Primary documentation

[Slurm] https://slurm.schedmd.com/job_array.html

[OpenMP] https://www.openmp.org/resources/refguides/

[Sobol] https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.qmc.Sobol.html
