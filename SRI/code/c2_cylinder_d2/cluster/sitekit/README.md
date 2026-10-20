# Multi-site launch layer (Expanse and symmetry)

One site-neutral plan, one set of job scripts, thin site profiles. The
scientific solver is untouched; every site writes records in the solver's single
format, so records from both sites (and from different regulator families) can
be indexed and compared together.

```text
cluster/production_plan.json   physics rows (PILOT, P1, P2) + science rules; identical on every site
cluster/sitekit/               this folder: site-independent code
cluster/expanse/profile.json   Expanse: account, partitions, limits, billing, per-N sizing, calibration
cluster/symmetry/profile.json  symmetry: partitions, limits, per-N sizing, node facts
cluster/<site>/submit.py       wrappers: sitekit/submit.py --site <site>; also make_tarball.sh, collect.sh
cluster/<site>/setup_env.sh    the pinned Python environment for that site
```

| File | Role |
|---|---|
| `submit.py` | checks rows (lambda*N minima, mixed cutoff) and a site's profiles (partitions, forbidden queues, memory, wall time, threads per package, node-local scratch, cost) and submits: one grid job per missing grid, then row jobs with `afterok` (one-row arrays, or whole-node jobs packing rows one per CPU package) |
| `grid_job.sbatch` | stage the tarball (two sha256 layers) into node-local scratch, `run_task.py prepare-grid` (workers = explicit, or min(one package, memory cap)), publish `.npy`/`.json`/`grid_receipt.json` + `SHA256SUMS` atomically |
| `rows_job.sbatch` | stage, fetch and verify the grid, run one or more plan rows (`numactl`-pinned per package when packed), publish each row with `job_receipt.json` and `run_log.txt` |
| `probe_job.sbatch` | node facts (node-local disk size and speed, CPU/NUMA map, cgroup) and the optional auxiliary-cutoff benchmark |
| `lib.sh`, `jobtools.py` | staging, version check, topology, monitor (peak RSS/PSS, cgroup, scratch), receipts with site, host, CPU vendor/model, topology and thread settings, publish/fetch without locks |
| `make_tarball.sh` | ONE tarball + sha256 from a commit; `--upload <site>` uses the profile's host and roots |
| `collect.sh` | fetch one site's published outputs as one tarball, verify, index (`collect_records.py`) and compare with the archived N=256/384 records |
| `merge_records.py` | merge collections from several sites: verify checksums and record schema, label each record with its site/node/CPU, compare every pair with the same (order, lambda), across sites too |
| `transfer_grid.sh` | copy a published grid between sites (streamed through this machine, verified, published atomically) |
| `compare.py`, `regression.sh`, `aux_cost_probe.py` | output and raw-overlap comparisons, old-vs-new regression, auxiliary-cutoff benchmark |
| `test_sitekit.py` | tests of all of the above for both profiles (dry-run submissions against a fake site) |

## Safety rules (enforced by code and tests)

