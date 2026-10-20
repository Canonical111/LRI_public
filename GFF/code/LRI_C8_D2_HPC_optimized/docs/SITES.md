# Running this package on SDSC Expanse and symmetry (the site layer)

The site layer runs a planned campaign on a managed cluster with **N whole-node runner jobs plus one merge job**,
instead of the package's job arrays. It adds only operations code. Nothing that determines the numbers changes: the
kernel, sampling, the map from seeds to streams, merge and assembly are the files pinned by every plan
(`production.py:18`), and `git diff df468f8 -- src/ Makefile tools/production.py tools/common.py tools/assemble.py
tools/prepare_inputs.py tools/task_schedule.py tools/stage_runtime.py tools/slurm_submit.py slurm/run_array.sh
slurm/merge.sh` is empty.

| File | Role |
|---|---|
| `tools/site_submit.py` | admission and submission of runners and the merge; stale-claim release |
| `tools/node_runner.py` | the runner (claim loop, deadline, identity guard), `status`, `retry`, the seed commands |
| `tools/seed_sync.sh` | Mac side: union of the three seed logs, ownership check, receipt |
| `slurm/node_runner.sh` | the runner job script (signals forwarded) |
| `slurm/env_expanse.sh`, `slurm/env_symmetry.sh` | the site environments (`C8_ENV_SETUP`) |
| `slurm/site_gate.sh` | the per-site gate job (AC1–AC4 and the tests) |
| `tests/site_layer.py` | the site-layer tests (local and on site; scheduler shims, no submission) |

## 1. How a site campaign runs

- **Runners.** Each runner job takes one node with all its cores (Expanse `compute`: 128; symmetry AMD: 64) and runs
  `tools/node_runner.py run`. It loops: claim the next eligible index, run the unchanged
  `production.py run RUN --index I --threads T --scratch $TMPDIR/idx<I> [--max-blocks k]`, record the outcome.
- **Why this is safe.** Correctness never depends on the claims. Blocks are atomic, an existing valid checkpoint is
  skipped, and a duplicate block is accepted only if it is scientifically identical (`production.py:574-580`). A wrong
  claim decision costs time, never results. The identity guard keeps duplicates identical (one CPU vendor and one
  library stack per campaign).
- **Campaign state** (all under `$C8_RUN`, atomic `mkdir` and hard links only; no `flock`):

  | Path | Meaning |
  |---|---|
  | `claims/<I>/owner.json` | live claim of index I: job id, restart count, host, pid, UTC |
  | `attempts/<I>.jsonl` | append-only history: `done`, `partial`, `failed`, `term`, `released`, `reset` |
  | `done/<I>`, `exhausted/<I>` | markers, published no-clobber |
  | `site_identity.json` | CPU vendor and the sha256 of every library `ldd` resolves for the campaign executable |
  | `runner_logs/idx<I>.<job>.<restart>.<ns>.log` | the output of one attempt |
  | `slurm_logs/run-<job>.log`, `merge-<job>.log` | job logs (`--open-mode=append`, so a requeue keeps the first part) |
  | `site_submissions.jsonl` | one record per submission: argv, ids, admission counts, ignored environment |
  | `seed_receipt.json` | non-test campaigns: the seed receipt (§5) |

- **Order.** Heaviest remaining work first. Plans made with `--cost-model`: the estimated core-seconds of the
  uncommitted blocks. Other plans (the pilot): loop descending, free before power, then shard index.
- **Deadline** (cost-model plans only). A block's wall estimate is `max(longest task, estimated_cost / (T × 0.80))`
  (`production.ASSUMED_EFFICIENCY`). An attempt gets `--max-blocks k`, the largest k whose cumulative estimate × 1.5
  + 600 s fits the job's remaining time (`squeue %L`). With k = 0 the runner skips the index; a fresh runner has the
  full limit, so a long index advances block by block over several jobs. Without a cost model there is no gating; a
  wall-time TERM loses at most one block per runner.
