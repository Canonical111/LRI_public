# Running on symmetry (amdq)

The `slurm/` templates are generic examples and are **not** for symmetry. On symmetry, every CPU partition except
sharedq allocates whole nodes, and BeeGFS `flock` is node-local. Use the tools below instead. Paths assume the defaults
in `cluster/symmetry/site.json`:
- base: `/mnt/beegfs/zzheng1/lri_spin`
- login host: `mn003`
- partition: amdq, excluding cn112
- 240G per node, 64 cores, 24 h, `--no-requeue`

## 0. Concepts

- **Frozen code.** Code is used from `<base>/code/<sha12>/`, a read-only `git archive` of a commit with a `GIT_SHA`
  file. Jobs and the submitter refuse other code. Never edit a frozen copy; freeze a new commit instead.
- **Receipt.** `validate.sbatch` runs the full test suite on an amdq node and writes `receipt.json`. It is bound to the
  source hash and to the node runtime (Python, NumPy, SciPy, OpenBLAS version and architecture). Items refuse to run
  without a matching receipt. A new code freeze or a module change needs a new receipt.
- **Campaign root.** A directory marked by `.campaign`. Inside it, each item is `<root>/<id>/`. The submitter writes
  `.owner` (a token plus a generation number), and the solver writes only into `<root>/<id>/gNNNN/` for its own
  generation. Writers without the current token exit 76 and write nothing, even `python -m lri_spin flow` by hand.
- **One ID, one definition.** The first submission records the item's hash in `.owner`. A later manifest that
  changes that item (α, config, bracket, ...) under the same ID is refused: use a new ID.
  - An item counts as done only if a `gNNNN/result.json` has exactly this item's identity on the receipt's runtime
    and passes the gates.
  - Anything else is reported as a conflict, and never as done.
  - One campaign uses one frozen source and one receipt runtime.
- **Snapshots.** Each submission copies the validated manifest and receipt into
  `<campaign>/lanes/<submission>/` (read-only, with sha256 in the lane spec). Lane admission and every item use that
  snapshot, so editing the original manifest after submission changes nothing.
- **Status.** An item whose `.owner` was submitted with a different definition shows as `conflict`; its progress is
  not reported.
- **Reserved names.** `SUBMITTED.jsonl` and `lanes` cannot be item IDs. Nothing except the solver (with the owner
  token) and the submitter writes inside a campaign root: `export`, `make_manifest.py` and `validate_release.py` refuse
  campaign destinations.
- **Lane.** One Slurm job on one exclusive node, running several items concurrently. An item starts only while the
  running threads (≤ 64) and the memory reservations (≤ 240 − 8 GiB) still fit. The reservation is
  `max(memory_limit_gib, plan())`.
- **Stop and resume.** 300 s before the wall limit (`--signal=B:USR1@300`), or on `scancel -s USR1 -b <job>`, the lane
  creates its `STOP` file. Each item checkpoints after its current site and exits 75.
  - `resubmit` later starts a new generation that seeds from the previous generation's checkpoint.
  - A restarted job (same job id) is refused (exit 79), so recovery always goes through `resubmit`.

## 1. One-time setup (login node)

```bash
# On the workstation: copy the wheels (pytest, pluggy, iniconfig) to symmetry.
scp wheels/*.whl symmetry:/mnt/beegfs/zzheng1/lri_spin/wheels/
# On mn003:
bash <code>/cluster/symmetry/setup_env.sh /mnt/beegfs/zzheng1/lri_spin/wheels   # venv + ENV.json
```

## 2. Freeze and validate

```bash
# On the workstation, from the repository (committed revision only):
cluster/symmetry/freeze.sh HEAD            # -> symmetry:/mnt/beegfs/zzheng1/lri_spin/code/<sha12>
# On mn003:
export LRI_SPIN_CODE=/mnt/beegfs/zzheng1/lri_spin/code/<sha12>
source $LRI_SPIN_CODE/cluster/symmetry/env.sh
python $LRI_SPIN_CODE/scripts/symmetry_submit.py validate          # amdq, 1 h, prints the job id
# afterwards: <base>/validation/<jobid>/receipt.json, lscpu.txt, threadpool_info.json; log validate-<jobid>.log
```

