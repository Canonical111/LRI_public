# Multi-node deployment without changing the Hamiltonian

## Scope

This is a new 2D performance candidate. It has not been run on symmetry, and the
1D release receipts do not validate it. Use a new immutable checkout, new output
directories and a new small on-cluster validation. The Slurm template deliberately
contains no guessed partition/account names. Modify scheduler resources/site
configuration, not the numerical thresholds, after calibration.

Run pytest and a small original-versus-new numerical comparison on the target
node first. Then test shared-filesystem atomic directory creation, two simultaneous
writers, SIGUSR1 checkpoint/restart, and stale-claim handling. These site checks
have only local analogues in the supplied tests.

## Prepare independent requests

Create a JSON list of argv arrays. Absolute paths are resolved/frozen by the
manifest builder. Train bases before referencing them; do not make array tasks
race teacher publication.

```json
[
 ["--L","10","--x",".25","--nz","16","--basis","reference/results/teacher_L6_x0.250.json","--backend","auto","--threads","4","--diagnostics","all","--memory-limit-gib","16","--output","runs/L10_x025_z16.json"],
 ["--L","10","--x",".25","--nz","12","--basis","reference/results/teacher_L6_x0.250.json","--backend","auto","--threads","4","--diagnostics","all","--memory-limit-gib","16","--output","runs/L10_x025_z12.json"]
]
```

```bash
python cluster/make_manifest.py --request-list requests.json --output manifest.json
mkdir -p logs
export HT2D_ROOT="$PWD"
export HT2D_MANIFEST="$PWD/manifest.json"
sbatch --array=0-1%2 cluster/array.sbatch
```

Match each request's `--threads` to the allocated CPUs. The template starts with
four CPUs and 16 GiB per job; these are example allocations, NOT measured large-L
resource guarantees. Use the memory/RSS records to calibrate. Prefer more
single/few-core jobs for throughput when strong scaling saturates. A single job
must still fit on one node. No numerical problem is split over MPI ranks.

The manifest binds code hash and all seed/basis file contents. If an input or
source changes, generate a NEW manifest and output namespace. Automatic restart
cannot silently change the branch seed or Hamiltonian.

## Continuation and branch ambiguity

Strong-coupling calibration can have multiple roots. Performance optimization
must not choose a thermal answer to decide between them. Pass an accepted
adjacent-cutoff `--seed` explicitly for continued curves and retain independent
multi-seed/descendant checks. Arrays across x can run independently. For a
cutoff continuation, submit successive stages using Slurm `afterok` dependencies,
or run a documented serial chain per x. Do not execute every L with an arbitrary
new seed and merge different roots into one apparent continuum sequence.

## Claims and safe stop

An output's `.claim/owner.json` records host, PID, scheduler job, token and request
hash. Atomic `mkdir` is the ownership operation; a second process returns 73.
SIGUSR1/TERM/INT request a stop after a safe Newton boundary; code 75 means the
checkpoint is reusable. No checkpoint is made inside a numerical library call.
Signals may therefore take a long time at a large fixed-point solve. The example
180-second lead time must be enlarged when necessary.

A crash leaves ownership in place. After confirming that the recorded process
and Slurm job are dead, archive the owner record and remove only that claim
**offline**. Then rerun the identical request with `--resume`. Never automatically
steal a claim based only on mtime, host reachability or elapsed walltime. On-node
PID liveness alone is not a cross-node recovery protocol.

This is a conservative, fail-closed single-writer policy, not the full historical
1D generation-lease service. Do not copy the old 1D validation receipt or assume
old cross-node tests cover this code.

## Precision and reporting

Keep five-root scalar residual checks and the 1e-11 absolute window gate. Record
local basis, bath cutoff, teacher, seed, exact backend, actual threads, CPU,
NumPy/SciPy/Numba/BLAS versions and timings. `--diagnostics none` and `first` must be
labelled as reduced diagnostics, not full-family runs. Compare the same roots and
regulator before drawing performance conclusions. A smaller run time does not
provide a smaller physical continuum error bar.