- **Failures.** Two `failed` outcomes since the last `reset` exhaust an index (`term`, `released` and `partial` are not
  failures). A runner does not retry an index that failed in the same job.
- **Signals.** `scancel`, wall time or preemption sends TERM. The batch shell forwards it to the runner, the runner to
  its `production.py run` child, which stops the native worker and removes its runtime (`production.py:487-536`). The
  attempt is recorded `term`, the claim removed, and the job exits 143.
- **Merge.** The unchanged `slurm/merge.sh` (status, merge, assemble) on `shared` (Expanse) or `sharedq` (symmetry),
  `-c 8`, `C8_MERGE_WORKERS=8`, 04:00:00, with `--dependency=afterany:<every runner>`. If anything is incomplete,
  `merge.sh` fails cleanly on `production.py status`; nothing waits forever.

## 2. Installation (each site)

1. **Code:** a git clone at a tag, `~/c8ind/LRI_C8_D2_HPC_optimized` (NFS home). Never `cp -r` the tree onto Lustre.
2. **Venv** `~/c8ind/venv`, separate from LRI_C8_D2_HPC's `~/c8d2/venv`, with the site's Python
   (Expanse `python/3.11.9`, symmetry `python/3.11`):

   ```bash
   python3 -m venv ~/c8ind/venv && ~/c8ind/venv/bin/pip install numpy==2.3.5 scipy==1.17.1 mpmath==1.3.0
   ```

   scipy is pinned to 1.17.x because `make_net` uses the private `qmc.Sobol._sv/_shift` (`production.py:95`).
3. **Environment:** `export C8_ENV_SETUP=~/c8ind/LRI_C8_D2_HPC_optimized/slurm/env_<site>.sh`, then `source
   "$C8_ENV_SETUP"`. It sets the compiler, Boost and GMP, the venv, `C8_SITE`, `C8_DATA`, `C8_SEEDS`,
   `C8_SEEDS_TOOL_DIR` and, inside a job, a node-local executable `TMPDIR`.
4. **Our seed tools** (LRI_C8_D2_HPC `aafa8a4`, sha256 pinned in `tools/node_runner.py`), on each site and on the Mac:

   ```bash
   git -C LRI_C8_D2_HPC archive aafa8a4 tools/seeds.py tools/common.py \
     | ssh <site> 'mkdir -p ~/c8ind/c8d2_seedtool && tar -x -C ~/c8ind/c8d2_seedtool'
   git -C LRI_C8_D2_HPC archive aafa8a4 tools/seeds.py tools/common.py | (mkdir -p ~/c8ind/c8d2_seedtool && tar -x -C ~/c8ind/c8d2_seedtool)
   ```

5. **Packs:** attach the staged original package's inputs by relative symlinks (the manifest and all 12 packs are
   hashed first):

   ```bash
   python3 tools/attach_inputs.py $C8_DATA/original/inputs --mode symlink
   ```

   Staged originals: Expanse `<SCRATCH>/temp_project/c8-d2-indep/original/inputs`, symmetry
   `<SCRATCH>/c8-d2-indep/original/inputs`. Never attach `../LRI_C8_D2_HPC`: on our machines that name is our
   own package (RECON D-8).
6. **Build** in a job on the production CPU type (one executable per campaign; a rebuild needs a new plan):

   ```bash
   sbatch -A <ACCOUNT> -p compute -N1 -n1 -c 128 --mem=240G -t 00:30:00 -J c8d2-ind-build \
     --wrap 'source "$C8_ENV_SETUP" && make -j16 gmp decimal'                        # Expanse
   sbatch -p amdq --exclude=cn112 -N1 -n1 -c 64 --mem=245G -t 00:30:00 -J c8d2-ind-build \
     --wrap 'source "$C8_ENV_SETUP" && make -j16 gmp decimal'                        # symmetry
   ```

   Check `BOOST_LIB_VERSION` "1_77" in `bin/c8d2_gmp.build.json`. `make` rewrites the tracked `bin/*.build.json`.