| Rule | Where |
|---|---|
| A submission is bound to the uploaded tarball: the login code copy must match the tarball byte for byte (its `STAGE_MANIFEST`/`STAGE_INFO` and every file; no added files; the plan must be inside), and the tarball, plan and scientific-source sha256 values are exported; every job re-checks them after staging and before computing (exit 65 on a mismatch) | `submit.py: verify_code_copy`, `lib.sh: lri_check_binding`, staging blocks of the job scripts |
| Every reserved `LRI_*` variable is set explicitly in `--export` (empty when unused) and the `sbatch` process gets no inherited `LRI_*` variable; a row job runs either `LRI_ROW_MODE=array` (row = `SLURM_ARRAY_TASK_ID`, `LRI_ROWS` must be empty) or `LRI_ROW_MODE=packed` (`LRI_ROWS`, not inside an array) | `submit.py: RESERVED_EXPORTS, slurm_env`, `lib.sh: lri_select_rows` |
| Published means complete: a non-empty, well-formed `SHA256SUMS` (no duplicate, hidden, absolute or `..` names) whose entries all verify, no unlisted files, and the required receipts (rows: `task_receipt.json`, `run_receipt.json`, a job receipt and one record per lambda; grids: `grid_receipt.json`, the array and its metadata). Absent means the directory does not exist; anything else is corrupt and stops `submit.py`, the jobs, `transfer_grid.sh`, `collect.sh` and `merge_records.py` (exit 74 / 1) | `manifests.py`, `jobtools.py published-check` |
| On login nodes `submit.py` checks a published grid's manifest, small files and array size; the array's hash (up to 52 GB) is checked by every consumer on its compute node, by the grid job before it skips, and at the destination of `transfer_grid.sh` (`--verify-grid-arrays` hashes it on the login node too) | `submit.py`, `grid_job.sbatch`, `lri_fetch_grid` |
| Every copy driven by a manifest first snapshots `SHA256SUMS` into the target, validates the snapshot's names (no traversal, absolute, subdirectory or hidden names), copies exactly those regular files (symlinks are not followed) and verifies the result; a fetched grid must be complete. A manifest changed after submission therefore cannot write outside the target or replace the staged package | `lib.sh: lri_manifest_names, lri_fetch_grid, lri_publish_dir`, `transfer_grid.sh` |
| Collection indexes and compares only the record paths that the strict verification lists; any other entry in the plan directory or a task directory (stray records, subdirectories) fails it. One semantic record check (finite sequences of the declared length, embedded cutoffs, order/lambda/N matching the file name) is shared by `collect_records.py` and `merge_records.py`, and the merger requires source hashes and a plan sha256 for every record and refuses more than one scientific source set unless `--allow-mixed-sources` | `collect.sh`, `manifests.py verify-rows`, `collect_records.py: validate_record`, `merge_records.py` |
| Queued work is identified by destination, not by name: grid jobs carry `--comment=lri1;g=<hash of root + source-tagged grid dir>`, packed row jobs `lri1;t=<token>+...` (all rows of the job), row arrays `lri1;a=<row>:<token>.<token>+...` so that each array element (`squeue -r` id `<job>_<row>`) holds only its own row; a grid job is reused only if its destination matches, a row is never submitted twice, and a legacy job without a comment that could do the same work blocks submission. Rows are decided first; a grid job is submitted only for a grid that an unfinished row needs, so a completed stage submits nothing | `submit.py: grid_token, task_tokens, comment_tokens, array_comment` |
| Expanse `normal` QOS: RUNNING + PENDING jobs of the account plus every new job in a normal-QOS partition (probes included) must stay <= 22 (32 - 10); no override; an unreadable queue means UNKNOWN and nothing is submitted (exit 75) | `submit.py: compute_guard` |
| Clean tarballs are reproducible byte for byte (commit time in `STAGE_INFO.json` and as entry mtime), so repeating `make_tarball.sh --upload` for a commit reuses the upload; an existing code copy that no longer verifies fails the upload (exit 74) | `make_tarball.sh` |
| Probes and regressions fail loudly: failed measurements or auxiliary-cutoff runs fail the probe job (partial results kept); `regression.sh` needs a fresh report directory, all five old-vs-new and five shipped reports, and fails on any failed run or comparison | `probe_job.sbatch`, `aux_cost_probe.py`, `regression.sh`, `compare.py regression-summary` |
| Probe resources and every `--grid-resources`/`--task-resources` override go through the same partition, memory, CPU and wall-time checks; `cpus`, `mem_gb`, `workers` (or `auto`), `rows_per_job` and `max_concurrent` must be positive integers, checked before anything is submitted | `submit.py: parse_resources, check_limits` |

## Which cluster

Both sites run the same rows with the same physics parameters. Numbers below
are `submit.py --check` output; Expanse rows use the measured Expanse pilot,
symmetry rows scale the pilots to the slower vendor (Intel 6148; the AMD pilot
ran 2.8 times faster per lambda than Expanse).

