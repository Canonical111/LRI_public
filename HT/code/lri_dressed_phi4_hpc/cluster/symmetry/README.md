# symmetry runbook

For the new opt-in density basis, use [../../INTEGRATION.md](../../INTEGRATION.md).
The staged validation now also includes the pinned e2ca07c window comparison and
the optimized-basis end-to-end check. No old receipt validates this release.


**Site facts**
- AMD `amdq` nodes: 64 cores, `--mem=245G`, 24 h, whole-node exclusive. `amddebugq`: 1 h.
- Avoid `longq`.
- Data and logs go on BeeGFS `/mnt/beegfs/zzheng1/lri_dressed`.
- **BeeGFS flock is node-local** (`tuneUseGlobalFileLocks = false`). Cross-node exclusion therefore uses the generation
  leases in `src/lri_dressed/lease.py`: `link()`-published owner records, tombstones, no online deletion, and
  Slurm-job liveness.

**1. Freeze the code** (from the Mac):

    git archive --prefix=<sha>/ <sha> | ssh symmetry 'mkdir -p ~/lri_dressed/incoming && tar -x -C ~/lri_dressed/incoming'
    ssh symmetry 'bash ~/lri_dressed/incoming/<sha>/cluster/symmetry/install.sh --from-dir ~/lri_dressed/incoming/<sha> <sha>'

The code lands read-only in `~/lri_dressed/code/<sha>`. The venv is `~/lri_dressed/venv` (the
`requirements-tested.txt` versions; Python 3.11).

**2. Validate.** This writes a receipt only if every stage passes:

    sbatch --export=ALL,LRI_CODE_DIR=$HOME/lri_dressed/code/<sha> ~/lri_dressed/code/<sha>/cluster/symmetry/validate.sbatch

Stages: pytest, saved-seed regression, `--window none` equality against `~/lri_dressed/code/e637dfd`, and a
calibration smoke run. Output: `$LRI_ROOT/validation/<job>/receipt.json`.

**3. Calibrate** item time and RSS (packed, as in production):

    sbatch --export=ALL,LRI_CODE_DIR=... calibrate.sbatch --cuts 20 24 28 --threads 1 4 \
           --windows none vacuum:consistent --deltas .2 .1 .05 --concurrent 16

**4. Make the campaign** (resources from calibration). Item ids end with a digest of their full numerical
configuration. An existing manifest is never replaced. Seed directories are made absolute and checked: an unseeded
point is refused unless `--allow-bridges` is given. Memory reservations are at least the planner envelope.

    python scripts/make_campaign.py --pack --campaign NAME --bath-cuts ... --deltas ... \
       --windows none vacuum:consistent --seed-dir <code>/inputs --calibration <cal.json> --threads T \
       --out $LRI_ROOT/campaigns/NAME/manifest.json

**5. Submit** K exclusive node jobs (job name `lri-NAME`; several nodes share one work queue):

    python cluster/symmetry/submit.py --campaign $LRI_ROOT/campaigns/NAME --receipt <receipt> --nodes K --time 15:30:00

**6. Monitor:** `python cluster/symmetry/status.py --campaign DIR`, plus `logs/launcher.*.jsonl` and
`logs/items/*.log`.

**7. Resubmit** the same campaign to continue. Done items are skipped, and interrupted items resume from their Newton
checkpoints. Failed items are retried only with `--pack-args '--max-attempts N'`; the attempt count is
checked under the item lease, and a later success supersedes the failure record.

**8. Export:**

    python -m lri_dressed export --input-dir DIR/results --output accepted.json

**Shutdown semantics**
- `#SBATCH --signal=B:USR1@900` makes the launcher stop launching and forward USR1. Children checkpoint at the next
  Newton boundary and exit 75.
- At end − 120 s the remaining process groups get TERM, then KILL after 30 s. Killed items count as interrupted, not
  failed.
- Leases are released only after children are reaped.

**Recovery of stuck leases** (rare)
- `status.py --break-lease KEY --generation G --job J`: the owner must be job J and J must be dead.
- An unreadable owner can only be broken offline: `status.py --maintenance --break-unreadable KEY --generation G`.
  This blocks launchers and requires that no `lri-NAME` job is queued or running.
