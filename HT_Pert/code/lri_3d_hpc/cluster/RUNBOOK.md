# Runbook: perturbative 3D HT coefficients on Expanse and symmetry

This directory is the supported way to run the package on SDSC Expanse and on Perimeter's
symmetry. Both sites use the same Python stack, job scripts, stage runner and submit
wrapper. Only `sites/<site>.sh` and the partition table in `submit.py` differ between them.
The `hpc/` scripts in the package root are the upstream generic examples. Do not use them on
these two sites.

## What runs where

| | Expanse | symmetry |
|---|---|---|
| Data root `HT3D_DATA` | `<SCRATCH>/temp_project/ht3d_pert` | `<SCRATCH>/ht3d_pert` |
| Locks `HT3D_LOCK_ROOT` | `$HT3D_DATA/locks` (Lustre; flock is cluster-wide) | `$HOME/ht3d_pert/locks` (NFS, `local_lock=none`; BeeGFS flock is node-local) |
| Node-local scratch | `/scratch/$USER/job_$SLURM_JOB_ID` (NVMe; Slurm removes it) | `/local1/$USER/ht3d_$SLURM_JOB_ID` (84 GB; the job removes it) |
| Compiler / MPI | modules `cpu/0.21.2a gcc/13.3.0 openmpi/4.1.8 slurm/expanse/23.02.7` | system g++ 11.4, Debian OpenMPI 4.1.2 |
| MPI launcher | `srun --mpi=pmix` (pmi2 fails) | `mpirun` inside the allocation (Slurm's pmix plugin cannot load its library and this Open MPI has no PMI2 component) |
| Production CPU | AMD EPYC 7742 (shared, compute, large-shared, debug) | AMD EPYC 7532 (amdq, amddebugq, amdpreq; cn112 excluded) |
| Partitions | `shared` (per core, ≤243G), `compute` (whole node 128c/240G), `large-shared` (≤2000G), `debug` (30 min) | `amdq` (whole node 64c/245G, 24 h), `amddebugq` (1 h) |

The two sites use the same stack:
- uv 0.12.23 and CPython 3.12.9 (the generic `x86_64-gnu` build);
- numpy 2.5.3, scipy 1.17.0, numba 0.68.0, llvmlite 0.50.0 and threadpoolctl 3.6.0, installed from `requirements.lock` (hash-pinned);
- mpi4py 4.1.2, built from source against the site MPI.

The venv is `$HT3D_DATA/venv-py3129-np253-sp1170-nb0680`. `bash cluster/install.sh` builds it, and `--check` verifies it. Both venvs were built on 2026-10-08.

## Release

On the Mac, in the repository, at a clean commit:

```bash
python cluster/make_release.py --out /tmp/ht3d_rel        # <git12>.tar and <git12>.tar.sha256
ssh expanse  'mkdir -p <SCRATCH>/temp_project/ht3d_pert/releases'
ssh symmetry 'mkdir -p <SCRATCH>/ht3d_pert/releases'
scp /tmp/ht3d_rel/<git12>.tar* expanse:<SCRATCH>/temp_project/ht3d_pert/releases/
scp /tmp/ht3d_rel/<git12>.tar* symmetry:<SCRATCH>/ht3d_pert/releases/
```

On each login node (Expanse inside `bash -l`), set the data root explicitly the first time,
verify and unpack a read-only reference copy, build or check the environment, then load it:

```bash
D=<SCRATCH>/temp_project/ht3d_pert      # symmetry: D=<SCRATCH>/ht3d_pert
cd $D/releases && sha256sum -c <git12>.tar.sha256 && chmod a-w <git12>.tar
mkdir -p ~/ht3d_pert/code/<git12> && tar -xf <git12>.tar -C ~/ht3d_pert/code/<git12>
cd ~/ht3d_pert/code/<git12> && sha256sum -c --quiet --strict RELEASE.sha256 && chmod -R a-w .
bash cluster/install.sh            # first time only; `bash cluster/install.sh --check` afterwards
source cluster/env.sh              # sets HT3D_SITE, HT3D_DATA, HT3D_VENV, HT3D_LOCK_ROOT, ...
```

`submit.py` runs from this reference copy. Before every submission it re-verifies the copy and
the tarball, and checks every tarball member against the copy's `RELEASE.sha256` (no extra,
duplicate or missing member). It then binds the job to that release fingerprint
(`HT3D_EXPECT_FINGERPRINT`). Before sourcing anything, each job (and each MPI node) copies the
tarball to node-local scratch, verifies the copy, and authenticates `cluster/stage.sh` and
`cluster/prologue.sh` against that manifest.