## 3. The gate (once per site, before any campaign)

```bash
cd ~/c8ind/LRI_C8_D2_HPC_optimized
sbatch -A <ACCOUNT> -p compute -N1 -n1 -c 128 --mem=240G -t 03:00:00 slurm/site_gate.sh          # Expanse
sbatch -p amdq --exclude=cn112 -N1 -n1 -c 64 --mem=245G -t 03:00:00 slurm/site_gate.sh        # symmetry
```

It runs in node-local scratch: AC1 (pinned files unchanged; df468f8 and HEAD built from `git archive` in one
environment give byte-identical `bin/c8d2_gmp` and `bin/c8d2_decimal`), AC2 (the frozen 52-case replay against the
pristine baseline: status passed, every case exact, 300 rows, 18,247 binary128 and 3,327 MP promotions per executable
and thread count, 4 split checks ≤ 5e-16; the aggregate science digest is recorded, and equality with their sandbox's
`366421b2…` is reported, not required), AC3 (the package tests and `tests/site_layer.py`; with packs: `hpc_cli`,
`make test-workflow`, `cluster_graph_tasks`; `tests/precision_allocation.py` needs the absent `precision_work/` and
fails as shipped, so it is not run) and AC4 (the same `--test-graphs 1` plan from both trees gives byte-identical
`config.json`, `sobol.bin` and `tasks.sqlite` in all 24 groups). Output: `$C8_DATA/gates/<site>-<date>-<job>/`, and
the summary in `verification/site_gates/`. The job is named `c8d2-ind-gate`, so both sessions' admission counts it.

## 4. Submission

```bash
source "$C8_ENV_SETUP"
export C8_SBATCH_ARGS='-A <ACCOUNT> -p compute -N1 -n1 -c 128 --mem 240G'            # Expanse runners
export C8_MERGE_SBATCH_ARGS='-A <ACCOUNT> -p shared -c 8 --mem 32G'                    # Expanse merge
# symmetry: C8_SBATCH_ARGS='-p amdq --exclude=cn112 -N1 -n1 -c 64 --mem 245G'
#           (amddebugq, 1 h; amdpreq with --requeue); C8_MERGE_SBATCH_ARGS='-p sharedq -c 8 --mem 16000M'
#           export C8_AMD_CAP=<this session's share> C8_AMD_POOL_TOTAL=<both sessions' total>   (from DECISIONS.md)
python3 tools/site_submit.py runners $C8_DATA/runs/<name> --nodes N --time HH:MM:SS --dry-run
python3 tools/site_submit.py runners $C8_DATA/runs/<name> --nodes N --time HH:MM:SS
```

- **Options** come only from `C8_SBATCH_ARGS` and `C8_MERGE_SBATCH_ARGS` and must match the site profile:

  | Role | Expanse | symmetry |
  |---|---|---|
  | runners | `-A <ACCOUNT> -p compute`, QoS unset or `normal`, `-N1 -n1 -c <plan --threads ≤ 128> --mem 240G`, ≤ 48 h | exactly one of `amdq` (24 h), `amddebugq` (1 h), `amdpreq` (24 h, `--requeue`); `--exclude` naming `cn112`; `-N1 -n1 -c 64 --mem 245G`; the plan has `--threads 64` |
  | merge | `-A <ACCOUNT> -p shared -c 8 --mem 32G` | `-p sharedq -c 8 --mem 16000M` (at most 8 CPUs × 2,000 MB) |

  Allowed besides: `--mail-type`, `--mail-user`, `--requeue`/`--no-requeue`. Refused: `--exclusive`, `--array`,
  `--dependency`, `-w`, `--nodes` > 1, `--time`, `--job-name`, `--output` and every other option. The tool sets
  `--time` (runners: `--time`; merge 04:00:00), `--job-name` (`c8d2-ind-run`, `c8d2-ind-merge`),
  `--comment=c8ind:<campaign tag>`, the logs, `--open-mode=append`, `--export=ALL` and the merge dependency.