## 3. Manifest and campaign

```bash
python $LRI_SPIN_CODE/scripts/make_manifest.py --items my_items.json \
    --receipt <base>/validation/<jobid>/receipt.json --output <base>/manifests/my.json
python $LRI_SPIN_CODE/scripts/symmetry_submit.py init --campaign <base>/campaigns/my
```

Items use the README's fields (`id`, `kind`, `config`, `alpha` or `bracket`, `memory_limit_gib`, ...).
- IDs must match `[A-Za-z0-9][A-Za-z0-9._-]{0,127}`.
- Only the `ordered` backend is accepted on symmetry.
- `config.threads` is the item's BLAS thread count; lanes pack items up to 64 threads per node.

## 4. Submit, watch, resubmit

```bash
S="python $LRI_SPIN_CODE/scripts/symmetry_submit.py"
$S submit   --campaign <base>/campaigns/my --manifest <base>/manifests/my.json \
            --receipt <base>/validation/<jobid>/receipt.json --lanes 4 --dry-run   # sbatch --test-only, writes nothing
$S submit   ... --lanes 4                  # new items only
python $LRI_SPIN_CODE/scripts/symmetry_status.py --campaign <base>/campaigns/my --manifest <base>/manifests/my.json \
       --receipt <base>/validation/<jobid>/receipt.json
$S resubmit ... --lanes 2                  # not-started items + items whose job is confirmed dead
```

How `resubmit` decides:
- It reclaims an item only if its job is absent from `squeue` and terminal in `sacct`. Any query failure or unknown
  state means refuse.
- An owner without a job id (the submitter crashed after sbatch) is matched to its job by the unique job name.
- An owner with no matching job is an orphan. It needs `--reclaim-orphans` and is reclaimed only once the owner is
  older than 15 minutes; this minimum cannot be lowered.
- Owner and campaign markers are published atomically (temp file plus `link()`), so a crash leaves no partial file.
- Run the submitter only on mn003. It refuses to run anywhere else, because its lock is a node-local flock.

Records and logs:
- Every submission is appended to `<campaign>/SUBMITTED.jsonl`.
- Lane specs are in `<campaign>/lanes/<submission>/`.
- Per-execution logs are in `<base>/logs/<jobid>.r0/`: `<id>.log`, plus `events.jsonl` with start and end events, rc,
  peak RSS and the threads and memory in use. There is also `node.json`, with the host, `lscpu` and the runtime,
  written before the receipt comparison; a mismatch prints the expected and actual runtime.
- Slurm output is `<base>/logs/slurm-<jobid>.out`.

Exit codes:

| Code | Meaning |
|---|---|
| 0 | done |
| 73 | already claimed on this node |
| 75 | interrupted with a checkpoint |
| 76 | not the owner, nothing written |
| 79 | the lane refused a restarted execution |
| 1 | failure (see the item log) |

## 5. Results and export

`symmetry_status.py` prints the result path (`<root>/<id>/gNNNN/result.json`). For analysis:

```bash
python $LRI_SPIN_CODE/scripts/export_legacy.py <root>/*/g*/result.json --output-dir exports/
python -m lri_spin export <root>/*/g*/result.json --output exports/all.json
```

- Campaign exports go to `exports/<item id>/` and record `campaign_item` and `generation` in their provenance.
- If an item has gated results in several generations, export the one that `symmetry_status.py` names.
- Destinations are resolved first. Symlinked destinations, aliases and campaign targets are refused. Exports to one
  destination are serialized by an `O_EXCL` lock file `.<name>.export.lock` in the output directory. A stale lock
  left by a crashed export is deleted by hand.
- A destination folder holds the components of exactly one record. An export from a different record is refused
  without `--replace`, which also removes stale components. Every record and destination is checked before
  anything is written.

## 6. Window correction

The LRI Hamiltonian-truncation "window correction" does not apply to this NRG. The reasoning is in
`review/CODE_REVIEW.md` §4. Control truncation effects with convergence scans in `keep`, `nb` and `Λ`.