Each job, on every node:
1. verifies the tarball's sha256 again;
2. extracts it to node-local scratch and checks `RELEASE.sha256`;
3. refuses unless the staged fingerprint equals the expected one;
4. runs only that staged copy.

The stage runner and the MPI driver also refuse a campaign frozen for another release.
Many-file trees are never copied on Lustre.

## 1. Validate (once per release and site)

```bash
python cluster/submit.py validate                     # symmetry: amddebugq, whole node, 1 h
python cluster/submit.py validate --time 02:00:00     # Expanse: shared, 16 cores, 64G
```

The receipt is `$HT3D_DATA/validation/<git12>_<job>/receipt.json`. It passes only if every
gate stage passes:
- **Environment and file systems:**
  - pins, x87 long double, the release fingerprint;
  - the lock file system is cluster-wide;
  - a hard link onto an existing name refuses on the data file system.
- **The package's own tests**, writing only to node-local scratch.
- **MPI:**
  - the first site launcher that gives a true 2-rank world;
  - `check_mpi_backend` on 2 and 4 ranks;
  - `check_hpc_driver` with real 2-rank MPI.
- **The L4 fixture** at tolerance 1e-16, both schemes.
- **An L14 store built through the production stage runner** on the data file system, with its cutoff-14 reference gate.
- **The 32-case saved grid:** 8 cutoffs × 2 schemes × stationary and recurrence. Every case passes the 5e-13 coefficient gate, and every recursion residual is ≤ 1e-16.
- **MPI L14 solves** within 1e-15 of serial.
- **Drills:** `srun` without `--mpi` is refused; a busy target exits 75; stale partials are swept; SIGTERM during prepare leaves no partial directory.

`fixture_bitwise_L4` is informational. It records whether this node class rebuilds the
shipped L4 fixture bit for bit. Neither site does: the fixture and the saved reference were
made on another machine, and the float64 SO(3) projector (built with the site's
BLAS and libm) differs at roundoff. It differs slightly in sparsity too, through exact zeros.

This sets the precision achieved across machines. On both sites the 32-case grid agrees with the
reference to at most **1.16e-14**:
- in C, r and g the agreement is ≤ 1.3e-15 at cutoff 14;
- the largest deviations are in low-subcutoff vacuum energies;
- the recursion residual stays ≤ 1.4e-17, so this is not an x87 issue.

Treat about 14 significant digits, not 19, as reproducible between machines. JSON reports
of every check are kept in `<receipt dir>/reports/`.

Optional: validate MPI across nodes before any MPI production run. This needs the L14 store and gates from a passing receipt:

```bash
R=$HT3D_DATA/validation/<git12>_<job>/campaign
python cluster/submit.py validate-mpi --store $R/stores/L14 --gates $R/gates/L14
```

Expanse runs this on `debug` (2 nodes). symmetry runs it on `amdq`, because `amddebugq` allows one node per job.

It checks:
- the launcher spans N hosts with the right CPU affinity;
- one rank exiting abnormally ends the step (abort drill);
- flock on the lock root blocks across nodes (it also records whether flock on the data file system does);
- `check_mpi_backend` passes on all ranks;
- the L14 MPI solves are within 1e-15 of serial.

