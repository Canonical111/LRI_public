# Running the C2 extension on SDSC Expanse

This is the Expanse site of the multi-site launch layer. The shared,
site-independent code is in [`cluster/sitekit/`](../sitekit/README.md) (staging,
checksums, job scripts, monitor, receipts, publishing, collection, merging,
the `submit.py` driver); the physics rows are in the site-neutral plan
`cluster/production_plan.json`; this folder holds only the Expanse profile and
thin wrappers. It changes **no scientific numerics**: the solver, matrix
elements, denominators, counterterms, tail coefficients and conversions are
those of the package. The older proposal `cluster/extension_plan.json` is kept
unchanged for reference. The same rows can run on symmetry
(`cluster/symmetry/`); records of both sites have one format and are merged with
`cluster/sitekit/merge_records.py`.

Nothing here computes a continuum C2. New records are fixed-regulator inputs
for an analysis that still has to be generalised to arbitrary N (see
`cluster/README.md`, section 5).

| File | Role |
|---|---|
| `profile.json` | Expanse facts (account <ACCOUNT>, partitions, limits, billing), paths, per-N resource sizing, and the pilot calibration |
| `setup_env.sh` | builds the pinned environment (CPython 3.13.5 + `requirements-tested.txt`) in `$HOME/envs/lri_c2` |
| `submit.py`, `make_tarball.sh`, `collect.sh` | wrappers of `cluster/sitekit/` with the Expanse profile |
| `test_expanse.py` | Expanse-profile tests (limits, documented commands as dry runs, wrappers) |
| `../production_plan.json` | PILOT / P1 / P2 rows and science rules, shared with symmetry |
| `../sitekit/grid_job.sbatch`, `rows_job.sbatch`, `probe_job.sbatch` | the job scripts (one-row arrays here) |

## 1. Where things live

| What | Where | Why |
|---|---|---|
| Python environment | `$HOME/envs/lri_c2/py3.13.5` (+ `bin/uv`, `python/`, `cache/`), ~0.46 GB, ~14k files | many small files: fast on home NFS, slow and quota-counted on the 90%-full Lustre; home is for code |
| code copy for submitting | `$HOME/lri_c2/pkgs/<tarball name>/` (~10 MB) | `submit.py` runs from the code that the jobs will stage |
| package tarballs | `$LUSTRE/pkg/<name>.tar` + `.tar.sha256` | one large file per version; jobs never copy file trees within Lustre |
| published grids | `$LUSTRE/grids/<key>_src<tag>/` (`.npy`, `.json`, `grid_receipt.json`, `SHA256SUMS`) | `<tag>` hashes the scientific sources, so code changes never reuse an old grid |
| task outputs | `$LUSTRE/outputs/production_plan/<task name>/` (records, `_analysis` sidecars, `run_receipt.json`, `task_receipt.json`, `job_receipt.json`, `run_log.txt`, `SHA256SUMS`; the pilot published by the first version has `expanse_job.json` instead) | immutable once published |
| job receipts | `$LUSTRE/receipts/<job name>_<job id>/` (`receipt.json`, `monitor_*.json`, `samples_*.jsonl`, `env_check.json`, `phases.txt`) | timing per phase, peak memory, scratch use, versions |
| Slurm logs | `$LUSTRE/logs/<job name>_<job id>.out`, arrays `<job name>_<array id>_<row>.out`; live row logs `<job name>_<job id>_row<row>.log` | |
| submission records | `$LUSTRE/submissions/<UTC>_<plan>_<stage>.json` | exact sbatch commands and job IDs |
| temporary arrays | `/scratch/$USER/job_$SLURM_JOB_ID` on the node (NVMe), removed by Slurm at job end | the 208 GB temporary grid array at N=1024 must not touch Lustre or home |

`$LUSTRE` = `<SCRATCH>/temp_project/lri_c2` (smoke tests use `.../lri_c2_smoke`).

Measured node-local scratch (2026-10-12): standard compute/shared/debug nodes
have one 916 GB NVMe (`/dev/nvme0n1p1`, ~870 GB free on an otherwise busy node),
**shared by every job on that node**; large-shared nodes have a 2.9 TB RAID0 of
two NVMe drives (3.4 GB/s write, 6.3 GB/s read with direct I/O). `sha256sum`
runs at ~1.3 GB/s. Each job checks free space before starting work and exits 75
if the node cannot hold its arrays.

## 2. One-time setup

On the Mac (or any git checkout of this package), after committing:

