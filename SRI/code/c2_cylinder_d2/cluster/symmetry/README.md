# Running the C2 extension on symmetry (Perimeter)

The symmetry site of the multi-site launch layer: the same plan rows
(`cluster/production_plan.json`), job scripts and tools
([`cluster/sitekit/`](../sitekit/README.md)) as on Expanse, with symmetry's
rules in `profile.json`. No scientific numerics are touched; records have the
same format as on Expanse and are merged with `cluster/sitekit/merge_records.py`.

| File | Role |
|---|---|
| `profile.json` | partitions, limits, paths, per-N sizing, measured node facts |
| `setup_env.sh` | venv from `module load python/3.13-mamba` with the exact pinned versions |
| `submit.py`, `make_tarball.sh`, `collect.sh` | wrappers of `cluster/sitekit/` with this profile |
| `test_symmetry.py` | profile rules, documented commands as dry runs, `bash -n` |

## 1. Rules encoded in the profile

| Rule | How it is applied |
|---|---|
| Slurm not on `PATH` | `submit.py` prepends `/cm/shared/apps/slurm/current/bin` |
| every CPU partition is whole-node exclusive | `--exclusive`; rows are packed: one numactl-pinned process per package |
| `amdq` first, `defq` fallback, both only if fine on either vendor | production jobs use `-p amdq,defq` with `--mem=180G` (the Intel limit); workers are chosen in the job from the node's own topology and memory |
| never `longq`; preemptible `amdpreq`/`preq` only with checkpoints | listed as forbidden (the jobs restart at row granularity, not from checkpoints) |
| debug: `amddebugq`/`debugq` (1 h) | probe and smoke profiles |
| `--exclude=cn112` on AMD partitions | added to every command that lists `amdq`/`amddebugq` |
| 24 h wall | every job is sized to at most 12 h on the slower vendor |
| a waiting job can preempt other campaigns' `preq`/`amdpreq` work | submit only when the target partition has idle nodes (`sinfo -h -p amdq -o '%t %D'`), including debug partitions |
| one process per package: <= 32 threads (AMD), <= 20 (Intel) | `jobtools.py topology` reads packages and NUMA nodes in the job; row k runs under `numactl --cpunodebind=<package k nodes>` (plus `--membind` when two rows share the node) with workers = that package's cores; never CPU-id ranges (Intel ids are interleaved) |
| cgroup OOM kills one process at a time | two rows per node only for N <= 768 (2 x 40 GB model); N = 1024 runs one row per node until a measured RSS proves two fit |
| persistent data on BeeGFS, code in `~` | root `<SCRATCH>/lri_c2` (grids, outputs, receipts, logs, tarballs); env and code copies in `~/envs`, `~/lri_c2/pkgs` |
| large temporaries on node-local `/local1` | jobs work in `/local1/$USER/job_<id>`, check free space first, remove it at exit |
| `flock` on BeeGFS is node-local | no locks: publishing is copy into a hidden directory, `sha256sum -c`, then an atomic rename |
| distinct job names | `c2ham-grid_<key>`, `c2ham-rows_production_plan_r<rows>`, `c2ham-task_...` (arrays), `c2ham-probe` |
| never touch other jobs | `submit.py` only queries `squeue -u $USER`; it refuses to submit a row that any queued job of yours already covers (matched by the destination/task identity in `--comment`, packed or array) |

Node-local disks differ by vendor (probes 574034 and 574042, pilot 574037):
Intel nodes (<NODE>) have a 568 GB `/local1` on a **rotating disk** (143 MB/s
write, 150 MB/s read); AMD nodes (<NODE>, <NODE>) have only **84 GB** (424 MB/s
write, 656 MB/s read). Row jobs fit everywhere (they stage at most the 52 GB
N=1024 grid). The grids for N=768 (122 GB of node-local space) and N=1024
(287 GB) therefore run on Intel `defq` nodes, where the N=1024 generator writes
and re-reads a 208 GB memory-mapped array (about 5-6 h; the profile allows
12 h), or are built on Expanse and copied with `cluster/sitekit/transfer_grid.sh`
(grids are site-independent). The N=512 grid (38 GB) also fits the AMD nodes.
The AMD fleet is not homogeneous (<NODE> is an EPYC 7532, <NODE> an EPYC 7543).