- **Environment.** sbatch runs without inherited `SBATCH_*`, `SALLOC_*`, `SLURM_*` and `*_CLUSTERS` variables
  (each ignored one is printed and recorded); squeue without `SQUEUE_*` and `*_CLUSTERS`. Every role is preflighted
  with `sbatch --test-only` before the first submission.
- **The plan** must have the backend `C8_REQUIRE_BACKEND` (default gmp: `production.py plan` defaults to decimal, so
  pass `--backend gmp`; RECON D-1), unchanged pinned tools and, with a cost model, no block whose estimate × 1.5 +
  600 s exceeds `--time` less 120 s of start-up (fix: re-plan with a smaller `--checkpoint-tasks` or
  `--checkpoint-seconds`, or raise `--time`).
- **Budgets** (one snapshot under the campaign lock `$C8_RUN/.c8_submit.lock` and the site lock
  `$HOME/.c8_site_<site>.lock`, which LRI_C8_D2_HPC's own admission takes too; `C8_SITE_LOCK_DIR` moves both):

  | Site | Limit |
  |---|---|
  | Expanse (`squeue -A <ACCOUNT>`) | session `c8d2-*` normal-QOS running + N ≤ 11, submitted + N ≤ 27 (H7E-R) |
  | | session `c8d2-*` nodes on `compute`/`debug` + N ≤ `C8_EXP_NODES` (default 4, H7E development cap) |
  | | session shared-partition jobs + 1 ≤ 32 |
  | | the user's normal-QOS running + N ≤ 22, submitted + N ≤ 54 (user rule) |
  | | the account's normal-QOS running + N ≤ 32 |
  | symmetry (`squeue -u <USER>`) | session `c8d2-*` AMD-pool nodes (amdq + amddebugq + amdpreq) + N ≤ `C8_AMD_CAP` |
  | | `c8d2-*` plus `c8d3-*` AMD-pool nodes + N ≤ `C8_AMD_POOL_TOTAL`; other jobs are listed, not counted |

  States are production.py's `LIVE_STATES`/`TERMINAL_STATES`; a counted job in any other state (COMPLETING,
  PREEMPTED, …) refuses with 69 until Slurm settles it. A failed or unparsable squeue is UNKNOWN (69), never zero.
- **Coordination with C63d** (`LRI_C8_shared/inventory/DECISIONS.md`). The `c8d2-` prefix makes both existing
  admission writers count these jobs as C62d's: our `LRI_C8_D2_HPC/tools/slurm_submit.py` and C63d's
  `LRI_C8_D3_HPC/tools/slurm_submit.py`, which treats any other <USER> normal-QOS name as foreign. Expanse: H7E-R (11
  running / 27 submitted for `c8d2-*`) and H7E (4 development nodes) apply; more nodes need a DECISIONS window and an
  explicit `C8_EXP_NODES`. symmetry: the window in force sets `C8_AMD_CAP` and `C8_AMD_POOL_TOTAL` (e.g.
  H11-prod-c63d-20261008: C62d 3, total 12); both must be exported explicitly. Inform C63d before a pilot.
- **Live campaign jobs.** A live merge of the campaign refuses (65): cancel it first. Live runners need `--add`
  (counted the same way). `--nodes 0` submits a merge only, waiting on the live runners. Stale claims (owner job not
  live) are released first; `site_submit.py release RUN` does only that.
- **Array scripts.** With `C8_SITE` set, `slurm/submit.sh` and `slurm/resubmit.sh` refuse (64) unless
  `C8_ALLOW_ARRAYS=1`; arrays stay available for unmanaged machines.