**Mixing sites.** Compare the two receipts' `store_L14_value_fingerprint`, which is format
`ht3d-store-values-v2`. It covers:
- cutoff, degree and precision;
- N and P;
- every sparsity pattern under its id;
- every matrix's key, shape, pattern id and data values.

It skips the 6 uninitialised padding bytes of each 16-byte x87 long double; because of that
padding, the file checksums of identical builds differ. If the fingerprints are equal, the two
sites build identical vertices and their results are interchangeable. Otherwise keep each
campaign on one site.

This was verified on 2026-10-08 for the pre-review builds (v1 fingerprint, values only):
- the Expanse (EPYC 7742, glibc 2.28, g++ 13.3) and symmetry (EPYC 7532, glibc 2.35, g++ 11.4) L14 stores were value-identical;
- their cutoff-14 gate results agreed with maximum scaled difference exactly 0.

## 2. Freeze a campaign

```bash
python cluster/submit.py init pert3d --receipt $HT3D_DATA/validation/<git12>_<job>/receipt.json \
   [--mpi-receipt $HT3D_DATA/validation/mpi_<git12>_<job>/receipt.json]
```

`$HT3D_DATA/campaigns/pert3d/campaign.json` records:
- the site and the release (tarball, sha256, fingerprint);
- the CPU class of the receipt node;
- the lock directory;
- the MPI launcher, if any.

