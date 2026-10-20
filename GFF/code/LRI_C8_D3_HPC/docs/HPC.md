# Cluster runbook (LRI_C8_D3_HPC, Expanse and symmetry)

This runbook covers C8(3) on Expanse (account <ACCOUNT>) and, since Amendment A1 (2026-10-05, "symmetry first, Expanse
only if symmetry is not enough"), on symmetry (section "Symmetry (Amendment A1)"). Its first part documents what
Stage 0 delivered: the submission, admission and budget tools (`tools/slurm_submit.py raw`, `tools/budget.py`,
`tools/ledger.py`). The parts that later stages add are listed at the end of that part as stubs. The C7(3) runbook
follows, unchanged; it is inherited from `LRI_C7_D3_HPC@a6ce987` and is kept as the record of the C7(3) design.

## Environment (Expanse)

- Copy `slurm/sites/expanse/env.sh.example` to `~/c8d3/env.sh`. It loads `cpu/0.21.2a gcc/13.3.0` and
  `slurm/expanse/23.02.7`, sets the Spack Boost 1.77 and GMP 6.2.1 paths with an RPATH, activates `~/c8d3/venv` and
  exports the `C8_*` settings below. Every job sources it before `set -u`. It never sets `C8_SCRATCH`: each job
  computes that at start.
- `C8_SITE=expanse`, and `C8_ROOT=<SCRATCH>/temp_project/c8d3` (the package constant
  `EXPANSE_ROOT`).
- **Expanse is detected independently of `C8_SITE`.** The tools look for a mount under `/expanse/lustre` in
  `/proc/self/mountinfo`, or for `SLURM_CLUSTER_NAME=expanse`. On such a host they refuse (64) unless
  `C8_SITE=expanse` and `C8_ROOT` resolves to `EXPANSE_ROOT`.
  - On Linux, an unreadable mountinfo also refuses (64).
  - A shell that did not source `env.sh` therefore cannot skip the mount check or the `-A <ACCOUNT>` rule.
  - `C8_SITE` may be unset only off Expanse. The Mac fakes use `C8_SITE=fake`, which alone admits the test hooks
    `C8_TEST_HOOKS`.
- **Fixed paths.** A `C8_LOCK` or `C8_LEDGER` that differs from them refuses (64):
  - the session lock `$C8_ROOT/locks/c8d3.lock`;
  - the ledger `$C8_ROOT/ledger.jsonl`;
  - the intent files `$C8_ROOT/intents/<T>.json`, and `intents/resolved/` for resolved ones;
  - evidence under `$C8_ROOT/ledger_evidence/`.
- **Budget line.** `C8_BUDGET_LINE=dev|pilot|production` is required (64 otherwise). The pilot line needs
  `C8_PILOT_SU_CAP=<the user-approved SU>` and the production line `C8_PRODUCTION_SU_CAP=<the user-approved SU>` (user
  decision 2026-10-08; section "Production"), each a finite positive number in the site's unit (`inf`, `nan`, `1e999`,
  0 or unset refuse, 64). `C8_SU_APPROVED="<approval reference>"` lifts the dev line's 4,000 SU stop
  to its 5,000 SU cap. The reference is recorded in every `submit` record. The dev cap is enforced as hard per-site
  sub-caps, 2,500 on Expanse and 2,500 on symmetry (`budget.SITE_CAPS`; S2-004, section "Symmetry", Accounting), which
  `C8_SU_APPROVED` never lifts.
- **The budget epoch** is the package constant `BUDGET_EPOCH = 1791000000`: 2026-10-03T00:00:00 EDT
  (2026-10-02T21:00:00 PDT), the plan's start. It is passed to `sacct -S` as Pacific local time, with
  `TZ=America/Los_Angeles`. A `C8_BUDGET_EPOCH` set to any other value refuses (64).
- **The CPU check (HD11).** Every job script that sources `slurm/common.sh`, and `slurm/native_job.sh`, first runs
  `slurm/site.sh`'s `c8_cpu_guard`: on Expanse the node's `/proc/cpuinfo` model name must be exactly `AMD EPYC 7742
  64-Core Processor` (every Expanse CPU record of the package says so), else the job exits 68 before anything is
  written; resubmit with `-x <node>` in the job's options and record the node ("Symmetry", CPU pin).

## Symmetry (Amendment A1)

`C8_SITE=symmetry` (user <USER>; `slurm/sites/symmetry/env.sh.example` → `~/c8d3/env.sh`, `profiles.sh`). The same
tools, the same ledger rules and the same admission steps as on Expanse, with the site's own facts:

- **Site detection.** A BeeGFS mount at `/mnt/beegfs` makes a host symmetry, whatever `C8_SITE` says (its Slurm
  `ClusterName` is the generic `slurm`). There every tool refuses (64) unless `C8_SITE=symmetry` and `C8_ROOT`
  resolves to `<SCRATCH>/c8d3` (`ledger.SYMMETRY_ROOT`). A host that looks like both sites refuses (64).
- **Session lock (addendum L, user decision 2026-10-05).** `<HOME>/c8d3/locks/c8d3.lock` on the NFS home
  (`ledger.SYMMETRY_LOCK_DIR`), not under `$C8_ROOT`. BeeGFS checks `flock()` on the local node only unless its client
  runs with `tuneUseGlobalFileLocks = 1`, and **on 2026-10-05 symmetry's clients run BeeGFS 7.4.5 with
  `tuneUseGlobalFileLocks = 0`**; the lock is also taken inside jobs on compute nodes (`plan.sh`: the seed
  reservation of `production.py plan --reserve-seed`, `ledger.py register`; sweep jobs: the same reservation,
  `register`; validation jobs: `seeds.py add`/`init`), so it must exclude across
  nodes. `/home` is NFS vers=3 from 172.16.4.228 with `local_lock=none`: Linux turns `flock()` there into a whole-file
  POSIX lock held at the server through NLM (nlockmgr v1–4 registered on the server; lockd and rpc.statd on <NODE>),
  which every node sees and which is released when its holder's descriptor closes, also after SIGKILL. The mount check
  of every acquisition requires NFS (`nfs` or `nfs4`) with `local_lock=none` and without `nolock`, and refuses (69)
  otherwise, BeeGFS included. Such a lock belongs to the process, not to the descriptor (a second descriptor of the
  same process would "acquire" it too, and closing any descriptor of the file releases it), so a second acquisition
  in one process is refused (69) while the first holds the lock. Ledger, intents, evidence and data stay on BeeGFS
  under `$C8_ROOT`. J-LOCK-0-sym (`ledger.py lockprobe` with `--probe <HOME>/c8d3/locks/probe.lock` on
  `amddebugq`, login node against a compute node, both directions and a SIGKILLed holder) is the first symmetry
  submission.
- **Partitions.** `amdq` (AMD, 24 h, ≤ 245G), `amddebugq` (AMD, 1 h), `defq` (Intel, 24 h, ≤ 180G) and `debugq`
  (Intel, 1 h), one per job. `longq` is always refused (user rule); `preq` and `amdpreq` are refused because they are
  preemptible with requeue while every `c8d3-` job carries `--no-requeue` (no role of the plan is requeue-safe);
  `sharedq`, `largememq` and every other partition are refused. `-A` is absent or the default account `<USER>`.
  Every AMD-pool job gets `--exclude` with cn112 and the CPU pin's nodes (below) merged into its own value, and a
  `--nodelist` naming any of them is refused (64): cn112 (EPYC 8534P) is AVX-512, and the C7(3) float64 assembly
  differs there by 4 ulp, so bitwise gates hold on the AVX2 nodes (EPYC 7532/7543) only; the pin keeps every AMD job on
  EPYC 7543. Without an own `--exclude` the token is
  `--exclude=cn112,<NODE>,<NODE>,<NODE>,<NODE>,<NODE>,<NODE>,<NODE>,<NODE>` (plus `C8_AMD_EXCLUDE_EXTRA`); an own
  `--exclude=cn[079-087]` becomes `--exclude=cn[079-087],cn112,<NODE>`.