Exit codes: 0 submitted, 1 a submission failed after a job was accepted (named), 64 invalid input, 65 budget or live
campaign jobs, 69 unknown or uncertain scheduler state, 75 a lock held (the site lock is waited for 120 s; a lock is
never broken automatically, its `owner.json` names the holder).

## 5. Seeds

The port's random streams use the same seed domain and mixing as our C8(2) package (`c8-d2|seed|…`; RECON D-3), so
every non-test base seed is reserved **in our forbidden-seed registry**: symmetry
`<SCRATCH>/c8-d2/forbidden_seeds.json`, Expanse
`<SCRATCH>/temp_project/c8d2/forbidden_seeds.json`, and the mirror
`LRI_C8_D2_HPC/designs/forbidden_seeds.json`, through our pinned `tools/seeds.py` (schema `c8-d2-seeds-1`, lock
`<log>.lock`, 120 s).

1. **Plan** with a fresh seed: `python3 -c 'import secrets;print(secrets.randbelow(2**63))'`.
2. **Import** (Mac): `bash tools/seed_sync.sh`. It makes the three logs the union of all three until a fresh
   snapshot of all three holds the same seeds (at most 5 rounds, else exit 1). Needs the Expanse ControlMaster.
3. **Reserve** (site X): `python3 tools/node_runner.py seed reserve RUN`. One `seeds.reserve()` transaction under the
   log's lock with source `c8ind:<abs RUN>:<manifest sha256[:12]>`; it refuses if the fresh log holds the base seed,
   a derived group seed (either way round), or the seed is in this package's `seed_registry`. Repeating it is
   `present`.
4. **Propagate and verify** (Mac): `bash tools/seed_sync.sh --owner <source> --seed S`. After convergence, S and each
   of its derived seeds must have exactly one owner in the union; any other entry is a conflict (exit 1: re-plan with
   a new seed). On success it writes `seed_receipt.json` and copies it to `RUN/` on X.
5. **Submit.** `site_submit.py runners` refuses a non-test campaign unless the receipt matches the plan's seed and
   source, is no older than the plan, and X's log, re-read under its lock, still shows that single owner.

Test plans (`--test-graphs` > 0) are never reserved; their seed must collide with nothing in X's log (a check only),
so the paired drills can reuse one test seed. Test results never enter science.

## 6. Pilot (Expanse) and production

```bash
python3 tools/production.py plan $C8_DATA/runs/pilot1 --seed <fresh> --backend gmp --purpose pilot --replicates 32 \
  --loop-points 3:16384,4:4096,5:2048,6:1024,7:512,8:256 --threads 128 --checkpoint-tasks 4096 --checkpoint-graphs 64 --shards 32
bash tools/seed_sync.sh                                                   # Mac
python3 tools/node_runner.py seed reserve $C8_DATA/runs/pilot1            # Expanse; prints the source
bash tools/seed_sync.sh --owner <source> --seed <seed>                    # Mac; receipt to the campaign
python3 tools/site_submit.py runners $C8_DATA/runs/pilot1 --nodes 4 --time 12:00:00
```

`plan` hashes all 7.8 GB of packs, so run it in a job. On Expanse, write the plan to node-local scratch
(`$TMPDIR/pilot1`) and copy the finished directory (about 75 files) to `$C8_DATA/runs/` before `seed reserve`: SQLite
writes on Lustre made a 24-group test plan take 1,018 s against about 10 s on local NVMe (stage B). A plan records no
path of its own (AC4 compares plans made in different directories file by file), so the copy is the same plan.
After the merge: `tools/make_cost_model.py`, a scan of
`tools/pilot_allocation.py --target-core-hours H` for SE ≈ 25, 15 and 10, `tools/inspect_result.py --top 25`, and the
runners' summary lines (node-hours) with `performance.wall_team_utilization` from the checkpoints. Production is a
new plan with `--allocation`, `--cost-model` and a fresh seed, submitted only after the user's choice of target SE and
a DECISIONS window.

## 7. Monitoring and recovery

