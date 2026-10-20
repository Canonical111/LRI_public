# Running ht3d on SDSC Expanse (account <ACCOUNT>)

This directory adds an Expanse site layer to the 3D dressed-window HT package. It does
**not** change the numerical code (`code/ht3d/*`, `code/*.py`, `inputs/prior_3d_points.json`:
`ht3d.hpc.source_hash()` is unchanged), and no file listed in `MANIFEST.sha256` is modified,
so `tests/verify_manifest.py` still verifies the 615 original distribution files.

## Model

- **Lane = one x.** One Slurm array element runs a cutoff ladder for one x: an L6 teacher
  (nz24/osc192, keep 20), then window L8, L10, … with nz16. Each step is seeded by the
  previous cutoff, and side checks (smaller nz, raw replay) hang off chosen cutoffs. This is
  the continuation the baseline `campaign.py` used, now resumable and Slurm-native.
- **Step = one unmodified point.** Each step runs the original point driver (`ht3d.hpc.main`)
  as a child, through `child.py`, with `--resume`. Existing valid outputs are reused by the
  driver's own checks.
- **Shared partition.** Thread scaling beyond about 4 is unmeasured, and a single ARPACK problem
  stays on one node. Lanes therefore run on `shared` with a few cores each. Expanse charges
  `shared` by max(cores, memory/1.95 GB) per hour.

## Files

| File | Role |
|---|---|
| `env.sh` | modules (cpu/0.21.2a gcc/13.3.0 python/3.11.9 slurm), pinned venv, single-thread BLAS, node-local Numba/MPL caches; every step checked (`source env.sh \|\| exit 70`) |
| `requirements-expanse.txt` | exact pins (numpy 2.3.5, scipy 1.17.0, numba 0.65.1, …) |
| `make_release.py` | local: deterministic release tarball from a git commit, plus `GIT_SHA` and `RELEASE.sha256` |
| `install.sh` | login node: publish the tarball to Lustre (one file), read-only reference copy in `~/ht3d/code/<tag>`, venv build and pin check |
| `stage.sh` | in jobs: verify the tarball sha256, extract to node-local `/scratch/$USER/job_$SLURM_JOB_ID/rel`, `sha256sum -c RELEASE.sha256`, fail closed (74) |
| `receipt.py`, `validate.sbatch` | on-node validation receipt: verify_manifest and release check on the pristine copy; pytest and the five validators (incl. `validate_l18_fix`) on a writable copy |
| `lanes.py` | lane runner: runtime binding, predecessor snapshot validation, request-digest recompute, stop forwarding |
| `child.py` | step wrapper: gap-free stop hand-off to the unmodified driver |
| `campaign.py` | login-node tool: `freeze`, `submit`, `status`, `recover`, `resubmit` |
| `lane.sbatch` | one lane per array element (only submitted by `campaign.py`) |
| `setup_probe.sbatch` | large-cutoff setup probe via `scripts/probe_large_setup.py` (graph/projector/vertices, per-stage RSS, SVD retry and block logging to `$HT3D_DATA/probe/<job>/`) |
| `probe.py`, `probe.sbatch` | setup-only size probe (graph, projector, vertices; peak RSS) at L14/16/18 |
| `calib_report.py` | per-step timing/RSS and per-attempt SU table for a campaign |
| `specs/smoke.json`, `specs/calibration.json` | the smoke/drill campaign and the stage-1 cost calibration |

## Workflow

Paths: `HT3D_DATA=<SCRATCH>/temp_project/ht3d` (all data, logs and
campaigns) and `~/ht3d/code/<tag>` (read-only reference copy for login-node tools).