- **CPU pin (HD11; one CPU model per measurement and per campaign; user decision 2026-10-05, "Fix package first").**
  HD11 compares the plan host's CPU with the cost model's, the 7532 nodes run about 10% slower on L8 claims (C62d's
  node note), and every speed gate must pin one CPU model. So every symmetry AMD-pool job runs on `AMD EPYC 7543
  32-Core Processor`, the CPU of symmetry's model `cost_models/gmp_symmetry_epyc7543_c8.json`:
  - **Submission** (`tools/slurm_submit.py amd_exclusions`): cn112, then `budget.SYMMETRY.cpu_exclude`, the AMD nodes
    known not to be EPYC 7543, each with its source: <NODE> (EPYC 7532: J-E0-sym 570281,
    `benchmarks/symmetry_2026-10-c8/stage5_02963bc/val1/environment.txt`; C7(3) pilot 566376), <NODE>–<NODE> (EPYC
    7532: C62d's node note, PLAN-REVIEW-LOG.md:402-407), <NODE> (EPYC 7532: `docs/NUMERICS.md`, the C7(3) run1
    assembly), <NODE> (EPYC 7532: J-E1-sym 570273, `stage5_02963bc/run1/environment.txt`; C7(3) validation_567197),
    <NODE> (EPYC 7532: the guard refused J-SMK-3 batch B's merge 570552, exit 68) and <NODE> (EPYC 7532: the guard
    refused re-merge 570589 and report 570591, exit 68; `stage5_59d4922/wave45_logs/*_570591.out`).
    Known EPYC 7543: <NODE>–097, <NODE>–102, <NODE>, <NODE>, <NODE>.
  - **Found in Stage 5 by the guard (exit 68):** <NODE> and <NODE> (above). They are in `budget.SYMMETRY.cpu_exclude`
    since Stage 6 (2026-10-06), so `C8_AMD_EXCLUDE_EXTRA` no longer needs them.
  - **Unknown** (no record): <NODE>, <NODE>, <NODE>–<NODE>, <NODE>, <NODE>, <NODE> and <NODE>–<NODE>. They stay admissible; the
    job-side guard catches any of them that is not a 7543. The AMD pool (`sinfo`, the draft Stage-5 runbook): `amdq` =
    <NODE>–<NODE> and cn112; `amddebugq` and `amdpreq` add <NODE>–<NODE>; so every pool node is in exactly one of the three
    lists or is cn112.
  - **Job side** (`slurm/site.sh c8_cpu_guard`, run by `slurm/common.sh` before the scratch, so by `lane_worker.sh`,
    `run_array.sh`, `plan.sh`, `merge.sh` and `scratch_probe.sh`, and by `native_job.sh` after its argument checks):
    it reads the first `vendor_id` and `model name` of `${C8_PROC:-/proc}/cpuinfo` (the source of
    `common.cpu_model`, which HD11 compares), collapses whitespace as `production.norm_cpu` does and requires exact
    equality with the site's constant (`c8_site_cpu`: symmetry EPYC 7543, Expanse EPYC 7742; computed in the job, an
    inherited `C8_CPU_EXPECT` is overwritten). An Intel node (`GenuineIntel`: `defq`, `debugq`) passes: it is outside
    the pin and the one-vendor rule covers it. Any other CPU, or an unreadable cpuinfo, exits **68** with one line
    naming the host, both CPUs and the remedy, before any scratch, lane claim, plan, merge, probe record, evidence
    directory or work copy exists ("nothing was claimed or written"). `native_job.sh`'s `environment.txt` records
    `cpu_source` (the file read) and `cpu_read` (the model read). `C8_PROC` is the Mac tests' seam: when it is set the
    guard prints a `C8: WARNING: C8_PROC=... is set ... TEST SEAM` line on stderr (the job's log) and `cpu_source`
    says "TEST SEAM", so a stray export from the submitting shell is never silent; unset it and resubmit.
  - **A new non-7543 node** (a 68, or a probe): `export C8_AMD_EXCLUDE_EXTRA=cnNNN[,cnNNN]` in the login shell
    (`env.sh.example`; only `^cn[0-9]{3}$` items, comma-separated; it can only add nodes, never remove cn112 or a
    constant node; refused under the Expanse profile), resubmit, and move the node into `budget.SYMMETRY.cpu_exclude`
    at the next code commit. `tools/budget.py` is not a pinned tool, so such an addition keeps every existing plan
    valid; `tools/slurm_submit.py` (pinned) only reads it.
- **Intel is AVX-512 too.** The Gold 6148 nodes of `defq`/`debugq` report `avx512` in `sinfo` and are outside the H7
  cap, so they are the natural overflow; the package keeps the bitwise work off them. `raw` admits a job there only
  under a role that starts with `intel_` or `drill_` (64 otherwise): validation, the J-E*-sym gates, replays, builds,
  flag checks, plans and reports run on the AMD pool (cn112 excluded). Campaign jobs (`lane`, `merge`, `off<N>`) may
  run on Intel only for a plan of role campaign: lane mode runs only such plans, and array mode (`submit`, `window`,
  `resubmit`) refuses (64, before the lock) windows or a merge on `defq`/`debugq` for a validation, cost_sweep,
  cost_refresh or flag_check plan (`c8_profile intel` would otherwise send them there, outside the H7 cap). A
  campaign's merge must be on its workers' CPU vendor: `lanes N`, `lanes 0` (against the campaign's live workers) and
  array mode refuse (64) a merge of another vendor, since `slurm/merge.sh` runs the float64 assembly (`assemble.py`).
  One CPU vendor per campaign, and it is durable (S2-001):
  - **The pin.** A campaign's first work admission (`lanes N`, `lanes 0`, `submit`, `window` or `resubmit` past every
    check, before its first `sbatch`) writes `$C8_RUN/cpu_vendor.json` (`amd` or `intel`, with the command, time, host
    and manifest sha256) under the session lock, exclusively (`O_EXCL`, fsynced); a dry run writes nothing.
  - **Every later admission** of the campaign is checked against it: its new jobs, and every live job of the campaign
    in the admission snapshot (the elements a `resubmit`'s merge waits on, also when it brings no new window), must be
    on the pinned vendor, or it refuses (64, nothing submitted); an unreadable pin refuses (69). Choose the pinned
    vendor's profile (`c8_profile`); the pin is never rewritten.
  - **Every job** of the campaign checks it on its node: `slurm/common.sh` runs `slurm/site.sh` `c8_vendor_guard` after
    the CPU pin, so a lane worker, array task or merge on a node of another vendor (`vendor_id` of `/proc/cpuinfo`)
    exits 68 before any scratch, claim or output, naming both vendors.
  - **The merge** refuses checkpoints computed on several vendors (every checkpoint records its CPU in
    `runtime.fingerprint.cpu_model`; `production.py merge`, parallel and `--serial`, before anything is published).
- **Caps (H7; DECISIONS A5 and the 2026-10-05 line "H11 pilot window on symmetry").**
  `C8_RESERVATION="mode=reservation;id=H7;amd_nodes=4;amd_total=8"` is the base split: the live `c8d3-` jobs on
  `amdq`, `amddebugq` and `amdpreq` (counted together, pending included, by their node counts) plus unresolved intents
  plus the new jobs stay ≤ `amd_nodes` (and ≤ `C8_COMPUTE_CAP`, which only lowers it), and together with the live
  `c8d2-` AMD-pool jobs ≤ `amd_total`. The pilot window re-splits it through its DECISIONS line with an expiry:
  `amd_nodes=5` for the pilot session (4 lane workers + 1 merge), `amd_nodes=3` for the other, `amd_total=8`. Intel
  `defq`/`debugq` jobs are outside the cap, as are other sessions' jobs of <USER> (`sri_eng_*`, `lri-prod2`, …).
  A malformed reservation refuses AMD-pool jobs (64) and still admits Intel ones. The snapshots are
  `squeue --all -u <USER> -h -r …` in the Expanse formats (Slurm 21.08.8 prints `-o` and `-O` with `tres-alloc`,
  `RestartCnt`, `SubmitTime` and `EligibleTime` alike; checked 2026-10-05) and the same two `sacct -u <USER>` queries,
  the state-selected one with `-E now`: Slurm 21.08 returns no row for `sacct -s <states> -S <start>` without an end
  time (0 rows on 2026-10-05, against 476 with `-E now`).
- **Accounting (A1.3).** The unit is the allocated core-hour: whole nodes, 64 per AMD node and 80 per Intel node
  (Slurm allocates the Intel node's 80 CPUs: `AllocTRES cpu=80`), or a record's allocated `cpu` when larger. A pending
  exclusive job's `tres-alloc` shows its request (`cpu=1,billing=1`); it is priced at the whole node. Core-hours and
  Expanse SU count 1:1 in one dev line (stop and ask at 4,000, cap 5,000), one pilot line and one production line.
  Each site sees only its own scheduler, so `C8_OTHER_SITE_SU="dev=<x>;pilot=<y>;production=<z>;asof=<UTC>;ref=<text>"`
  carries the other site's **own** line totals into this site's lines. The `production=` key (2026-10-08) is optional:
  a carry without it (the format of an export before the production line) parses, with production 0. An export before
  the production line refuses (64) a carry that has the key; there, drop `production=<z>;` from the pasted line (that
  export has no production line to gate).
  - **Hard per-site sub-caps (S2-004; host decision 2026-10-06).** The dev line's 5,000 is split into 2,500 for
    Expanse and 2,500 for symmetry, defined once in `budget.SITE_CAPS` (their sum is the joint cap; a test asserts it).
    Each site's admission refuses (65) when its **own** projected total (spent + live reservations + unresolved intents
    + the new jobs, from its own ledger and scheduler alone, no carry) exceeds its sub-cap; `C8_SU_APPROVED` does not
    lift it. So no stale carry and no pair of concurrent admissions on the two sites can take the joint line over
    5,000: each site's share is bounded by its own durable records. Moving room from one site to the other is a code
    change of that table. The pilot line has no package value yet (`C8_PILOT_SU_CAP` is approved per pilot), so it has
    no split and keeps its joint check through the carry; so has the production line (`C8_PRODUCTION_SU_CAP`, approved
    per production; `SITE_CAPS['production']` is None). `budget.py` prints each line's `own` against the sub-cap.
  - **Required on both real sites** (`C8_SITE=expanse` and `symmetry`): admission and `budget.py` refuse (64) while it
    is unset. While the other site has no `c8d3-` job since the epoch, the carry is an explicit
    `dev=0;pilot=0;asof=<now>;ref=<why>`. Only the Mac fakes (`C8_SITE=fake`) treat an unset carry as 0.
  - **What to carry.** `budget.py` prints, per line, `own` (spent + live reservations + unresolved intents of this
    site, without the carry it holds) next to `total` (own + the carry), and a ready line
    `carry ... C8_OTHER_SITE_SU="dev=<own dev>;pilot=<own pilot>;production=<own production>;asof=<first-read UTC>;ref=..."` (rounded up to the
    cent; also `carry` in `--json`). That line, and never `total`, is what the other site sets: carrying `total` would
    count each site twice.
  - **Freshness, and what the carry still gates.** The joint checks through the carry, the dev line's 4,000 stop and
    its 5,000 cap (and the pilot line's cap), are **soft**: they are only as fresh as the carry, and their refusals say
    so; the hard bound of the dev line is the pair of sub-caps above. A carry older than 24 h, or more than 10 min in
    the future, is refused (64). The other site's
    existing jobs are in its `own` at their full reservations (a job never spends more than its reservation).
    `budget.py` reads without the lock, in the order intent files, ledger, `squeue`, the two `sacct` queries, so an
    admission running meanwhile can be missing from `own` (its intent appended after the ledger read, its job accepted
    after the unfiltered `sacct`; up to one admission call's reservations, e.g. about 4,640 core-h for `lanes 3`). The
    carry's `asof` is therefore stamped at the first read, the intent-file scan (`carry_asof_utc` in `--json`), not at
    the snapshot: a submission the carry misses always has its intent written after `asof` (repair round 2 of A1; before
    it, `asof` was the snapshot time and such a miss predated it). So the carry misses only the other site's
    submissions whose intents postdate `asof`, and the rule covers them: after every submission on one site, take a new
    carry there (its `asof` then follows that submission) and set it on the other before its next admission. With both
    sites submitting within the same 24 h without that refresh, or concurrently, the joint ask (4,000) can be passed
    by at most the unrefreshed site's new reservations; the joint cap cannot, since each site stays within its hard
    sub-cap of 2,500.
  - Set it in the login shell before an admission, not in `env.sh` (it is a measurement, not a setting); a job that
    runs `budget.py` (the stage-A report) inherits it at submission. Every intent and `submit` record names its
    `site`, `unit` and the carry it was admitted under.
  - **Only an A1 export enforces the joint line.** The carry is read by the `budget.py` and `slurm_submit.py` of the
    export that admits the job (`$C8_PACKAGE/tools/`); exports of commits before 66f3c8d (A1) ignore
    `C8_OTHER_SITE_SU` and gate on their own site alone. The Stage-4b tail on Expanse was admitted that way: the R5b
    rerun (export 75041af) and J-OPT-8 (export 5b9519b, branch `opt-8`), 2026-10-05 19:11 UTC. They are inside the
    joint line because symmetry had no `c8d3-` job since the epoch at that time (`sacct -X -u <USER> -S 2026-10-03`:
    0 jobs, checked just before), so symmetry's own line was 0. From G4b on, every admission on either site runs from
    an A1 export, with the carry set; a pre-A1 export may admit again only while the other site's `c8d3-` count
    is still 0, checked and logged before the admission.
- **Lanes.** `lanes N` puts N workers and the merge on `amdq` (N + 1 AMD-pool nodes: N ≤ 3 in development, N ≤ 4 in
  the pilot window). The default lane shape is 8 × 8 on an AMD node at `--threads 8` and one lane per socket (2 × 20)
  on Intel. The auto lane time uses 64 cores per AMD node (f_class 1) and 40 per Intel node (f_class 1.5, no measured
  Intel model) and is at most 23:30:00. f_class 1 on `amdq` rests on the CPU pin: every lane runs on the model's CPU
  (EPYC 7543), so `tools/lanes.py` never falls back to its 1.5 deadline factor of an unknown CPU. One CPU vendor per
  campaign.
- **Merges.** A merge holds a whole exclusive node and one H7 slot, so it takes the node's cores:
  `-p amdq -c 64 --mem=240G -t 02:00:00` by default (`slurm/merge.sh` sizes `--jobs`/`--parse-jobs` from
  `SLURM_CPUS_PER_TASK`, 4 without `-c`), `-p defq -c 40 --mem=180G -t 02:00:00` for Intel campaigns. Every
  `c8_profile` branch of `profiles.sh` sets `C8_MERGE_SBATCH_ARGS` itself (`lanes`, `debug`: the amdq merge; `intel`,
  `debug-intel`: the defq merge), so a merge cannot carry over from a previous profile.
- **The seed log (HD6), two sites.** Symmetry keeps its own `$C8_SEEDS` (`<SCRATCH>/c8d3/forbidden_seeds.json`).
  - It never starts empty: `seeds.py init` refuses on symmetry without `--from COPY`, and `--from` refuses a copy
    that is not a `c8-d3-seeds-1` log or lacks a seed of the package mirror `designs/forbidden_seeds.json`. Create it
    from a copy of Expanse's `$C8_SEEDS` when Expanse can be read, else from the mirror:
    `python3 -B tools/seeds.py init --from <copy>`. `seeds.py add` and `seeds.py merge` refuse (64) a missing log
    everywhere; only `init` creates one.
  - A non-test `production.py plan` on symmetry refuses (1) a forbidden set (`--forbid-seeds-from`, which may be given
    more than once) that lacks a seed of the package mirror, or a missing mirror.
  - **Reservation before publication (S2-002).** `slurm/plan.sh` runs `production.py plan --reserve-seed $C8_SEEDS`
    (`tools/sweep.py --reserve-seed`, which `native_job.sh`'s `sweep1`/`sweep2` pass, does the same for sweeps): after
    every check and before anything is built or published, under the seed log's own lock (the session lock: on
    symmetry the NFS home's), the log is re-read, the seed rechecked and an entry appended for the campaign's identity,
    its resolved directory. A retry of that directory finds its own entry (idempotent, nothing written); a plan that
    checks seeds (`--forbid-seeds-from`: every non-test plan and every sweep) refuses (65) a seed the log holds for
    another directory, or a derived-seed collision, so two concurrent plans of one seed publish one campaign; a
    test-only plan that checks no seed (the J-SMK-1 twins, `prefix_check.py --real`) registers its seed without that
    recheck, so twins keep sharing theirs. The entry is never removed: a plan, sweep or run killed later keeps it.
    **The reservation is required wherever seeds are checked:** `production.py plan` with `--forbid-seeds-from` and
    without `--reserve-seed` naming one of those logs is refused (65) before anything is read or built, and so is
    `tools/sweep.py`; `tests/argmax_run.py` reserves in its plan (no `seeds.py add` afterwards); `tests/plan_gate.py`'s
    hermetic request checks no seed (its scenarios stop at the input gate or are made test-only by it). `plan.sh` no
    longer runs `seeds.py add` after the plan; `seeds.py add` stays for seeds without a campaign and for test-only
    plans that check none (`prefix_check.py --real`), and finds a reserved campaign `present`.
  - **Sync.** After a seed reservation or `seeds.py add` on one site (a plan job's included), fold that log into the other:
    copy it over through the Mac (`scp`; the two clusters do not reach each other) and run
    `python3 -B tools/seeds.py merge <copy> --log $C8_SEEDS` there (under that site's lock; it appends the entries the
    log lacks, verbatim and in order, and prints the sha256). Before a plan on either site, its log holds every seed
    the other site has registered. The HD6 mirror is refreshed from the symmetry log after a sync (`seeds.py mirror
    --log <copy of the symmetry log>`; append-only: if it refuses because the logs interleave differently, merge the
    copies into the mirror with `seeds.py merge` on the Mac under `C8_SITE=fake`).
- **Scratch.** Every job script computes `C8_SCRATCH` with `slurm/site.sh` (`c8_set_scratch`): `$SLURM_TMPDIR`,
  else `/local1/$USER/job_$SLURM_JOB_ID` on symmetry (`/scratch/$USER/job_$SLURM_JOB_ID` on Expanse), created at
  once (74 if it cannot be). Symmetry sets no `SLURM_TMPDIR` (TaskProlog and JobContainerType are unset) and its
  `/scratch` is `root:root 0755`; `/local1` is `root:root 1777` on <NODE> (2026-10-05) and about 568 GB per node; that a
  compute node lets a job create `/local1/<USER>/` is [I] until J-SCRATCH-sym (`slurm/scratch_probe.sh` on
  `amddebugq`). `C8_MERGE_SCRATCH_BYTES` 5e11 in env.sh. Before repair round 2 of A1 only the jobs that source
  `slurm/common.sh` (lane workers, array tasks, merges, plans) used `/local1`; `native_job.sh`, `inputs_job.sh`,
  `gen_d3_0.sh`, `gen_d3.sh` and `h1_copy.sh` still used `/scratch` and would have failed at once on symmetry.
- **Native jobs (`slurm/native_job.sh`) and their toolchain checks.** `slurm/site.sh` (`c8_toolchain_args`) gives
  `tests/check_build.py` the site's expectations: symmetry g++ 11.4.0 (Ubuntu 22.04's system GCC), Boost 107700 (the
  `boost/1.77.0` module's headers through `CPATH`), the system GMP 6.2.1 with `libgmp.so.10` resolving to
  `/usr/lib/x86_64-linux-gnu` (ldd prints `/lib/x86_64-linux-gnu`, the same file under the merged `/usr`) by the
  loader's default search and no RPATH (`--gmp-search system`); Expanse g++ 13.3.0, Boost 107700 and the Spack GMP
  6.2.1 of `$C8_GMP` by RPATH (`$C8_GMP` must be set there; a missing one stops the job with a message). Any other
  `C8_SITE` refuses (64). Every native job passes the CPU pin first (`c8_cpu_guard`, 68) and records `cpu_expect:`,
  `site_model:`, `cpu_source:` and `cpu_read:` in its `environment.txt` ("TEST SEAM" in `cpu_source` when `C8_PROC` is set). `val1` records a Mac fake refused with "this host is symmetry but C8_SITE is 'fake'" as
  `SITE_REFUSED` (the text comes from the site; another site's text is a FAIL). A symmetry node is symmetry for
  `production.py` and `seeds.py` by its BeeGFS mount whatever `C8_SITE` says, so the scratch packages of the tests
  (`tests/c8pkg.py`) carry the HD6 mirror `designs/forbidden_seeds.json` as every export does, and their seed logs
  start as copies of it (`seeds.py init --from`): the non-test fake plans of `uo_allocation`, `uo_selection_files`,
  `uo_atomic_and_guards` and `prefix_check` then meet HD6/A1 there, and `test_pipeline` reaches its `C8_SITE=fake`
  refusal (`SITE_REFUSED`, as on Expanse). On symmetry the native jobs run as raw jobs on one whole AMD node
  (`-p amddebugq -c 64 --mem=240G -t 00:59:00`, or `amdq` for longer ones; no `-A`).
- **The c8-stage3 baseline per site (`tools/baseline.py`).** Bitwise gates hold within one toolchain (HD9), so every
  reader of the baseline takes its site's record: `reference/baseline_c8_stage3.json` on Expanse (J-SWEEP-1 54676977,
  `c8d3_gmp` 24adff54…), `reference/baseline_c8_stage3_symmetry.json` on symmetry (`--site`, else `C8_SITE`; the Mac
  fakes use Expanse's). `baseline.py sha` gives B0 to the profile and speed jobs (`--expect B0=`, `--expect-sha256`),
  `baseline.py val3` the site's J-VAL-3 `forced_tiers` record for the `forced_tiers` gate, `make baseline` installs
  the site's binaries. A site without its record refuses every reader (65) and the jobs that need B0 fail, so an
  Expanse binary is never used as a symmetry baseline. **The symmetry record was made on 2026-10-05**:
  - J-BASE-sym 570275 built `c8d3_gmp` 3a9a556b… and `c8d3_decimal` 679a0e25… on <NODE>.
  - The symmetry J-VAL-3 570319 passed every step on <NODE> (EPYC 7543). It ran the final default code (export 80ec5e5;
    `src/` is 9fa9421's) with `C8_FT_THREADS=64 C8_FT_MAX_SECONDS=2400`. Its `forced_tiers` record equals Expanse's
    Stage-3 record (`tests/record_compare.py --kind forced_tiers`: status, findings, counts, bounds, sampling,
    results), and so stands for the Stage-3 code there.
  - `reference/baseline_c8_stage3_symmetry.json` names the J-VAL-3 record
    `benchmarks/symmetry_2026-10-c8/stage5_80ec5e5/val3/forced_tiers.json`.

  The procedure: J-BASE-sym (`C8_JOB=basestore
  C8_BASE_PKG=8b8778273bd9`: the c8-stage3 commit's export built on an AMD AVX2 node, `check_build.py` with
  symmetry's expectations, stored read-only in symmetry's `$C8_STORE/baseline/8b8778273bd9/`), then the symmetry
  J-VAL-3 on the same toolchain, then `python3 -B tools/baseline.py record <its SHA256SUMS> --site symmetry --commit
  8b8778273bd9b909461f6ed4f7bf50f68a7cdae5 --job <J-BASE-sym> --forced-tiers-record <the J-VAL-3 forced_tiers.json in
  benchmarks/>` and a commit of the record.
- **The symmetry store (`$C8_STORE=<SCRATCH>/c8d3/store`).** Expanse's store cannot be read while its
  Lustre is unreachable (2026-10-05), so symmetry's is staged from the Mac or rebuilt there, every file by its pin:
  - the run1 archive `run1-20260930-m4096_full.tgz` (sha256 `08969c10…fc80`, 130 MB; J-RUN1 and the pilot report's
    run1 part) from `LRI_C7_D3_HPC_production/` on the Mac (`scp`, then `sha256sum` on symmetry before the rename);
  - the C7(2) d=2 payloads `$C8_STORE/c7d2_frozen/` (a copy of `LRI_C7_D2_HPC/reference/`, checked file for file
    against `gen3/pins/c7d2_frozen_d2.sha256`), the H1 copy `$C8_STORE/h1/46341a3c0f11/` (J-H1-COPY from C62d's
    HANDOFF tree; `C8_H1_PIN` 46341a3c…) and the published d=3 payload `$C8_STORE/d3_payload/46341a3c0f11/`
    (J-GEN-D3 on symmetry, or a copy verified by its `MANIFEST_d3.json` pin);
  - the L8 packs `$C8_STORE/packs/<sha256>.pack`: `make inputs-l8 D3PAYLOAD=… D3PIN=… STORE=$C8_STORE` (J-IN-1's l8
    part) on symmetry, or copies whose sha256 equal the two that `inputs/manifest.json` pins (`make link-l8` checks
    them);
  - `$C8_STORE/baseline/<sha12>/` from J-BASE-sym (above); `$C8_STORE/opt/` stays Expanse's (Stage 4b ends there).
- **Before Stage 5 on symmetry (decisions and work, 2026-10-05).**
  1. *The session lock (decided 2026-10-05: (b), the NFS home; addendum L, "Session lock" above).* The options were
     (a) the administrators enable `tuneUseGlobalFileLocks = 1` on every BeeGFS client, (b) the lock on the NFS home,
     (c) Expanse only, (d) C62d's atomic `mkdir` lock directory (`LRI_C8_D2_HPC/tools/common.py` `DirLock`), which a
     SIGKILLed holder leaves behind until a person removes it. Pinning the lock to <NODE> was rejected because jobs on
     compute nodes take it too.
  2. *After the lock:* J-LOCK-0-sym; J-SCRATCH-sym; the store staging above; J-E0-sym (`val1`: the builds, check_build,
     `make test`'s tests, the vendored suite; since the J-E0-sym repairs of 2026-10-05 in the L8 work copy
     `$C8_ROOT/work/val1_<id>` on BeeGFS, so the store's two L8 blobs must be staged first and `make link-l8` must be
     able to hard-link them across directories there: probe `ln` from `$C8_STORE` into a `$C8_ROOT/work` directory on
     the login node and on an `amddebugq` node first; if BeeGFS refuses it, `link-l8` copies 8.8 GB and
     `check_inputs`' hard-linked scratch packages fail) and J-E1-sym (`run1`: the run1 replay and the order-7 replay
     against c7ref built on the same node) on an AMD AVX2 node; J-BASE-sym and the symmetry J-VAL-3, then the symmetry
     baseline record.
  3. *Array mode under H7.* Each array task counts as one AMD-pool node while unresolved (HD17), so in development an
     AMD array call admits at most 3 tasks with its merge (4 in total; `window OFF:RANGE` windows of at most 3 tasks
     for larger plans), and only campaign plans may put windows or merges on Intel (validation, cost_sweep,
     cost_refresh and flag_check plans are refused there, 64).
- **Not ported.** The Lustre file guards (`C8_FILE_BUDGET`, `lfs quota`) run on Expanse only; symmetry's BeeGFS quota
  is 5 TiB (`beegfs-ctl --getquota --uid <USER>`).
- **The pilot's re-projection** (`pilot_report.py stage-a`, A-PIL-2) prices in the site's unit: the PF and PC lanes on
  the site's lane shape (`C8_SBATCH_ARGS`, or the site's lane default when it names no lane partition: Expanse
  `compute`, 128 SU per node-hour, at most 47:30:00; symmetry `amdq`, 64 core-h, or `defq`, 80 core-h with f_class
  1.5, at most 23:30:00) and the runbook's jobs as Expanse `shared` jobs or symmetry whole nodes (plans, selection and
  report on `amdq`; merges on the lanes' vendor). On symmetry the six runbook jobs reserve 512 core-h (Expanse: 168 SU).
- **Tests (Mac).** `tests/test_ledger.py` (`mount_check_symmetry_lock_on_nfs_home_…`, `lockprobe_symmetry_…`), `tests/test_submit.py`
  (`symmetry_…`), `tests/test_pilot_report.py` (A-PIL-2 on symmetry) and `tests/unit_orchestration.py`
  (`seed_logs_two_sites`), with the fake Slurm in its symmetry mode (`tests/fake_slurm/core.py`, `config(site='symmetry')`).

## Submitting a job: `slurm_submit.py raw`

Every directly submitted job (validation, generation, plans, reports, profiles, sweeps, drills) goes through:

```bash
python3 -B $C8_PACKAGE/tools/slurm_submit.py raw --role val2 --dir $C8_ROOT/evidence/<sha12>/val2 -- \
    -A <ACCOUNT> -p shared --nodes=1 -c 8 --mem=16G -t 01:00:00 -o $C8_ROOT/logs/%x_%j.out --wrap "..."
```

- **`--dir`** must be `$C8_ROOT/runs/<name>` (a campaign the job plans, sweeps or reports on) or
  `$C8_ROOT/evidence/<sha12>/<name>` (64 otherwise). It need not exist yet.
- **Allowed options.**
  - The campaign allowlist without `--begin`: `-A`, `-p`, `-q` (the partition's default only), `--reservation`,
    `-C`, `--mem` or `--mem-per-cpu`, `-t`, `-c`, `--gres`, `--tmp`, `--mail-*`, `--signal`, `-x`, `-w`, `-L` and
    `--wckey`.
  - Plus `--wrap`, `-o`, `--nodes=1`, `--ntasks=1`, `--exclusive` (on `compute` only), `--no-requeue`, and one
    batch script, whose `#SBATCH` lines are read with the same allowlist.
  - **Batch scripts are read as `sbatch` reads them.** A directive counts only at column 0: an indented `#SBATCH` is a
    comment to `sbatch`, and to the tool. Blank and comment lines are skipped, and the first command line ends the
    scan. Refused (64): any `#SLURM`, `#PBS` or `#BSUB` line (`sbatch` would apply it unpriced), a script that is not
    UTF-8, one that does not start with `#!`, and one with DOS line breaks (`sbatch` refuses those two itself).
- **Required.** `-A <ACCOUNT>`, a partition (`compute`, `shared` or `debug`), `--mem` (or `--mem-per-cpu`) and `--time`.
  `shared` also requires `--nodes=1`.
- **`--time` in whole minutes (S2-003).** Slurm reserves whole minutes (a seconds part rounds up), so the resolved
  limit is normalized up to the minute before the partition check, the pricing and the intent, and a request with a
  seconds part is submitted as that value (a `--time=<D-HH:MM:00>` token after the user's, which wins over the user's,
  `#SBATCH` and `SBATCH_TIMELIMIT`); a whole-minute request is submitted as given. Elapsed times (`sacct`, `squeue`)
  are never rounded.
- **Refused (64)**, on the command line, in `#SBATCH` lines and in `C8_SBATCH_ARGS`/`C8_MERGE_SBATCH_ARGS`:
  - `-J`/`--job-name`, `--comment`, `--hold`/`-H`, `--begin`, `--requeue` and `--array`;
  - `--dependency`, except `--dependency=afterany:<job id>` for a `drill_*` role on `shared` or `debug` (J-DRL-10);
  - `--exclusive` off `compute`: an exclusive `shared` or `debug` job gets, and is billed, the whole node;
  - both memory forms, neither, or `--mem=0`;
  - a time above the partition's limit (debug 30 min, else 48 h);
  - memory above the ceiling (compute and debug 240G, shared 243G).
  - `SBATCH_*` inputs outside the allowlist are removed from `sbatch`'s environment; `SBATCH_REQUEUE` refuses (64).
- **The campaign option sets** `C8_SBATCH_ARGS` and `C8_MERGE_SBATCH_ARGS` take only the campaign allowlist (the
  inherited one without `--begin`, `-J`/`--job-name`, `--hold` and `--requeue`). `raw`'s extra options are refused there
  (64): `--wrap`, `-o`/`--output`, `-d`/`--dependency`, `-N`/`--nodes`, `-n`/`--ntasks` and `--exclusive`. The tool and
  the campaign scripts set those (the scripts add `--nodes=1`).
- **Names and comments.** Every job is named `c8d3-<role>-<C>-<T>` and carries the comment `c8d3:<C>:<P>:<T>`.
  - C is the first 12 hex digits of the sha256 of the resolved directory.
  - P is the same of `<dir>/manifest.json` if a plan is published there, else `000000000000`.
  - T is a fresh 12-hex token from `secrets.token_hex(6)`, which links the job to its intent.
  - Under `C8_BUDGET_LINE=pilot` the tool prefixes every role with `pilot_`, under `C8_BUDGET_LINE=production` with
    `prod_` (`budget.LINE_PREFIX`). A caller's role that starts with `pilot_` or `prod_` is refused (64) under every
    line: the name alone puts a job in its line.
  - `raw` refuses (64) the campaign roles `lane`, `merge` and `off<N>`: such a job would look like a lane worker, a
    merge or an array window of its campaign to every rule that selects a campaign's jobs by role and C.
  - Every job carries `--no-requeue`.
- **`--dry-run`** prints the admission counts, the SU projection and the new reservations, and submits nothing.

### What admission does (D.11), under the session lock

1. **Snapshot.** Two `squeue` snapshots, then two `sacct` queries. A failure or a 60 s timeout refuses (69):
   - the account snapshot `squeue --all -A <ACCOUNT> -h -r` over the live states, with `%i|%F|%u|%P|%q|%T|%j|%D|%C|%m|%l|%r|%k`;
   - the user snapshot `squeue --all -u <USER> -h -r --states=all -O ...`, with the same fields plus `tres-alloc`,
     `StartTime`, `TimeUsed` and the attempt fields `RestartCnt`, `SubmitTime` and `EligibleTime`;
   - `sacct -u <USER> -X --duplicates -S <epoch> -P`, and the same with `-s CA,CD,F,TO,NF,OOM,PR,BF,DL,RQ`.
2. **Ledger, intents and adoption.**
   - The ledger's record check runs (below).
   - The intents of both copies are evaluated against the snapshot. Each one that evidence resolves gets its
     `resolution` record, and its file is renamed. A resolution interrupted before its rename is completed first.
   - Every `c8d3-` job of the scheduler that no `submit` or `adopted` record names is adopted. An array is one record
     `{job_id, task_range}`. The directory is resolved to an existing directory with the same C, or else recorded as
     `dir: null`; a later admission appends the resolving `annotation`.
   - An **unattributable** job blocks admission (69) until `ledger.py rebuild --reason ...` records it or the host
     decides. Unattributable means: its name does not parse, a live job's comment is missing or does not parse, or
     the comment's C or T differs from the name's. No tool ever cancels such a job.
3. **Shares** (H7E-R, from `C8_RESERVATION`). The count k is the call's new jobs; array tasks count individually:
   - live `c8d3-` normal-QOS jobs, pending ones included, + k <= `run` (11);
   - non-terminal ones + k <= `sub` (27);
   - account: running normal-QOS jobs of every <ACCOUNT> user + this session's pending ones + k <= `acct_run` (32);
   - live `c8d3-` compute nodes + k <= the node cap: `C8_COMPUTE_CAP` (4 during development), never above the active
     reservation's `dev_nodes` (after `until`, the base split's 4). A cap left at a pilot window's count under the base
     split therefore binds at 4, and the tool says so;
   - live `c8d3-` `shared` jobs + k <= `shared` (32);
   - account `debug` jobs + k <= 2.

   Every unresolved intent counts as stated under "Slots" below. The detectors refuse normal-QOS admission (65) and
   cancel nothing: `c8d2-` jobs beyond 11 running or 27 live; any live `<USER>` normal-QOS job outside both
   prefixes; the user's normal-QOS total beyond 22 running or 54 submitted. A refusal exits 65, names the binding
   share and prints the largest admissible N.
4. **SU gate** of the line (below).
5. **Per job: intent, then submit.**
   - The tool prints the partition's idle-node count and `sbatch --test-only`'s estimate.
   - It writes the **intent twice**: first a fsynced `intent` record in the ledger, then `intents/<T>.json`, created
     with `O_CREAT|O_EXCL` and fsynced with its directory.
   - **Age check.** If more than 60 s have passed since the intent's monotonic stamp, a `not_submitted` record is
     appended and the call exits 69.
   - The launch is `timeout -s KILL 120 slurm/exec_guard.sh <intent utc + 60> sbatch --parsable ...`. The guard execs
     `sbatch` only within the intent's utc + 60 s; otherwise it exits 86 (`c8d3-exec-guard: late`).
   - **The exec guard must be an executable file.** `timeout` runs it through its exec bit, so a missing guard or one
     without its mode (an export that dropped file modes) refuses the call (64) before any intent is written. A
     `timeout` that cannot start its command anyway (exit 125, 126 or 127 with `timeout: failed to run command`) is
     recorded `launched: false`, at zero cost; it is never an ambiguous submission.
   - **A `timeout` that cannot be started at all** (missing from `PATH`, not executable, a failed fork) is also
     `launched: false`: no process ran, so no `sbatch` can exist. The `not_submitted` record resolves T at zero cost and
     the call exits 69. Only an OS error after the wrapper started is ambiguous.
   - **The 60 s age check and the 120 s KILL bound the client only.** `slurmctld` can accept a request at any later
     time, and no rule assumes a deadline.
6. **One `submit` record per job.** It carries `C8_RESERVATION`, the counts, the SU projection and the approval.
   A failed append exits 74 and cancels nothing: the job is counted through its intent and adopted next time.
   - **No append after a failed one.** A failed or short ledger append (or a failed `fsync`) is followed by no further
     append in that call, whatever job of the call it hit: the ledger ends in the torn bytes, which the next admission
     truncates, and the call's jobs already submitted get no `submit` record; the tool prints their ids and the next
     admission adopts them. The same holds after a failed lock-descriptor `fsync` check.
7. **Re-snapshot.**
   - On a violation (other users' jobs starting in the window), the call cancels its normal-QOS jobs with
     `scancel --state=PENDING`. It then re-queries and reports every job that had started, or that started and was
     then cancelled, and exits 65.
   - A merge is cancelled only if no live worker depends on it, and a superseded merge only after the re-snapshot
     passes.
   - `squeue --start` and `sprio -j` are printed and recorded as an `annotation`. Their failure is reported, not fatal.
   - **A failed `scancel` or re-query ends the call (69), state unknown.** The tool then names every job of the call
     that may still be pending and claims no cancellation: check `squeue --all -u <USER>` and cancel those jobs before
     any new submission. A failed `scancel` of a superseded merge also exits 69; that merge stays pending and counted.

**Residual race (stated bound)** (D.11).

- **Within this session nothing undercounts.** The lock serializes admission decisions, and every job is preceded by
  a durable intent that every later admission counts.
  - A killed submitter's intent is on disk before its `sbatch` starts.
  - An evicted holder's intent was either fsynced before the eviction, so the next holder counts it, or its
    lock-descriptor `fsync` check fails, so no `sbatch` follows.
  - A damaged or missing ledger cannot hide an intent either: each intent has a second copy, and repair restores it or
    stays blocked (up to D.12's stated residual).
  - Nothing is released on a sighting, on G, on elapsed time or on empty queries. So a job accepted at any moment
    relative to a later admission's queries (before its `squeue` snapshots, between them and its `sacct` queries, or
    after G) is counted through its intent before that admission decides, up to the residual that a user's decision
    accepts ("Manual closing" below). The re-snapshot is not needed for this.
- **Across sessions:** C62d submits only `c8d2-` jobs inside its own disjoint share (H7E-R), so neither session can
  consume the other's 11 / 27, and the user's 22 / 54 holds whenever both shares do.
- **The one rule others can invalidate after a snapshot** is the account total (at most 32 running), through jobs of
  other users or of C62d that start in the window Δ between this call's snapshot and its re-snapshot. Δ is bounded by
  the command timeouts (60 s per query, 120 s for `sbatch`) and lasts seconds in practice.
- **The bound.** A call can put at most its own k normal-QOS jobs (k ≤ 11) over the account total, for at most Δ plus
  the run time of those of them that started inside Δ; the re-snapshot cancels the rest while they are pending.
  Slurm's MaxJobsPA = 32 still caps the account's running jobs, so the excess can only delay other users' pending jobs.
  It never breaks the QOS limit or this session's share.

**Exit codes:** 64 invalid input; 65 refused by admission or the SU gate; 69 unknown state (a query failure, a
damaged ledger, a repair block, an unattributable job, a failed lock `fsync` check, the age check, a failed `scancel`
or re-query at the re-snapshot); 74 a ledger or
intent write failed (EDQUOT, ENOSPC, EIO, a short write); 75 the session lock is held past `C8_LOCK_WAIT`. An OS error
that no step maps (an unreadable directory, say) exits 74 for a write failure and 69 otherwise, naming the path; no
tool ends in a traceback.

### Cross-session admission mode (`C8_RESERVATION`)

- The default is `mode=reservation;id=H7E-R;run=11;sub=27;acct_run=32;shared=32;dev_nodes=4`, the base split. It is
  parsed strictly.
- **Malformed** (an invalid line, an unknown or withdrawn mode, or a re-split without `until`): every normal-QOS
  submission is refused (64). `shared` and `debug` jobs are still admitted, under the base `shared` share (32) and the
  `debug` limit (2) (A-ORC-11).
- **Unset, or `mode=none`.** No normal-QOS job is admitted (65). `shared` and `debug` jobs still are, under their own
  rules.
- **Pilot re-split.** A pilot window re-splits the shares only through a new DECISIONS line. Its id goes in `id=`,
  with `;until=<UTC YYYY-MM-DDTHH:MM:SSZ>`. Only the base split (`id=H7E-R` with the counts above) may omit `until`.
  After `until`, normal-QOS admission refuses (65) until the base split is restored, and the `shared` share falls back
  to at most the base split's 32: an expired window never keeps a larger share.
- **Withdrawn.** The r1 modes `common-lock` and `turn` are refused as unknown (64).
- **The agreed reservation**, copied from `LRI_C8_shared/inventory/DECISIONS.md:87` (that file's sha256 at the copy,
  2026-10-04: `c81aa0faae0da6f420a6f54c3116ab48131ea2206e8b7734228d309a0faf67a8`):

  > | 2026-10-03 | H7E-R (Expanse disjoint reservation) | AGREED by C62d and C63d (C63d proposal after its Codex plan
  > review r1, finding R08; C62d's answer relayed 2026-10-03). Of the user's 22 running / 54 submitted normal-QOS
  > budget on <ACCOUNT>: C62d at most 11 running / 27 submitted `c8d2-*` jobs; C63d at most 11 / 27 `c8d3-*` jobs. Every
  > admission also checks that the whole <ACCOUNT> account stays at or below 32 running, other users included. Shared
  > partition: at most 32 live jobs per session. Development: at most 4 compute nodes per session. A pilot window can
  > re-split the budget temporarily, through a DECISIONS line. Each submitter needs only its own lock. C62d implements
  > it in its slurm_submit admission in Stage 3 (A-ORC-11/12). | C63d |

## The budget: `tools/budget.py` (HD17)

- **The billing function**, one for proposed jobs, intents and scheduler records. In SU per hour:
  - `compute`: 128 per node;
  - `shared` and `debug`: max(CPUs, ceil(mem_GiB/2)), so a job is charged by cores while `--mem` <= 2G per core.
  - A proposed job's options are resolved in `sbatch`'s precedence: the command line, then the allowed `SBATCH_*`,
    then `#SBATCH` lines. A scheduler record is priced from the `cpu`, `mem` and `node` of its `AllocTRES` (`ReqTRES`
    while pending), or from `billing`/3600 when that is larger.
  - A live `squeue` line takes those from its `sacct` row. Without one, it takes them from `tres-alloc`; with
    neither, it is priced at 128 per hour and reported. `%m` is never read as memory.
  - A reservation is the billing value × the time limit in hours.
- **Charges**, per attempt and per array task. Every rule errs towards charging more:
  - a finished `sacct` attempt (`REQUEUED`, `NODE_FAIL` and `PREEMPTED` included): billing × ElapsedRaw;
  - a live `squeue -r` line: its full reservation;
  - a live `sacct` row that `squeue` does not list at all: its full reservation, per task for a collapsed row;
  - a finished `squeue` line whose own attempt has no finished `sacct` row: billing × `TimeUsed`. The attempt is told
    by its start (`StartTime` against `Start`; two never-started entries match), since a requeued job keeps its job id:
    an older attempt's finished row (a `NODE_FAIL`, say) does not account for a later attempt that `sacct` has not
    delivered yet.
  - an earlier attempt that `squeue`'s `RestartCnt` shows and `sacct` has not delivered as a finished row (a requeue
    despite `--no-requeue` while `sacct` lags): its full reservation, each, until `sacct` delivers it. This holds while
    the job is live again too, since `squeue` lists only the current attempt.
  - `squeue` runs before `sacct`, so a requeue between them is charged both ways.
- **Lines.** A role that starts with `pilot_` counts in the pilot line, one that starts with `prod_` in the production
  line, any other parseable `c8d3-` name in the dev line, and an unparseable `c8d3-` name in all three
  (`budget.name_info`, `line_of`). `c8d2-` jobs never count. An intent counts in the line its payload names. So
  production jobs never enter the dev or pilot line, and dev and pilot jobs never enter the production line.
- **Gate.** The projected total is spent + live reservations + unresolved intents + resolution records (one count per
  token) + the new jobs' reservations. First this site's own projected total against its hard sub-cap (dev: 2,500,
  `budget.SITE_CAPS`, no carry; S2-004); then, with the other site's carry, the dev line refuses above 4,000 SU without
  `C8_SU_APPROVED`, and always above 5,000 (both soft: as fresh as the carry); the pilot line refuses above
  `C8_PILOT_SU_CAP` and the production line above `C8_PRODUCTION_SU_CAP` (both with the other site's carry; no
  per-site split). Every job runs with `--no-requeue`, so a job admitted under
  the gate costs at most its full reservation. Under Amendment A1 every line also holds the other site's carry
  (`C8_OTHER_SITE_SU`, section "Symmetry (Amendment A1)"), required on Expanse and symmetry alike.
- **Standalone.** `python3 -B tools/budget.py [--json]` reads without the lock, records nothing, and says so. It
  applies the same evidence rules as admission, in memory: an intent that terminal rows (a) or never-started evidence
  (c) resolves is shown as "resolved by evidence now" and counted at that rule's charge (the scheduler charge, or 0),
  without its slots; the next admission records it. An interrupted resolution (its record written, its file not yet
  renamed) stays counted until admission completes it. It reports jobs with more than one attempt. It refuses (69)
  on a query failure or a ledger in need of repair. It opens no file of the package but the ledger and the intent
  files.
  - **Read order without the lock.** `budget.py` and `ledger.py check` scan `intents/` and `intents/resolved/` before
    they read the ledger. An intent file exists only after its ledger record was fsynced, so every file seen has its
    ledger copy in the later read: a file still being written by a concurrent submitter, or one whose write failed,
    counts from that copy and never raises a false repair alarm.

### Intents (H-f, H-g, H-h)

Every `sbatch` is preceded, under the lock, by an intent written twice: a ledger record and `intents/<T>.json`.

- **Union rule.** A token is unresolved while either copy is: the ledger holds no `resolution` and no `not_submitted`
  without `ambiguous`, or the file is still in `intents/`.
- **Slots (HD17 "Slots", the one statement of the slot rule).** An unresolved intent counts, in every slot class it
  occupies, the larger of its planned jobs (array tasks individually) and the live `squeue` lines carrying T, at every
  age, until it is resolved, by affirmative evidence or by the user's decision. Nothing else frees a slot:
  - no sighting of its job in either source;
  - no elapsed time;
  - not G = 30 min (`INTENT_GRACE`), which only gates `ledger.py resolve` and `rebuild --user-decision`.

  An ended job holds its slots until its terminal rows arrive, normally minutes. An array holds all its planned tasks
  until every task is terminal.
- **SU.** An unresolved intent is charged the larger of its `reservation_su` and the charge of the scheduler entries
  carrying T, and for good unless evidence resolves it. The evidence is one of:
  - (a) terminal `sacct` rows for the latest attempt of the job, or of every task (a collapsed finished row covers its
    tasks), with no live `squeue` line carrying T. While `squeue` still lists a finished line of T whose own attempt
    has no finished `sacct` row, (a) waits: an older attempt's row is never taken as the last one;
  - (b) the submitter's unambiguous `not_submitted` record: no `sbatch` launched, or a listed rejection;
  - (c) never started: every job or task finished, with no start, zero elapsed and no other attempt, in the user
    snapshot or the state-selected `sacct`. From the user snapshot alone, "no other attempt" needs the line itself to
    prove it: `RestartCnt` 0 and `SubmitTime` equal to `EligibleTime` (or no eligible time, a dependency never
    satisfied). A requeue increments the count, resets the submit time and delays the eligible time. Any other line
    leaves (c) to `sacct`, and a line whose `RestartCnt` shows a requeue rules (c) out whatever `sacct` shows. (a) also
    waits while an earlier attempt that `RestartCnt` shows has no finished row.

  Admission records each resolution it sees: a `resolution` record, then the rename to `intents/resolved/`.
- **Ambiguous submissions.** A kill by `timeout`, and any unlisted `sbatch` error (a socket timeout, a lost
  connection), are recorded `ambiguous: true` and release nothing.
- **Over-count bound.** An intent over-counts by at most one reservation and one submission's slots, per crashed or
  ambiguous submission, or per job whose accounting Slurm lost. Nothing under-counts, beyond D.12's stated residual
  (both copies destroyed while the job's accounting was lost).
- **Manual closing.** `ledger.py resolve T --user-decision PLAN-REVIEW-LOG.md:<line>` is for a stuck intent: a job
  whose accounting never arrives, an ambiguous submission whose job is never seen, or an array with a task cancelled
  alone. **Cancel whole arrays, never single tasks.**
  - It needs a logged decision line of the decision log (`--decision-log`, default
    `$C8_ROOT/decisions/PLAN-REVIEW-LOG.md`, a copy of `LRI_C8_D3_HPC_loop/PLAN-REVIEW-LOG.md`). The tool records the
    line's text and its sha256.
  - It is accepted only from G after the intent, and refused (69) while a live `squeue` line carries T.
  - It frees the intent's slots. Its SU stays at the full reservation without evidence; a later larger `sacct`
    charge replaces it, a smaller one never does.

## The session lock and the ledger: `tools/ledger.py` (D.11, D.12)

- **The session lock.** It is `fcntl.flock` on `$C8_ROOT/locks/c8d3.lock`, held by every submitter and every ledger
  and intent-file writer, `ledger.py register` inside jobs included, and by `lanes.py queue` and `release-stale` in
  place of the inherited mkdir campaign lock `.c7_submit.lock` (D.11 "Who takes it").
  - A failed `fsync` check at acquisition (69) releases the lock at once, also inside a process that goes on.
  - The kernel releases it when its holder exits or dies, SIGKILL included, so there is nothing to remove by hand.
    The file is created 0600 (its directory 0700) and never deleted or renamed.
  - It is polled every 0.2 s for at most `C8_LOCK_WAIT` (1,800 s; a finite number of seconds >= 0, else 64). On timeout the caller exits 75, printing the
    holder line.
  - **A lost client** keeps the lock until Lustre evicts it. Before each `sbatch`, each ledger append and each
    intent-file write or rename, the holder rewrites its holder line through the lock descriptor and calls `fsync`.
    A failure ends the call (69) before that step.
  - **Mount check.** At every acquisition under `C8_SITE=expanse`, the lock file's mount must be `lustre` with `flock`
    among its super options. `localflock`, `noflock`, no `flock`, another type, a missing entry and an unreadable
    mountinfo refuse (69), naming the host, the mount point and the options.
  - **J-LOCK-0 is the first Expanse submission.** It runs `ledger.py lockprobe` on `$C8_ROOT/locks/probe.lock`, never
    the live lock. If its lock or mount check fails, the host STOPS, submits nothing further, and revises the plan
    with the user.
    - Each run keeps its markers in `--markers DIR/<SLURM_JOB_ID>`; the login side passes `--job ID` (or, off Slurm,
      takes the one fresh run directory). With `--job ID` the login side starts only once `squeue` shows the job
      RUNNING (polled every 5 s, in the scheduler environment, so an exported `SQUEUE_STATES` cannot hide it) and the
      ready marker exists. A job that is not RUNNING within `--wait` is a queue wait (69, not a lock result). A repeat
      therefore needs a new job, and never reads an earlier run's markers.
    - `--interval` (default 15 s) must be finite, in [0, 60] s; `--wait` (default 600 s, the handshake bound) finite,
      in (0, 600] s, and at least 4 × `--interval`, so that every marker wait outlasts the three `LOCK_NB` attempts
      and the holder's hold. Anything else (`nan`, `inf`, `1e999`) refuses (64) before the probe file or a marker
      exists.
    - A side whose lock call (`flock`, including `ENOSYS`/`EOPNOTSUPP`) or mount check fails writes `failed.<side>`
      and its `--out` and exits 69; the other side records `peer_failed` with that step. Both verdicts then say "the
      host STOPS". Only a handshake that expires with no failure on either side is "repeat; not a lock result".
    - **"Returns only after the recorded release" is checked causally** in (i) and (ii). The holder keeps the lock for
      `--interval` (15 s) after the waiter's NB-failed marker, then writes its release marker and only then unlocks.
      The waiter's step passes only if that marker exists at the moment its blocking acquisition returns; the two
      sides' timestamps (two clocks) are compared, with 1 s of skew, only as a second check. A lock that grants early
      fails the step, and the host STOPS.
- **The ledger.** One framed record per line: `{"rec":<canonical JSON>,"sha256":"<sha256 of it>"}`, at most 65,536
  bytes. The kinds are `intent`, `submit`, `adopted`, `register`, `annotation`, `resolution` and `not_submitted`, and
  every record names its tokens. Nobody edits the ledger or an intent file by hand: a hand-written line fails its
  checksum.
  - **Record check at every acquisition.** A torn final record (no newline) is copied to
    `ledger_evidence/tail.<UTC>.<sha12>`, then truncated. Anything else is interior corruption: every writer and
    admission refuse (69), naming the file, the line and the byte offset.
- **`ledger.py rebuild --reason TEXT`** is the only repair.
  - It keeps every valid record in order and restores every intent from its file.
  - It matches every segment of every invalid line (split at frame starts) to a surviving intent copy, by byte range
    or by token.
  - It adopts unrecorded jobs, records unattributable jobs with `attribution: null` and the reason, and installs the
    new file by rename.
  - **It stays blocked (69, nothing written but evidence)** when a segment is unmatched, when an intent file cannot be
    read and no valid intent record carries its token, when a token has resolving or `not_submitted` records but no
    intent copy (both copies of a resolved intent lost), and always when the ledger is missing. These are exactly the
    conditions on which admission and `budget.py` refuse, so a rebuild either repairs or reports a block.
  - Only the user's decision ends a block: `rebuild --reason ... --user-decision PLAN-REVIEW-LOG.md:<line> --hold-su S
    --hold-line dev|pilot`. S must be a finite number >= 0 (64 otherwise, before anything is written). It holds S SU in that line for good, and its hold lists the tokens it covers (`covers`):
    their leftovers (a resolving record, an unreadable file) block nothing afterwards.
    - **G runs from the current conditions.** Each block record lists its conditions. The decision is accepted no
      earlier than G after every current condition has been on record without a break; an older block of a condition
      that has since cleared does not count.
    - **Crash safety.** The new ledger with the hold is installed (rename, directory `fsync`) before any unreadable
      intent file leaves `intents/` for the evidence. A kill or a write failure (EDQUOT at create, a short write, EIO
      on a rename) at any step leaves either the block or the hold, never a lifted block without the hold; re-run the
      decision (still blocked) or `rebuild --reason` (to finish moving the files).
- **`ledger.py register DIR --role plan|sweep`**, inside a plan or sweep job, links the job (id, restart count, T) to
  DIR and its published plan's P. It is idempotent per restart.
- **No writer re-creates a missing ledger.** `register` and `resolve` refuse (69) on a missing ledger. Only admission's
  first use on a new root (no intent file, no `c8d3-` job) and `rebuild` create the file.
- **Write failures exit 74, never a traceback**, also at file creation (EDQUOT from Lustre's file quota is raised at
  create): intent files, evidence files, the ledger, `rebuild`'s temporary file and its renames.
- **`ledger.py check`** prints the record check and the unresolved intents, without the lock.

## Tests (Mac)

```bash
python3 -B tests/test_ledger.py            # ledger.py alone: framing, intent files, record check, rebuild, lock, mounts, lockprobe
python3 -B tests/test_submit.py            # A-ORC-11/12/17 on the stateful fake Slurm (tests/fake_slurm/); about 1 min
python3 -B tests/test_submit.py --quick    # 60 instead of 500 seeded interleavings
python3 -B gen3/test_gen3.py               # A-INV-1 and the gen3 gate tools on tiny fixtures (builds with g++-16 on macOS)
python3 -B gen3/test_gen3.py --sanitize --build-sanitize   # the same under the sanitizer builds, with the self-test
C8_ALLOW_NO_L8=1 python3 -B tests/check_inputs.py   # the inputs: regeneration, A-IN-1, A-IN-2, A-IN-4 (L <= 7); about 40 s
python3 -B tests/check_vendored.py         # A-ASM-1(a) and (b): the vendored set, its read rule and the inputs pins
make test-python                           # Stage 3a: every pure-Python test (about 25 min on the Mac; list in the Makefile)
```

`make test-python` (with `C8_ALLOW_NO_L8=1` on the Mac) runs `check_inputs`, `unit_orchestration` (A-ORC-1..16 on the
fake worker and the fake Slurm; `recovery_merge` is F8-d3's J-DRL-8 through `slurm/merge.sh`), `blocks_test`,
`test_pipeline` (A-DES-7 (a)–(e)), `test_submit`, `test_ledger`,
`cost_refresh_test` (D.14), `prefix_check` (A-DES-8 (a)–(d)), `members_test`, `merge_scale` (A-ORC-6, Mac part),
`assembly_checks --exact` (A-ASM-2/4/5), `compat_run1` (A-ASM-3), `verify_result_tamper` (A-ASM-6/7),
`test_pilot_report` (A-DES-3/4), `design_fallback_test` (A-DES-2), `ast_scan`, `archived_replay`,
`test_delivery_verifier`, `thru_report_test` (J-SMK-4's report on fake lane campaigns), `drill_select_test` (J-DRL-9's
selections; `test_pipeline` runs the drl9 scenario end to end), `integration_3a` (the worker contract: A-KER-3 refusals,
the C.3 row forms, the CPU pin, the Stage-5 native modes),
`native_static` (A-KER-1 grep, C.9, the C.8 Makefile on a fake compiler), `check_build --selftest` (A-KER-3) and
`workflow`/`staging --fake` (with stage_runtime's pack reads under a read spy) and `pack_reads_test` (F12: every pack
member reader reads exactly the members' bytes with `os.pread`). `tests/vendored_isolated.py` (`--in-place` on an export) and `gen3/test_gen3.py` run
beside it; `vendored_isolated.py` fails on an export that carries bytecode anywhere and names the paths, and the root
`.gitignore` keeps `__pycache__/`, `*.pyc` and `.pytest_cache/` out of commits (03e1e7e–cd90cd7 tracked two Mac `.pyc`
files, which failed J-E0-sym's `vendored_isolated`), and `tools/verify_delivery.py` skips any `.pytest_cache/` like
`__pycache__/` (so `--strict` passes on a Mac tree after pytest ran, and `--write` neither lists nor refuses one). On a git-archive export, `check_vendored.py` needs the review
record at `../LRI_C8_shared/inventory/reviews/` or `--no-review-record`.

The `lanes N` and `submit` cases of A-ORC-11/17 run the admission engine through `tests/fake_slurm/driver.py` with
the job sets of those entry points. Stage 3 wires the campaign entry points themselves. A-ORC-17 (k)'s negative scan
holds as written: `tools/` and `slurm/` contain no mkdir lock and no job-creating `sbatch` launch outside D.11 step 5.

## d=3 payloads: `gen3/` (Stage 1; PLAN component A)

`gen3/` turns H1's d=2 G-files into the d=3 payloads and holds C63d's gates on H1. Every gen3 writer refuses an
output, scratch, staging or evidence path under C62d's trees (`<SCRATCH>/temp_project/c8d2/`
and any `.../LRI_C8_shared/inventory/`, symlinks resolved): exit 2, naming the path.

- **`make gen3`** builds `bin/gen3/regenerate_rates` with A.1's exact command (`g++ -O2 -std=c++17 -fopenmp -Wall
  -Wextra`) and `bin/gen3/size_probe`. **`make gen3-sanitize`** builds `bin/gen3/regenerate_rates_san` (A.1's command
  plus `-O1 -g -fno-omit-frame-pointer -fsanitize=address,undefined -fno-sanitize-recover=all -D_GLIBCXX_ASSERTIONS
  -ftrivial-auto-var-init=pattern` and STRICT) and the coverage self-test binary
  `bin/selftest/regenerate_rates_unguarded_san` (`-DC8_TEST_UNGUARDED_INDEX`, which cannot compile without
  `_GLIBCXX_ASSERTIONS`). A build that prints a compiler warning fails. Each binary gets `<binary>.build.txt`.
- **`regenerate_rates JOBLIST`** (pairs `<input> <output>`): the d=3 rate line of each G-file, everything else copied.
  A malformed input exits 2 with `<input path>: <field> <reason>`, writes no output and prints no record; outputs are
  written as `.tmp` and renamed only after every job succeeded. The stdout record per file: `cancelled_nonpositive_subsets`,
  `minimum_rate_quarters`, `raw_histogram`, `min_raw`, `double_lift_subsets` (raw p4 <= -5).
- **Pins.** `gen3/pins/c7d2_frozen_d2.sha256` lists the 3,774 frozen C7(2) d=2 payloads (relative to
  `LRI_C7_D2_HPC/reference/`; the Stage-0 copy `$C8_STORE/c7d2_frozen/` matches it file for file);
  `gen3/pins/PINS.json` pins that list and the digest of the 3,512 C7(3) payloads (`reference/inputs/`).
- **Tools.** `gates_d3.py` (gate1a, summary-gen-d3-0; h1-copy, h1-auth, source-unchanged, split-audit, gate1b, gate2, gate3,
  gate4, gate5, gate7, determinism; report), `opcount.py`, `weights_check.py`, `kirchhoff3.py`, `forest_check.py`,
  `check_dimension8.py`, `publish_d3.py`, `verify_d3.py`, and the driver `run_d3.sh`. Exit 0 = passed, 1 = a gate
  failed (the record says which check), 2 = refused or bad input.
- **Job scripts** (`slurm/`; D.10): `gen_d3_0.sh` (J-GEN-D3-0), `h1_copy.sh` (J-H1-COPY), `gen_d3.sh` (J-GEN-D3).
  Each runs `set -eo pipefail; source "$C8_ENV_SETUP"; set -u`, computes `C8_SCRATCH` inside the job
  (`$SLURM_TMPDIR`, else `/scratch/$USER/job_$SLURM_JOB_ID`; a login-node value is overwritten) and sets
  `TMPDIR=$C8_SCRATCH/tmp`, so neither g++ nor Python writes to the node's `/tmp`. They take no arguments
  (`slurm_submit.py raw` refuses words after the script): their inputs are environment variables exported on the
  login node, which sbatch's default `--export=ALL` carries into the job. Malformed inputs exit 64; a missing
  required variable stops the script at bash's `${VAR:?}` check with exit 1.

### J-GEN-D3-0 (Stage 1a; G1a = A-INV-1 and A-INV-2(a))

`slurm/gen_d3_0.sh` on `shared`: `make gen3 gen3-sanitize`; `gen3/run_d3.sh --pre-h1` (gate 1(a): the pinned d=2
copy verified, all 3,774 regenerated at N threads, at 1 thread and once more over the outputs; all 3,512 C7(3)
payloads byte for byte; bodies equal to the d=2 inputs except the magic and the rate line; minimum rates); then
`gen3/test_gen3.py --sanitize` (A-INV-1's targeted cases and 2,000-mutant corpus under the sanitizer build, the
unguarded-index self-test aborting at the `dist[masks[m]]` line, the gate tools and the job scripts on their fixtures);
then `gates_d3.py summary-gen-d3-0`. About 10 min.

A-INV-2(a) is an Expanse x86-64 gate (PLAN A.3 1(a)). `gate1a.json` says `a_inv_2a: true` and `run_class:
"expanse"` only for a full pass whose environment record has machine `x86_64`, a numeric `SLURM_JOB_ID` and
`C8_SITE=expanse` (set by `~/c8d3/env.sh`); any other run is `run_class: "rehearsal"` with the reasons in
`not_expanse_because`. `jgen_d3_0.json` says `passed: true` (G1a) only when that holds and the sanitizer part passed;
the job then exits 0, and otherwise 1. An off-Expanse dry run exits 0 when every check passed only with
`C8_GEN3_REHEARSAL=1`, and its `jgen_d3_0.json` still says `passed: false`, `rehearsal: true`. `gates_d3.py report`
re-derives the same rule from `gate1a.json` and refuses a rehearsal.

```bash
# on the Mac: export the commit under test
git -C <PROJECT>/LRI_C8_D3_HPC archive --format=tar <commit> -o /tmp/c8d3_<sha12>.tar
rsync -e 'ssh -o BatchMode=yes' /tmp/c8d3_<sha12>.tar expanse:<SCRATCH>/temp_project/c8d3/pkg/
# on the login node
source ~/c8d3/env.sh
mkdir $C8_ROOT/pkg/<sha12> && tar -xf $C8_ROOT/pkg/c8d3_<sha12>.tar -C $C8_ROOT/pkg/<sha12> && rm $C8_ROOT/pkg/c8d3_<sha12>.tar
export C8_PACKAGE=$C8_ROOT/pkg/<sha12>
python3 -B $C8_PACKAGE/tools/slurm_submit.py raw --role gen_d3_0 --dir $C8_ROOT/evidence/<sha12>/gen_d3_0 -- \
  -A <ACCOUNT> -p shared --nodes=1 --ntasks=1 -c 32 --mem=60G -t 01:00:00 --no-requeue \
  -o $C8_ROOT/logs/%x_%j.out $C8_PACKAGE/slurm/gen_d3_0.sh
```

Evidence in `$C8_ROOT/evidence/<sha12>/gen_d3_0/`: `gate1a.json` (`a_inv_2a: true`, `run_class: "expanse"`,
3,512 / 3,512 identical), `rate_audit_pre_h1.json`, `test_gen3_sanitize.json` (its `tmpdir` is under the job's
scratch), the build records, `binaries.sha256`, `environment.txt` (machine, site, scratch, tmpdir) and the summary
`jgen_d3_0.json` (`passed: true`). The log is `$C8_ROOT/logs/c8d3-gen_d3_0-<C>-<T>_<jobid>.out`.

### Stage 1b (on H1; G1b = A-INV-2(b), A-INV-3..6)

Both jobs run on an export at `$C8_ROOT/pkg/<sha12>` (as above). The H1 pin is the HANDOFF's MANIFEST sha256,
`46341a3c0f11d74f0cf7c08cdd685d9cf073a142160de5a0ca408e021b4ff099`; the source is the HANDOFF's Expanse tree, today
`<SCRATCH>/temp_project/LRI_C8_shared/inventory/inventory8_d2`. Both are only read.

- **J-H1-COPY** (`slurm/h1_copy.sh`, `shared -c 4 --mem=8G -t 01:00:00`): `gates_d3.py h1-copy` into
  `$C8_STORE/h1/<pin sha12>/` (a staging directory and one rename), H1's own `verify_inventory.py --pin` on the copy,
  the source's listing before and after. Since S4-001 the copy's code (every file under `src/`, through MANIFEST.json at
  the pin, SHA256SUMS, nothing unlisted) is authenticated by the package's own `g3common.h1_code_snapshot` before the
  verifier runs, from a private snapshot; `run_d3.sh` does the same with `gates_d3.py h1-auth` before it runs or builds
  anything of the copy. Evidence in `$C8_ROOT/evidence/<sha12>/h1_copy/`, including
  `h1_source_listing_before.json`, which J-GEN-D3 reads.

  ```bash
  source ~/c8d3/env.sh
  export C8_PACKAGE=$C8_ROOT/pkg/<sha12> \
    C8_H1_PIN=46341a3c0f11d74f0cf7c08cdd685d9cf073a142160de5a0ca408e021b4ff099 \
    C8_H1_SOURCE=<SCRATCH>/temp_project/LRI_C8_shared/inventory/inventory8_d2
  python3 -B $C8_PACKAGE/tools/slurm_submit.py raw --role h1_copy --dir $C8_ROOT/evidence/<sha12>/h1_copy -- \
    -A <ACCOUNT> -p shared --nodes=1 --ntasks=1 -c 4 --mem=8G -t 01:00:00 --no-requeue \
    -o $C8_ROOT/logs/%x_%j.out $C8_PACKAGE/slurm/h1_copy.sh
  ```
- **J-GEN-D3** (`slurm/gen_d3.sh`, `shared -c 64 --mem=120G -t 02:00:00`): `make gen3`, then `gen3/run_d3.sh --h1
  $C8_STORE/h1/<pin sha12> --pin $C8_H1_PIN --d2 $C8_STORE/c7d2_frozen --evidence $C8_ROOT/evidence/<sha12>/gen_d3
  --work $C8_SCRATCH/gen_d3 --target $C8_STORE/d3_payload/<pin sha12> --source $C8_H1_SOURCE --source-before
  $C8_H1_BEFORE --threads $SLURM_CPUS_PER_TASK --commit <sha12>`, every path computed inside the job. Steps: verify,
  extract, builders (gate-5 side files from H1's pinned builders), probe, regen (N threads and N single-thread
  shards), gate1b, gate2, gate3, gate4, gate5, gate7, determinism, publish (only after every gate exited 0), verify_d3
  (the printed MANIFEST_d3 sha256 is the external pin for the A.5 gate record), source. Gate 7 reads the inputs that
  Stage 2a writes (`inputs/two_loop.json`, `inputs/order7/two_loop.json`, `inputs/gamma_d3_8.txt`), so J-GEN-D3 runs on
  a commit after G2a; the script exits 64 at start without them, without the H1 copy, or when the target exists. Gate
  6 (pack identity) runs where the C8 packs are built (Stage 2b).

  ```bash
  source ~/c8d3/env.sh
  export C8_PACKAGE=$C8_ROOT/pkg/<sha12> \
    C8_H1_PIN=46341a3c0f11d74f0cf7c08cdd685d9cf073a142160de5a0ca408e021b4ff099 \
    C8_H1_SOURCE=<SCRATCH>/temp_project/LRI_C8_shared/inventory/inventory8_d2 \
    C8_H1_BEFORE=$C8_ROOT/evidence/<J-H1-COPY sha12>/h1_copy/h1_source_listing_before.json
  python3 -B $C8_PACKAGE/tools/slurm_submit.py raw --role gen_d3 --dir $C8_ROOT/evidence/<sha12>/gen_d3 -- \
    -A <ACCOUNT> -p shared --nodes=1 --ntasks=1 -c 64 --mem=120G -t 02:00:00 --no-requeue \
    -o $C8_ROOT/logs/%x_%j.out $C8_PACKAGE/slurm/gen_d3.sh
  ```
- **The published tree** `$C8_STORE/d3_payload/<pin sha12>/` (schema `c8-d3-d3-payload-1`): `payload/*.tar`,
  `MEMBERS_d3.sha256`, `rate_audit_L{7,8}.json`, `gates/` (every record of the job's gates directory, unchanged: the
  seven gate records, which must say `passed: true`; their supporting records `gate2_opcount.json`,
  `gate2_weights.json`, `gate4_kirchhoff.json`, `gate5_forest_check.json`, `gate7_check_dimension8.json`, which must
  be present and, carrying `passed`, say true; and H1's raw `check_edge_forests` outputs
  `gate3_edge_forests_L{7,8}.json`, which carry no `passed` because `gate3.json` is their verdict), `gates/gate5/`
  (the four builder side files `L{7,8}_{free,power}.subgraphs.txt` of A.2 step 2a), `SHA256SUMS` and
  `MANIFEST_d3.json` (which also lists the gate records and the side files' sha256s).
- **A.5 report** (login node, a copy of JSON only): `gates_d3.py report --evidence <J-GEN-D3 ev> --gate1a <J-GEN-D3-0
  ev>/gate1a.json --h1-pin <H1 pin> --commit <sha> --output
  LRI_C8_shared/assembly/H1_gates/inventory8_d2_46341a3c0f11_C63d_gates.json` writes the gate record (with the
  MANIFEST_d3 sha256 and the HANDOFF's `c63d` block) once, and only when every gate passed and `gate1a.json` is a full
  pass on Expanse x86-64. The A3 mechanism is agreed (DECISIONS acknowledgment log, 2026-10-04, "A3 report-back"):
  **C63d** writes `pin_recorded`, `gates_1_7` and `gate_5_forest_certificate` into the `c63d` block of
  `LRI_C8_shared/inventory/HANDOFF_inventory8_d2.json` and nothing else; both sessions pin the MANIFEST sha256, not
  the HANDOFF's own bytes. See "The A.5 report-back" below for the tools that write it.

## Inputs: `tools/prepare_inputs.py` (Stages 2a and 2b; PLAN component B)

`inputs/` holds the C8(3) inputs (schema `c8-d3-hpc-inputs-1`, dimension 3, order 8, ε = 2s−3). They are
generated data: `make inputs` rebuilds every file byte for byte, and `tests/check_inputs.py` checks that. Since
Stage 2b (below) they are the complete inputs: 24,173 kernels, `l7_complete` and `l8_present` true.

| File | Content |
|---|---|
| `two_loop.json`, `gamma_d3_8.txt` | the order-8 low-loop files: byte copies of `vendor/c8_assembly/inputs_d3/` (HANDOFF sha256 `6c31bf7f…`, `f868fbe2…`; HD4) |
| `order7/two_loop.json`, `order7/gamma_d3_7.txt` | C7(3)'s order-7 files (`reference/inputs/`; sha256 `3dddb802…`, `d5008ca0…`), for the order-7 replays |
| `packs/{free,power}_L{3..6}.pack` | the C7(3) kernels, ascending id, byte-identical to `LRI_C7_D3_HPC@a6ce987` |
| `packs/{free,power}_L7.pack` | Stage 2a: C7(3)'s 2,298 + 590 only (a6ce987's bytes). Stage 2b: `selection.json`'s 2,441 + 709, the C7(3) members (whose concatenation in id order is a6ce987's pack: gate 6) and the 143 + 119 s_G = 4 kernels of the d=3 payload |
| `packs/{free,power}_L8.pack` | Stage 2b, **not in git**: the 16,064 + 4,336 L8 kernels of `selection.json`, pinned in the manifest; hard links of the store blobs `$C8_STORE/packs/<sha256>.pack` (`make link-l8`) |
| `selection.json`, `h1/{MANIFEST.json,SHA256SUMS}` | Stage 2b: byte copies from the H1 copy; the chain H1 `MANIFEST.json` (pin `46341a3c…`) → `SHA256SUMS` → `selection.json` |
| `d3/{MANIFEST_d3.json,SHA256SUMS,MEMBERS_d3.sha256,rate_audit_L7.json,rate_audit_L8.json}` | Stage 2b: byte copies from the d=3 payload; the chain `MANIFEST_d3.json` (pin = the A.5 gate record's) → `SHA256SUMS` → the member list and the rate audits |
| `inventory.json` | `inspect_complete` and per sector and loop one row per kernel (below) |
| `manifest.json` | the sha256 of every file above (15 at Stage 2a, 25 at Stage 2b, the L8 packs included), counts, `l7_complete`, `l8_present`, `inspect_complete`, the H1 and d3 pins (copies: the HANDOFF's and the A.5 gate record's), the vendored pins, the prepare_low8 comparison, `reference_manifest_sha256` |

- **Inventory rows** `{id, primitive, s_G, wa, wb, offset, length, sha256, monomials, terms, cost, products,
  segments, addends, numerators, kernel_bytes, fmax, double_lift}`, one row per line.
  - `wa` and `wb` are the payload header's tokens (text, as the worker reads them). `s_G = 12 wb / wa` is an integer;
    s_G = 4 ⇔ 3w_B = w_A.
  - `cost = max(1, M·T)`.
  - `double_lift` is the number of subsets whose raw d=3 valuation p4 is ≤ −5 (`regenerate_rates`'
    `double_lift_subsets`). It is computed in numpy (`prepare_inputs.raw_valuations`; p4 = 3L − 3d + 4ν_N, since d
    and |s| + L have the same parity) and compared with `gen3/g3common.d3_rates` by `check_inputs.py`. The C7(3)
    kernels of power L7 hold 106 such subsets in 42 kernels, and the free sector holds none. From Stage 2b the L7
    counts must also equal `d3/rate_audit_L7.json`'s (regenerate_rates' C++ count) for every kernel, and the L8 counts
    are the audit's (`rate_audit_L8.json`; numpy at E = 16 is too slow for 20,400 kernels), compared with numpy on the
    smallest L8 kernels by `check_inputs.py` on Expanse.
  - The inspect fields (`products` … `fmax`) are null and `inspect_complete` is false until `make inputs-inspect`
    fills them from `bin/c8d3_inspect` (Stage 3a). `plan` will refuse any selected graph without them.
- **`make inputs`** (`tools/prepare_inputs.py build [--out DIR]`, about 25 s on the Mac):
  1. It checks the HANDOFF copy against its pin and every vendored file against the HANDOFF.
  2. It copies `inputs_d3/{two_loop.json,gamma_d3_8.txt}`, read once through `common.verified_bytes`.
  3. It runs the vendored `prepare_low8.py --d 3` as a separate `python -B` process, in compare mode, with
     `LRI_ROOT=vendor/c8_assembly_fixtures` and `PYTHONPYCACHEPREFIX` unset. Exit 0 with three files `identical` is
     required, and the result goes into the manifest.
  4. It packs the C7(3) kernels from `reference/inputs/` and checks each pack against a6ce987's sha256.
  5. It writes the inventory, then the manifest last. The files are built in a staging directory inside the target
     and moved into place one by one; an unchanged file is left alone. The L8 packs (Stage 2b) are never written.

  Once the manifest carries the d3 pin (Stage 2b), `make inputs` rebuilds the Stage-2b state from the package's own
  copies (mode `2b-carry`): the Stage-2b small files after their chain check; L7 from the C7(3) members and the new
  members of the committed L7 pack, each at its `MEMBERS_d3.sha256` hash; L8 rows re-derived from the L8 packs when
  they are present (each member split by its header's T, at its member hash, the pack at its pin), or, without them
  (the Mac), the committed rows carried forward after checking each row's id, primitive flag, sha256, double_lift
  and offset against `selection.json`, `MEMBERS_d3.sha256` and the rate audit.
- **`verify()`** (`tools/prepare_inputs.py verify [--inputs DIR]`, `make verify-inputs`) is what `plan` calls. It
  writes nothing, and a failure names the file. It checks:
  - the manifest's schema, dimension and order. A C7(3) manifest is refused, naming `LRI_C7_D3_HPC@a6ce987`, and so
    is a dimension-2 manifest (C62d's);
  - every pinned file, by sha256 (the L8 packs, about 9.4 GB, included: about a minute on Lustre);
  - with the d3 pin set, the chain of the Stage-2b small files to the manifest's two pins (`prepare_inputs.Stage2b`);
  - the HANDOFF copy and the 13 vendored files at the manifest's pins, which must equal `tools/VENDORED.json`.

  A pinned L8 pack that is missing is skipped only with `C8_ALLOW_NO_L8=1`, printing `SKIPPED`, and the plan is then
  test-only. A present but different L8 pack is refused even then.
- **The plan's input gate** `plan_inputs(test_only)` (`tools/prepare_inputs.py gate [--test-only]`). `C8_INPUTS`
  selects an inputs directory; the default is the package's `inputs/`.
  - A non-test plan with any other `C8_INPUTS` is refused before anything is read.
  - Then the gate runs `verify()`.
  - The plan is test-only when it was asked to be, when `l7_complete` or `l8_present` is false, when an L8 pack was
    skipped, or when `C8_INPUTS` is foreign; the reasons are returned. Before Stage 2b every plan is test-only.
  - Its wiring into `tools/production.py plan` is Stage 3a (D.1). Until then the C7(3) planner calls
    `prepare_inputs.prepare()`, which refuses the C8(3) inputs before the planner creates anything.
  - **Stage-3a obligation** (Stage 2a repair rounds 1 and 2). Once `plan` calls `plan_inputs`,
    `tests/check_inputs.py` and `tests/check_vendored.py` (b) repeat the gate's checks through the real
    `production.py plan` in scratch packages. The checks are:
    - a one-byte change to `packs/free_L7.pack`, refused naming the file;
    - a one-byte change to a vendored file, refused naming it;
    - a non-test plan with a foreign `C8_INPUTS`, refused;
    - a non-test request on the untouched inputs, which must come out test-only.

    No refusal may leave a campaign directory, a plan temporary directory (anything beside the campaign path or in
    `TMPDIR`) or a changed package file. `tests/plan_gate.py` runs these checks. While `plan` does not call the gate,
    it requires the transitional refusal instead. Once `plan` calls the gate, it fails until `plan_gate.STAGE3A` names
    the ported plan's non-test arguments (since S2-002 without `--forbid-seeds-from`: a plan that checks seeds must
    reserve its seed under the session lock, which the runner's hermetic children cannot take, and every scenario stops
    at the gate or is made test-only by it). These runs are G3a evidence (A-ASM-1 Mac; A-IN-4 at L ≤ 7).
  - **The fixed input state.** The runner does not use the live inputs as they are. It first puts the scratch
    package's `inputs/` into a fixed state:
    - the live manifest, with `l7_complete` and `l8_present` false;
    - no pin, count or inventory row above L7, and any L8 pack removed from the scratch package;
    - every other pin and file unchanged.

    The package's own gate must then pass this state and make a non-test plan test-only (the `fixed-state` check).
    So the checks hold whether Stage 2b lands before or after the Stage-3a wiring, on Expanse with the L8 packs and on
    the Mac with `C8_ALLOW_NO_L8=1`, which the runner passes through. At Stage 2a the live inputs are already in this
    state.
- **The inherited C7(3) tests** were ported in Stage 3a: the C7(3) input view (`tests/c7_view.py`) is gone, and every
  test runs on the C8(3) inputs or on the synthetic complete inputs of a scratch package (`tests/c8pkg.py`).
  `tests/fixtures/c7_inputs/` keeps a6ce987's manifest and inventory for `tests/check_inputs.py`'s refusal of a C7(3)
  manifest.
- **Checks.** `C8_ALLOW_NO_L8=1 python3 -B tests/check_inputs.py` (`make check-inputs`, part of `make test-python`;
  about 40 s) covers:
  - the regeneration;
  - A-IN-1;
  - A-IN-2, with `gen3/check_dimension8.py` on the package inputs;
  - the manifest and the inventory, with gate 6 for L ≤ 7 against `gen3/pins/PINS.json`;
  - A-IN-4 for L ≤ 7: one-byte changes to 8 of the 15 pinned inputs (all three file kinds) and to 4 vendored files
    (verify() checks every pin in one loop), `C8_INPUTS`, the C7(3) and
    dimension-2 manifests, and the L8 skip rule on a synthetic manifest;
  - the same refusals through `production.py plan` (`tests/plan_gate.py`; wired since Stage 3a: `plan` calls the
    input gate), on the runner's fixed input state. A self-test runs one correct and four wrong fake planners through the runner, and
    runs the correct one on simulated post-Stage-2b inputs (Expanse and Mac).

  `python3 -B tests/check_vendored.py` without `--standalone` covers A-ASM-1(b), including the vendored flip through
  `production.py plan`. Its read-rule spies cover `verify()` and `make inputs`.

### Stage 2b: the complete inputs (J-IN-1; G2b = A-IN-3..5, A-KER-5 on all 24,173 kernels)

- **`make inputs-l8 D3PAYLOAD=$C8_STORE/d3_payload/46341a3c0f11 D3PIN=<sha256 of MANIFEST_d3.json>
  STORE=$C8_STORE [H1=…] [GATE_RECORD=…]`** (`prepare_inputs.py l8`; A.2 step 6). D3PIN is the A.5 gate record's
  `manifest_d3_sha256` (`70af9d22…` for H1 `46341a3c…`).
  1. Without D3PIN the Makefile refuses (exit 2) before running anything, and so does the tool.
  2. With `GATE_RECORD`, D3PIN and the H1 pin must equal the record's.
  3. `gen3/verify_d3.py TREE --pin D3PIN` runs first (its four steps); on a failure the tool stops with exit 1 before
     opening any payload member and writes nothing (`gen3/test_gen3.py` checks this with an audit-hook spy).
  4. The small files are copied from the payload and from the H1 copy (`$C8_STORE/h1/46341a3c0f11/` by default) and
     their chains checked; `selection.json` must have H1's counts (2,441 + 709 at L7, 16,064 + 4,336 at L8) and
     primitives (44, 248).
  5. L7: the C7(3) members from `reference/inputs/` (their concatenation in id order must be a6ce987's pack, and every
     one must equal the payload's member byte for byte and its `MEMBERS_d3.sha256` hash: gate 6) and the new s_G = 4
     members from the payload's tars (read by offset).
  6. L8: the selected members from the tars, each at its member hash, written to `$C8_STORE/packs/.tmp-…` and
     published as `$C8_STORE/packs/<sha256>.pack`, read-only and never overwritten (an existing blob of the same
     name must have the same bytes); the package gets a hard link (a copy across filesystems). The rows' double_lift
     is the rate audit's; the L7 numpy counts must equal the audit's.
  7. The inventory (inspect fields only for the kernels `inspect/inspect.json` covers) and the manifest, last.
- **`make link-l8 STORE=$C8_STORE`** hard-links the two blobs that `inputs/manifest.json` pins into `inputs/packs/` of
  a package export (idempotent; a different file in the way is refused). Every job that plans or reads L8 data on an
  export needs it first; `verify()` hashes the packs.
- **`make inputs-inspect`** (unchanged) now covers all 24,173 kernels; **`make inputs-mini`** writes
  `tests/fixtures/inputs_mini/` (`prepare_inputs.py mini`): the 8 smallest L8 kernels per sector (by bytes, then id) in
  their own packs, an inventory with the package's L3–L7 rows and those rows, and a manifest pinning the package's
  other inputs (`package_files`). `tools/members.py mini --to DIR` (or `members.mini_inputs()`) materializes it as a
  `C8_INPUTS` directory (its files copied, the package files hard-linked); any plan on it is test-only.
- **Gate 6** (pack identity, A.3 6, A-INV-2(b)): `python3 -B gen3/gates_d3.py gate6 --evidence DIR` reads every C7(3)
  member from the C8 packs at the C8 inventory's offsets (3,511, against a6ce987's rows), the PINS digest, the L3–L6
  pack sha256s and every L7 member against `d3/MEMBERS_d3.sha256`. The A.5 gate record is written once (`report`), so
  gate 6 goes into an addendum next to it (login node or Mac, JSON only): `gates_d3.py addendum --gate6 <ev>/gate6.json
  --gate-record LRI_C8_shared/assembly/H1_gates/inventory8_d2_46341a3c0f11_C63d_gates.json --inputs-manifest
  inputs/manifest.json --commit <sha> --output
  LRI_C8_shared/assembly/H1_gates/inventory8_d2_46341a3c0f11_C63d_gates_addendum_gate6.json`. The addendum writes
  nothing else; its `handoff_c63d_update` (`gates_1_7["6"]: true`) goes into the HANDOFF's `c63d` block through
  `gates_d3.py handoff-gate6` (below), because under DECISIONS A3 C63d writes that block.
- **The A.5 report-back** (Mac, where `LRI_C8_shared/` lives; JSON and text only; PLAN A.2 step 6 and A.5, DECISIONS
  A3). Three subcommands, run in this order once gate 6 has its addendum. Each makes exactly one write, re-reads the
  target just before its one rename and refuses (exit 1, nothing written) if the bytes changed meanwhile, keeps the
  file's mode, records the sha256 before and after, and changes nothing when its write is already there; `--dry-run`
  prints the record or the text and writes nothing. These two inventory files, by exact name, are the only paths under
  C62d's trees that any gen3 tool writes (`g3common.refuse_c62d` refuses every other one).
  ```bash
  S=<PROJECT>/LRI_C8_shared G=$S/assembly/H1_gates
  R=(--gate-record $G/inventory8_d2_46341a3c0f11_C63d_gates.json
     --addendum $G/inventory8_d2_46341a3c0f11_C63d_gates_addendum_gate6.json)
  # 1. c63d.gates_1_7["6"]: "pending (Stage 2b, with the C8 packs)" -> true, nothing else (A3)
  python3 -B gen3/gates_d3.py handoff-gate6 --handoff $S/inventory/HANDOFF_inventory8_d2.json "${R[@]}" --evidence EV1
  # 2. one acknowledgment-log line carrying the d3 pin (A.2 step 6: "the A.5 gate record and its DECISIONS log line")
  python3 -B gen3/gates_d3.py decisions-ack --decisions $S/inventory/DECISIONS.md \
    --handoff $S/inventory/HANDOFF_inventory8_d2.json "${R[@]}" --evidence EV2
  # 3. the NOTE to C62d (C63d's own folder), written once
  python3 -B gen3/gates_d3.py note --handoff $S/inventory/HANDOFF_inventory8_d2.json --decisions $S/inventory/DECISIONS.md \
    "${R[@]}" --h1-copy <J-H1-COPY ev>/h1_copy.json --payload-path '$C8_STORE/d3_payload/46341a3c0f11' \
    --output $S/assembly/NOTE_C63d_to_C62d_<date>.md
  ```
  - `handoff-gate6` writes only when the addendum is a passed gate 6 whose `addendum_to` sha256 is the gate record's
    bytes, the pins agree (the HANDOFF's `manifest_sha256` = the record's H1 pin = `c63d.pin_recorded`), the `c63d`
    block equals the record's `handoff_c63d` apart from gate 6, and the file is the `json.dumps(indent=1)` text that
    C62d's `gen/handoff_inventory.py` writes (so the rewrite changes no other byte). The structural difference must be
    exactly `c63d.gates_1_7["6"]`. EV1 keeps the old bytes (`HANDOFF_inventory8_d2.before.json`) and
    `handoff_gate6.json`.
  - `decisions-ack` appends only after the HANDOFF holds gate 6, only to a file whose last section is the
    acknowledgment log ending in a table row, and only one line (the old bytes are a prefix of the new). EV2 keeps
    `decisions_ack.json`.
  - `note` writes `assembly/NOTE_C63d_to_C62d_<YYYY-MM-DD>[a-z].md` from the records, only after the HANDOFF holds gate
    6 and the log holds the pin line, and never over an existing NOTE.
- **J-IN-1** runs as two jobs of `slurm/inputs_job.sh` (`shared -c 16 --mem=32G`), each in a work copy on Lustre
  (`$C8_ROOT/work/<job>_<id>`, so the store's blobs can be hard-linked into it; removed when every step passed):
  - `C8_JOB=in1build` on the code commit: `make inputs` (unchanged), `make inputs-l8` (with `GATE_RECORD`), `make
    inputs-inspect`, `make inputs-mini`, `gates_d3.py gate6`, `verify`; the generated files go to
    `$EV/generated/` for the generated-data commit (`inputs/` without the L8 packs, `inspect/inspect.json`,
    `tests/fixtures/inputs_mini/`);
  - `C8_JOB=in1check` on the generated-data commit: `make link-l8`, the builds, `verify`, `tests/check_inputs.py`
    (A-IN-1..5 with the L8 packs present, including the one-byte change to `packs/free_L8.pack` through the gate and
    through `production.py plan`), `tests/inspect_check.py` (A-KER-5 on all 24,173 kernels, the worker part on ≥ 100
    graphs), `tests/members_test.py`, gate 6, `make inputs` and `make inputs-mini` (both unchanged), `gen3/test_gen3.py
    --only tools`.

  ```bash
  source ~/c8d3/env.sh
  export C8_PACKAGE=$C8_ROOT/pkg/<sha12> C8_JOB=in1build C8_D3_PAYLOAD=$C8_STORE/d3_payload/46341a3c0f11 \
    C8_D3_PIN=70af9d2242439bc1f3f24a2bcb97466e7717aa87fb50fc538232935e6b038aca \
    C8_GATE_RECORD=<a copy of the A.5 gate record>
  python3 -B $C8_PACKAGE/tools/slurm_submit.py raw --role in1build --dir $C8_ROOT/evidence/<sha12>/in1build -- \
    -A <ACCOUNT> -p shared --nodes=1 --ntasks=1 -c 16 --mem=32G -t 02:00:00 --no-requeue \
    -o $C8_ROOT/logs/%x_%j.out $C8_PACKAGE/slurm/inputs_job.sh
  # after the generated-data commit <sha12'> is exported: C8_JOB=in1check, --role in1check, its own --dir
  ```
- **On the Mac** the L8 packs are absent: `make check-inputs` sets `C8_ALLOW_NO_L8=1` when `inputs/packs/free_L8.pack`
  does not exist, and `check_inputs.py` then checks the L8 rows against the member list, the selection and the audit
  (not the member bytes). `tests/inputs_l8_test.py` runs the whole Stage-2b path on a miniature payload (about 2 min).

## Campaigns: `production.py`, lanes and submission (Stage 3a; PLAN D)

- **Roles and bases.** Campaign roles: `test`, `pilot_subset`, `pilot_full` and `production` (D.3a). Plan roles:
  `campaign`, `cost_sweep`, `cost_refresh`, `flag_check` and `validation` (D.2). Cost bases (D.5):
  - `measured`, with the HD11 identity: executable sha256, CPU model and `mp_check` mode;
  - `bootstrap`: the preliminary proxy `tools/bootstrap_proxy.json`, which is never used as a cost;
  - `prior_model` (×F), for `cost_refresh` only;
  - `synthetic`: the labelled fixture, for `validation` only.

  Each campaign stores a copy of the scheduling model that planned it (`prior_cost_model.json` or
  `synthetic_cost_model.json`). Cost consumers never open that copy: `make_cost_model.py` calls
  `verify_base(scheduling_copies=False)`, and a spy checks this in `cost_refresh_test.py`.
- **Blocks (D.6, R10)** are frozen in the per-index task files, as a seventh column. The per-block records (W(B), φ,
  est_peak_bytes, the small_block record) are in `groups/<g>/tasks/s<shard>.blocks.json`, pinned by sha256 in each job
  entry. This keeps the manifest size independent of the task counts: a claim reads a fixed number of bytes whether
  the other indices hold 10^3 or 10^6 tasks (A-ORC-13).
- **The input gate** is wired. `plan` calls `prepare_inputs.plan_inputs()` first. A request that the gate makes
  test-only, for example because `l7_complete` is false before Stage 2b, is planned test-only and recorded that way.
- **Plan publication (D.4, S2-005).** A plan's staging copy beside the target is its own,
  `<dir>.tmp.<host>.<pid>[.<SLURM_JOB_ID>]`; another attempt's staging copy is never removed, only listed on stderr
  (it may belong to a live plan; remove leftovers by hand once their plan jobs have ended). The copy is published with a
  rename that fails when the target exists (`common.rename_noreplace`: `renameat2(RENAME_NOREPLACE)` on Linux,
  `renamex_np(RENAME_EXCL)` on macOS; where the file system lacks the flag, a recheck and `rename(2)`, which still
  fails on any non-empty target), and a target created meanwhile ends the plan (exit 1) with nothing replaced and only
  its own staging copy removed.
- **Merge (D.13).**
  - Phase 1 runs in parallel over shards. Phase 2 is an external merge with fan-in F = min(--fan-in, RLIMIT_NOFILE − 32);
    it refuses when F < 2.
  - The final pass is the unchanged 50-digit Decimal summation.
  - It writes `graph_replicates`, `graph_tails`, `graph_promotions` and `graph_costs`, plus `graph_prefixes` for nested
    graphs (jets on the full-stream scale, total/P, R06).
  - `--serial` is the SQLite reference merge.
  - Quota errors stop with exit 74 in the parallel path too, because `Refuse` is picklable.
  - **`merged.json` is a group's commit point (F8-d3, Stage 6; C62d's F8).** Its tables are committed once
    `merged.json` exists, and a committed table never changes ("Checksum mismatch"). A table without a `merged.json`
    is uncommitted: the recovery of a completed index deletes a checkpoint and the group's `merged.json`, and the
    re-merge replaces a different table atomically and prints it (`graph_costs.csv`: "timing only"; a scientific table:
    "SCIENTIFIC TABLE CHANGED"). `merged.json` records the digests of the bytes the merge published.
    `assemble.publish_result` (also behind `combine.py`) supersedes a result whose only change is `merged_sha256`
    (`combine.py`: in `combined_from`), keeping the old bytes as `<name>.superseded.<sha12>.json`, and refuses any other
    difference. The scientific content includes each group's scientific identity (`science_sha256`, S3-R2-007: the
    sha256 of every scientific table and a canonical digest of `merged.json` without its timing fields; per batch in
    `combined_from`), so a re-merged table whose rows changed is refused even when every assembled value is equal.
    The pilot's screens and PC selections are bound by the same identities, never by `merged.json` bytes (S3-R2-009). `pilot_report.py subset-check` does the same for `subset_summary.json` when only the timing digests of
    its `merged_sha256` change (`merged.json`, `graph_costs.csv`); a scientific table's digest is never superseded.
- **Lanes** (`tools/lanes.py`) follow C62d's designs (H8):
  - NUMA lane shapes come from sysfs (`numa`, `numa:k`, `socket`, n), with the `C8_SYSFS`/`C8_PROC` test overrides;
  - done markers are hints, and the lane view does bounded scans;
  - a memory guard at 0.85, the CPU-class deadline factor and the time policy;
  - drill mode, and held jobs (`launch failed requeued held`: released once, then cancelled). The release (S2-006)
    refuses a missing or unusable ledger before any scheduler command, appends and fsyncs a `release_attempt`
    annotation before the scontrol `release` command (a failed append releases nothing), counts an ambiguous outcome
    (`release_unknown`) as the one attempt and reconciles the result with `squeue` (`released`, or
    `release_unconfirmed` while the hold still shows), so a later hold is cancelled, never released again;
  - `attempt()` runs one index, its `production.py run` in its own session;
  - stop signals (F7, C62d's port): the worker (the batch process: `lane_worker.sh` execs it) forwards SIGTERM, SIGINT
    or SIGHUP to its lanes and each lane to its run, which stops its native worker and removes its runtime; a lane
    removes its scratch and exits 143 with its claim left stale and no failure record. Every wait counts from the
    signal toward one absolute deadline, S = `C8_LANE_STOP_SECONDS` (25 s, below KillWait 30 s; S2-R2-005, round 2): a
    lane's run has until 0.7 S (its session killed at 0.665 S, reaped until 0.7 S), then the lane removes its scratch;
    the worker waits for its lanes until 0.836 S, kills every lane still running (all before it waits on any), reaps
    them until 0.88 S and keeps the last 0.12 S (3 s; 8 s before KillWait) to remove any lane scratch of its job left
    behind and exit. A child not reaped by its deadline is not waited for longer.
- **Submission** (`tools/slurm_submit.py`) has the entry points `lanes N` (`--dry-run` anywhere), `submit`, `window`,
  `resubmit` and `release`, all on the Stage-0 admission engine.
  - Drill mode never uses `--exclusive` and needs 2..16 CPUs on `shared` or `debug`.
  - The merge defaults are `-A <ACCOUNT> -p shared -c 24 --mem=48G -t 02:00:00`.
  - `slurm/merge.sh` dispatches on `production.py role`: `pilot_subset` runs `pilot_report.py subset-check`; `test`,
    `pilot_full` and `production` run `assemble`; any other role exits 64.
- **D.14.** `sweep.py` picks the basis from PREV's identity:
  - the same executable sha256: measured;
  - only the sha256 differs: `prior_model` at F = 2, with the fit check before any index;
  - otherwise, or with `--refresh-bootstrap`: bootstrap.

  `make_cost_model.py` writes `scheduled_with` and `refresh_report.json`. `cost_identity.py check` compares a model
  with an executable, or the published plans with their pinned models.

## Stage-3a validation jobs: `slurm/native_job.sh`

One script runs the Stage-3a validation jobs in a node-local copy of the export (`$C8_SCRATCH/pkg`; `val1` and the
L8 jobs of Stage 3b and later in the work copy `$C8_ROOT/work/<job>_<id>`, below), so concurrent jobs on one export
never share `bin/`. Evidence goes to `$C8_ROOT/evidence/<sha12>/<job>/` (environment, step logs, build
records, binary sha256s, one JSON per test, `summary.json`); each step's status is recorded and the job exits 1 if any
step failed.

```bash
source ~/c8d3/env.sh; export C8_PACKAGE=$C8_ROOT/pkg/<sha12>
C8_JOB=<job> python3 -B $C8_PACKAGE/tools/slurm_submit.py raw --role <job> --dir $C8_ROOT/evidence/<sha12>/<job> -- \
    -A <ACCOUNT> -p shared --nodes=1 --ntasks=1 -c <n> --mem=<m> -t <t> --no-requeue -o $C8_ROOT/logs/%x_%j.out \
    $C8_PACKAGE/slurm/native_job.sh
```

| `C8_JOB` | Job | Runs |
|---|---|---|
| `val1` | J-VAL-1 | the builds, `check_build.py`, `make test-python`'s tests in parallel streams (`unit_orchestration.py` one function per step), `check_vendored.py --no-review-record`, then `validate.py` (subset) and `class_b.py`, `workflow.py` and `staging.py` with the real workers, `vendored_isolated.py --in-place` with the job's A-ASM-3 record. Since Stage 2b pinned the L8 packs (which `check_inputs`, `class_b`, `workflow` and `staging` read), `val1` works in the L8 work copy `$C8_ROOT/work/val1_<id>` with `make link-l8 STORE=$C8_STORE` before the builds, like `val2` (Stage 3b below), and removes it after a full pass |
| `inspect` | J-INSPECT | `make inputs-inspect` (L ≤ 7 now; L8 in Stage 2b), the generated files copied to the evidence, `inspect_check.py --no-worker` |
| `val2` | J-VAL-2 (L ≤ 7) | the builds, `check_build.py`, `validate.py --full` (G-C7 with the nondirect totals and the shift case on the A-L18 hunk; G-JET), `class_b.py` (with the new zero-channel L7 kernels of the d=3 payload when `C8_D3_PAYLOAD` and `C8_D3_PIN` are set), `inspect_check.py` (≥ 100 graphs), `check_points.py`, a `forced_tiers.py` smoke |
| `val3a` | J-VAL-3 tool check at L ≤ 7 | `validate.py --bk8 --l2-control` (the gates are G3b's) |
| `val4` | J-VAL-4 (L ≤ 7) | `make sanitize`; `sanitize.py --selftest --parsers --runs --max-loop 7` |
| `run1` | J-RUN1 | `run1_replay.py` on the pinned run1 archive (G-RUN1 T1–T5); `archived_stream_replay.py` with the C8 worker in order 7; `test_pilot_report.py --run1` (A-DES-3's run1 part) |
| `repair3a` | Stage 3a repair round 1 | the builds, `check_build.py`, `validate.py --full --parts identity,g_c7`, `inspect_check.py`, `class_b.py --parts e` (payload as in `val2`), `test_pilot_report.py --run1`, and the G-RUN1 selection seed 20261004 registered in `$C8_SEEDS` (created if absent) |
| `repair3b` | Stage 3a repair round 2 (A-DES-3's real-tail part) | the C8 workers, `inspect`, `test-builds`; `class_b.py --parts e --zero-channel-tails` (payload as in `val2`): every zero-channel kernel integrated in the pilot shape (campaigns a and b, 8 replicates × 32,768 points nested at 4,096); `test_pilot_report.py --zero-channel` on those rows; `$C8_SEEDS` copied byte for byte to the evidence (the HD6 mirror) |

`C8_D3_PAYLOAD` is the published d=3 payload tree (`$C8_STORE/d3_payload/<H1 sha12>`) and `C8_D3_PIN` the sha256 of its
`MANIFEST_d3.json` (the A.5 gate record's `manifest_d3_sha256`); `class_b.py` verifies the chosen members along the
payload's checksum chain before use.

**A-EXP-1's scratch check** is `slurm/scratch_probe.sh`, submitted from a login shell that exports
`C8_SCRATCH=/tmp/login-value` (`raw --role scratchprobe`, `debug -c 1 --mem=1G -t 00:05:00`, `C8_PROBE_OUT` the record):
the job sources `slurm/common.sh` as every C8(3) job script does and records the inherited and the computed value; it
passes when the computed value is `$SLURM_TMPDIR` (else `/scratch/$USER/job_<id>`) and not the inherited one.

**On Expanse some Mac fakes cannot run, by design.** A-ORC-17's site detection (a `/expanse/lustre` mount or
`SLURM_CLUSTER_NAME=expanse`, whatever `C8_SITE` says) refuses `C8_SITE=fake` on an Expanse node (64), so the fake-Slurm
and ledger tests (`test_submit.py`, `test_ledger.py`, `test_pipeline.py`, and `unit_orchestration.py`'s
`seeds_and_nets`, `roles`, `first_sweep_bootstrap`, `blocks_plan_level`, `lanes_submission`, `done_markers`,
`arrays_and_recovery`) end with that refusal; `val1` records them `SITE_REFUSED` (their evidence is the Mac run), and
any other failure stays `FAIL`. Likewise `common.io_fault` ignores `C8_TEST_IO_FAULT` on Expanse, so
`atomic_and_guards` there checks only that a requested fault is inert. The test campaigns of `check_vendored`,
`workflow` and `staging` live in node-local scratch; `check_inputs`/`plan_gate`'s live beside the package when the L8
packs are present (its scratch packages hard-link them: on the shared filesystem in `val1` and `val2`), else in
node-local scratch. All are planned without `C8_SITE` (each test drops it from its children's environment), so
D.7's Lustre file guard (which needs `lfs quota` on a Lustre path) does not apply to them.

## Stage 3b: the L8 validation, the first sweep, the argmax run (`slurm/native_job.sh`)

Stage 3b needs G2b (the inputs pin the L8 packs). Its jobs run `slurm/native_job.sh` in a **work copy on Lustre**
(`$C8_ROOT/work/<job>_<jobid>`: `cp -a` of a pristine export; of an export J-BLD built in place, everything but `bin/`
and the L8 pack links, Stage 5 below) with the store's L8 packs hard-linked in by `make link-l8 STORE=$C8_STORE` (same
filesystem, so no 8.8 GB copy; on symmetry the work copy is on BeeGFS); `val1` (since the J-E0-sym repairs of
2026-10-05), `val2`, `val3`, `val4` and `smoke3b` remove the copy after a full pass, `sweep1` and `argmax` keep it
(their campaigns name it). Submission as above (`raw --role <job> --dir $C8_ROOT/evidence/<sha12>/<job>`;
for `sweep1` and `argmax` `--dir` is the campaign `$C8_ROOT/runs/<name>`).

| `C8_JOB` | Job | Runs |
|---|---|---|
| `smoke3b` | tool check (debug) | the new Stage-3b drivers on small samples: `forced_tiers.py` at L8 with the doubling rounds, `thread_identity.py` (2 and 4 lane parts), `class_b.py --parts f`, `check_points.py` (L8 in contract mode), `prefix_check.py --real`, `sweep.py --choose-only` |
| `val2` | J-VAL-2 with L8 | the builds, `check_build.py`, `validate.py --full` (A-RPL-1 on the L2 graph and every L ≤ 7 kernel; A-RPL-2 on all 3,773 L ≤ 7 kernels, the 262 new L7 included), `class_b.py` ((a) with L8, (b)–(e), (f) at L8), `inspect_check.py`, `check_points.py` (L3–L7 hard; L8 in `--contract` mode, every breach recorded), the `forced_tiers.py` smoke, `check_inputs.py` (A-IN-5), `workflow.py` and `staging.py` with the real workers, `compat_run1.py` |
| `val3` | J-VAL-3 (compute, exclusive) | three streams: `forced_tiers.py` (A-RPL-4 at L7 and L8; `C8_FT_THREADS`, default 128, and `C8_FT_MAX_SECONDS`, default 1200 s per sector and loop for the doubling rounds; the 450-digit reference costs about 1.4 s per L8 point and thread); `thread_identity.py` (A-RPL-6) then `validate.py --bk8 --l2-control` (A-RPL-3, A-IN-6); `merge_scale.py --rows 1000000` (A-ORC-6; its scale merge, the first step, runs while the other two streams load the node, so its phase rates are not clean merge rates: measure the scale part alone, e.g. in J-PROF, before changing `tools/production.py`'s merge constants), `assembly_checks.py --exact` and `compat_run1.py` (A-ASM-3/4), `prefix_check.py --real` (A-DES-8 (e)) |
| `val4` | J-VAL-4 with L8 | `make sanitize`; `sanitize.py --selftest --parsers --runs --max-loop 8` (A-KER-4; the L8 point checks in `--contract` mode) |
| `sweep1` | J-SWEEP-1 (compute, exclusive) | needs `C8_SWEEP_RUN` (a new `$C8_ROOT/runs/<name>`) and `C8_SWEEP_SEED` (fresh). `bin/c8d3_{gmp,decimal}`, `check_build.py`; `tools/sweep.py` (bootstrap basis, `--bootstrap-chunk 512 --shards 32`, one lane per NUMA domain: plan, run every index heaviest first, merge, `make_cost_model.py` → `$EV/$C8_SITE_MODEL` (Expanse `gmp_expanse_epyc7742_c8.json`); its plan reserves the seed, `--reserve-seed $C8_SEEDS`, S2-002); `seeds.py add` (idempotent); `assemble.py` on the test campaign (A-IN-7); `cost_identity.py check --model --exe`; `tools/cost_summary.py`; the measured binaries copied read-only to `$C8_STORE/baseline/<sha12>/` with a `SHA256SUMS` |
| `argmaxre` | J-ARGMAX's step 4 again (debug) | `tests/argmax_run.py $C8_ARGMAX_RUN --reinspect --cost-model cost_models/$C8_SITE_MODEL`: the argmax points of the merged campaign regenerated again with `y`, `jac` and `t` recorded too; no plan, no new point |
| `argmax` | J-ARGMAX (shared) | on the export of the data-only commit carrying the model as `cost_models/$C8_SITE_MODEL` (Expanse `gmp_expanse_epyc7742_c8.json`) and `reference/baseline_c8_stage3.json`; needs `C8_ARGMAX_RUN`, `C8_ARGMAX_SEED` (fresh), `C8_SWEEP_RUN`, `C8_SWEEP_PKG` (the sweep's work copy) and `C8_BASELINE_SHA12`. The rebuilt `bin/c8d3_gmp` checked against the model (`cost_identity.py check --model --exe`, J-BLD's check) and the stored baseline; `make baseline`; `tests/argmax_run.py` (A-DES-6); `accounting.py` on the sweep campaign (from its work copy) and `cost_summary.py` with the sweep's measured allocated/busy |
| `profbuild` | Stage-4a tool check (shared, 16 c) | the builds (`bin/c8d3_gmp`, `make profile ratiohist c7ref`) and the c8-stage3 baseline check (the rebuilt `bin/c8d3_gmp` must be `24adff54…`, else no profile runs); `prepare_benchmarks.py --order 8` (verify, `--stage-check` of every fixture graph from the packs) and `--order 7`; smoke runs of `perf_profile.py p1/mpcheck/p2/p3/fe` and `benchmark.py --interleave-probe/--lane-shapes` on tiny cuts (`--smoke-tasks`, `--fake-topology --no-pin`: function tests, never measurements) |
| `prof1` | J-PROF-1 (compute, exclusive) | first, with nothing else on the node, `tests/merge_scale.py`'s scale part (`--rows 1000000 --jobs 16 --run-jobs 16 --skip-many-shards --skip-memory-scaling`: the clean merge rates); the builds and the baseline check; `perf_profile.py fe` (the f_E repeat), `p1` (perf record on socket 0, tier timers on socket 1, 64 threads each) and `mpcheck` (the MP self-check overhead) |
| `prof2` | J-PROF-2 (compute, exclusive) | the build and the baseline check; `benchmark.py --lane-shapes 8x16,4x32,2x64,1x128,16x8` (P4; `C8_P4_SHAPES` overrides) |
| `prof3` | J-PROF-3 (compute, exclusive) | the builds and the baseline check; `perf_profile.py p2` (perf stat IPC), `benchmark.py --interleave-probe`, `perf_profile.py p3` (ratio histograms at rates .8 and .7) |
| `optsmoke` | Stage-4b tool check (shared, 16 c) | the builds (`bin/c8d3_{gmp,decimal}`, `make quaddiff` when the commit has it), `make baseline` and the c8-stage3 check; smoke runs, never measurements, of `validate.py --l8self` (`--l8self-sizes 2,6,4`), `first_error.py`, `opt_speed.py` (`--sample-sizes 2,6,4 --fake-topology 1x2x8 --no-pin`), `thread_identity.py` (1 and 8 threads, 2 and 16 lanes) and, with quaddiff, `quad_differential.py` at 2^20 pairs |
| `opt` | J-OPT-<R> (compute, exclusive; Stage 4b) | needs `C8_OPT_STEP` (`R5a`, `R5b`, `4`, `6`, `8`, `7` or `final`); `C8_OPT_PREV` (the sha12 of the last kept commit, whose binaries an earlier `opt` job stored in `$C8_STORE/opt/<sha12>/`) or `C8_OPT_PREV_PKG` (the sha12 of its export in `$C8_ROOT/pkg/`, built first on the job's node, so successive J-OPT jobs can run together), `C8_OPT_VARIANT_OPTFLAGS` (#7, opt-in: the same source also built with these OPTFLAGS, STRICT kept, gated by `validate.py --full` and `--l8self` and timed as VAR, step 7 = CAND:VAR; never stored or default), `C8_OPT_GATES` (default `validate_full,l8self,thread_identity`; also `first_error`, `same_binary`, `inspect_check`, `quaddiff`, `forced_tiers`) and `C8_OPT_SHAPES` (`B0=8x16,PREV=8x16`: another lane shape for a binary). The builds, `check_build.py`, `make baseline`; the exact gates first (`validate.py --full` with `validate.py --l8self bin/baseline` concurrently, then the others; `forced_tiers.py` is compared with Stage 3's J-VAL-3 record by `tests/record_compare.py`); only when all passed, `tools/opt_speed.py` (A-PERF-2: B0 = the Stage-3 baseline, PREV, CAND; the L8 sweep sample at 16 x 8, 3 interleaved repeats, medians of the lane-thread seconds); then the candidate's binaries stored read-only in `$C8_STORE/opt/<sha12>/`. Evidence: `$C8_ROOT/evidence/<sha12>/opt_<STEP>/` (`opt/` for the first jobs) |

**Precision contract at L8.** `check_points.py` runs the L8 kernels in `--contract` mode and `forced_tiers.py` records
every breach with its point (graph, replicate, index, tier, value, the 450-digit value). A breach at L8 is a
precision-contract finding: it does not fail the job (the step passes with status `passed_with_contract_findings` or
`contract_finding`), it is recorded and reported to the user, and Stage 5 waits for the answer (A-RPL-4/5). Thresholds
are never changed to remove one.

**`tools/cost_summary.py RUN MODEL [--symmetry-model M7] [--accounting FILE]`.** Per group the busy core-seconds and
seconds per point, the model's per-graph mean, median and maximum, the share of the heaviest 1%, the promotion rates
(binary128 and MP points per point, MP self-check alarms, shifted and non-moderate points), the ratio to C7(3)'s
symmetry model at L ≤ 7, and the pilot cost it implies on the model's own CPU (`cpu_label`: EPYC 7742 on Expanse, EPYC
7543 on symmetry; PF at R = 8, the R = 16 branch, PA as the
expectation of `pilot_select.py`'s draw, PC at its cap) in busy core-hours and SU, next to the plan's symmetry-basis
figures. Read only; it plans nothing and draws no seed.

**The Stage-3 baseline (A-RPL-8; tag `c8-stage3`).** `bin/baseline/c8d3_{gmp,decimal}` are the binaries J-SWEEP-1
measured. The sweep job copies them, read-only, to `$C8_STORE/baseline/<sha12>/`; `tools/baseline.py record` pins
their sha256s in `reference/baseline_c8_stage3.json`; `make baseline STORE=$C8_STORE` installs them into `bin/baseline/`
of any export and verifies every sha256 (refuses 65 otherwise); `tools/baseline.py check` re-verifies. Stage 4's G-L8SELF
compares every kernel change with them.

**Seeds (HD6).** The Stage-3b test seeds (the L8 bindings of the existing call sites, `thread_identity.py`'s, class_b
(f)'s) were registered before the runs (`benchmarks/expanse_2026-10-c8/stage_3b/seeds/`) and are listed in
`tests/fixtures/stage3a_test_seeds.json`; `prefix_check.py --real` draws fresh seeds and registers them after planning
(`seeds.py add RUN`; test-only twins that check no seed); the sweep's and the argmax run's plans reserve their seeds
before anything runs (`--reserve-seed`, required with `--forbid-seeds-from`; S2-002).

## Stage 5: the calibration refresh and the campaign build (`slurm/native_job.sh` sweep2, bld)

Stage 5 (PLAN "Stage 5"; D.14; J-SWEEP-2, J-BLD) runs on either site. J-SWEEP-2 refreshes the cost model on the final
binary after the final J-VAL-1 build and before every other Stage-5 plan; its model goes into a data-only commit, whose
export J-BLD builds in place; every later Stage-5 job runs from that export. The site's model name comes from
`slurm/site.sh c8_site_cpu` (`$C8_SITE_MODEL`: Expanse `gmp_expanse_epyc7742_c8.json`, symmetry
`gmp_symmetry_epyc7543_c8.json`), and both modes pass the CPU pin first (68).

| `C8_JOB` | Job | Variables | Runs |
|---|---|---|---|
| `sweep2` | J-SWEEP-2, the calibration refresh (D.14) | `C8_SWEEP_RUN` (a new `$C8_ROOT/runs/<name>`), `C8_SWEEP_SEED` (fresh, all digits); optional `C8_SWEEP_PREV` (`cost_models/<file>.json` of the export) and `C8_SWEEP_LANES` (`numa`, `numa:<k>`, `socket` or a lane count); `$C8_SEEDS` must exist. 64 for anything else, before any evidence | in the L8 work copy `$C8_ROOT/work/sweep2_<id>` (kept: its campaign names it): `make link-l8`; `bin/c8d3_{gmp,decimal}`; `check_build.py` with the site's toolchain; if all passed, `sweep.py RUN --seed S --refresh PREV --choose-only` (`basis.log`: role, basis, why, both executables, PREV) and `sweep.py RUN --seed S --refresh PREV --output $EV/$C8_SITE_MODEL --report $EV/refresh_report.json --forbid-seeds-from $C8_SEEDS --reserve-seed $C8_SEEDS --scratch $C8_SCRATCH` (the seed reserved before anything runs, S2-002) with `C8_LANES` = `C8_SWEEP_LANES`, else the site default (an inherited `C8_LANES` is ignored); `seeds.py add RUN` whenever its manifest exists (HD6; idempotent); with a model: `cost_identity.py check --model $EV/$C8_SITE_MODEL --exe bin/c8d3_gmp --host-cpu --mp-check on`, `refresh_record.json` (fails unless the manifest's role is `cost_refresh` and its executable is `bin/c8d3_gmp`, and the model's `source.plan_role` is `cost_refresh` and its `scheduled_with.basis` is `basis.log`'s; records PREV's path, sha256 and executable sha256), `assemble.py RUN --bootstrap 1024` (A-IN-7; `C8_test_result.json` copied), `cost_summary.py` (`--symmetry-model cost_models/gmp_symmetry_epyc7532.json`); then sweep1's evidence copies (status, manifest, per-group merged/costs/promotions, the seed log). Nothing goes to `$C8_STORE/baseline` (the c8-stage3 baseline is not this binary). Evidence: `$C8_ROOT/evidence/<sha12>/sweep2_<id>/` (never overwritten; PLAN risk 32) |
| `bld` | J-BLD, the campaign build (PLAN J-BLD row; run once per export, before any plan on it) | `C8_BLD_BASE_PKG` (the sha12 of the code commit's export in `$C8_ROOT/pkg/`, with a Makefile); optional `C8_SWEEP_RUN` and `C8_SWEEP_PKG` (the sweep's kept work copy) together. 64 before anything is written: a missing or foreign base, the data export itself as its base (by sha12 or a path to the same directory: a tree compared with itself passes anything), a base whose `tools/cost_identity.py` has no data-only check, one of the two sweep variables alone, a missing `cost_models/$C8_SITE_MODEL`, an existing `bin/c8d3_gmp` ("J-BLD builds an export once") | **in place** (`W=$C8_PACKAGE`, no copy): first the **base export's** `$C8_ROOT/pkg/$C8_BLD_BASE_PKG/tools/cost_identity.py data-only --base $C8_ROOT/pkg/$C8_BLD_BASE_PKG --data $C8_PACKAGE` (the tree under test never judges itself; `data_only_diff.json`; `designs/forbidden_seeds.json` may only grow, the base's entries an exact prefix as `seeds.py mirror` requires, else `refused`; on failure "not a data-only export", nothing linked or built); `make link-l8 PYTHON=python3 STORE=$C8_STORE`; `make verify-inputs` (what `plan` checks, the L8 packs included); `make -j <n> CXX=g++ PYTHON=python3 bin/c8d3_gmp bin/c8d3_decimal` (explicit targets: `make inputs` never rewrites a pinned input; the same binaries as `make && make decimal`); `check_build.py` with the site's toolchain; `cost_identity.py check --model cost_models/$C8_SITE_MODEL --exe bin/c8d3_gmp --host-cpu --mp-check on` (HD11's three fields as `plan` will check them on this CPU class); `model_record.json` (sha256, executable, CPU, mp_check, lane shape, job ids, `scheduled_with`, source; fails unless measured, schema `c8-d3-cost-model-1` and `source.plan_role` `cost_sweep` or `cost_refresh`); with the sweep variables, `accounting.py` on the sweep (from its work copy; A-ORC-9's sweep part) and `cost_summary.py --accounting` (bookkeeping). A failed build or check (`link_l8` … `model_record`) moves `bin/` to `bin.bld_failed_<id>` before the summary (no plan or lane worker can use an unchecked binary of this export; the L8 links stay, harmless) and exits 1; then PLAN risk 32: repeat the refresh on this export (`sweep2` with `C8_PACKAGE` = it), make a new data-only commit and a new J-BLD. When only the bookkeeping failed, `bin/` stays (the build, `check_build` and the HD11 identity passed; the export is built and usable), the job exits 1 and its log names the two commands to rerun (`accounting.py` from the sweep's work copy into `$EV/sweep_accounting_rerun.json`, then `cost_summary.py --accounting` into `$EV/cost_summary_rerun.json`, on a login node or in a short raw job); no risk-32 loop and no second J-BLD (it would refuse: `bin/c8d3_gmp` exists). Evidence: `$C8_ROOT/evidence/<D sha12>/bld_<id>/` |

**PREV and lanes.** PREV is `C8_SWEEP_PREV` when set; else `cost_models/$C8_SITE_MODEL` when the export has it (the
site's previous final-binary model: Stage 6, or Expanse's J-SWEEP-1 model); else `cost_models/gmp_expanse_epyc7742_c8.json`,
the package's first measured model (D.14). `sweep.py` picks the basis from PREV's HD11 fields: the same executable
gives the measured basis, another executable with the same CPU and `mp_check` the prior-model basis at F = 2 (with the
fit check against `squeue %L`), anything else the bootstrap basis (`--bootstrap-chunk 512 --shards 32`). Symmetry's
first refresh is bootstrap ("the previous model does not qualify: cpu_model"; D10 deviation accepted 2026-10-05);
Expanse's, and later symmetry ones, are prior-model. Lanes: Expanse 16 (P4's best shape 16 × 8; the production default
stayed 8 × 16 after R5b's revert, so `C8_SWEEP_LANES=numa` measures at that shape), symmetry `numa` (8 × 8 on NPS4; D8).

```bash
# symmetry (no -A; the CPU pin's --exclude is added by the tool)
C8_JOB=sweep2 C8_SWEEP_RUN=$C8_ROOT/runs/sweep2-<date> C8_SWEEP_SEED=<fresh> python3 -B $C8_PACKAGE/tools/slurm_submit.py raw \
    --role sweep2 --dir $C8_SWEEP_RUN -- -p amdq --nodes=1 --ntasks=1 -c 64 --mem=240G -t 01:00:00 -o $C8_ROOT/logs/%x_%j.out \
    $C8_PACKAGE/slurm/native_job.sh
C8_JOB=bld C8_BLD_BASE_PKG=<F' sha12> [C8_SWEEP_RUN=... C8_SWEEP_PKG=$C8_ROOT/work/sweep2_<id>] python3 -B $C8_PACKAGE/tools/slurm_submit.py raw \
    --role bld --dir $C8_ROOT/evidence/<D sha12>/bld -- -p amddebugq --nodes=1 --ntasks=1 -c 64 --mem=240G -t 00:30:00 \
    -o $C8_ROOT/logs/%x_%j.out $C8_PACKAGE/slurm/native_job.sh
# Expanse
C8_JOB=sweep2 ... raw --role sweep2 --dir $C8_SWEEP_RUN -- -A <ACCOUNT> -p compute --exclusive --nodes=1 --ntasks=1 --mem=240G \
    -t 01:00:00 --no-requeue -o $C8_ROOT/logs/%x_%j.out $C8_PACKAGE/slurm/native_job.sh
C8_JOB=bld ... raw --role bld --dir $C8_ROOT/evidence/<D sha12>/bld -- -A <ACCOUNT> -p shared --nodes=1 --ntasks=1 -c 32 --mem=60G \
    -t 00:20:00 --no-requeue -o $C8_ROOT/logs/%x_%j.out $C8_PACKAGE/slurm/native_job.sh
```

**The data-only commit** (on the Mac, after copying the evidence; `$C8_SITE_MODEL` is the job's name for
`gmp_symmetry_epyc7543_c8.json` on symmetry and `gmp_expanse_epyc7742_c8.json` on Expanse, no login shell or Mac sets
it): `$EV/$C8_SITE_MODEL` goes byte-identical (sha256 recorded) to `cost_models/$C8_SITE_MODEL` (a new file on symmetry; on Expanse it replaces J-SWEEP-1's model, as the
J-BLD row names it), all of `$EV` to `benchmarks/<site dir>/stage5_<sha12>/sweep2_<jobid>/` (`refresh_report.json`,
`basis.log`, `refresh_record.json`, `cost_summary.json`, `check_build.json`, `environment.txt`, `summary.json`,
`binaries.sha256`, `buildinfo/`, `sweep_manifest.json`, `sweep_status.txt`, `groups/`, `C8_test_result.json`,
`forbidden_seeds.json`, the step logs; `<site dir>` is `symmetry_2026-10-c8` or `expanse_2026-10-c8`) and a
`cost_models/README.md` paragraph (job, node, CPU, model sha256, executable sha256, `scheduled_with`, PREV); nothing
outside `cost_models/` and `benchmarks/` (J-BLD's data-only check allows the carry set too: `docs/`, `README.md`,
`CHANGELOG.md`, `designs/forbidden_seeds.json` (append-only: refreshed with `seeds.py mirror`, never shrunk),
`DELIVERY_MANIFEST.json`, `SHA256SUMS`; user decision 2026-10-05). Before committing, on the Mac: `python3 -B tools/prepare_benchmarks.py --order 8 --check` (the Stage-4a fixtures and their Stage-3 model copy unchanged). Then `git add -A`, `python3 -B tools/verify_delivery.py --write`, commit, export, J-BLD on the new export.

**The Stage-4a fixtures keep the Stage-3 model.** Replacing `cost_models/gmp_expanse_epyc7742_c8.json` on Expanse
does not touch `benchmarks/fixtures8` (the Stage-4a profiling fixtures of the Stage-3 baseline, `tools/prepare_benchmarks.py
--order 8`). Their cost model is the Stage-3 Expanse model (J-SWEEP-1, sha256 `fc78fc8f…`, executable `24adff54…`), read
from J-SWEEP-1's evidence copy `benchmarks/expanse_2026-10-c8/stage_3b/8b8778273bd9/sweep1/gmp_expanse_epyc7742_c8.json`
(the same bytes; `FIX8['cost_model']` and the manifest's `cost_model.path`, since 2026-10-06), never from `cost_models/`.
`tests/test_profiling.py` (`fixtures`, `determinism`; `make test-python`) checks that path, its sha256 and the
byte-identical rebuild, and that the manifest is the Stage-4a one (sha256 `becacd70…`, the value the Stage-4a profiling
records cite) except for that path (now `dedc515f…`). A data-only commit must never change or remove that evidence file.
The other readers of the `cost_models/` file mean the live site model and accept the refreshed one: `tools/opt_speed.py`'s
default `--cost-model` (lane LPT of the A-PERF-2 speed runs; the record names the model's sha256), `tests/test_opt.py`
`sample` (every L8 sample kernel has a key), `tests/drill_select_test.py` (recomputes its expected pick from the same file)
and `tests/integration_3a.py` (the site's model names the site's pinned CPU).

**Seeds (HD6).** The sweep's base seed is in `$C8_SEEDS` from its plan's reservation, before any index runs
(`--reserve-seed`, S2-002; the `seeds.py add` after it finds it `present`); fold that log into the other
site's (`seeds.py merge`, "Symmetry", the seed log) and refresh the mirror before the next plan on either site.

**`copy_export`.** Every native mode but `bld` copies the export: `cp -a` of a pristine export (no `bin/`, no
`bin.bld_failed_*`, no L8 pack links), exactly as before, so Expanse's jobs on git-archive exports are unchanged; an
export J-BLD built is copied without `bin/`, `bin.bld_failed_*` and `inputs/packs/{free,power}_L8.pack` (GNU `tar
--exclude`; logged "built export: ..."), so a later `val1`, J-E0-final or `sweep2` on it neither copies 8.8 GB of packs
nor reuses stale binaries: L8 modes re-link with `make link-l8` and every mode rebuilds. The other copies of an
export take `copy_export` too: `opt`'s variant copy of `$C8_PACKAGE`, its copy of `C8_OPT_PREV_PKG` and `basestore`'s
copy of `C8_BASE_PKG` (each rebuilt there; a copied built `bin/c8d3_gmp` would look up to date to make and the OPTFLAGS
variant or PREV would silently be the export's binary).

### J-DRL-9's selections (`tools/drill_select.py`)

`tools/drill_select.py drl9 --cost-model M --out-dir DIR [--inputs DIR]` writes the subset-pilot drill's hand-made
selections (PLAN J-DRL-9; `tools/pilot_select.py` stays untouched, pinned for the PA plan). Per sector the candidates
are the inventory's L8 rows without the zero-channel graphs (`pilot_select.zero_channel_l8`, s_G = 4), ranked by the
measured model's mean of the a and b seconds per point (ties by id; a candidate without an a or b key refuses, 1): the
cheapest at 1,024 points nested at [256] (`drill_nested`), the second at 512 points (`drill`). `DIR/stage_a_drl9.json`
(role `stage_a`, seed null, groups `free:8` and `power:8`) and `DIR/confirm_empty_drl9.json` (role `confirm`, groups
`{}`, an `empty_reason`), both with the inputs manifest's sha256, the purpose, the rule, the model's path and sha256.
Before writing, `production.read_selection` must accept the stage_a file for a test-only plan, refuse it for any other
("power of two >= 4096") and refuse the empty one with 65; any surprise exits 1 and writes nothing; an existing
output refuses (64). It prints both files, the four graphs and the drill's estimated busy core-seconds. The drill:

`$C8_SITE_MODEL` is set inside jobs only (`slurm/site.sh c8_site_cpu`; no `env.sh` exports it), so a login shell
names the site's model file itself:

```bash
M=$C8_PACKAGE/cost_models/gmp_symmetry_epyc7543_c8.json     # symmetry; Expanse: $C8_PACKAGE/cost_models/gmp_expanse_epyc7742_c8.json
python3 -B $C8_PACKAGE/tools/drill_select.py drl9 --cost-model $M --out-dir $C8_ROOT/evidence/<sha12>/drl9_sel
# a raw plan job (--role plan): plan.sh runs the plan with its seed reservation, then ledger.py register ($M is expanded in the login
# shell when the --wrap line is built)
$C8_PACKAGE/slurm/plan.sh $C8_ROOT/runs/D9 --pilot --graphs <DIR>/stage_a_drl9.json --replicates 2 --test-only --threads <w> \
    --backend gmp --mp-check on --cost-model $M --seed <S>
# the same plan with <DIR>/confirm_empty_drl9.json exits 65 and leaves no directory; then, in drill mode:
C8_RUN=$C8_ROOT/runs/D9 C8_LANE_DRILL=1 C8_LANE_CPUS=<c> python3 -B $C8_PACKAGE/tools/slurm_submit.py lanes 1
```

## Stage 5: the throughput report (`tools/thru_report.py`; J-SMK-4, A-PERF-3, A-ORC-13, A-ORC-5)

```bash
python3 -B tools/accounting.py RUN --json > ACC.json          # after the drill's jobs ended
python3 -B tools/thru_report.py RUN --accounting ACC.json [--job J] [--sweep SWEEP_RUN] \
    [--reference-p4 P4.json [--reference-shape NxT] | --reference-opt-speed OPT.json --reference-binary NAME [--reference-shape NxT] \
     | --reference-throughput X --reference-note TEXT] [--hook-dir DIR] [--parts perf3,orc13,orc5] [--strict] --output OUT.json
```

Read-only on RUN, no scheduler call: a short raw job (`--role report`) or the Mac against a copy of the files it
reads. **Inputs:** `RUN/manifest.json`; `RUN/cost_model.json` (65 unless the campaign is on the measured basis with
the model at its pin); `RUN/groups/<g>/config.json`; the sizes of `RUN/groups/<g>/tasks.sqlite`, `sobol.bin` and the
per-index `tasks/s<shard>.tsv` and `.blocks.json`; `inputs/inventory.json` (member lengths); every
`RUN/groups/<g>/checkpoints/<block>.json`, validated against its frozen block (65), attributed to the job its
fingerprint names; `RUN/slurm_logs/lane-<J>.log` (host, CPU, lane widths; required for perf3, 65);
`RUN/lanes/logs/idx<index>.<job>.<restart>.<lane>.<ns>.log` (fingerprint line, committed blocks); `ACC.json` (W = J's
work attempts' ElapsedRaw and the node's allocated cores = their `alloc_cpus`, sacct's AllocTRES cpu, one value; an
`ACC.json` without `alloc_cpus`, from an older `accounting.py`, falls back to the lane log's node CPU count, the sum of
the lane widths, unless the lane log shows a memory-guard cut (65); required for perf3, 64; `--job` required when it
names several work jobs); `--sweep` (65 unless its manifest is the model's source; **required for an A-PERF-3 PASS**,
the PLAN's speed comparator); one reference (64 for two): a P4 record re-expressed in the campaign
model's units over `benchmarks/fixtures8`'s workload (campaign-a keys), an `opt_speed.json` (D9 on symmetry:
`tests/validate.l8self_sample` × replicates × points at campaign-a keys over the median node wall of the binary's
runs; 65 for a smoke record or one that did not pass) or a given value with a note; a reference of another binary
leaves the throughput INCOMPLETE.

**The hook (D7; outside the package).** `--hook-dir` reads one JSON per `production.py run` process, schema
`c8-d3-host-io-hook-1` (`pid`, `host`, `job`, `argv`, `utc`, `io{rchar,...}` from `/proc/self/io`,
`ru_maxrss_self_kb`, `ru_maxrss_children_kb`), written at exit by a `sitecustomize.py` that the host keeps outside the
package. Activate it in the submitting shell before `lanes N` (sbatch `--export=ALL` carries both into the workers):
`export PYTHONPATH=<hook dir> C8_RCHAR_DIR=<record dir>`. Records of another schema, campaign or command are counted as
foreign and ignored; an index with more than one attempt in a job is listed as ambiguous and skipped.

**Rules** (verdict PASS iff every rule of a part passes, FAIL if one fails, else INCOMPLETE; `--strict` exits 1 unless
every requested part passes):
- **A-PERF-3** (PLAN A-PERF-3, J-SMK-4): busy = Σ row seconds / (allocated node cores × W) ≥ 0.90 (the PLAN's "Σ task
  seconds/(128 × wall)": lanes that leave cores idle count against it; the lanes' widths are reported as `lane_cores`
  with a note when they differ); OpenMP efficiency per block = row
  seconds / (threads × integration_seconds) ≥ 0.95 for **every** block, as the PLAN states it ("per-block OpenMP
  efficiency ≥ 0.95"; Stage 6, Codex S4-007; Stage 5 gated the time-weighted mean); the time-weighted mean, min, P10,
  median and the share ≥ 0.95 are reported over all blocks and over L8 blocks. A block is evaluated only with valid
  timing: threads a positive integer, `integration_seconds` positive and finite, row seconds finite and ≥ 0 (S4-R2-001,
  round 2). Any other block is listed in `untimed_blocks` with the reason and keeps the OpenMP verdict from PASS:
  INCOMPLETE, or SHORTFALL when a timed block is below. A block below is a **SHORTFALL** (the
  OpenMP and the A-PERF-3 verdict; FAIL outranks it, it outranks INCOMPLETE), listed with its cause analysis
  (`openmp.shortfall`): per block its index, group, graphs, points, tasks, threads, efficiency, wall, idle core-seconds,
  tasks per thread, the wall's rank among the job's blocks, host and, from the per-row seconds, the longest row's bound on
  balance and the residual; its causes split into `established` (what the records' numbers imply: fewer tasks than
  threads, the longest row's bound, one thread meaning no imbalance between threads) and `possible` (per-launch
  overhead, end-of-block imbalance: labelled "not measured", since no record times them; S4-R2-002, round 2); a summary
  (their share of the integration core-seconds, the short blocks below 1 s, the lowest efficiency of the blocks of 1 s
  or more, the untimed blocks); the node and the allocation; `co_tenancy`, which keeps the job's configured lane
  capacity apart from the lanes' concurrent activity, which is not recorded (a single lane: no other lane of the job ran
  beside the block); and what the records can and cannot show (no per-thread or per-block times: the OpenMP runtime's
  own costs cannot be measured or separated from the imbalance, nor interference from the job's other lanes observed);
  throughput = Σ spp × points ×
  `production.mp_factor` / W ≥ 0.95 × the reference (per node-second and node-hour); median per-task speed (cost-model seconds / row seconds) at L8 within 10% of the `--sweep`
  campaign's L8 median under the same model (without `--sweep` the ratio to 1.0, "model definition", is reported for
  information only and the speed, so A-PERF-3, is INCOMPLETE, never PASS; `a_perf_3.references` records the throughput,
  speed and core sources used); the lane log's CPU equals the model's; sizing: L8 row seconds / allocated cores ≥
  3,600 s and busy core-h ≥ 140 on 128 cores (PLAN) or **≥ 72 on a 64-core
  symmetry node (A1 deviation, user decision 2026-10-05)**; other core counts are INCOMPLETE. A shortfall is reported
  with its causes: native integration, native load and outside-native core-seconds and the load share.
- **A-ORC-13 real Slurm** (PLAN A-ORC-13): one `fingerprint_bytes` value per fingerprint key (idx logs and checkpoints);
  per paired run the own bytes: those of the reading process (`own_bytes_process`: tasks file, blocks file, the group's
  `sobol.bin`, per committed block the inventory length of each distinct graph (the staging read) plus
  `len(json.dumps(native))` for `native.json` read back, an estimate, and the checkpoint file of each block already
  present) and **`native_staged_reads`** (F13-d3, Stage 6): Linux adds a reaped child's I/O to its parent's
  `/proc/self/io`, so the hook's rchar of `production.py run` holds each native launch's read of its block's staged
  copy; the hook gives process totals only, so these reads are modelled as the staged bytes of every block the run
  executed (the rule `NATIVE_RULE` is written into the record; the native's other per-launch reads, its net, gamma and
  task-file copies, stay in non-own). `non_own = rchar − own_bytes` and `non_own − fingerprint_bytes` decide;
  `non_own_raw = rchar − own_bytes_process` (the Stage-5 model) is reported beside them. The medians of the smallest
  and the largest group by `tasks.sqlite` bytes (ratio > 10, else INCOMPLETE "not applicable") agree within max(10%,
  2 MB = 2,000,000 bytes), both; least-squares fits of rchar (slope near 2) and of non_own (slope near 0) on the staged
  bytes are reported.
- **A-ORC-5** (PLAN A-ORC-5): per index (native `max_rss_kb` + Python `ru_maxrss_self_kb`) × 1024 / `est_peak_bytes` ≤
  1.2; without the hook the native-only ratio, INCOMPLETE; `ru_maxrss_children_kb` is reported against `max_rss_kb`.
  On the smoke (J-SMK-2) run it with `--parts orc5 --hook-dir DIR` (without `--job` it covers both workers).

The output (`c8-d3-thru-report-2` since Stage 6; Stage 5 wrote `-1`; never overwritten): inputs with sha256s and hook
counts, the job (host, CPU, lanes, widths, `lane_cores`, the allocated `cores` and their source, W, attempts), sizing,
`a_perf_3`, `a_orc_13`, `a_orc_5`, `block_detail` (now with points, the longest row and the host per block), `runs`,
notes.

**Re-evaluating a committed report** (Stage 6, on the Mac, without the campaign): `thru_report.py --rederive
REPORT.json [--hook-dir DIR] --output OUT.json` applies the Stage-6 rules to a `-1` or `-2` record: the OpenMP rule per
block from its `block_detail` (each block's timing validity checked; the cause analysis without the per-row seconds,
which need the checkpoints) with the A-PERF-3 verdict recombined, and A-ORC-13 under `NATIVE_RULE` from its `runs` (with
`--hook-dir` each run's rchar is re-read from its hook record; schema, job and index checked, 65 otherwise). Everything
else is the source's; the output (`-2`) names its source, what was recomputed and what was taken over (`rederived`).
J-SMK-4's current one is `benchmarks/symmetry_2026-10-c8/stage5_59d4922/smk4/thru_report_s6b.json` (fix round 2: the
cause analysis of S4-R2-002 and the timing rule of S4-R2-001; every verdict and number as before). Fix round 1's
`thru_report_s6.json` is kept as a historical record; it asserts the causes that `s6b` labels as possible (see "Stage 6
results").

## Stage 5 results (2026-10-06)

**Historical verdicts.** This section keeps Stage 5's verdicts as they were recorded. Three were replaced in Stage 6
(see "Stage 6 results" below):
- A-ORC-4 (i) and the J-DRL-5/J-DRL-8 re-merges, FAIL (F8-d3): fixed by F8-d3, and both re-merges passed on real
  Slurm (J-DRL-5 570796, J-DRL-8 570815);
- A-ORC-13, FAIL (F13-d3): **PASS** on re-derivation (`smk4/thru_report_s6b.json`);
- A-PERF-3 / A-SMK-4, PASS on the time-weighted mean: **SHORTFALL** under the PLAN's per-block rule (S4-007; three
  blocks of a few milliseconds; `smk4/thru_report_s6b.json`).

Stage 5 ran on symmetry, as Amendment A1 requires. Expanse ran only J-VAL-4 (GCC ≥ 12), J-E0-final (val1 on G), its
own calibration refresh with J-BLD-exp, and the J-EXP template checks (user decisions,
`LRI_C8_D3_HPC_loop/PLAN-REVIEW-LOG.md:488-504`).
- **Commits.**
  - F' = 2241d64 is the final Stage-5 code (export 3cbe7a4; e3b9252 adds only tests and manifests).
  - D = 6d04eee (export 59d4922) is the data-only commit with symmetry's model.
  - G = c4b9502 (export a7f5707) is a tests/tools code commit with the same binaries.
  - D2 = 3fa41f7 (export bd7f2e1) is the data-only commit with Expanse's model.
- **Where it ran.** Every symmetry Stage-5 job after J-BLD ran from D's export, except J-VAL-1-G (G's export). From
  the final validations on F', every AMD job ran with the CPU pin (`ExcNodeList cn[079-082,084-085,112]`,
  `stage5_3cbe7a4/README.md`).
- **Records.** Procedures: `LRI_C8_D3_HPC_loop/artifacts/STAGE5_SYMMETRY_RUNBOOK.md`. Every job and its verdict: the
  READMEs of `benchmarks/symmetry_2026-10-c8/stage5_*/` and `benchmarks/expanse_2026-10-c8/stage5_bd7f2e1/`. The
  paths below are relative to `benchmarks/symmetry_2026-10-c8/` unless stated.

| Item | Jobs (node) | Verdict | Evidence |
|---|---|---|---|
| A1 site validation (2026-10-05) | J-LOCK-0-sym 570267 (<NODE> against <NODE>), J-SCRATCH-sym 570271 (<NODE>), J-E1-sym 570273 (<NODE>), J-BASE-sym 570275 (<NODE>), storeverify 570304 (<NODE>), symmetry J-VAL-3 570319 (<NODE>), J-E0-sym 570323 (<NODE>) | pass. Before that, J-E0-sym 570281, 570309 and 570317 failed and were repaired (5b08e50, 79089a9, 2bda68e), and J-VAL-3 570311 failed until the seed log existed | `lock0sym_02963bc/`, `stage5_{02963bc,4a136e8,80ec5e5,f975f20}/` |
| Final validations on F' | J-RUN1 570390 (<NODE>), J-VAL-3 570392 (<NODE>), J-VAL-2 570394 (<NODE>); J-VAL-4 54690085 (Expanse <NODE>, GCC 13.3); J-VAL-1 570401 (<NODE>, e3b9252, 16.7 min) | pass. Before that, val1 570388 and 570397 failed on test-only host assumptions (81b94f0, 6772026); the targeted rerun 570399 passed | `stage5_3cbe7a4/`, `stage5_e3b9252/val1/`, `stage5_67720266/testsym/`, `../expanse_2026-10-c8/stage5_3cbe7a4/val4/` |
| Refresh, symmetry | J-SWEEP-2 `sweep2` 570403 (<NODE>, 7.7 min, seed 396244834); J-BLD `bld` 570406 (<NODE>, 37 s) | pass; bootstrap basis (D10); model `0fc934e7…`, executable `8f3a36aa…` | `stage5_e3b9252/sweep2_570403/`, `stage5_59d4922/bld_570406/` |
| Refresh, Expanse | J-SWEEP-2-exp 54694602 (<NODE>: `module load cpu/0.21.2a` unknown, failed in 4 s), rerun 54694976 (<NODE>); J-BLD-exp 54695102 (<NODE>) | pass on the rerun; prior_model at F = 2 on J-SWEEP-1's model; model `56df9d61…`, executable `b7db88c1…` | `../expanse_2026-10-c8/stage5_59d4922/sweep2_54694976/`, `../expanse_2026-10-c8/stage5_bd7f2e1/` |
| val1 on G | J-VAL-1-G 570433 (<NODE>); J-E0-final 54694604 (Expanse <NODE>) | pass | `stage5_a7f5707/val1/`, `../expanse_2026-10-c8/stage5_a7f5707/val1/` |
| W1 | J-L8SELF-sym 570410 (<NODE>); J-SCRATCH-intel 570412 (debugq, <NODE>) | pass: l8self exact against the symmetry baseline, ×1.366 (`docs/PERFORMANCE.md`); `/local1/<USER>/job_570412` computed in the job | `stage5_59d4922/opt_final/`, `scratch_intel/` |
| Smoke and twins | J-SMK-1 570427 (<NODE>; 3 plans, manifest `5b32e9fc…`: 1,024 stratified test graphs, 4,096 points, 4 replicates, 30 jobs, 17.0 core-h); J-SMK-2 `lanes 2` 570437, 570438, merge 570439; R-SMK2 570481 | pass (A-SMK-1) | `stage5_59d4922/smk1/`, `smk2/`, `wave2_logs/`, `wave3_logs/` |
| Drill, throughput and production-size plans | J-DRL-0 570429 (<NODE>); DL re-plan 570441; J-DES-5 570431 (<NODE>) | pass; D9E refused (65) | `drl0/`, `dl2/`, `drl9_sel/`, `des5/` |
| Drills on Intel `debugq` | J-DRL-4, -5, -6, -7, -8, -9; drill_check 570492 | below; J-DRL-5 and J-DRL-8 re-merges FAIL (F8-d3; historical: both PASS in Stage 6, 570796 and 570815) | `drl4/` … `drl9/`, `drlchk/`, `wave3_logs/merge_logs/` |
| Throughput drill | J-SMK-4 570496 (<NODE>, 1 h 56 min), merge 570497; R-SMK4 570554 (<NODE>) | Historical: A-PERF-3 PASS, A-ORC-5 PASS, **A-ORC-13 FAIL (F13-d3)**. Replaced by the re-derivation `smk4/thru_report_s6b.json`: A-PERF-3 **SHORTFALL** (per block, S4-007), A-ORC-13 **PASS**, A-ORC-5 PASS | `smk4/`, `smk4_hook/` |
| Twin drills on `amdq` | J-DRL-3 570499, 570500; J-DRL-2 570503, 570504; J-DRL-1 570507, 570508, 570510, 570511; R-DRL 570556 | pass | `drl1/`, `drl2/`, `drl3/`, `drl12/` |
| Design chain | J-SMK-3a 570523 (fallback freeze at 1e-3, 2 batches; RA, RB 113 jobs each); batch A 570525 (2 h 58 min), merge 570526; batch B 570551 (3 h 00 min), merge 570552 (68 on <NODE>), re-merge 570589 (68 on <NODE>), re-merge 570593 (<NODE>); R-SMK3 570595 | **pass** (A-SMK-3): both batches status 0 and `verify_result` 0; the partial (1 batch) and final (2 batches) combines written, label partial, final false, verified | `smk3/`, `wave45_logs/` |
| Pilot readiness | J-PIL-0 570565; `lanes 2/3 --dry-run` | **pass** (A-SMK-5): PA plan (`docs/PILOT_RUNBOOK.md`); both dry runs admitted (0+3/4, 0+4/4; lane time 45 min; merge path subset-check) with no other C63d AMD job | `pil0/` |
| J-EXP (Expanse) | J-EXP-0 plan 54698448 (41 jobs, measured); J-EXP-1 `window 0:0-1` 54698533; J-EXP-2 `debug` drill lane 54698588 (21 min); J-EXP-3 `compute` lane 54698591 (5 min, superseding the pending merge 54698589); J-EXP-4 `shared` merge with assembly 54698592; report 54700018 | pass: status 0, `verify_result` 0, `C8_test_result.json`, accounting 17.13 SU (A-EXP-3) | `../expanse_2026-10-c8/stage5_bd7f2e1/exp/`, `logs/` |
| Adoption drill | J-DRL-10: drill_kill 570597 (submitter SIGKILLed after sbatch; adopted), drill_after 570599, drill_anchor 570601, drill_dep 570603 (cancelled while pending; charge 0), drill_res 570605, window 570607 (`_2` cancelled while pending: stuck), drill_tmo (kill_during_launch, rc 137: stuck) | **pass** (A-ORC-17 real, A-ORC-11/12): `timeout` outlived the submitter, the stand-in killed at 120 s; hand sum equal; both stuck intents held past G and resolved by the user decision PLAN-REVIEW-LOG.md:667, slot freed, SU kept | `drl10_host/` |

**Drills (A-SMK-2, A-ORC-8, A-ORC-10, A-ORC-7, A-DES-7 (f)).** The evidence directories are under `stage5_59d4922/`.
- **J-DRL-1** (A-ORC-8 (a)). Worker A 570507 was cancelled at 34 s holding 8 claims, and its merge M1 570508 exited 65.
  - The next `lanes 1` logged "released stale claim of index … (job 570507, CANCELLED)" for all 8, then ran worker B
    570510 and merge M2 570511. The twin's status is 0.
  - C62d's F7 leftovers would be in node-local scratch, which <NODE> cannot see. The check is limited to the lane log
    and the next worker's behaviour.
- **J-DRL-2** (A-ORC-8 (b)). A user `scontrol requeue` of the `--no-requeue` worker 570503 was refused: rc 1,
  `JobState=RUNNING`, `Requeue=0`, `Restarts=0` (`drl2/requeue.txt`); Slurm's message was "Requested operation is
  presently disabled" (`stage5_59d4922/README.md`; `PLAN-REVIEW-LOG.md:609-610`). The worker completed, merge 570504
  ran, and twin2's status is 0 (`drl2/status_after.txt`).
- **J-DRL-3** (A-ORC-8 (c)). With `C8_LANE_TIME=00:20:00`, worker 570499 completed in 6.5 min with no killed index and
  no claim or failure left. Status exits 1, and merge 570500 exits 65.
- **R-DRL** (A-ORC-8 (a), (b)). Both twins' 24 groups have `batches` bitwise equal to the smoke's
  (`wave45_logs/…_570556.out`).
- **A-ORC-8 (d).** `Requeue=0` on 570427, 570437, 570438 and 570439 (`smk1/requeue.txt`, `smk2/requeue.txt`).
- **J-DRL-4** (A-ORC-7 real lock). With the lock held, `lanes 2 --dry-run` exits 75 after `C8_LOCK_WAIT` 5 s, naming
  the holder (`{"host": "<NODE>", …, "command": "J-DRL-4 holder"}`). Once the lock is freed it exits 0 at once.
  It then submitted lanes 570443 and 570444 and merge 570445 on `debugq` (`drl4/lanes2.out`); J-DRL-6 (a) superseded
  that merge.
- **J-DRL-6** (A-ORC-10).
  - (a) `lanes 1` after `lanes 2` (worker 570447, merge 570448), then `lanes 0` (merge 570450), each leave one pending
    merge depending on all three live workers (`drl6/queue_after_lanes1.txt`, `queue_after_lanes0.txt`). The
    superseded merges 570445 and 570448 were cancelled before eligibility: `sacct -s CA -E now` shows CANCELLED with
    ElapsedRaw 0, and the unfiltered query does not list them (`drl6/superseded_sacct.txt`).
  - (b) `lanes 0` on a complete campaign submits only the merge (570483), and DL's tree hash is unchanged
    (`4d002407…`).
  - (c) `resubmit` submits the merge only ("no work to resubmit", 570487).
- **J-DRL-7** (mixed mode). `submit` on live lanes exits 65, and `lanes` on live arrays exits 65.
- **J-DRL-5** (array mode, window line, recovery).
  - DA ran in 3 windows of 8 (570452–570454), then merge 570455.
  - After one checkpoint (a_free_L3, index 0) and its group's `merged.json` were deleted, `status` exits 1 and names
    `window 0:0` (`drl5/status.txt`). That window (570485) recomputed the index, and its scientific rows equal the
    saved ones (drill_check 570492).
  - **The re-merge 570487 failed (F8-d3).**
- **J-DRL-8** (A-ORC-4 (i) on real Slurm). Index 0's done marker was invalidated ("queue rebuild: checkpoint blocks
  missing", `lanes/done_invalidated.jsonl`), and the recomputed scientific rows equal the saved ones. **The re-merge
  570490 failed (F8-d3).**
- **J-DRL-9** (A-DES-7 (f), A-DES-8 (c)). D9 ran as lane 570478 and merge 570479.
  - Role `pilot_subset`; `subset_summary.json` was written; no `assemble.py` line and no `C8_*result.json`.
  - 2 prefix rows per group; `prefix_verify` ok on 8 rows.
  - The runbook's grep for "subset-check" in the merge log was wrong (rc 1). The role, the summary and the missing
    result file decide the drill.
  - The empty confirm selection D9E exited 65 and left no directory (J-DRL-0).
- **A-ORC-14, real part.** `find` for `-journal`, `-wal`, `-shm` or `.sqlite-lock` files over DL, DA and D9
  (drill_check 570492) and over the smoke (`smk2/sqlite_side_files.txt`) finds nothing. BeeGFS here plays the part of
  the PLAN's `lfs find`.
- **A-ORC-9, real part.** R-BLD: `sacct` 570403 ElapsedRaw 462 s × 64 / 3600 = 8.2133 core-h, which equals
  `sweep_accounting.json`'s `su_total` (`bld_570406/sweep_sacct.txt`). R-SMK2: the smoke's `accounting.py` gives
  23.627 core-h, which equals Σ 64 × ElapsedRaw / 3600 over its 4 `sacct` rows (47, 737, 539 and 6 s;
  `smk2/sacct_rows.txt`).

**Findings.**
- **F8-d3: C62d's F8 recurs here.** After a recovered index, the group re-merge stops at `Checksum mismatch:
  groups/a_free_L3/graph_costs.csv`. This happened in both DA (570487) and DL (570490). The first merge's tables remain
  while `merged.json` is deleted, and the recomputed scientific rows are equal.
  - Host decision: record it, do not work around it. The fix moves to Stage 6, porting C62d's `LRI_C8_D2_HPC` 86e15f4:
    `merged.json` becomes the group's commit point, and a result whose only change is `merged_sha256` is superseded.
  - It changes pinned tools (`production.py`, `assemble.py`), so it voids the Stage-5 plans and re-runs J-SWEEP-2,
    J-BLD, the affected drills and J-PIL-0 (`PLAN-REVIEW-LOG.md:590-600`).
  - A-ORC-4 (i) on real Slurm (C62d's R03/A-ORC-12) cannot pass until then.
  - **Stage 6 (2026-10-06):** fixed as "Merge (D.13)" above describes. The test
    `recovery_merge` (`tests/unit_orchestration.py`) runs J-DRL-8 unattended through `slurm/merge.sh` on the fake Slurm;
    on the Stage-5 code it stops at exactly the two points ("Checksum mismatch" on `a_free_L3/graph_costs.csv`, then
    "exists and differs"). The pinned tools that change are `production.py` and `common.py` (`assemble.py` is not
    pinned here), so the Stage-5 plans must be re-planned. **On real Slurm, J-DRL-5 (re-merge 570796) and J-DRL-8
    (re-merge 570815) passed: A-ORC-4 (i) PASS** ("Stage 6 results").
- **F13-d3: a gap in `thru_report`'s analysis, not an I/O defect.** The hook's rchar fits 2.00 × staged bytes +
  32.8 MB over 82 runs.
  - The kernel adds a reaped child's I/O to the parent's `/proc/self/io`. The rchar therefore includes the native
    worker reading its job-private staged copy (own work), which `thru_report`'s own-bytes model omits.
  - Non-own bytes then grow with the group: median 30.05 MB at a_free_L3 against 1,389.3 MB at a_free_L8
    (`smk4/thru_report.json`).
  - The fix in Stage 6 is in `tools/thru_report.py` (not pinned): subtract the native reads as C62d's `claim_io` does,
    then recompute from the kept hook records `smk4_hook/` (`PLAN-REVIEW-LOG.md:639-643`).
  - **Stage 6 (2026-10-06):** `NATIVE_RULE` (A-ORC-13 above). `thru_report.py --rederive` on `smk4/thru_report.json`
    with every rchar re-read from the 82 hook records gives `smk4/thru_report_s6b.json` (fix round 1's
    `thru_report_s6.json` has the same A-ORC-13 part): non-own medians 30,046,840 bytes
    (a_free_L3) and 31,734,238 (a_free_L8), 1,687,398 apart, within max(10% = 3,173,424, 2,000,000); without
    `fingerprint_bytes` 23,038,341 and 24,725,739 (within 2,472,574); **A-ORC-13 PASS**. The Stage-5 model's 30,049,197
    and 1,389,313,912 are reproduced as `non_own_raw`; the fits are rchar = 2.001 × staged + 32.8 MB and non-own slope
    0.0007.
- **S4-007 (Codex, Stage 6): A-PERF-3's OpenMP rule is per block.** Stage 5 gated the time-weighted mean (0.990, PASS)
  while three blocks were below 0.95. Under the PLAN's per-block rule `smk4/thru_report_s6b.json` gives A-PERF-3
  **SHORTFALL**: a_power_L3 (index 16) 0.929, b_power_L3 (57) 0.936 and b_power_L4 (58) 0.916, the three among the six
  shortest of the 789 blocks (walls 5.5 ms, 6.0 ms and 63 ms against a median of 26.5 s), with 1, 1 and 3 tasks per
  thread on 8 threads; together 1.4e-6 of the integration core-seconds; every block of 1 s or more is at least 0.9688;
  no block is untimed.
  - Cause (S4-R2-002, round 2): per-launch overhead and end-of-block imbalance are **possible** explanations, not
    measured. No record times them, so they can be neither confirmed nor told apart. The records establish no cause
    for these three blocks: each has at least as many tasks as threads, and the per-row seconds behind the longest
    row's bound are not in the committed record.
  - The job was configured with 8 lanes of 8 cores covering its 64 allocated cores. That is capacity: whether any of
    the other 7 lanes ran at the same moment as these blocks is not recorded (no per-block start and end times), so
    interference from them can be neither confirmed nor excluded.
  - Fix round 1's `smk4/thru_report_s6.json` (kept as a historical record) states the same verdict and numbers, but
    asserts the two causes and that every block ran beside the job's other lanes.
- **J-SMK-3's runbook estimate was too low.** Batch A took 2 h 58 min and was charged 189.49 core-h (its intent
  `e8ec9db97c9f` resolved at 189.4933, `smk3/lanes1_RB.out`), against the runbook's 25–40 core-h per batch [I]
  (`STAGE5_SYMMETRY_RUNBOOK.md:517`). The plan's own lane estimate was 178.3 core-h (`smk3/lanes1_RA.out`). Batch B
  was submitted as planned (570551, merge 570552; 320 + 64 core-h reserved) on the user's decision "yes go ahead"
  (`PLAN-REVIEW-LOG.md:633-635`); its result is pending.
- **DL's first plan held 0.22 busy core-h,** too little for the drills. It was re-planned as `drl-lanes2`: 2,048
  stratified graphs, 105 jobs, 15.3 busy core-h.
- **Expanse <NODE>** did not know `module load cpu/0.21.2a`, while other nodes of the same zen2 class did. Every
  later `compute`/`shared` job excluded it.

**Symmetry facts learned in Stage 5.**
- **`/bin/sh` is bash** on <NODE> (`PLAN-REVIEW-LOG.md:521`), so `--wrap` one-liners behave as on Expanse. The draft
  runbook's dash assumption was wrong.
- **BeeGFS 7.4.5 allows hard links across directories** (store → work, nlink 2; `stage5_02963bc/README.md`). So
  `make link-l8` hard-links the store's two L8 packs (8.8 GB) into every work copy instead of copying them.
- **BeeGFS reports a directory's `st_size` lazily.** It is 0 for a new directory and the entry count later:
  `inputs` 0 → 9, `inputs/d3` 0 → 5, `inputs/h1` 0 → 2, `inputs/order7` 0 → 2, `tools` 0 → 41
  (`stage5_80ec5e5/README.md`). Never compare directory sizes there. Since 2bda68e, `check_inputs` compares
  directories by kind, as `tests/plan_gate.py` does.
- **The CPU map in the Stage-5 evidence.**
  - Every AMD native job's `environment.txt` except the two of the next item names EPYC 7543, on <NODE>, <NODE>,
    <NODE>, <NODE>, <NODE>, <NODE> and <NODE>.
    They are 2 × 32 cores with 8 NUMA nodes of 8 cores (NPS4; `stage5_59d4922/opt_final/node.txt`).
  - EPYC 7532 shows up on <NODE> (570281) and <NODE> (570273), both before the pin.
  - The Intel `debugq` probe ran on <NODE> (570412).
  - The guard refused (68) J-SMK-3 batch B's merge 570552 on <NODE> and re-merge 570589 and report 570591 on <NODE>,
    both EPYC 7532 (the 570591 log is `wave45_logs/c8d3-report-*_570591.out`); the merge then passed on <NODE> (570593).
  - Stage 6 adds <NODE> and <NODE> to `budget.SYMMETRY.cpu_exclude` ("CPU pin" above).
- **Slurm 21.08 refuses a user `scontrol requeue` of a `--no-requeue` job** (J-DRL-2). C62d had seen one accepted.

**Dev line at the last committed snapshot** (`stage5_59d4922/drl12/budget_after_requeue.json`, 2026-10-06T13:17:50Z).
Symmetry's own line was 1,180.93 core-h: 754.26 spent plus 426.67 live, which includes batch B's 384. With Expanse's
carry of 1,260.13 SU (as of 13:17:37Z), the total is 2,441.06. That is below the 4,000 stop. The G5-CLOSE reading on
both sites is pending.

**Pending for G5, as recorded at the end of Stage 5 (historical).** Every item below was later closed: J-SMK-3 batch
B 570551 and the R-SMK3 combine (A-SMK-3 pass); J-PIL-0's `lanes 2/3 --dry-run` (pass); J-DRL-10 and its user-decision
close (A-ORC-17 real, A-ORC-11/12: pass); the Stage-6 fixes of F8-d3 (A-ORC-4 (i)) and F13-d3 (A-ORC-13), both now
PASS; the final val1 (symmetry val1 570736 on K₃: PASS; it repeats on fix round 2's commit); `verify_delivery.py
--strict` (passed at 47ed466). The current status and what is still pending are in "Stage 6 results" below and in
`LRI_C8_D3_HPC_loop/artifacts/G5_TABLE.md`.

## Stage 6 results (2026-10-06)

Stage 6 is the Codex inspection of the Stage-5 package (two rounds, the user's limit), its fix rounds, and the
revalidation of fix round 1 on the clusters. Sources: `LRI_C8_D3_HPC_loop/artifacts/r2_briefs/STAGE6_REVALIDATION.md`
and `LRI_C8_D3_HPC_loop/PLAN-REVIEW-LOG.md`. The evidence is under `benchmarks/symmetry_2026-10-c8/stage6_*/`, and the
paths below are relative to `benchmarks/symmetry_2026-10-c8/`.
- **Commits.**
  - K = 95f6eaf merges the four fix-round-1 branches.
  - K₂ = ca7d482 is K plus a test-reporting fix (98cb772).
  - K₃ = 0dde6ad is code acd3b39 (a test-environment fix) plus K's symmetry evidence.
  - Binaries and tools are identical across K, K₂ and K₃; only `tests/` changed.
  - D′₁ = 3e2480a is the data-only commit on K₃ with the refreshed symmetry model. 47ed466 adds the symmetry Stage-6
    evidence and the HD6 mirror (149 → 156 seeds); `verify_delivery.py --strict` passed there.
  - D′₂ (Expanse's model and evidence) follows when Expanse's backlog clears.
- **Fix round 2** (after the second inspection) changes code after 47ed466. It is tested on the Mac with negative
  controls, not reviewed by Codex (user decision), and its cluster chain is still to run ("Pending" below).

**Symmetry** (AMD jobs on EPYC 7543 under the CPU pin; the drills on Intel Gold 6148 `debugq`):

| Item | Jobs (node) | Verdict | Evidence |
|---|---|---|---|
| Bitwise rows proof, S1-04/S1-05 (`opt` final: l8self, thread_identity, inspect_check, speed) | 570658 (<NODE>), on K | **pass**: the new `c8d3_gmp` `e9b6f6c3…` gives G-L8SELF rows equal to the Stage-3 binary `3a9a556b…` for both backends on 1,600 free + 400 power L8 graphs; B0 → CAND ×1.389 (Stage 5's binary ×1.366); inspect_check refuses 9 malformed or empty index cases | `stage6_95f6eaf/opt_final/` |
| val1 | 570662 on K; 570678 on K₂; 570736 (<NODE>) on K₃ | **pass** on K₃: 38 PASS, 19 SITE_REFUSED, 0 FAIL. On K, `uo_seed_reservations` failed behind a timeout assertion that hid the plans' stderr (fixed in 98cb772). On K₂ the cause showed: `slurm/common.sh` sourced the real `~/c8d3/env.sh` over the test's environment, and the plans refused at the seed-log check before writing anything (fixed in acd3b39: `tests/c8pkg.CLEAN_ENV` scrubs `C8_ENV_SETUP` and `C8_SEEDS`). **Disclosed:** prefix_check, uo_allocation and uo_selection_files moved from PASS to SITE_REFUSED, so their real-cluster execution is lost (they pass on the Mac) | `stage6_95f6eaf/val1/`, `stage6_ca7d482/val1/`, `stage6_0dde6ad/val1/` |
| Calibration refresh (sweep2) | 570664 (<NODE>), on K | **pass**: model `554bb1d6…`, executable `e9b6f6c3…`, prior_model at F = 2 from `0fc934e7…`, 48,346 keys, `mp_check` on; the seed was reserved before the sweep ran | `stage6_95f6eaf/sweep2_570664/` |
| J-BLD on D′₁ | 570738 (<NODE>) | **pass** in every step, `data_only_diff` and `model_identity` included | `stage6_3e2480a/bld_570738/` |
| Plans on D′₁ | 570742, 570744 | **pass**: DL (vendor drill), DA (array drill), PA (pilot re-plan) and DL2 (lanes drill) published, each seed reserved exclusively in the log (S2-002); `cost_identity` rc 0 | `stage6_3e2480a/plans/`, `job_logs/` |
| S2-001 vendor pin | DL: 570746, 570747 (Intel), 570749 (AMD `amddebugq`, <NODE>) | **pass**: the first work admission wrote `cpu_vendor.json` (intel); an AMD `lanes 1 --dry-run` with DL idle was refused 64, naming the pin; `lane_worker.sh` with `C8_RUN=DL` on <NODE> exited 68 at `c8_vendor_guard`, before any scratch or claim | `stage6_3e2480a/vendor/` |
| F7 stop signals (A-ORC-8a) | DL2: 570751 (<NODE>), scancelled at 27 s | **pass**: "SIGTERM forwarded to 1 lane(s); waiting at most 25 s"; index 57 stopped by signal 15 (run exit 143), claim left for release-stale; "scratch removed"; lane exit codes [143]; no failure record; the next admission released the stale claim. This drilled fix round 1's stop path; S2-R2-005 (round 2) changes its waits, which the Mac tests cover | `stage6_3e2480a/f7/`, `campaigns/drl-lanes2-s6-20261006/slurm_logs/lane-570751.log` |
| J-DRL-5, F8-d3 in array mode | DA: window 570794, re-merge 570796 | **pass**: "a_free_L3: replaced the uncommitted graph_costs.csv (no merged.json; …; timing only)"; result "superseded: scientific content unchanged", the previous one kept as `C8_test_result.superseded.6864151c740d.json`; status 0; scientific rows and batches equal the saved ones; `verify_result` 0. Stage 5 failed exactly here ("Checksum mismatch: graph_costs.csv") | `stage6_3e2480a/drl5/` |
| J-DRL-8, F8-d3 in lanes mode (A-ORC-4 (i) real) | DL2: worker 570814, re-merge 570815 (<NODE>) | **pass**: index 0's checkpoint and a_free_L3's `merged.json` deleted; `lanes 1` removed the done marker of index 0 ("queue rebuild: checkpoint blocks missing"); the re-merge replaced the uncommitted `graph_costs.csv` (timing only) and superseded the result (previous kept as `…superseded.d7a941c58fff.json`); status 0; scientific rows equal; batches equal in all 24 groups; `verify_result` 0; no SQLite side files | `stage6_3e2480a/drl8/` |
| J-PIL-0 (PA re-plan on D′₁) | 570742; dry runs on the login node | **plan pass**: PA `pilot_subset`, `stage_a` selection of 2,737 graphs, measured basis, 30.7 busy core-h, `cost_identity` 0. `lanes 2/3 --dry-run` printed the auto lane time 0:45, the reservation, 30.7 core-h and the merge path subset-check, then refused 65 at H7/H11 (the H11 limitation below) | `stage6_3e2480a/pil0/` |
| Rename probe (S2-005) | 570666 (<NODE>) | BeeGFS: `recheck_rename` (no `RENAME_NOREPLACE`); `/tmp`: `noreplace`; non-empty and empty targets refused (errno 17) on both | `stage6_95f6eaf/rename/probe.json` |

**Expanse** (EPYC 7742):

| Item | Job | State |
|---|---|---|
| Rename probe | 54709529 | Lustre: `recheck_rename`; `/tmp`: `noreplace`; non-empty and empty targets refused (evidence in D′₂) |
| Bitwise proof (+ forced_tiers against Stage 3) | 54709473 | pending (backlog; estimated start 2026-10-07 07:11 PDT) |
| val1 on K₃ | 54710114 | pending (shared backlog) |
| sweep2 | 54709504 TIMEOUT (a 45-min Lustre export copy), then 54710244 at 3:00 | pending (estimated start 2026-10-08) |

**Re-derived on the Mac, not rerun.** A-ORC-13 and A-PERF-3 come from J-SMK-4's committed records (F13-d3, S4-007;
round 2: S4-R2-001, S4-R2-002): `stage5_59d4922/smk4/thru_report_s6b.json`. A-ORC-13 **PASS** (non-own medians
30,046,840 and 31,734,238 bytes). A-PERF-3 **SHORTFALL**: three blocks of 5.5–63 ms below 0.95, no block untimed.
Per-launch overhead and end-of-block imbalance are possible causes, not measured. The 8-lane configuration is capacity;
the other lanes' activity at those moments is not recorded ("Stage 5 results", S4-007).

**Rename probes.** On both shared filesystems, BeeGFS (symmetry) and Lustre (Expanse), `common.rename_noreplace`
takes the `recheck_rename` fallback, because neither supports `RENAME_NOREPLACE`. Node-local `/tmp` takes `noreplace`.
The fallback refuses a target that exists when it checks, empty or not. Its check-to-rename window stays open
(S2-R2-006, a residual the user accepted): a second planner of the same campaign directory inside that window is
outside the operating procedure.

**H11 limitation and its fix** (found in J-PIL-0; fixed in fix round 2 after the user's decision of 2026-10-06, "Raise the
cap, use my 3").
- Found: `slurm_submit.Reservation` capped every symmetry re-split at `amd_total ≤ 8` (`SYM_AMD_TOTAL_MAX`), the H11
  pilot-window rule (DECISIONS:94). It could not express C62d's agreed 9/3 = 12 production window (DECISIONS:98), so every
  C63d AMD admission was refused (65) while that window was open: conservative, never an over-admission.
- Fixed: a re-split that carries `;until=<UTC>` (an agreed DECISIONS window) may reach `SYM_AMD_WINDOW_MAX` = 12. The
  base split (`id=H7;amd_nodes=4;amd_total=8`, no `until`) stays at 8; an undated 12 or any 13 is malformed (64).
  After `until`, `amd_total_now` falls back to 8, as before.
- For the production window: `C8_RESERVATION="mode=reservation;id=<the DECISIONS item>;amd_nodes=3;amd_total=12;until=<UTC>"`.
  The `until` value is the agreed end, refreshed if C62d extends the window.
- Tests: `tests/test_submit.py` `test_sym_admission` covers 3 of C63d's admitted beside c8d2's 9, a fourth refused (65),
  an expired window (65), and the undated-12 and 13 cases malformed (64).

**G5 after Stage 6.** G5 holds except:
- **A-PERF-3 / A-SMK-4**: per-block SHORTFALL, reported with its cause (above and "Stage 5 results", S4-007);
- **A-ORC-4 (i)**: fixed by F8-d3 and passed in J-DRL-5 and J-DRL-8 on real Slurm (above);
- **A-ORC-13**: PASS on re-derivation.

The Stage-5 verdicts are kept as historical records. The table is `LRI_C8_D3_HPC_loop/artifacts/G5_TABLE.md`
("Stage 6 update").

**Inspection and accepted residuals.**
- Round 1: all four scopes REVISE, 33 findings. Fix round 1 (groups A, B and C, F8-d3, F13-d3, the CPU pin) is the
  code revalidated above.
- Round 2 (final): all four scopes REVISE, 23 findings (`LRI_C8_D3_HPC_loop/artifacts/inspect_r2_findings.md`).
- The user decided on a targeted fix with no third Codex round. Fix round 2 covers S3-R2-007, S3-R2-009, S3-R2-001,
  S2-R2-005, S3-R2-003, S4-R2-001, S3-R2-002, S3-R2-004/005, S3-R2-006, S4-R2-002, S4-R2-003 and S1-R2-01/02/05, plus
  S1-R2-03's duplicate-ID refusal.
- **Residuals the user accepted:**
  - concurrency races outside the operating procedure:
    - S2-R2-002: each site's seed reservation locks only its own log;
    - S2-R2-003: overlapping merges of one campaign;
    - S2-R2-004 = S3-R2-008: two concurrent supersedes of one result;
    - S2-R2-006: the `recheck_rename` window;
  - defense in depth behind working guards:
    - S2-R2-001: the merge's vendor check covers only the groups it merges, behind the admission pin and the job-side
      vendor guard;
    - S1-R2-04: the HANDOFF take-aside, a one-time handoff already done;
  - S1-R2-03 beyond uniqueness: the identity of the L3–L6 rows against C7's reference inventory.

**Fix round 2 and its cluster chain (2026-10-07).** The code is final at **K₆ a914db2**. Fix round 2 is K₅ ad983e8,
plus two site-aware test fixes. The data commits are D′₂ 451bc09 (the symmetry model) and D′₃ (the Expanse model).
Everything after K₆ is data-only, grep-checked.
- **Symmetry**, admitted under the production-window re-split (C63d 3, both sessions 12):
  - **val1:** PASS on K₆ (570902; 38 PASS, 19 SITE_REFUSED, 0 FAIL). The run on K₅ (570893) showed check_inputs and
    cost_refresh_test refused on the real host: their new fake-site cases. K₆ made both tests site-aware.
  - **val2:** PASS on K₆ (570904; validate_full, class_b, inspect_check, check_points, forced_tiers_smoke,
    check_inputs, workflow, staging, compat_run1).
  - **val3:** PASS on K₅ (570897; assembly_checks, forced_tiers, merge_scale, prefix_check_real, thread_identity,
    validate_bk8_l2). This meets PLAN:3932 for round 1's `src/` change.
  - **sweep2 570900 on K₅:** measured basis, the same executable e9b6f6c3. The model is `01b67d0a…`.
  - **J-BLD 570906 on D′₂:** PASS.
  - **Plans 570908:** DL3 (103 jobs) and PA2 `pilotA2-s6-20261007` (pilot_subset, 2,737 graphs, 30.7 core-h).
  - **J-PIL-0:** `lanes 1/2 --dry-run` rc 0 (auto lane time 1:15 and 0:45; merge path subset-check). `lanes 3` gives
    65: 4 nodes > C63d's 3.
  - **F7 drill on the new stop path** (DL3, 570910 scancelled at 16 s with 5 claims): "waiting at most 25 s in all
    (lanes still running killed at 20.9 s, reaped until 22 s, then 3 s for cleanup)". Every lane: exit 143, claim left
    stale, scratch removed. The next `lanes 2` released all 5 stale claims and finished DL3 (verify_result 0).
- **Expanse** (EPYC 7742):
  - **Bitwise proof 54709473: PASS** (l8self exact against the Stage-3 binary; forced_tiers and forced_tiers_vs_stage3;
    inspect_check). Candidate `61d291eb…`, ×1.714 against Stage 3 (G4b ×1.718), rows_identical.
  - **val1 on K₆ 54712716: PASS** (38 PASS, 19 SITE_REFUSED, 0 FAIL).
    - The earlier val1 on K₃ (54710114, <NODE>) hit two corrupted node-local copies from Lustre: a reference
      input without its final newline, and a staged executable whose hash differed. Both were caught fail-closed.
    - The originals are intact, and the rerun on <NODE> is clean. This is a platform I/O fault, not a package
      defect.
  - **sweep2 54712666 on K₅: PASS.** prior_model F = 2 from Stage 5's `56df9d61…`. The model is `d92ebbfc…`
    (executable 61d291eb).
  - **J-BLD-exp 54716341 on D′₃ d3bc5a9: PASS**, every step, base K₆. The data-only diff took 711 s on the degraded
    Lustre. The first attempt, 54714801, hit its 0:40 wall inside that step before any build.
- **Seeds:** both logs and the HD6 mirror hold 164 seeds.

**G6 (2026-10-07):** closed on the user's acceptance of the residuals above, after the second and final inspection round. No item of Stage 6 is pending. Stage 7 (the pilot) needs the user's pilot line, its site and an H11 window.

## Production (user decisions 2026-10-08)

The user approved C8(3) production at target SE 1 (0.06% of |C8| ≈ 1619) with a 20,000 core-h production line on
symmetry, the conservative tail rule for the heavy-tailed graphs ("produce with the plan's conservative rule"), and the
H11 production window `H11-prod-c63d-20261008` (C63d 9 AMD-pool nodes, C62d 3, until 2026-10-10T12:00:00Z;
DECISIONS.md line 102). The step-by-step procedure is `docs/PRODUCTION_RUNBOOK.md`.

- **The production line** (`tools/budget.py`, `tools/slurm_submit.py`). `C8_BUDGET_LINE=production` with the required
  `C8_PRODUCTION_SU_CAP` (the approved line in the site's unit: 20000 core-h on symmetry), mirroring the pilot line:
  every role becomes `prod_<role>` (`prod_lane`, `prod_merge`, `prod_plan`, ...); the name classifies the job; the gate
  refuses (65) above the cap, with the other site's `production=` carry, and (64) without a cap; `budget.py` prints a
  `production` row and puts `production=<own>` in its carry; intents, `submit` records, `ledger.py rebuild --hold-line
  production`, `accounting.py` (`prod_lane` is a work role) and `production.py`'s queue parser (`recover`, `resubmit`)
  know the line. The dev line's 2,500 per-site sub-cap and the pilot line are untouched by production jobs.
- **The conservative tail rule** (`tools/design_fallback.py freeze|report --pc PC`, RECON:1373). For every
  graph-campaign of the pilot's PC campaign, the allocation sigma is max(PF's 3%-floored sigma at 4,096 points, PC's
  sqrt(32768 Var_rep(J_8 . jets)) at 32,768 points), both from the campaigns' merged full-stream replicates with one
  function (`sigma_hat`) and J_8 at PF's means. PC is bound to PF before anything is computed: a pilot_subset campaign
  of a `confirm` selection whose screen names PF's identity (manifest, role, selection and every group's scientific
  identity, `pilot_report.bound`), with PF's inputs manifest, executable, backend, numerics, MP mode and test_only flag;
  a PC of another pilot is refused (1). `design.json` gains `conservative_tail_rule` (the rule, PC's identity, every
  raised graph-campaign with both sigmas and the factor, the unchanged ones, and `monitored`: the graphs PC confirmed,
  `pilot_report.confirm_graph`); `design_meta.json` gains `pc` (PC's identity and the PF identity it is bound to) and
  `monitored_graphs`. Neither `production.py` nor the merge (`assemble.tail_monitor`) takes a list of graphs, so the
  bundle, which the production manifest names (`design.bundle`, `design.meta_sha256`), carries the monitored list for
  the results review; the production merge's tail monitor lists and flags graphs from the production data as before.
  Without `--pc` the bundle and the report are byte for byte as before.
- **The real pilot's binding** (Mac check 2026-10-08): `benchmarks/symmetry_2026-10-c8/pilot/evidence/pc.json` (sha256
  `f9f72144…`, PC's manifest selection) names PF `pilotF-s6-20261007`'s identity as recomputed from the copied
  manifest and merged.json files (manifest `862321a1ad39…`): `freeze --pc` will bind them.
- **Tool hashes.** `slurm_submit.py` and `production.py` are pinned tools: plans made before this change keep their
  pins; their merges and assembles need `--accept-tool-change` (recorded), and the production campaign is planned on
  the new export.

## Margin re-derivation (`tools/margin_probe8.py`; user decision 2026-10-08)

The C8(3) pilot reported 441 of the 710 checked L8 graphs as "possible infinite variance" (two-campaign mean
ξ̂(32,768) > 0.44; `benchmarks/symmetry_2026-10-c8/pilot/evidence/pilot_report.json`), and both sectors are on the
pre-registered 3% hold (action 3: free 3.9% of the projected variance and 12.9% of the cost, power 6.3% and 12.5%).

The user's decision (2026-10-08) has two parts:
- Production starts with a conservative allocation.
- In parallel, the margin re-derivation (RECON "Margin re-derivation" (a)–(e)) runs on the worst flagged graphs. A
  real deficit would lead to a lower proposal rate for those graphs. That is a pre-registered change, and the user must
  approve it (D1).

`tools/margin_probe8.py` only reads the inputs. It never plans, submits or changes a production value. Its module text
has the full method; the essentials follow.

**Subcommands.**
- `select`: picks graphs from the pilot report.
  - Per sector, it takes the PC-confirmed graphs ranked by variance share, the top 12 (`--top`), plus 2 light controls
    (`--controls`). `--class-reps K` adds the K best-ranked members of each action-3b double-lift class.
  - The share is action 3's σ̂√c over the sector sum. It uses PF's σ̂ from `sigma_cost.csv`, raised by √V_ratio where
    action 3 used the 32,768-point estimate (`action3_hold.sigma_from_32768`).
  - That is the closest reconstruction from the committed files: sector totals 3.8% / 7.0% against the recorded 3.9% /
    6.3%. `--rank-by share_pf` uses PF's σ̂ alone.
  - It writes a selection JSON in which each graph has its reason, share, ξ̂_a / ξ̂_b, M, T, double-lift count and
    clamped count (from the rate audit).
- `probe`: runs RECON (a)–(d) per graph, in parallel over `--workers` processes. It reads the members through
  `tools/members.py`, so the inventory and member sha256s and `MEMBERS_d3.sha256` are checked. It writes one JSON per
  graph and `probe_run.json`. Results are never overwritten; `--skip-existing` resumes.
- `report`: a markdown summary of one or more probe directories.
- `estimate`: core-hours per selected graph, fitted on earlier runs.

**The probe.**
- (a) It recomputes the rate line from masks and terms (margin_probe [M1]) and compares it with the payload at every
  subset. It also compares the raw line with `prepare_inputs.raw_valuations` and the double-lift count with the
  inventory.
- (b) At every clamped subset, it measures the single-scale exponent of the forest sum against α, 0.8α and 0.7α.
- (c) Two-scale flags and chains of ≥ 3 scales around the anchors, at margin_probe's scales:
  - The anchors are the double-lift subsets, plus 4 "tight" clamped subsets (`--tight-anchors`, the smallest margin
    e − 0.8α). The tight anchors stand in for the flags the argmax points approach, which are not available yet;
    `--anchors` adds any.
  - The budgets are 40,000 unique flags (`--max-flags`) and 20,000 chains (`--max-chains`) per graph. A larger
    population is sampled uniformly, with a registered seed, and the JSON says so.
- The depth ladder. Every level is measured twice:
  - at margin_probe's scales ("shallow");
  - towards its asymptotic exponent: its scale pushed 40 and 80 decades deeper (160 when those differ) at fixed other
    scales (`--depth`).
  - Why: on graph 228, a chain level reads 0.689 at margin_probe's chain scales but 1.000 from 10⁻¹² on. Another level
    reads 1.5 down to 10⁻³⁰ and 1.0 below 10⁻⁴⁶.
  - The tail index depends on the asymptotic exponent: the smallest power of t_k as t_k → 0 at fixed other scales.
    Deficits are judged on it.
  - A level below its proposal rate only at the shallow scales is a "dip": a peaked, sub-asymptotic weight. Dips are
    counted and listed apart.
- (d) The cross-campaign shift: ξ̂_b against the face model 1 − (8/7)(1 − ξ̂_a) and against ξ̂_b = ξ̂_a.
- (e) The verdict is either "deficit at <flag> (level exponent m < proposal rate r; a = r/(r − m))" (worst a first;
  infinite variance when r ≥ 2m) or "no deficit found within the probed flags (finite-variance, peaked)".
- Arithmetic.
  - Every probe point is a power-of-ten scaling of an integer base point (margin_probe's), so the monomials, U_T, N_T
    and S are exact integers.
  - Σ_T N_T U_T^(−3/2) is computed in fixed point with integer square roots and a rigorous error bound, growing until
    60 bits are correct. margin_probe's fixed 80 digits cancel to exactly zero at some deep points.
  - An mpmath cross-check (margin_probe's Kern.f, at adaptive digits) is recorded per graph.

**Validation on the Mac (2026-10-08).** The C8 L7 packs hold margin_probe's graphs byte for byte: all 590 C7(3)
power-L7 members are identical. With margin_probe's anchors (`--tight-anchors 0`), every recorded number is reproduced
(cd3:margin_probe:18-28):

| graph | clamped | min / max (e − α) | equal | below 0.8α | double-lift exponents | two-scale flags | chains |
|---|---|---|---|---|---|---|---|
| 228 | 399 | −0.000 / +2.004 | 32 | 0 | 0.500, 1.500, 1.500, 1.500 | 1,984, min margin +0.050 | 4,620 in the 6-edge subset, +0.050 |
| 1357 | 399 | −0.000 / +2.008 | 32 | 0 | the same | (new) 1,984, +0.050 | (new) 4,620, +0.050 |
| 318 | 399 | −0.000 / +2.012 | 32 | 0 | the same | (new) 1,984, +0.050 | (new) 4,620, +0.050 |
| 3754 | 261 | −0.000 / +2.000 | 35 | 0 | 0.500, 1.500 | 632, +0.050 | (new) 4,620, +0.050 |
| 328 (control) | 191 | −0.000 / +4.000 | 19 | 0 | none | | |
| 3507 (control) | 191 | −0.000 / +3.000 | 22 | 0 | none | | |

Beyond margin_probe's record, with the same anchors:
- (c) on 1357 and 318 (RECON's "next step").
- Chains in the 8- and 10-edge double-lift subsets of 228, 1357 and 318: 5,126–5,127 sampled from populations of
  545,580 and 102,246,540.
- No level is below its proposal rate at its asymptotic exponent. The smallest margin is +0.050 everywhere.
- At margin_probe's chain scales, 2, 1 and 3 of those levels dip below 0.8α: 0.675–0.708 at rate-1 faces, all 1.000
  asymptotically. These are sub-asymptotic dips.

Other Mac runs:
- **The six graphs, default anchors** (4 tight anchors added): 8,141–12,915 two-scale flags and 20,000 chains each. No
  deficit; smallest margin +0.050.
- **mpmath cross-check:** it agrees to ≤ 1.3e-12 in ln f, at 172–534 digits.
- **(d) on run1's ξ_sd:** mean ξ_b − ξ_a over the six = −0.003 ± 0.007, against −0.079 for the face model. That is no
  rate dependence, as RECON found.
- **Two real L8 kernels** of `inputs_mini`, power 12211 and 12233: 1,681 clamped subsets each, 38 double-lift subsets
  (two at raw −9: three units of cancellation).
  - No deficit: 40,000 of 78,220 two-scale flags and 20,000 chains each, smallest margin +0.050.
  - Their double-lift exponents, 0.5–2.5, are at or above their rates.
  - 310 cpu-s each.
- **Power L7 2034** (T 96, no double-lift subset; default anchors, reduced budgets): 55 shallow dips (shallow margin down
  to −0.61), asymptotic margin +0.050.
- **Free L7 2878** (T 116): 1 dip, asymptotic margin +0.150.

**Tests.** `tests/margin_probe8_test.py` (in `make test-python`; about 6 s on the Mac) covers:
- the rate recomputation on 49 real L3–L6 members;
- the integer engine against margin_probe's mpmath f;
- synthetic forests with analytic exponents (3/4; 3/4 and 3/2; 3/4 → 7/4 after a subtraction; 1/4 on a clamped
  face), with a no-deficit verdict and a deficit verdict (a = 2.67 in campaign a, 3.5 in campaign b);
- chain enumeration and sampling;
- `select` on the committed pilot report;
- `probe` end to end, including a planted deficit.

**Cost.** Measured on the Mac (Apple arm, gmpy2, one process per core). The cpu-seconds per evaluation are fitted by
`estimate` on 16 calibration phases with T 16–116:

| phase | cpu-s per evaluation |
|---|---|
| single scale | 5.6e-5 + 5.4e-6 T |
| two-scale | 5.2e-5 + 6.0e-6 T |
| chains | 1.8e-5 T (more for large anchors) |

There are about 6 evaluations per level (the ladder). M enters only the per-flag preparation, 2–3% of the cost.

Per L8 graph at the default budgets (40,000 flags and 20,000 chains, an upper bound):
- free top graphs (T 128–176): 0.55–0.80 core-h;
- power top graphs (T 64–160): 0.25–0.72 core-h;
- double-lift class representatives: 0.04–0.15 core-h;
- controls: ≤ 0.04 core-h.

Totals at the Mac's speed: 13.3 core-h for the default selection (28 graphs), 14.0 core-h with `--class-reps 1` (34
graphs).

On symmetry's EPYC 7543, assume 1.5× that per core (not measured). Without gmpy2 it is a further 1.8× (measured:
identical results, 1.82× slower; the job records whether gmpy2 is present). That makes 21–38 core-h of work, 0.4–0.7 h
on one 64-core node.

**Suggested run:** the 34 graphs of `select --class-reps 1` on one `amdq` node, `-c 64`, `-t 02:00:00` (128 core-h
reserved). The run is resumable.

**The job (symmetry).** `tools/margin_probe8_job.sh` is a raw job on one whole `amdq` node. It:
- passes the CPU pin;
- extracts the members to `/local1`;
- uses the export's L8 packs when J-BLD linked them, else a work copy of the inputs with the store's packs linked in;
- runs `select` (unless the selection exists), `probe --skip-existing` over the 64 cores, and `report`, then writes the
  sha256 sums.

```bash
source ~/c8d3/env.sh; export C8_PACKAGE=$C8_ROOT/pkg/<sha12 of the export with this tool>; cd "$C8_PACKAGE"
export C8_OTHER_SITE_SU='<the carry line of Expanse budget.py, < 24 h old>'
E=$C8_ROOT/evidence/<sha12>/margin
# optional before the job: copy a Mac-made selection to $E/selection.json; else the job makes it from the committed
# pilot report (add C8_MARGIN_SELECT_ARGS="--class-reps 1" for the double-lift class representatives)
C8_MARGIN_EV=$E C8_MARGIN_SELECT_ARGS="--class-reps 1" python3 -B $C8_PACKAGE/tools/slurm_submit.py raw --role margin \
    --dir $E -- -p amdq --nodes=1 --ntasks=1 -c 64 --mem=240G -t 02:00:00 -o $C8_ROOT/logs/%x_%j.out \
    $C8_PACKAGE/tools/margin_probe8_job.sh
```

- Variables:
  - `C8_MARGIN_EV` (required; the `--dir`);
  - `C8_MARGIN_SELECTION` (a selection file elsewhere);
  - `C8_MARGIN_SELECT_ARGS`;
  - `C8_MARGIN_ARGS` (extra probe options, e.g. larger budgets).
- The job takes one H7 AMD-pool slot (`C8_RESERVATION`) for its wall time. Under `C8_BUDGET_LINE=pilot` the role
  becomes `pilot_margin`.
- A timed-out job is resubmitted with the same command into the same `$E`: finished graphs are kept. A graph's JSON is
  written only when its graph is complete, so one interrupted graph costs one graph's time.
- Outputs in `$E`:
  - `selection.json`;
  - `probe/<sector>_L8_G<id>.json`, one per graph: (a)–(d), the verdict, every clamped subset's shallow and asymptotic
    exponents, the worst levels and dips, the plan with its population counts and samples, the mpmath check and the
    cost;
  - `probe/probe_run.json`;
  - `MARGIN_REPORT_<job>.md` and `margin_report_<job>.json`;
  - `environment_<job>.txt`, the logs, and `SHA256SUMS_<job>`.
- Copy `$E` to `benchmarks/symmetry_2026-10-c8/margin_<sha12>/` for the evidence commit. Report the verdicts to the
  user before the results review; a deficit goes to the user (D1) with its flag, m, r and a.

**On the Mac** (small runs only; the cluster runs the L8 graphs, whose packs are not on the Mac):

```bash
python3 -B tools/margin_probe8.py select --out SEL.json [--class-reps 1]
python3 -B tools/margin_probe8.py probe --graphs power:7:228,power:7:3754 --out DIR --tight-anchors 0 --workers 8
python3 -B tools/margin_probe8.py report DIR --out DIR/SUMMARY.md
python3 -B tools/margin_probe8.py estimate --selection SEL.json --calibration DIR [DIR ...] --speed 1.5 --cores 64
```

**Limits.**
- The flags the pilot's argmax points approach (RECON (c)) are not available: action3b's `argmax_points` says
  "regenerate with bin/c8d3_inspect --point". The tight anchors stand in for them, and `--anchors` takes them once they
  exist.
- The probe is one generic base point per graph, as in margin_probe.
- The budgets sample large populations (8- to 16-edge anchors), so "no deficit" means none at the probed flags. The
  JSON records which populations were sampled and how.
- **What a deficit would mean [I].**
  - At fixed other scales, a level's asymptotic exponent is the smallest power of t_k in the forest sum's expansion. Its
    coefficient is generically non-zero at any fixed values of the other scales.
  - So the exponent is the single-scale exponent of the level's set at another generic point, hence at least the set's
    table rate by the single-scale bound (RECON (b)).
  - Every asymptotic level measured so far agrees: the smallest margin is +0.050, at the α = 1/4 faces.
  - A deficit would therefore point at the payload, the bound's assumptions or the precision, and the probe locates it.
- **What the pilot's ξ̂ more likely reflects.** The pilot's ξ̂ is above 0.5, and up to 1.8 in the power sector, where
  a = r/(r − m) > 1 cannot give ξ ≥ 1 for any m > 0. That points to the shallow dips: peaked, sub-asymptotic weights
  (RECON open item (2)). The report counts and lists them.

## Added by later stages (stubs)

- **Stage 3, campaign entry points: done in Stage 3a** (see "Campaigns" above). `c7_legacy/` is deleted.
- **Lanes.** Lane shapes (`C8_LANES=numa|numa:<k>|<n>`), memory and the memory guard, done markers, and held jobs
  (`launch failed requeued held`: released once, then cancelled and resubmitted).
- **Files.** User and group quotas and the Lustre file guards: `C8_FILE_BUDGET`, `C8_PARTNER_FILE_RESERVE`, and
  EDQUOT failing closed.
- **Operations.** Drills J-DRL-1..9 and their outcomes: done in Stage 5 ("Stage 5 results" above; procedures in
  `LRI_C8_D3_HPC_loop/artifacts/STAGE5_SYMMETRY_RUNBOOK.md`). Still to come: J-DRL-10 (with its evidence and the
  user-decision close), start-latency escalation (4 h on `debug`/`shared`, 12 h on `compute`), and the G0
  reconciliation against `expanse-client user -p`. The pilot's procedure is in `docs/PILOT_RUNBOOK.md`.
- **Records and access.** The seed log (`$C8_SEEDS`) and ssh ControlMaster/MFA. The HD6 mirror is done:
  `designs/forbidden_seeds.json` is a byte copy of `$C8_SEEDS`, refreshed in a data-only commit at each evidence commit
  (then `verify_delivery.py --write`) with `tools/seeds.py mirror --log COPY`, where COPY is the evidence's byte copy
  (`repair3b` copies the log) or `ssh expanse 'source ~/c8d3/env.sh; cat $C8_SEEDS'`; `mirror` refuses a copy that
  drops or changes an entry of the committed mirror (the log is append-only) and prints both sha256s. Test runs with
  the real workers register every seed they use: base, native and net seeds, and the `random.Random` seeds that draw
  kernels or generate inputs. `tests/fixtures/stage3a_test_seeds.json` lists the net seeds of each `nc.net` call site
  of the real-worker tests (with the values the Stage-3a runs bound to its names), and `unit_orchestration`
  `seeds_and_nets` fails when a call site is added or changed without an entry, or when a listed seed is missing from
  the mirror. Fake-worker test plans (`tests/c8pkg.py`, `C8_SITE=fake`) sample no integrand and are not registered.
- **Pilot tools (Stage 3a repair round 3).** `tools/pilot_report.py` and `tools/pilot_select.py` accept the exact
  command lines of PLAN "Pilot (Stage 7)": `stage-a RUN --output FILE`, `confirm --screen <PF run> --pa <PA run>
  --seed S --out FILE` (the screen is computed inside; PF's own measured model gives the PC costs) and `full ...
  --output FILE --markdown FILE` (`pilot_report.json`, `PILOT_REPORT.md`, `growth_c63d.csv`, `sigma_cost.csv`); the
  older spellings (`--out`, `confirm --screen SCREEN.json --pf PF --cost-model M`, `full --out DIR`) stay as aliases.
  `tests/fixtures/runbook_stage7_pilot_tools.txt` is a verbatim copy of those runbook lines, and `test_pipeline` runs
  them. `stage-a` gives GO only with no `mp_alarm`, no worker failure and every pre-registered branch's peak
  reservation (PF at R = 8, PF with R = 16 at L8, action 4's mixed R, each followed by PC at its cap) inside the pilot
  line, re-projected from PA's measured f_E, eta and per-graph cost; otherwise NO-GO with the reasons (the pilot stops
  and the user is asked). The line is `C8_PILOT_SU_CAP` (or `--line-cap`) with its committed SU from `budget.py` (or
  `--spent`); eta comes from `accounting.py` (or `--eta-node` for test pilots). Zero-channel L8 graphs (s_G = 4) are
  reported as "zero-channel heavy tail, not confirmed" and take part in no action, PC selection or C8-variance
  statistic.
- **Seed log after Stage 3a.** `$C8_SEEDS` (and its mirror) holds, besides the G-RUN1 seed 20261004, the A-IN-6 L=2
  control's base, native and net seeds (6602215; 6602267, 6602275; 220052, 220060) and the base and native seeds of
  the Stage-3a test runs with the real workers (validate.py 7738251 and 741987, class_b.py 6619043-6619045,
  forced_tiers.py 4401, sanitize.py 4242 and 1, inspect_check.py 1, workflow.py 7611826, staging.py 816615 and
  816616), registered with `seeds.py add --seed S --label ...` on the login node.
- **Symmetry.** Done by Amendment A1: section "Symmetry (Amendment A1)" above.

# C7(3) runbook (inherited from LRI_C7_D3_HPC@a6ce987; symmetry; not revalidated for C8(3))

The C7(3) wrappers and entry points this runbook names (`slurm/submit.sh`, `slurm/resubmit.sh`, `tools/c7_submit.py`
and the campaign lock `.c7_submit.lock`) were quarantined in `c7_legacy/` in Stage 0 and deleted in Stage 3a; the C8(3)
entry points are in "Campaigns" above. This part is kept as the record of the C7(3) design.

## Execution model

- **Strata.** A scientific stratum is (campaign, sector, loop, graph, replicate).
  - Its full power-of-two Sobol net may be split into arbitrary non-overlapping sample intervals for execution.
  - The scheduler assigns intervals, not new replicates.
  - The scientific stream is independent of node, lane, shard, thread and checkpoint boundaries.
- **Groups and jobs.** Twenty groups cover two campaigns × two sectors × loops 3–7 (`--max-loop 5|6` plans fewer
  loops, for tests).
  - A *job index* is one shard of one group.
  - A shard runs as consecutive checkpoint blocks of at most `checkpoint_tasks` tasks.
  - Each block is one native call with OpenMP inside.
  - There is no MPI, no shared mutable counter and no central server in the hot path.
- **Planning.** The planner uses disk-backed SQLite.
  - Shard counts follow estimated seconds: `--shards N` goes to the most expensive group and the others scale down
    (`--shard-policy uniform` keeps N everywhere).
  - Tasks are assigned longest first to the lightest shard.
  - Inside a shard, tasks have a frozen position (estimated cost descending). So a block holds similar tasks and the
    per-block barrier idles few cores.
- **Integrity.**
  - Every native call runs from a **job-private runtime**: a copy of the executable, the gamma table and the group's
    Sobol net, each verified against the plan, plus the block's graph members staged from the kernel pack with
    their member hashes.
  - Each checkpoint records the digests of those copies and the node and CPU model.
  - Merge and restart reject a checkpoint from any other executable, input set or net.

## Build and environment

- **Toolchain.** On symmetry: system GCC 11.4, `module load boost/1.77.0` (headers only; Boost ≥ 1.86 does not
  compile `src/kernel.hpp`, and `make` refuses it), system GMP 6.2.1, Python ≥ 3.10 with `requirements.txt`. Copy
  `slurm/symmetry_env.sh.example`, adapt the venv path, and export `C7_ENV_SETUP` to it. Every job script sources it
  before `set -u`.
- **Where to build.** Build on the target node type: `make clean && make && make decimal`. Then run `make test`
  (and `make test-full`, `make test-replay`).
- **Toolchain identity.** The default command line equals the delivered one, so on the same toolchain the binaries
  are byte-identical to the delivered build. On symmetry that build is gmp `635428f9…`, decimal `24b2b941…`.
- **Never rebuild inside a campaign.** The plan freezes the executable's hash, and each job verifies its private
  copy. A new executable needs a new plan.
- **Mixed CPU types.** Symmetry's exclusive partitions mix AMD EPYC 7532, 7543 and 8534P (cn112) and Intel Gold 6148 nodes.
  Results are not bit-reproducible across CPU types (AMD EPYC 7532 vs Intel Gold 6148: last-bit
  differences ≤ 2e-11 normalized, identical promotion counts; `docs/NUMERICS.md`). Mixing node types is
  statistically harmless, and every checkpoint records its CPU. For a bitwise rerun, use the same CPU type.

## Plan

```bash
export C7_PACKAGE=/path/to/LRI_C7_D3_HPC C7_RUN=<SCRATCH>/c7-d3/run2
python3 "$C7_PACKAGE/tools/production.py" plan "$C7_RUN" --seed <fresh 63-bit integer> --multiplier 4096 --replicates 64
```

- **Defaults.**
  - gmp backend; 64 threads; `--checkpoint-tasks 1024` (≥ 16 × threads; `run` warns below that and refuses
    threads > checkpoint_tasks); `--chunk-points 2^20`; `--shards 64`.
  - Hashed seeds. `--seed-scheme legacy` reproduces the delivered tools' arithmetic, and refuses seeds already used
    with it (`production.py used_base_seeds`).
  - Frozen Neyman allocation for every stratum, the 44 seven-loop primitives included. `--points` overrides every
    stratum, for tests only.
- **Before anything is created**, the plan verifies every input file (packs included) and self-tests the
  executable.
- **The plan prints and records** in `manifest.json`:
  - estimated core-hours per group and in total;
  - per-index core-seconds;
  - the largest shard wall time and a suggested `--time` (3× the largest shard at 0.9 thread efficiency, ≥ 15 min);
  - a projected C7 SE, scaled from run1, for full recompute plans only.
- **Cost model.** These estimates come from the shipped symmetry cost model (`cost_models/`). `--cost-model PATH`
  replaces it; `--cost-model none` and the decimal backend have none. Without a model:
  - placement uses proxy costs and nothing is estimated;
  - array submission needs an explicit `--time`;
  - lane mode refuses the plan. Make a model from a small pilot with `tools/make_cost_model.py`.
- **Recorded fingerprint.** The plan records the host, CPU, libc, Python, NumPy and SciPy versions and the
  executable's resolved libraries.

## Submit (symmetry: exclusive whole-node partitions)

All submissions go through `tools/slurm_submit.py`. The wrappers `slurm/submit.sh` and `slurm/resubmit.sh` call it.

- **Allowlists.**
  - `C7_SBATCH_ARGS` (site options, one line, e.g. `-p amdq`) and extra arguments are each checked against an
    allowlist: account, partition, qos, reservation, constraint, mem, time, cpus, gres, mail, begin, signal,
    job-name, exclude, nodelist, licenses, wckey, requeue, hold.
  - Arrays, dependencies, exports, comments, outputs, nodes and cluster selectors are refused (64).
- **Environment.** Inherited `SBATCH_*` variables outside a small allowlist are dropped.
- **Lock.** Every submission holds `$C7_RUN/.c7_submit.lock`. A concurrent one exits 75. A lock left by a killed
  process names its owner; remove it by hand.
- **Mixed modes.** Array mode and lane mode are never mixed while jobs are live (65).
- **Merge wall time.** Merge jobs get their own `--time`, `C7_MERGE_TIME` (default 01:00:00). This fits symmetry's
  1-hour debug partitions, and the site options' work `--time` never applies to merges. If a merge submission fails
  after the work was accepted, the message names the live jobs. Then run `slurm/resubmit.sh` (arrays) or
  `slurm/submit.sh --lanes 0` (lanes).

**Lane mode (recommended on symmetry).** `slurm/submit.sh --lanes N [sbatch options]`:
- it releases claims of finished workers and writes `$C7_RUN/lanes/queue.txt` (incomplete indices, heaviest first);
- it submits N exclusive one-node workers (`slurm/lane_worker.sh`, `C7_LANE_TIME`, default 24:00:00) and a merge
  with `afterany` on every live and new worker.

Each worker splits the node's physical cores into lanes: one lane on AMD, one per socket elsewhere, and `C7_LANES=n`
overrides. A lane:
- claims an index by publishing `lanes/claims/<index>.json` (atomic, carries its owner);
- runs `production.py run`;
- removes the claim.

It skips indices that are complete, claimed, failed `C7_LANE_MAX_FAILURES` (2) times, or that do not fit the job's
remaining time (estimate / (cores × 0.9) × `C7_LANE_SAFETY` 1.5 + `C7_LANE_MARGIN` 300 s). A requeued worker reclaims
its own job's claims at start.
- **Lane width.** Lanes never have more cores than the plan's `checkpoint_tasks`: the default split adds lanes, and
  an explicit `C7_LANES` that would be wider refuses (64) before any claim.
- **Failures.** A lane stops after `C7_LANE_MAX_CONSECUTIVE_FAILURES` (3) failed runs in a row. To retry an index
  after fixing a failure, remove its `lanes/failures/<index>.*` records.
- **Logs.** Each attempt writes its own log, `lanes/logs/idx<index>.<job>.<ns>.log`.
- **Remaining time.** The worker asks Slurm for its job's remaining time (`squeue -j <job> -o %L`, with inherited
  `SQUEUE_*` filters removed). `C7_LANE_SECONDS` is only a fallback for when squeue gives no answer. To add workers, or to continue after workers end, run `--lanes N` again.
`--lanes 0` submits only a merge that waits for the live lane workers, for example after a failed merge
submission.

**Array mode.** `slurm/submit.sh`:
- arrays of at most `C7_MAX_ARRAY` elements (default 1000; symmetry MaxArraySize 1001), each with its
  `C7_INDEX_OFFSET` and `%C7_THROTTLE` (default 64), plus an afterok merge;
- elements get the plan's threads and suggested time, and extra options may override both;
- `slurm/submit.sh --window OFFSET:ARRAY` submits one window. These are the lines `production.py status` prints.

## Status, recovery, merge

```bash
python3 tools/production.py status "$C7_RUN"        # blocks per index and group, claims, failures, resubmission lines (exit 1 if incomplete)
python3 tools/lanes.py release-stale "$C7_RUN" --dry-run   # classify lane claims by their owner job (squeue)
slurm/resubmit.sh                                   # array mode: resubmit missing indices not still live + a merge waiting on live work
slurm/submit.sh --lanes N                           # lane mode: release stale claims, requeue, add workers + a merge
```

- **Recovery decision.** Recovery reads a complete `squeue --states=all -r` snapshot of the campaign's tagged jobs
  (`<tag>:off=K`, `<tag>:lane`, `<tag>:merge`; `production.py tag`).
  - Live work is never resubmitted.
  - A live merge refuses array recovery (65).
  - Completing, preempted or unknown states refuse (69); rerun later.
- **Duplicate execution.** Running an index twice only wastes work. Blocks are published no-clobber, and a duplicate
  is verified equal and logged as `verified duplicate`.

`slurm/merge.sh` does three things, and is safe to rerun and to run concurrently:
- it runs `status` and exits 65 if the campaign is incomplete;
- it merges every group, `C7_MERGE_JOBS` (4) in parallel, skipping groups whose `merged.json` is valid and refusing
  invalid ones;
- it assembles `C7_result.json` (`C7_test_result.json` for `--test-graphs` plans). An identical existing result is
  kept, and so is one that differs only by float rounding (assembled on another CPU type; `docs/NUMERICS.md`). A
  different one is refused.

Manual equivalents:

```bash
python3 tools/production.py merge "$C7_RUN" --jobs 8 --scratch /tmp
python3 tools/assemble.py "$C7_RUN" --bootstrap 4096
python3 tools/report.py "$C7_RUN" --output report.json     # read-only re-verification + gates (also for plans made by the delivered tools)
```

## Memory and filesystem

- **Packs.** Kernel packs replace thousands of graph files with indexed reads. Only the needed members of a block
  are read, hash-checked and staged on node-local scratch.
- **Sizes.** The largest pack is free_L7 at 251 MB (240 MiB); power_L7 is 56 MB.
- **Memory.** Native memory is bounded by the block (its distinct graphs and per-thread scratch). Planning and
  merging use disk-backed SQLite.
- **Optional staging.** `C7_STAGE=1` (array mode) also stages the Python tools, one pack and the executable per job.
- **Filesystem requirement.** Checkpoints, claims and results are published with POSIX hard links (no-clobber). This
  was used on symmetry BeeGFS by run1 and by this release's validation. Test it on any other filesystem.

## Remaining limits

- There is no cross-node work stealing beyond lane claims. The slowest index still sets the tail.
- Tasks and checkpoints grow with total samples at a fixed chunk size.
- Rare severe cancellations make the arithmetic fallback costly. Precision is never lowered to avoid that.
- The cost model's time estimates are hardware-specific planning aids, not guarantees.