The campaign also records the environment identity the receipt validated: interpreter path, every installed package version, compiler banner, mpi4py build, and the MPI runtime. The runtime part is the mpi4py extension and every library it resolves (`ldd`: MPI, PMI, UCX's libucp/libuct/libucm/libucs, fabrics, libc, …), by path and sha256, plus each site launcher's binary and `--version`. The receipt checks this coverage against an independent `ldd` parse. MPI jobs check this identity on every node. Every job refuses to run in a different environment, and so does `init` on the login node. After any change to the venv, the modules or the site's MPI/Slurm installation, validate again and start a new campaign. A campaign never continues across an environment change.

Submissions for another release or site are refused. The `prepare` stage refuses on any other
CPU model, because it depends on BLAS kernels and libm at the last bit. The other stages are
plain x87 arithmetic and only record the node.

## 3. Run

`submit.py run NAME --cutoff L --stages S,...` submits one job. That job runs
`cluster/ht3d_stage.py`, which handles the stages in this order:

| stage | output | notes |
|---|---|---|
| prepare | `prepared/L<L>/` | graph + SO(3) projectors. One process. Exact state/byte guards from `preflight`. Refuses if the memory cgroup is below 2× the graph arrays. `--blas-threads` speeds up the SVDs (recorded) |
| images | `prepared/L<L>/images/p<p>/` | one task per particle sector, `--lanes` at a time, high sectors first |
| matrix | `prepared/L<L>/tasks/k<k>-r<r>/` | 28 tasks, `--lanes` at a time, k=4 first. Memory is dominated by k=4 |
| finalize | `stores/L<L>/` | combines all tasks with full checksums |
| verify | `records/L<L>/verify/store.json` | full checksum pass. Later solves then skip re-hashing (`--trust-staged-arrays`) |
| gate | `gates/L<L>/{raw,consistent}_c14.json` | cutoff-14 solves from this store against the saved reference. Exact: the N≤14 block is the L14 problem |
| solve | `results/L<L>/c<C>_<scheme>.json` | production solves, `--threads` OpenMP threads. Refused unless both cutoff-14 gates of this store passed against the shipped reference with this code |
| crosscheck | `crosscheck/L<L>/c<C>_<scheme>.json` + `.compare.json` | recurrence strategy against stationary (≤ 1e-15). Complete only when the comparison record, bound to both files' sha256, exists. Run it at the first new cutoff |

Rules that hold for every stage:
- An existing result counts as done only for the exact case: store, cutoff, scheme, order, strategy, arithmetic, the driver's defaults, the current solver source, and serial versus MPI rank count. Anything else exits 65 ("move it aside"). It is never reused or replaced silently.
- Every command first checks two things. The staged release must be the campaign's. The campaign lock directory must still have cluster-wide flock: Lustre `flock` on Expanse, NFS `local_lock=none` on symmetry. The job exits 3 otherwise.
- Stages that are already complete at manifest level are skipped at submission time. The job also skips published tasks.
- Each task holds a cluster-wide flock on its target. A second job finds the target busy (exit 75) and never duplicates work.
- Stale `*.partial-*` directories of dead attempts are removed only under that lock.
- Every job that reads a store (gate, solve, crosscheck, MPI solve) first re-hashes all its arrays once. Only that job's own solver subprocesses then skip hashing. The verify stage re-hashes too, every time it is run (exit 65 if a file changed). A marker from an earlier job never vouches for a later one.
- SIGTERM at the time limit becomes an exception, so the pipeline's own cleanup runs.
- Every task writes `records/L<L>/<stage>/<key>.<job>.<pid>.json`: host, CPU, threads, wall time, peak RSS. These records are the calibration data for the next cutoff.

Every solve, through `code/ht3d_coefficients.py`:
- refuses a long double narrower than x87;
- probes x87 arithmetic in NumPy and on every native thread;
- requires `native-openmp` when it runs threaded;
- refuses publication if the seed-recursion residual exceeds 1e-16;
- takes its output lock in the campaign lock directory;
- publishes with a hard link, so an existing result is never replaced.

### Sizing

Exact counts come from `python cluster/submit.py plan --cutoff L`, which wraps the package's preflight. Every L≥16 resource figure is an extrapolation from L8–L14 (two independent reviews, 2026-10-08). Replace them with the L16 and L18 records before going higher.

| L | bath states | graph arrays | scalar dim | store | matrix k=4 RSS | 1-thread solve / scheme | prepare SVD (1 BLAS thread) |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 14 | 1.78 M | 0.14 GiB | 4,486 | 0.2 GB | 0.3 GB | 21 s | 9–15 s |
| 16 | 8.78 M | 0.75 GiB | 15,815 | ~2.5 GB | ~2 GB | ~3 min | ~5 min |
| 18 | 41.0 M | 3.7 GiB | 55,859 | 13–25 GB | 12–21 GB | 15–25 min | 1.2–1.9 h |
| 20 | 183 M | 17.4 GiB | 196,585 | 77–210 GB | 66–180 GB | 1.3–3.6 h | 22–37 h |
| 22 | 783 M | 78.5 GiB | 686,552 | 0.4–1.7 TB | 0.4–1.5 TB | 7–30 h | 17–28 days |

Suggested first runs (whole pipeline, gate, solve and crosscheck in one job):

```bash
# symmetry (amdq: whole node, 64 cores; --cpus is filled in)
python cluster/submit.py run pert3d --cutoff 16 --stages prepare,images,matrix,finalize,verify,gate,solve,crosscheck \
   --mem 240G --time 08:00:00 --lanes 16 --blas-threads 16
python cluster/submit.py run pert3d --cutoff 18 --stages prepare,images,matrix,finalize,verify,gate,solve \
   --mem 240G --time 24:00:00 --lanes 6 --blas-threads 32
# Expanse (shared: charged max(cores, GB/2) SU per hour)
python cluster/submit.py run pert3d --cutoff 16 --stages prepare,images,matrix,finalize,verify,gate,solve,crosscheck \
   --cpus 16 --mem 32G --time 08:00:00 --lanes 8 --blas-threads 8
python cluster/submit.py run pert3d --cutoff 18 --stages prepare,images,matrix,finalize,verify,gate,solve \
   --cpus 64 --mem 160G --time 30:00:00 --lanes 6 --blas-threads 32
```

`--threads` defaults to all the job's cores. Solves run one at a time, each with all
threads. Add `--solve-cutoffs 14 16` to solve several cutoffs from one store: a larger store
supplies every smaller even cutoff exactly.

**L20.** Run it stage by stage, with resources taken from the L16 and L18 records, and chain
the stages with `--after`:
- **prepare.** Use Expanse `compute` (128c/240G, 48 h) or `large-shared`. Give `--blas-threads` explicitly: one thread would take 22–37 h.
- **images and matrix.** Either use `--array N --throttle K` on `shared`, or pack `--lanes` on whole nodes. Plan by k=4 RSS, which is up to 180 GB per task.
- **solve.** A 77–210 GB store needs `large-shared`, or `solve-mpi` across 2–4 nodes.
- **symmetry.** Its 24 h limit and 245G nodes make the L20 prepare and k=4 tasks marginal there.

**L22** is not feasible with this code on either site:
- prepare is one process with no checkpoint, needing 160–470 GB and weeks of single-thread SVD;
- the k=4 matrix tasks need up to 1.5 TB each;
- the pipeline needs several TB of Lustre.

It needs code changes first: a projector checkpoint, threaded or distributed SVD, spilled matrix
assembly, and image cleanup.

### Chaining and arrays

```bash
J=$(python cluster/submit.py run pert3d --cutoff 20 --stages prepare ... | awk '/^submitted/{print $2}')
I=$(python cluster/submit.py run pert3d --cutoff 20 --stages images --array 8 --throttle 8 --after $J ... | awk '/^submitted/{print $2}')
python cluster/submit.py run pert3d --cutoff 20 --stages matrix --array 7 --after $J,$I ...
```

An array takes exactly one stage. Matrix tasks read the images of every particle sector, so a
matrix array must wait for the whole image array, by depending on its parent id.

`--after` must name every live job of that campaign and cutoff. An array counts as its parent id,
the one `sbatch` returned. A named predecessor that has already ended is accepted only in two
cases: it is in this campaign's ledger, and `sacct` reports it (every array element)
COMPLETED with exit 0:0. Its dependency is then dropped. Anything else is refused: a failed
predecessor, an unknown one, or a job of another campaign. The wrapper refuses while any
other job of that campaign and cutoff is queued or running, and it refuses if `squeue` fails.
Dependent jobs use `afterok` and `--kill-on-invalid-dep=yes`, so a failed stage cancels its
dependents instead of leaving them pending forever.

## 4. Monitor

```bash
python cluster/submit.py status pert3d --cutoff 16
tail -f $HT3D_DATA/campaigns/pert3d/logs/ht3d.pert3d.L16.<stages>_<job>.out
ls $HT3D_DATA/campaigns/pert3d/records/L16/*/
```

## Exit codes

| code | meaning | action |
|---|---|---|
| 0 | all requested stages done | none |
| 75 | a target is held by another job, or the job stopped early on a signal | wait for that job, then resubmit (only missing work runs) |
| 65 | an existing target fails verification | move it aside by hand after inspection, resubmit |
| 3 | wrong CPU class for prepare, allocation differs from the request (`HT3D_EXPECT_*`), memory below the prepare floor, or MPI prebuild/world check failed | fix the submission |
| 70 / 74 | environment / release staging failed | read the log head |
| 1, 143 | a task failed or was interrupted | read the log and the task record; resubmit after fixing |

## Notes

- Expanse campaign `prepared/` and `stores/` use a progressive Lustre layout: small files get one stripe, files above 64 MB get 8 × 16 MB stripes.
- Expanse user rule: at most 22 compute jobs at a time on <ACCOUNT>. Every `submit.py` submission to
  `compute`, validations included, counts queued and running array elements individually,
  includes the new submission, and holds a data-root mutex through the check and the `sbatch` call.
- symmetry: `--exclude` adds to the fixed cn112 exclusion and never replaces it.
- `submit.py init` refuses unless `HT3D_LOCK_ROOT` is the lock root the receipt validated and still passes the lock check.
- symmetry: amdq first, never longq. `submit.py` allows only the AMD partitions.
- After a store is verified and the solves are done, `prepared/L<L>/images` and `tasks` can be
  deleted. They are rebuilt only if a new store is needed.
