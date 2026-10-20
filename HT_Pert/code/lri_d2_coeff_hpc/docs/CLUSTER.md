# Running the coefficient tasks on Expanse or symmetry

This runbook covers the cluster layer added on top of the solver (`cluster/`, `scripts/submit.py`,
`scripts/validate_cluster.py`, `scripts/make_release.py`, `scripts/stack.py`). The solver itself
(`src/lri_coeff/`) is unchanged, so the source digest `550e9266…` of the archived L=22 pilot still applies
and result identities stay comparable.

## Design

- **One Slurm job per task** (cutoff L, degree, scheme), sized from that task's own memory plan: no array
  that requests the largest task's memory for every element.
- **Code comes only from a checksummed release tar.** `scripts/make_release.py` builds it with `git archive`
  from a clean commit and checks it against `MANIFEST.sha256`. Each job copies the tar to node-local disk,
  checks its SHA-256 against the value recorded at submission, unpacks it there, and verifies every file
  against `MANIFEST.sha256` before running anything. Nothing is copied file by file on Lustre or BeeGFS.
- **Node-local:** code, working directory, Numba cache, compiled native library, temporary files and the
  solver's checkpoints, in a private (0700) directory made by `mktemp` under `/scratch/$USER/job_<id>`
  (Expanse) or `/local1` (symmetry), after checking that every component of the parent path is a real
  directory owned by root or by you (group/other-writable only if root-owned and sticky). Only that
  directory is removed when the job ends. **Shared data root** `$LRI_COEFF_DATA`: results and their locks,
  one checkpoint archive per task, receipts, logs.
- **Imports:** the solver runs with `PYTHONPATH` set to the staged `src` only and `PYTHONSAFEPATH=1`, from the
  private working directory, so nothing on the data root can shadow the checked code.
- **No shared graph cache** (`make_campaign.py --cache-mode none`, the default): each job builds its graph in
  memory (seconds to minutes), instead of memory-mapping tens of GB of arrays from Lustre/BeeGFS.
  `submit.py` and cluster jobs refuse manifests made with `--cache-mode shared` (left for local use).