```bash
bash cluster/expanse/make_tarball.sh --upload expanse
# -> $LUSTRE/pkg/lri_c2_<commit12>.tar(.sha256) and ~/lri_c2/pkgs/lri_c2_<commit12>/ on Expanse
```

On the Expanse login node (once; idempotent, about 6 minutes, needs network):

```bash
cd ~/lri_c2/pkgs/lri_c2_<commit12>
bash cluster/expanse/setup_env.sh
PY=$HOME/envs/lri_c2/py3.13.5/bin/python
$PY cluster/sitekit/test_sitekit.py && $PY cluster/expanse/test_expanse.py && $PY cluster/test_cluster.py
```

Expanse offers `python/3.8.5` (module), `anaconda3/2021.05` (3.8) and system
3.6.8, none of which can host the tested wheels; `setup_env.sh` installs a
pinned `uv` (release checksum verified), CPython 3.13.5 and the exact versions
of `requirements-tested.txt`, and records everything in
`py3.13.5/lri_env_receipt.json`. Every job re-checks the versions and exits 78
on a mismatch.

## 3. Launching

Always dry-run first (the default); it prints the checks, the SU estimate and
the exact `sbatch` commands. Add `--submit` to submit. From the code copy:

```bash
cd ~/lri_c2/pkgs/lri_c2_<commit12>
PY=$HOME/envs/lri_c2/py3.13.5/bin/python
$PY cluster/expanse/submit.py --check                      # whole plan, no Slurm needed
$PY cluster/expanse/submit.py --stage PILOT                # dry run
$PY cluster/expanse/submit.py --stage P1 --submit          # N=768: one grid job + one task array (rows 1-3)
$PY cluster/expanse/submit.py --stage P2 --submit          # N=1024: one grid job + one task array (rows 4-5)
$PY cluster/expanse/submit.py --tasks 2 --submit           # resubmit one row (published rows are skipped)
$PY cluster/expanse/submit.py --probe --probe-aux --submit # node probe + auxiliary-cutoff benchmark
```

What happens (the safety rules are listed in `cluster/sitekit/README.md`):
`submit.py` first checks that this code copy is exactly the uploaded tarball
(exit 65 otherwise) and exports the tarball, plan and source hashes, which every
job re-checks after staging. A grid job is submitted only if an unfinished row
needs the grid, the grid is not published (complete and verified) and no
queued job carries the same destination in its `--comment`; tasks become one array per resource profile
(array task ID = plan row, `LRI_ROW_MODE=array`), throttled by
`max_concurrent` (large-shared is capped at 2 running per user), depending
`afterok` on the grid job and killed automatically if it fails
(`--kill-on-invalid-dep=yes`). Rows whose outputs are published and verify are
left out; an incomplete or corrupt published directory stops the submission
(inspect it, never overwrite); a row already queued or running in any job
(matched by its destination and task identity) is refused. Profiles never put
more than 64 threads/workers into one process (one EPYC 7742 package). If a
profile uses `compute`, `submit.py` counts the RUNNING and PENDING
`normal`-QOS jobs of the whole <ACCOUNT> account and refuses (no override) when
they plus the new jobs would exceed 22, keeping 10 of the 32 slots free.

Per-job steps (all logged with timestamps, phases recorded in the receipt):
copy the tarball and its `.sha256` to node-local scratch, verify, extract,
verify every file against `STAGE_MANIFEST.sha256`, check that the running batch
script is the shipped one, check the environment versions, count physical
cores (capped at 64), check node-local space, then

* grid job: `run_task.py prepare-grid --cache-root <node-local>` under the
  resource monitor; hash the three grid files; copy them to a hidden
  `.<dir>.partial.<jobid>` directory on Lustre (stripe count 8), re-read and
  verify them there, then rename the directory into place;
* task job: copy the published grid to node-local scratch and verify
  `SHA256SUMS` (`run_task.py` additionally checks the grid receipt, source
  hashes, shape and metadata), run `run_task.py run` for the row with
  `--workers`/`--fft-workers` = physical cores (BLAS/OpenMP pools stay at one
  thread, as in `run_task.py`), write `job_receipt.json` (site, node, CPU,
  topology, thread settings, phases, peaks) and `run_log.txt`, hash and publish the
  output directory the same way.

Exit codes: 64 usage, 65 staged package, plan or sources differ from what was
submitted, 73 cannot create, 74 staging/checksum/publish I/O or a corrupt
published directory, 75 not enough node-local scratch (resubmit), 78 environment
mismatch; other
codes come from the solver. Once the package is staged, every job writes a
receipt, also on failure; a staging failure shows only in the Slurm log and
the exit code.