```bash
# 1. local: build the release from a committed tree
python cluster/expanse/make_release.py --commit HEAD --out /tmp/ht3d-rel
scp /tmp/ht3d-rel/<tag>.tar expanse:<SCRATCH>/temp_project/ht3d/incoming/

# 2. Expanse login node: install (publishes the tarball, reference copy, venv)
bash ~/ht3d/install.sh $HT3D_DATA/incoming/<tag>.tar <sha256>   # or from the extracted copy's cluster/expanse/
source ~/ht3d/code/<tag>/cluster/expanse/env.sh || exit 70

# 3. validation receipt on a compute node (shared, 8 cores, ~1 h)
# set the bindings in the submitting environment itself, so no stale exported value can win
HT3D_RELEASE_TAR=$HT3D_DATA/releases/<tag>.tar HT3D_RELEASE_TAR_SHA256=<sha> \
       sbatch --export=ALL ~/ht3d/code/<tag>/cluster/expanse/validate.sbatch
#    -> $HT3D_DATA/validation/<job>/receipt.json   (log: $HT3D_DATA/logs/ht3d-validate_<job>.out)

# 4. freeze and submit a campaign
C=~/ht3d/code/<tag>/cluster/expanse
python $C/campaign.py freeze --spec $C/specs/smoke.json --receipt $HT3D_DATA/validation/<job>/receipt.json \
       --release-tar $HT3D_DATA/releases/<tag>.tar --release-tar-sha256 <sha> --out $HT3D_DATA/campaigns/smoke
python $C/campaign.py submit $HT3D_DATA/campaigns/smoke --dry-run      # prints the exact sbatch argv
python $C/campaign.py submit $HT3D_DATA/campaigns/smoke
python $C/campaign.py status $HT3D_DATA/campaigns/smoke

# 5. after a timeout/kill: recover stale claims (sacct-confirmed only) and resubmit unfinished lanes
python $C/campaign.py resubmit $HT3D_DATA/campaigns/smoke --dry-run
python $C/campaign.py resubmit $HT3D_DATA/campaigns/smoke
```

Logs: `$CAMPAIGN/logs/<jobname>_<array>_<lane>.out`, plus per-lane journals in
`$CAMPAIGN/journal/lane_NNN.jsonl` and failures in `$CAMPAIGN/lane_failures/`.

## Safety rules implemented

- **Fail-closed bindings.**
  - Every job verifies the release tarball and every staged file.
  - The lane runner refuses a different source hash, release fingerprint or runtime identity
    (python, numpy, scipy, numba, llvmlite, threadpoolctl, BLAS) than the validated receipt.
- **Chained inputs.**
  - A predecessor output is read once, validated (checksum, gates, request digest recomputed
    from the frozen argv) and only then hashed for its consumer.
  - The driver re-hashes the bytes it reads.
- **Stops.**
  - `--signal=B:USR1@lead` reaches the batch shell, then the runner, then the child.
  - The child checkpoints at a Newton or publication boundary and exits 75. The runner never
    starts a step after a stop.
  - A stop cannot kill a step at any moment of its life.
- **Claims.**
  - Output claims are the driver's atomic `mkdir` claims.
  - `recover` tombstones a claim only when sacct shows the owner's **individual** job id in a
    terminal state **and** squeue does not list it. It re-checks the owner token and directory
    identity immediately before the rename.
  - It runs under the campaign admin lock (atomic `mkdir`, never broken automatically) and is
    never age-based.
- **Campaign binding.** `campaign.py` runs `sbatch` with an explicit environment whose `HT3D_MANIFEST` and
  `HT3D_RELEASE_TAR(_SHA256)` are this campaign's. Inside Slurm, the runner also refuses any job name not
  journaled for its campaign, so a stale exported variable cannot run another campaign. The probe is submitted
  the same way as validation: environment assignments on the `sbatch` command line.
- **Submissions.**
  - The intent is journaled before `sbatch` under a unique job name.
  - Liveness is checked by job name, so a job whose id was lost still blocks duplicates.
  - There is one array per resource tuple and no automatic resubmission.
- **Charges.**
  - Measured SU = Slurm billing TRES × elapsed, over all requeued attempts (`sacct --duplicates`).
  - The estimate uses the shared memory-aware formula. The two are always reported separately.

## Benchmark records (0.2.1rc1)

`tests/validate_benchmarks.py` audits the shipped `results/benchmarks/` records against the
pinned 0.2.0 snapshot (`reference/performance_0_2_0`). Do **not** run `benchmarks/run.py`
inside a release tree: it writes into `results/benchmarks/` with the current 0.2.1 code, and the
audit then (correctly) rejects those records. This is Codex finding L18-01. The fix is to give new
benchmark runs a release-specific output directory; it is pending a decision because it touches
the distribution's benchmark tooling. The receipt and the campaigns never run `benchmarks/run.py`.

## Not validated here

- Physics beyond the inherited checks.
- Scaling past 8 threads.
- L ≥ 16 full solves: measure them with the probe and a continuation campaign first.
- Two campaigns writing the same outputs: freeze confines outputs to `DIR/results`, so do not
  point two campaigns at one directory.