- **Checkpoints** at complete wave, moment or quotient stages, at most every 30 minutes
  (`--checkpoint-seconds 1800`), plus one at the next stage boundary after `USR1`/`TERM`/`INT`. The solver
  writes them to node-local disk (a generation is about 120 `.npy` files for the consistent scheme, roughly
  the "checkpoint GiB" column below). `scripts/ckpt_sync.py`, which runs the solver as a child, publishes
  each new generation within a minute as ONE file, `<checkpoint dir>/task-<digest16>.tar`: hard-link
  snapshot, tar written under a temporary name, fsync, atomic rename, so the previous archive stays valid
  until the new one is complete. Before the rename every file is read back from shared storage and checked
  against the SHA-256 digests the solver recorded (the same check `--resume` makes); a generation that fails
  is never published.
  A resumed job unpacks the archive on its own node before the solver starts (the solver then checks every
  array's SHA-256). The archive is deleted when the task succeeds. If the newest checkpoint still cannot be
  published after the solver stopped (three attempts), the job exits 76 instead of 75, leaves its node-local
  directory in place and says so in the log; partial archives of hard-killed earlier jobs are removed once
  `squeue` reports those jobs ended.
- **Threads** = physical cores in the job's CPU set (`cluster/job.sbatch`), passed to the solver through
  `LRI_COEFF_THREADS`. Thread count does not change the numbers (tested) and is not part of a result's identity.
- **Validation gate.** `submit.py campaign` refuses to submit unless a compute-node validation of the *same
  release tar on the same site* has passed. Each task job also checks that its node's Python, numpy, scipy,
  numba, venv and compiler equal those recorded in that receipt.
- **Signals.** Jobs get `--signal=B:USR1@900`. Only the batch shell receives it; `cluster/forward.sh` runs the
  solver in the background and forwards `USR1`, `TERM` and `INT`. The solver checkpoints at its next stage
  boundary and exits 75. A stage can take a long time at large L, so the checkpoint may come from the
  periodic one rather than the signal. Jobs use `--no-requeue`; resuming is an explicit resubmission.

## Sites

| | Expanse | symmetry |
|---|---|---|
| `LRI_COEFF_SITE` | `expanse` | `symmetry` |
| software | modules `cpu/0.21.2a gcc/13.3.0 python/3.11.9 slurm/expanse/23.02.7` | system g++ 11.4, Slurm in `/cm/shared/apps/slurm/current/bin` |
| venv (`LRI_COEFF_VENV`) | `~/lri2d_coeff/venv` (from module Python 3.11.9) | `~/lri2d_coeff/venv` (from anaconda3/2023.07-2 Python 3.11.4) |
| data (`LRI_COEFF_DATA`) | `<SCRATCH>/temp_project/lri2d_coeff` | `<SCRATCH>/lri2d_coeff` |
| partitions (automatic) | `shared` ≤ 243 GiB, `large-shared` ≤ 2000 GiB; account `<ACCOUNT>` | `amdq` ≤ 245 GiB, `largememq` ≤ 370 GiB; whole node, all cores, all of its memory |
| other partitions | — | `defq` (≤ 180 GiB), `amddebugq`/`debugq` (1 h) with `--partition` |
| wall limit | 48 h | 24 h |

Paths are `lri2d_coeff`, never `lri2d`: on Expanse `~/lri2d` and `temp_project/lri2d` belong to another project.
On Expanse `shared`, CPUs are raised to match the memory charge (Expanse charges the larger of cores and
memory / 1.9 GiB), so those cores cost nothing extra; `--cpus` sets the minimum (default 16).

## Sizing (degree 8, consistent scheme; raw is about 0.6× the time)

`plan GiB` is the solver's conservative plan (the measured L=22 peak was 0.75× of it). `memory_gib` adds the
campaign's 10%. The job needs `memory_gib` plus max(4 GiB, 5%); that is Expanse's `--mem`, while symmetry jobs
ask for the whole node's memory (245G on amdq, 370G on largememq). The default `--time` comes from a rough model
(50 s for the L=22 pilot at 4 threads, ×3.5 per +2 in L, ×4 safety, +30 min, at least 1 h), capped by the chosen
partition's limit; an explicit `--time` above that limit is refused. The model has not been checked above
L=22: look at the first L=26–28 jobs and pass `--time` explicitly after that.

| L | states | plan GiB | task `memory_gib` | needed (Expanse `--mem`) | checkpoint GiB | Expanse | symmetry | default `--time` Expanse / symmetry |
|---|---|---|---|---|---|---|---|---|
| 24 | 1.55e+07 | 8.7 | 9.75 | 14G | 0.4 | shared 16 cpus | amdq | 01:00:00 / 01:00:00 |
| 26 | 3.79e+07 | 21.2 | 23.5 | 28G | 0.9 | shared 16 cpus | amdq | 02:00:00 / 02:00:00 |
| 28 | 9.06e+07 | 51.1 | 56.25 | 61G | 2.2 | shared 33 cpus | amdq | 03:00:00 / 03:00:00 |
| 30 | 2.12e+08 | 120.7 | 133.0 | 140G | 5.0 | shared 74 cpus | amdq | 09:00:00 / 09:00:00 |
| 32 | 4.88e+08 | 280.3 | 308.5 | 324G | 11.2 | large-shared 21 cpus | largememq | 30:00:00 / 24:00:00 |
| 34 | 1.10e+09 | 639.2 | 703.25 | 739G | 24.7 | large-shared 48 cpus | none (refused) | 48:00:00 / — |

Expanse charges a job's full request (charged cores × wall limit) when it starts and refunds the unused
part at the end; `submit.py` prints that upper bound. Large-shared allows 2 running jobs per user.

## One-time setup

On the Mac (or wherever the git repository is):

```bash
python scripts/write_manifest.py && git commit -am "..."     # only if files changed
python scripts/make_release.py --out dist/
# -> dist/lri2d_coeff-<commit12>.tar, .tar.sha256, .json
```

Copy the three files to `$LRI_COEFF_DATA/releases/` on the chosen cluster (create the directory first), and
unpack a login-node copy from the same tar into home (small files do not belong on Lustre/BeeGFS):

```bash
# on the login node
export LRI_COEFF_SITE=expanse          # or symmetry
R=lri2d_coeff-<commit12>
mkdir -p ~/lri2d_coeff/code/$R && tar -xf $LRI_COEFF_DATA/releases/$R.tar -C ~/lri2d_coeff/code/$R
cd ~/lri2d_coeff/code/$R/lri_d2_coeff_hpc
bash cluster/setup_venv.sh             # once per cluster; refuses to touch an existing venv
source cluster/site.sh && python tests/verify_manifest.py
```

`$LRI_COEFF_DATA` is set by `site.sh`; before sourcing it, use the path from the table.

## Validate on a compute node

```bash
python scripts/submit.py validate --release $LRI_COEFF_DATA/releases/$R.tar            # dry run
python scripts/submit.py validate --release $LRI_COEFF_DATA/releases/$R.tar --submit
```

The job (Expanse `shared` 16 CPUs 30 GiB, symmetry `amdq` node; 1 h) runs `tests/run_all.py` (all 61 tests,
including the reference-engine comparisons, the interrupt/resume drills and the checkpoint-archive resume;
inherited `PYTEST_*` settings are removed and any skip or deselection fails it) and replays the archived L=22
pilot (consistent d8, consistent d7, raw d8) without a graph cache; the coefficients must agree to 1e-10. It
writes `$LRI_COEFF_DATA/validation/<sha16>_<site>_<jobid>/receipt.json` and `tests.json`, and exits 0 only if
everything passed. Log: `$LRI_COEFF_DATA/logs/lri2dc-val-<sha8>-<site>_<jobid>.out`.

## Campaigns

```bash
C=$LRI_COEFF_DATA/campaigns/smoke
python scripts/make_campaign.py --cutoffs 4 6 --schemes raw consistent --output-root $C --manifest $C/campaign.json
python scripts/submit.py campaign --release $LRI_COEFF_DATA/releases/$R.tar --manifest $C/campaign.json            # dry run
python scripts/submit.py campaign --release $LRI_COEFF_DATA/releases/$R.tar --manifest $C/campaign.json --submit
```

Submit such a small smoke campaign first: it exercises the task path of `cluster/job.sbatch` (receipt
match, `run_task.py`, output publication) in a minute. Then make the production manifest, e.g.
`--cutoffs 24 26 28 30 --schemes raw consistent`, in its own directory (`make_campaign.py` refuses to rewrite
an existing manifest with different content, because queued jobs check its SHA-256).

`submit.py campaign` prints one line per task with its state:

| state | meaning | action |
|---|---|---|
| `todo` | no output, no lock, no live job | submitted with `--submit` |
| `live` | a pending/running/suspended job writing this output: job names are derived from the output path alone (`lri2dc-o<hash12>`), so this holds across manifests and configurations; job ids recorded in `submissions.jsonl` are checked too | none |
| `done` | verified, complete output whose identity is the one this solver source gives on the validated stack | none |
| `locked` | `OUTPUT.json.lock` exists but no live job | see "Stale locks" |
| `conflict` | an output exists that does not verify, is incomplete, or has another identity (configuration, source, or Python/numpy/scipy/numba/machine) | move it away |
| `refused` | no partition fits the memory or the requested time | adjust `--partition`/`--time`, or another site |

Options: `--tasks 0-3,7`, `--partition`, `--time HH:MM:SS`, `--cpus N` (Expanse minimum), `--mem-scale 1.3`
(after an out-of-memory failure), `--max-new N`. Submission holds a cross-node mutex
`$LRI_COEFF_DATA/.submit.lock` (mkdir); if a crashed `submit.py` left it, remove it by hand once no
`submit.py` is running. Every submission is appended to `$LRI_COEFF_DATA/submissions.jsonl`.

Logs: `$LRI_COEFF_DATA/logs/lri2dc-o<hash12>_<jobid>.out` (the dry run prints each task's name; `tail -f` it). Results:
`$C/d<degree>/<scheme>_L<L>.json`; task paths in a manifest must be absolute (make_campaign.py writes them so).
Collect with
`python scripts/collect.py --inputs $C/d8/*.json --output $C/coefficients.csv`.

## Interruption and resume

| job exit | meaning | next step |
|---|---|---|
| 0 | result written (or a verified result already existed) | none |
| 75 | stopped at a stage boundary after a signal (wall-time warning or `scancel -b -s USR1`), checkpoint published | rerun the same `submit.py campaign` command |
| 76 | as 75, but the newest checkpoint could NOT be published (shared storage full or failing) | fix the storage; a resubmission restarts from the previous archive, if any |
| 73 | another process holds the output lock | see "Stale locks" |
| 74 | staging failed (tar copy, checksum, unpack, manifest) | resubmit; if repeated, check the node and the tar |
| 3 | node software differs from the pins or the validated receipt | fix the venv/modules, revalidate |
| 2 | setup error (environment, missing variables) | read the log |
| 1 | solver error (guards, identity mismatch, numerical gate) | read the log |
| 137 / OUT_OF_MEMORY | killed by Slurm or the cgroup | lock left behind: see below; resubmit with `--mem-scale` |

A stage may be long at large L; a job killed at the wall limit restarts from the last published periodic
checkpoint. For a graceful stop use `scancel --batch --signal=USR1 <jobid>` (plain `scancel` sends TERM and
kills 30 s later, usually before the next stage boundary).

## Stale locks

There is no automatic stale-lock stealing. If a job died hard (OOM kill, node failure, `scancel` at a bad
moment), `OUTPUT.json.lock/owner.json` remains and the task shows as `locked`. Read `slurm_job` in
`owner.json`, confirm with `sacct -j <id> -X -o JobID,State,End` that it has ended and that no other job
of the task is live, then remove that one lock directory and rerun `submit.py campaign`.

## Data layout

```
$LRI_COEFF_DATA/
  releases/lri2d_coeff-<commit12>.tar(.sha256,.json)
  validation/<sha16>_<site>_<jobid>/{receipt.json,tests.json}
  campaigns/<name>/{campaign.json, d8/<scheme>_L<L>.json, checkpoints/task-<digest16>.tar}
  logs/<jobname>_<jobid>.out
  submissions.jsonl
```