## 4. Monitoring

```bash
squeue -u $USER -o "%.18i %.9P %.40j %.8T %.10M %.6D %R"
sacct -j <ids> -o JobID%20,JobName%40,Partition,State,Elapsed,MaxRSS,ExitCode
sstat -j <id>.batch --format=MaxRSS,AveRSS            # running jobs
tail -f $LUSTRE/logs/lri_c2_grid_N768_o4_r4p5_<id>.out
tail -f $LUSTRE/logs/lri_c2_task_production_plan_N768_<job id>_row<row>.log   # live solver output
tail -f $LUSTRE/logs/lri_c2_task_production_plan_N768_<array id>_<row>.out     # job log
cat $LUSTRE/receipts/<job name>_<id>/receipt.json      # phases, peak memory, scratch, versions
```

Grid logs print `PARALLEL K done total seconds` about 20 times, then six
`FFT U` lines. Task logs print `RUN ...` and one `Saved cluster_k*_a*_N*.json
finite-cutoff h = ...` per lambda. The monitor line `MONITOR grid|task: ...`
summarises wall time, CPU time and peaks: `cgroup_anon_peak` is the
anonymous memory of the job, `tree_pss_peak` the sum over the worker processes
without double counting (it includes mapped pages of the memory-mapped arrays),
`largest_maxrss` what `/usr/bin/time -v` would report. `sacct` MaxRSS is
sampled per step; prefer the receipt. Look at each log about ten minutes after
the job starts: header written, progress lines advancing, no early exit.

## 5. Collecting results

On the Mac, from the package root:

```bash
bash cluster/expanse/collect.sh                         # plan production_plan by default
# -> outputs/expanse/production_plan_<UTC>/ with outputs/, receipts/, record_index.json, overlap_vs_archived.json
```

`collect.sh` packs `outputs/<plan>/` and `receipts/` into one tarball on Lustre,
copies it, verifies its checksum and every task's `SHA256SUMS`, then runs
`cluster/collect_records.py --compare-overlaps` and
`compare.py archive-overlaps` (differences against the archived N=256/384
records of the same order and lambda). Neither performs a continuum fit.

## 6. Cleanup

* Node-local `/scratch/$USER/job_<id>` is removed by Slurm when the job ends.
* Grids are large (`N768`: 21.8 GB, `N1024`: 51.7 GB). Delete a grid once all
  rows that use it are published and collected:
  `rm -rf $LUSTRE/grids/N1024_o4_r4p5_src<tag>` (one large file: fast).
* A killed job may leave `$LUSTRE/grids/.<dir>.partial.<jobid>` or
  `$LUSTRE/outputs/<plan>/.<task>.partial.<jobid>`; remove them after
  `squeue -j <jobid>` shows the job is gone. They are never read.
* Old tarballs and code copies: `$LUSTRE/pkg/lri_c2_<old>.tar*`,
  `~/lri_c2/pkgs/lri_c2_<old>/`; collected tarballs: `$LUSTRE/collected/`.
* The environment can be rebuilt at any time; `~/envs/lri_c2/cache` (~0.18 GB)
  may be deleted.

## 7. Resources and cost

Measured on Expanse (PILOT, 2 x EPYC 7742, large-shared node; details in
`profile.json` -> `calibration` and `results/expanse/pilot/`):

| Job | Measured |
|---|---|
| grid N=512, 16 workers | 305 s compute (272 s phase slices, 29 s final FFT), 14.3 busy cores, anonymous peak 22.2 GB (51.4 GB with page cache of the memory-mapped arrays), 29.8 GB node-local scratch; hash 5 s, publish + re-verify on Lustre 32 s |
| task N=512, order 1, one lambda | 486 s: mixed sums at 16384 ~150 s, raw cube sums ~320 s, tail at 8192 ~10 s; 1.5 busy cores of 16; peak 10.9 GB (mixed stage); grid fetch + verify 8 s |
| mixed sums, lambda 0.05 (probe) | 4096: 6.5 s/0.8 GB; 8192: 37 s/2.8 GB; 16384: 148 s/10.9 GB; 32768: 602 s/43 GB |
| leading tail, lambda 0.05 (probe) | 2048: 0.7 s; 4096: 2.5 s; 8192: 9.4 s/3.4 GB; 16384: 37 s/13 GB |

