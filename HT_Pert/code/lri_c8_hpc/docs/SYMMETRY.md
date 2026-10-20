# Runbook: C8 campaign on symmetry `defq`

## Layout

- Code: a fixed checkout on home NFS, e.g. `~/lri_c8_hpc` (a clone of this repository).
  Do not edit it while jobs run: the Numba cache index is keyed on source paths and
  mtimes, and every output fingerprints `src/lri_c8`.
- Data: `C8_DATA=<SCRATCH>/lri_c8` (BeeGFS) with
  `logs/`, `validation/`, `numba_cache/`, `campaigns/`, `runs/<name>/`, `fs_probe/`.
- Stack: `module load anaconda3/2023.07-2` (Python 3.11.4, numpy 1.24.3, numba 0.57.0,
  scipy 1.10.1, threadpoolctl 2.2.0, pytest 7.4.0, MKL). `slurm/symmetry_env.sh`
  loads it, refuses any other stack, pins `NUMBA_THREADING_LAYER=tbb`, and sets a
  source-digest-keyed `NUMBA_CACHE_DIR`.
- Nodes: defq <NODE>-068, 2 x 20-core Xeon Gold 6148, 191488 MB, exclusive, 24 h.
  Jobs request `--exclusive --mem=180G`; items are admitted up to 170 GiB.

## Sequence (login node; light work only)

```bash
cd ~/lri_c8_hpc && python3 tests/verify_manifest.py       # code matches the manifest
slurm/submit_defq.sh validate                              # ~1 h on one defq node
```

The validation job writes `$C8_DATA/validation/<src16>_<jobid>/receipt.json`
(manifest, pytest with a fresh Numba cache, the 38-point saved-grid replay, the
original solver against stored and ranked at L=60 for both prescriptions, and a
BeeGFS probe; `make_campaign.py` refuses a receipt missing any of these or with a
comparison cutoff below 60), records `node.txt` (lscpu, numactl -H, free, kernel, cgroup), warms the
production Numba cache, and copies the receipt to
`$C8_DATA/validation/receipt_<src16>.json`. Read the log and the receipt before going on.

```bash
export C8_ROOT=~/lri_c8_hpc C8_DATA=<SCRATCH>/lri_c8 C8_CACHE_ROLE=login
source slurm/symmetry_env.sh
python scripts/make_campaign.py --cutoffs $(seq 52 2 92) --schemes raw vacuum_only \
  --outer-backend auto --threads 40 --memory-limit-gib 170 \
  --receipt $C8_DATA/validation/receipt_$C8_SRC16.json \
  --output $C8_DATA/campaigns/c8_L52-92.json
slurm/submit_defq.sh lanes $C8_DATA/campaigns/c8_L52-92.json $C8_DATA/runs/c8_L52-92
```

`--outer-backend auto` picks `stored` while its conservative plan fits 170 GiB
(L<=88, 162.7 GiB) and `ranked` above (L=90 138.4, L=92 168.3 GiB). L>=94 does not
fit the conservative envelope on defq; a calibrated envelope is deferred until the
production items' measured `peak_rss_kib` (recorded in the journals) is reviewed.
With no `--lanes` every item is its own array task, largest first; the wrapper
throttles to `C8_MAX_NODES` (default 8) concurrent nodes.

## Monitoring

```bash
squeue -u $USER
python scripts/campaign_info.py status $C8_DATA/campaigns/c8_L52-92.json $C8_DATA/runs/c8_L52-92
tail -f $C8_DATA/runs/c8_L52-92/logs/<jobname>_<arrayjob>_<lane>.out
```

Per lane, `runs/<name>/journals/<campaign16>/lane_<k>.json` appends one record per
attempt: job, host, binding, physical cores, and per item the return code, status,
output sha256, C8, seconds and peak RSS.

## Exit codes and what to do

| exit | meaning | action |
|---|---|---|
| 0 | every item of the lane accepted | none |
| 75 | stopped at a safe boundary after a signal (time-limit warning, scancel --signal) | rerun the same `submit_defq.sh lanes` command |
| 73 | lane or item owned by another job, or flock held | wait for that job; rerun |
| 64 | allocation smaller than the frozen thread count, or Python stack / Numba layer differ from the campaign | fix the submission or environment |
| other (1, 137, ...) | real failure (exception, OOM, supervisor error) | read the log and journal; the lane is held back until `C8_RETRY_FAILED=1` |

`submit_defq.sh lanes` takes a cross-node mutex (`<out>/.submit.lock`, an atomic mkdir
on BeeGFS) and, while holding it, refuses if any job writing to the same output
directory is queued or running (by job-name prefix and by the job ids recorded in
`<out>/submissions.txt`; a failed `squeue` refuses too). Only then does it move owner
files to `owners_stale/<timestamp>/` (`scripts/clean_owners.py`: only if none records a
live job, none lacks a Slurm job id, and all are readable) and submit the lanes that
still need work. It is the only supported launcher of lanes.
Extra arguments go to sbatch only from an exact allowlist in `--name=value` form
(`--time=`, `--partition=`, `--qos=`, `--account=`, `--exclude=`, `--nodelist=`,
`--begin=`, `--dependency=`, `--reservation=`, `--mail-type=`, `--mail-user=`,
`--comment=`, `--nice=`, `--hold`); anything else, including abbreviations and short
options, is rejected, so the job name, array, export, output and chdir stay the wrapper's.

A lane is held (reported, not resubmitted) when an existing output is unreadable or
does not match its frozen item (source, cutoff, scheme, references, backend, threads,
stack, layer; move the file aside), when its last attempt failed, or when its last
attempt has no exit record and `sacct` does not report an interruption (TIMEOUT,
CANCELLED, NODE_FAIL, PREEMPTED, ...), or when the lane's latest submitted array task
(`<out>/submissions.txt`) left no journal attempt and did not end interrupted (for
example it failed while loading the environment). `C8_RETRY_FAILED=1` releases the
last three. `campaign_info.py todo` also refuses a campaign frozen for another source,
stack or Numba layer, so it never reaches sbatch. Jobs are submitted `--no-requeue`;
owner files are never taken over by a job, only moved aside by the wrapper.

## Export

```bash
python -m lri_c8 export --inputs $C8_DATA/runs/c8_L52-92/accepted/raw_L*_d8.json \
  --output $C8_DATA/exports/raw_L52-92.json
python -m lri_c8 export --inputs $C8_DATA/runs/c8_L52-92/accepted/vacuum_only_L*_d8.json \
  --output $C8_DATA/exports/vacuum_only_L52-92.json
```

Rows with different backends (stored/ranked) or thread counts export together; each
row keeps its full configuration. Prescriptions are exported separately.