| Phase | Expanse (account <ACCOUNT>, SU) | symmetry (whole nodes, no SU) |
|---|---|---|
| queue limits | 48 h wall; `shared`/`large-shared` (large-shared: 2 running per user, 4 per account); `compute` only by override, and then at most 22 running `normal`-QOS jobs for <ACCOUNT> (10 of 32 kept free) | 24 h wall; every job takes a whole node; `amdq` (29 AMD nodes) first, `defq` (Intel) as fallback, never `longq`/preemptible queues; both were fully allocated on 2026-10-12 (hours to a day of queueing) |
| PILOT (N=512, 1 row) | grid 6 min + row 8 min measured; 15 SU used | grid 4 min + row 3.5 min measured on an AMD node (jobs 574037/574038) |
| P1 (N=768, rows 1-3) | grid: large-shared 24 cores/128 GB, 2 h limit, ~0.3 h, ~29 SU; rows: 3-element array on shared 16 cores/64 GB, 6 h limit, <= 1.4 h each (~21 min per lambda), ~45 SU each; **~165 SU** (<= 770 at wall limits) | grid: 1 Intel `defq` node (AMD `/local1` is too small), 6 h limit, ~0.8 h; rows: 2 node jobs (rows 1+2 packed one per package, row 3), 6 h limit, ~1.2 h each; **~3.2 node-h** (<= 18 at limits) |
| P2 (N=1024, rows 4-5) | grid: large-shared 32 cores/256 GB, 3 h limit, ~0.6 h, ~77 SU; rows: 2-element array on large-shared 8 cores/160 GB, 6 h limit, ~1.6 h each, ~64 SU each; **~205 SU** (<= 860 at limits) | grid: 1 Intel `defq` node, 12 h limit, ~5.5 h (its `/local1` is a rotating disk; or copy the Expanse grid); rows: 2 node jobs (one row per node), 8 h limit, ~1.8 h each; **~9 node-h** (<= 28 at limits) |
| node-local scratch | NVMe: 916 GB per standard node (shared by co-located jobs), 2.9 TB on large-shared | `/local1`: 568 GB rotating disk on Intel nodes, 84 GB on AMD nodes |
| strengths | measured, schedules at once on large-shared, fast NVMe for the 260 GB N=1024 grid; P1+P2 cost ~370 SU of a 22 M SU allocation | no SU; but whole nodes queue behind other campaigns, and debug jobs can preempt `preq` work |

A practical split: build grids on Expanse (or wherever node-local scratch is
fast), copy them with `transfer_grid.sh` if rows run elsewhere, and run rows on
whichever site has free capacity. Records and grids are interchangeable: the
grid directory name carries a hash of the scientific sources, and every record
carries its site and CPU in `job_receipt.json`.

## Exact launch commands

Build and upload once per commit (on the Mac):

```bash
bash cluster/expanse/make_tarball.sh --upload expanse
bash cluster/symmetry/make_tarball.sh --upload symmetry
```

Expanse (login node; `PY=$HOME/envs/lri_c2/py3.13.5/bin/python`, from `~/lri_c2/pkgs/lri_c2_<commit12>`):

```bash
$PY cluster/expanse/submit.py --check
$PY cluster/expanse/submit.py --stage P1 --submit
$PY cluster/expanse/submit.py --stage P2 --submit
```

symmetry (`<NODE>`; `PY=$HOME/envs/lri_c2/py3.13-mamba/bin/python`, from `~/lri_c2/pkgs/lri_c2_<commit12>`):

```bash
export PATH=/cm/shared/apps/slurm/current/bin:$PATH; sinfo -h -p amdq -o '%t %D'; squeue -u $USER
$PY cluster/symmetry/submit.py --check
$PY cluster/symmetry/submit.py --stage P1 --submit
$PY cluster/symmetry/submit.py --stage P2 --submit
```

Every command without `--submit` is a dry run that prints the checks, the cost
and the exact `sbatch` lines. Published grids and rows are never recomputed.

## Merging records from both sites

```bash
bash cluster/expanse/collect.sh  --dest outputs/expanse/production_plan_<A>
bash cluster/symmetry/collect.sh --dest outputs/symmetry/production_plan_<B>
python cluster/sitekit/merge_records.py \
    --site-dir expanse=outputs/expanse/production_plan_<A> \
    --site-dir symmetry=outputs/symmetry/production_plan_<B> \
    --output outputs/merged_production_plan.json
```

`merge_records.py` verifies every task directory strictly (see the safety
rules), reads only listed and verified files, checks that all records share one
schema, labels each with its site, node and CPU vendor/model, carries its
scientific source hashes, plan sha256 and configuration (N, order, lambda,
oversample, radius_cost, mixed/collapsed/tail cutoffs), and compares every pair
with the same (order, lambda) on overlapping coefficient boxes, classified as
`replica` (same configuration and sources), `variant` (declared configuration
differences, listed) or `incompatible` (different sources: a problem, exit 1,
unless `--allow-mixed-sources`). If a row ran on both sites, both records are
kept. Cross-site agreement measured so far: the N=512 pilot
(Expanse EPYC 7742 vs symmetry EPYC 7543) agrees to 6.9e-11 in the raw partial
sums (2.1e-15 relative, all 512 cutoffs), bit for bit in the two-point,
planar, curvature and tail constants, and to 1.0e-9 in the sidecar's
finite-cutoff h (from the mixed-sum fit median); the N=12 smoke record agrees
to 5.5e-12 between an AMD and an Intel node. Ill-conditioned fit diagnostics
in the records differ more, as between any two machines. A merged index is an input for the arbitrary-N
analysis, not a continuum result.