- `python3 tools/production.py status RUN --json` (blocks per index, fingerprints) and `python3 tools/node_runner.py
  status RUN` (done, exhausted, claimed, failures since reset). `squeue -u $USER -n c8d2-ind-run,c8d2-ind-merge`;
  on symmetry (Slurm 21.08) `sacct -s` needs `-E now`.
- **A runner was cancelled or timed out:** its attempt is `term` and its claim gone; submit again
  (`runners RUN --nodes N`, after the failed merge has ended). A runner killed without cleanup leaves a stale claim,
  which the next `runners` (or `release`) removes.
- **A leftover claims lock:** every claim is created and removed under `RUN/claims/.lock` (held for milliseconds).
  A runner killed inside that window leaves the lock behind; claim changes then wait 120 s and refuse with 75, and the
  runners stop taking work. Check that no runner of the campaign is live, then remove
  `RUN/claims/.lock/owner.json` and the directory by hand.
- **An exhausted index:** read `attempts/<I>.jsonl` and its `runner_logs/`, fix the cause, then
  `python3 tools/node_runner.py retry RUN --index I --reason '...'` and submit again.
- **Identity refusal (exit 64 before any claim):** the node's CPU vendor or library set (every library `ldd`
  resolves, and every absolute-path entry such as a system-wide preload) differs from `site_identity.json`. The runner
  also refuses when a dynamic-loader override is set (`LD_PRELOAD`, `LD_AUDIT`, `GLIBC_TUNABLES`) or a dependency is
  unresolved. Keep the campaign on its site and partition; never mix vendors (x87 `expl`/`logl` make rows
  differ at about 1e-16; a cross-vendor duplicate block fails as a conflict).
- **Merge:** runs automatically after the runners; rerun with `runners RUN --nodes 0` (merge only).
  When the campaign is incomplete, the unchanged `merge.sh` exits 65 and its message says to run
  `slurm/resubmit.sh`. On a managed site that script refuses (§4); instead check `node_runner.py status RUN` and submit
  `tools/site_submit.py runners RUN --nodes N --time HH:MM:SS` again.
- **Build records:** `make` rewrites the tracked `bin/*.build.json`, so a deployed clone shows them modified after a
  build. This is expected and does not touch the AC1 files.
  `tools/report_result.py` hard-codes `results/<name>` in its text (D-7).

## 8. Independence and known defects

- **Shared with our code:** the C7(2) kernel algorithm and precision policy, the importance proposal and rates, Sobol
  and the scipy net construction, the seed domain and mixing, the L3–L7 packs, the finite RG scheme and the ops layer.
  A common-mode error of the C7(2) kernel design would not be detected.
- **Independent:** the L8 graph generation and packs, the C8 kernel extension, the analytic inputs, the assembly, the
  allocation and, with a fresh seed, the random streams. Their earlier result is 45510 ± 520 (−0.92σ against our
  45990.0 ± 8.2).
- **Defects recorded, not fixed** (RECON §6): D-1 `plan` defaults to `--backend decimal`; D-2 vendor drift is recorded,
  never refused (the identity guard covers it); D-3 stream collisions with our campaigns (the seed workflow covers it);
  D-4 Boost `convert_to<long double>` may differ by 1 ulp across Boost versions; D-5 buffered pack over-read, the 8.6 MB
  `inventory.json` parse per run, `status` opening every checkpoint head; D-6 scheduler defaults (per-window throttle,
  merges on the work partition, 4G/2h defaults, overwritten requeue logs; the site layer avoids them); D-7 test and
  tool hygiene (`tests/precision_allocation.py`, dead `tools/build_record.py`, build records without the GMP version,
  `report_result.py`, `run_local.py` scratch); D-8 `benchmark_native.py --source` defaulted to the sibling
  `LRI_C8_D2_HPC` (now required); D-9 reproducible builds are assumed (no `-g`), checked by the gate's AC1.
