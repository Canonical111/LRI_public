# HPC deployment and resource calibration

## Supported topology

One process per cutoff/reference shard, Numba shared-memory loops within a node.
Use Slurm arrays for independent cutoffs and, optionally, the four reference-state
components per cutoff. `assemble` recombines scalar components and performs the
common eighth-order tuning. No collective communication or file-sized wavefunction
transfer is needed between shards.

This does not distribute a single rank's arrays. Multi-rank launches fail clearly.
The retained `_core/parallel.py` is historical reference machinery, not a tested C8
MPI backend. It must not be relabeled production MPI support for this algorithm.

## Thread teams and binding

Set NUMBA_NUM_THREADS to the maximum allocated CPUs and choose --threads no larger
than the allocation. Cap OpenBLAS, MKL and general BLAS threadpools at one to avoid
nested teams; production also uses threadpoolctl for that purpose. Profile actual
1,2,4,... teams on the target architecture. The local tests had a four-CPU quota;
no 32/64/128-core speedup is asserted. Large ladders are often memory-bandwidth
limited.

On symmetry defq (2 x 20-core Gold 6148, exclusive nodes) the lane script binds the
single solver process with `numactl --physcpubind=<first hardware thread of each core>
--interleave=all` and the campaign uses 40 threads. `run_lane.py` refuses (exit 64)
items whose thread count exceeds the physical cores in its CPU affinity. Running two
solver processes per node (one per socket) was rejected: it doubles the processes a
cgroup OOM can hit and the projected campaign is only ~10 node-hours anyway.

Warm a persistent, writable Numba cache on the compute-node architecture. A cache
built on a different architecture may recompile. Do not distribute compiled-cache
files as a substitute for source-based validation. Numba's cache index tracks each
file's own mtime, but `residual.py` kernels inline `_core/basis.py` functions, so an
edit to basis.py is NOT noticed. Key the cache directory by `io.source_digest()`
(`slurm/symmetry_env.sh` does) and run the release tests with a fresh temporary
cache (`validate_release.py` does). Cold compilation is not included
in the clean performance medians.

## Allocation and memory

`plan` uses integer counting tables, not Fock enumeration. It reports dimensions,
edge counts, index widths indirectly through byte counts, and a deliberately padded
memory envelope. It checks the DP tables before making them too large and raises
on signed-int64 count overflow.

Perform actual RSS/time calibration on several successively larger cutoffs for
BOTH outer backends. The ranked backend trades repeated integer ranking work for
removal of the full creation graph. Do not request memory using the old degree-seven
campaign's bytes-per-state constants: C8 has different support and this algorithm
has two spaces with different storage roles.

There is no automatic precision reduction, amplitude pruning, cutoff reduction or
oversubscription to make an item fit. The CLI rejects its conservative memory
estimate above the usable allocation. To use a less conservative calibrated model,
update and review the resource layer and regenerate the validation receipt rather
than falsifying the allocation size. The model is not a proof of OS peak RSS.

## Recovery contract

A solver owns a persistent-inode flock file for the entire numerical process.
Do not unlink lock files while jobs may be running. Existence of a lock file is not
proof of ownership; the active kernel lock is. SIGKILL/node failure releases the
process's kernel lock when the process actually dies. A dead supervisor cannot
release the child's lock. A held flock makes `lri_c8 run` exit 73.

flock is only node-local on BeeGFS unless the client sets
`tuneUseGlobalFileLocks=true`; symmetry has it false. Cross-node exclusivity
therefore uses O_EXCL owner files, recording host, pid and Slurm job, held by every
writer for its whole read-modify-write lifetime:

- every destination file `<dir>/<stem>.json` has exactly one owner file,
  `<dir>/claims/<stem>.owner` (`io.owner_path`), used by all of its writers;
- the solver (`lri_c8 run`, however launched) holds the owners of its output and of
  its checkpoint, next to its flock file, from before its first read until after its
  last write;