Pilot (N=512, order 1, lambda 0.1) on amdq node <NODE>: grid 167 s with 32
workers pinned to package 0 (37 GB anonymous memory), row 173 s (2.3 busy
cores, 10.9 GB): about 2.8 times faster per lambda than Expanse's EPYC 7742.
Its raw partial sums agree with the Expanse pilot to 6.9e-11 (2.1e-15
relative) on all 512 cutoffs (`results/symmetry/pilot`).

Preemption note: `debugq` and `amddebugq` have a higher priority tier than
`preq`/`amdpreq`, so a debug job can preempt (requeue) other users' or other
campaigns' preemptible jobs. The N = 12 smoke grid job 574035 did so for one
`preq` job (requeued under its own id by Slurm). Keep debug use short and rare.

## 2. One-time setup

On the Mac, after committing:

```bash
bash cluster/symmetry/make_tarball.sh --upload symmetry
# -> <SCRATCH>/lri_c2/pkg/lri_c2_<commit12>.tar(.sha256), ~/lri_c2/pkgs/lri_c2_<commit12>/ on symmetry
```

On `<NODE>` (once, about one minute; idempotent; refuses to substitute versions):

```bash
cd ~/lri_c2/pkgs/lri_c2_<commit12>
bash cluster/symmetry/setup_env.sh                  # -> ~/envs/lri_c2/py3.13-mamba (CPython 3.13.3)
PY=$HOME/envs/lri_c2/py3.13-mamba/bin/python
$PY cluster/sitekit/test_sitekit.py && $PY cluster/symmetry/test_symmetry.py
```

## 3. Launching

Survey first, then dry-run, then submit (from the code copy on `<NODE>`):

```bash
export PATH=/cm/shared/apps/slurm/current/bin:$PATH
sinfo -h -p amdq -o '%t %D'; sinfo -h -p defq -o '%t %D'; scontrol show res | grep -E 'ReservationName|Nodes='
squeue -u $USER
cd ~/lri_c2/pkgs/lri_c2_<commit12>; PY=$HOME/envs/lri_c2/py3.13-mamba/bin/python
$PY cluster/symmetry/submit.py --check
$PY cluster/symmetry/submit.py --stage P1                 # dry run: 1 grid job + 2 row jobs (rows 1+2, row 3)
$PY cluster/symmetry/submit.py --stage P1 --submit
$PY cluster/symmetry/submit.py --stage P2 --submit        # 1 grid job + array of 2 one-row node jobs
$PY cluster/symmetry/submit.py --probe --submit           # node probe (debug partitions)
```

AMD only (for example to compare with Expanse's AMD nodes):
`--grid-resources partition=amdq --task-resources partition=amdq`. Before P2 you
may copy an Expanse-built grid instead of building it here:

```bash
bash cluster/sitekit/transfer_grid.sh --from expanse --to symmetry --grid N1024_o4_r4p5_src<tag>
```

The grid job then finds the grid published and exits at once.

## 4. Monitoring, collection, cleanup

```bash
squeue -u $USER -o "%.18i %.12P %.40j %.8T %.10M %R" | grep c2ham
sacct -j <ids> -S now-2days -E now -o JobID%20,JobName%40,Partition,NodeList,State,Elapsed,MaxRSS,ExitCode
tail -f <SCRATCH>/lri_c2/logs/c2ham-rows_production_plan_r1-2_<id>.out           # job log
tail -f <SCRATCH>/lri_c2/logs/c2ham-rows_production_plan_r1-2_<id>_row1.log      # live solver output
cat <SCRATCH>/lri_c2/receipts/<job name>_<id>/receipt.json
```

(`sacct -S` needs `-E now` on Slurm 21.08.) On the Mac:
`bash cluster/symmetry/collect.sh` (outputs land in `outputs/symmetry/production_plan_<UTC>/`),
then merge with the Expanse collection as described in `cluster/sitekit/README.md`.
`/local1/$USER/job_<id>` is removed by the job itself; delete grids under
`<SCRATCH>/lri_c2/grids/` once their rows are collected; remove
`.<name>.partial.<jobid>` directories only after the job has left the queue.
Check the BeeGFS quota with `beegfs-ctl --getquota --uid $USER`.

## 5. Cost and wall time

No SU: the cost is node-hours (whole nodes). `submit.py --check` prints, per
job, the wall limit and the projection; summary in `cluster/sitekit/README.md`.