Compared with the reviewer's EPYC 7282 numbers (N=384: grid 192 s with 16
workers, ~160 s per lambda, 13.7 GB) scaled to N=512, the grid ran about 35%
faster and the raw cube stage about 15% faster; the larger mixed cutoff adds
~150 s per lambda. Projected per-lambda times (N=768: ~21 min, N=1024: ~45 min)
fall inside the reviewer's ranges (10-15 and 40-60 min plus the mixed stage),
and the memory models (40 and 95 GB including page cache; 29 and 69 GB
anonymous) at or below them (40-60 and 110-130 GB).
Default profiles (`submit.py --check` prints the same numbers):

| Stage | Job | Partition, CPUs, memory | Wall limit | Projected run | Peak memory model | Node-local scratch | SU/h | SU projected (at wall limit) |
|---|---|---|---|---|---|---|---|---|
| PILOT | grid N=512 | large-shared, 16 (16 workers), 64 GB | 1 h | 0.1 h (measured) | 23 GB | 38 GB | 64 | 6 (64) |
| PILOT | task row 0 | large-shared, 16, 64 GB | 2 h | 0.15 h (measured) | 13 GB | 9 GB | 64 | 10 (128) |
| P1 | grid N=768 | large-shared, 24 (24 workers), 128 GB | 2 h | 0.3 h | 77 GB | 122 GB | 96 | 29 (192) |
| P1 | tasks rows 1-3 (3, 3, 4 lambdas) | shared, 16, 64 GB, 3 at once | 6 h | <= 1.4 h each (~21 min per lambda) | 40 GB | 26 GB | 32 | 3 x 45 (3 x 192) |
| P2 | grid N=1024 | large-shared, 32 (32 workers), 256 GB | 3 h | 0.6 h | 183 GB | 287 GB | 128 | 77 (384) |
| P2 | tasks rows 4-5 (2 lambdas each) | large-shared, 8, 160 GB, 2 at once | 6 h | 1.6 h each (~45 min per lambda) | 95 GB | 59 GB | 40 | 2 x 64 (2 x 240) |

P1 + P2 together: about **370 SU** projected, at most 1630 SU if every job ran
to its wall limit (Expanse charges the full wall-limit reservation at job start
and refunds the unused part at the end). Margins: wall limits are 3.5-7x the
projections; memory requests are at least 1.6x the models, which are
themselves conservative (pilot grid 22.2 GB measured vs 23.0 GB model; task
10.9 GB vs 12.9 GB). Projections scale the pilot: grid slice phase
~ (M/2+1) M^2 log M / workers, raw cube stage ~ K^3 per lambda, mixed and tail
stages independent of N. The test jobs of this revision cost 20.4 SU in total
(probe 5.0, pilot grid 6.2, pilot task 8.9, three smoke chains and three
regression runs 0.3; `sacct` elapsed time x billing rate).

Billing (Slurm TRES weights on Expanse): shared = max(cores, GB/2) SU/h;
large-shared = max(4 x cores, GB/4) SU/h; compute = 128 SU/h per node.
Large-shared is therefore cheapest for memory-heavy jobs with few busy cores
(grids, N=1024 tasks) and has a 2.9 TB node-local NVMe; it allows 4 running
jobs per account and 2 per user, which `submit.py` respects. Standard nodes
(shared/compute) have a 916 GB NVMe shared by all jobs on the node, enough for
the N=768 grid but not a safe default for the 260 GB of the N=1024 grid.

If large-shared is unavailable (on 2026-10-12 three of its four nodes were
drained or reserved), override the profile, for example

```bash
$PY cluster/expanse/submit.py --stage P2 --submit \
    --grid-resources partition=compute,cpus=128,mem_gb=240,time=03:00:00,workers=32 \
    --task-resources partition=shared,cpus=16,mem_gb=160,time=06:00:00
```

(`compute` is a whole node at 128 SU/h and counts against the 32-job `normal`
QOS of the account; shared at 160 GB costs 80 SU/h). Tasks are mostly
single-threaded (FFT workers help only in parts of the raw cube stage), so
more cores do not shorten them much.

## 8. Tests and regression

```bash
python cluster/sitekit/test_sitekit.py --output outputs/sitekit_tests.json   # shared layer, both profiles
python cluster/expanse/test_expanse.py --output outputs/expanse_tests.json
python cluster/test_cluster.py --output outputs/cluster_tests.json
bash cluster/sitekit/regression.sh <old package root> . outputs/regression <python>
```

`regression.sh` runs `validate`, `analyze`, `analyze-recorded`, `demo` and the
N=12 cluster smoke task in two package trees with one interpreter and compares
all outputs. The evidence for this revision is in `results/expanse/`.