- `assemble`, `export` (data and sidecar) and `make_campaign.py` hold the owners of
  every file they publish and refuse existing destinations (`export` writes its
  provenance sidecar last: an export without sidecar is an interrupted publication);
- the lane supervisor holds `<out>/owners/lanes/<campaign16>_lane_<k>.owner` around
  every read and write of its journal.

A writer that finds an owner exits 73 (the lane reports 73). Owners are released on
every exit the process survives and are never taken over, not even by the same Slurm
job (the batch scripts use `--no-requeue`). Stale owners from a hard kill are moved
aside only by `scripts/clean_owners.py`, which `slurm/submit_defq.sh lanes` runs under
its mutex after its own live-job check; it moves nothing if any owner records a live
job, records no Slurm job (a direct run: remove by hand after checking), or cannot be
read, or if squeue fails. A crashed `assemble`/`export`/`make_campaign.py` leaves
`claims/<stem>.owner` next to its destination; remove it by hand after checking. Temporary file names include host, pid and a
random suffix.

Atomic writes use temporary files in the destination directory, file fsync, rename,
and directory fsync. SHA-256 detects truncated or altered payloads. Compatibility
checks reject source/runtime/prescription changes. These are integrity measures,
not a security boundary against intentionally forged files.

Only scalar phase results are checkpointed. Mid-reference interruption recomputes
that reference. Complete scalar checkpoints are finalized without constructing the
large bases, even under a smaller memory allocation. Acceptance is applied before
publication, reuse, and export. A partially computed reference file is not a C8
result; four reference files are required for assembly.

The lane's signal handler forwards graceful signals to the solver. The defq lane
script execs numactl, which execs the supervisor, so the batch-warning signal
(`--signal=B:USR1@1800`) reaches it. Handlers are installed before the heavy imports
in both the supervisor and the solver. A warning may still arrive too late to finish
a large reference: the defq projection is minutes per reference, far inside the
margin. No memory/correctness failure is retried automatically: the lane stops at
its first failed item, records it in `journals/<campaign16>/lane_<k>.json`, and the
submit wrapper does not resubmit that lane unless `C8_RETRY_FAILED=1`.

## Integration with other campaigns

Install as `lri_c8`, separate from `lri_hpc_Hamitonian`, `lri_eh`, `lri_dressed`, and
`lri_spin`. The symmetry deployment (docs/SYMMETRY.md) has its own submit wrapper,
journals and failure routing; it does not reuse the Expanse campaign layer.

The source fingerprint differs from c0c30783db5d... . Never claim that new C8 outputs
were produced by that older degree-seven executable. Output configuration makes
clear whether raw or isolated g²D was used. No Dconn implementation is provided.

## First cluster acceptance sequence

1. Fresh install, release tests, int64 kernel checks, cache warmup on the node.
2. Reproduce the whole saved grid (38 points to L=50) in both prescriptions, and
   compare the retained original solver at L=60 (both prescriptions, stored and
   ranked) at atol 1e-7 / rtol 2e-11. `validate_release.py --full` does steps 1-2
   and a single-node file-system probe in the defq validation job.
3. Compare stored and ranked outside residuals; inspect exact dimensions and RSS.
4. Run identical four-reference shard and single-job calculations; require agreement.
5. Test graceful interruption/resume and claim rejection on the actual filesystem.
6. Calibrate larger cutoffs and thread counts; freeze the source and item manifest.
7. Expand the campaign only after the above tests pass. Extrapolation is a separate
   scientific workflow and must not be selected to conceal numerical failures.

Official implementation references consulted: Numba parallel-loop/performance
manual, Python fcntl documentation, and Slurm sbatch/job-array documentation. They
explain the facilities; they do not validate this code on the user's cluster.

https://numba.readthedocs.io/en/stable/user/parallel.html
https://numba.readthedocs.io/en/stable/user/performance-tips.html
https://docs.python.org/3/library/fcntl.html
https://slurm.schedmd.com/sbatch.html
https://slurm.schedmd.com/job_array.html
