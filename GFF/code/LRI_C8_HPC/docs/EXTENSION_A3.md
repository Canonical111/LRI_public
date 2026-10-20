# Amendment A3: the planned batches b12–b14 on Expanse

Status: written 2026-10-12 before any A3 action; to be reviewed (fresh Codex session) before anything is changed on
either cluster. Builds on `docs/EXTENSION_A2.md` (A2, Codex APPROVED r9 at 4adf719) and `docs/EXTENSION_A1.md` (A1,
APPROVED r12 at 15a110e). Everything not stated here is unchanged from A2 and A1.

## Decision record and disclosure

- **User decision, 2026-10-12 ~13:35 EDT:** "yes do it, b12-b14 on expanse as you proposed", after the user asked
  whether b11–b14 could move to Expanse and was shown both splits. Motivation: wall time. Every Intel node of
  symmetry is allocated, so A2's 8 preq lanes may not start; with the 15 longq lanes alone A2 would close around
  2026-10-14 evening.
- **What was visible.** The interim combinations through b1–b9 (b1–b9: C8 = 8,061,480, SE 5,300, allowance ±22,000;
  earlier ones listed in A2). b10 had 37 of 498 elements done (13:02 EDT); b11–b14 had no element run or claimed in
  either queue.
- **No effect on which samples enter.** A3 changes only the machine that computes b12–b14. The target (all of b10–b14,
  K = 14), the seeds, the planned batches and the closing-on-completion rule are A2's. The machine choice cannot select
  samples: every planned element of every batch is computed and included.

## What stays unchanged

Frozen design prod4_34000, estimator, allowance rule and checks; the planned batches b12–b14 exactly as planned under A1
(byte-identical copies on Expanse, verified by file manifests); `runs/ext1/extension.json` (not edited); the production
executable (sha256 ffb200d4…7db8b); the frozen production code: `tools/production8.py` and `tools/campaign.py` are
byte-identical in c0ffa63 (the Expanse code copy that ran b1–b4) and 15a110e (checked by `git diff` and again on Expanse
before submission); `combine8.py` and `lane8.py` of 15a110e; the A1 record (A1-close snapshot, derived inclusion file,
A1-close combination); A2's lanes, `lane8_a2.slurm`, mode ht, wave-wide stop and recovery rules for b10–b11.

## What A3 changes

1. **queue_a2 holds b10 and b11 only.** `submit_a2.sh close` builds `queue_a2` from b10 and b11 (996 elements) and
   checks that the staged queue holds exactly these two labels and 996 elements before the atomic rename. Nothing else
   in the A1-close job changes. Because the pending A1-close job (573583, code 4adf719) runs the 4adf719 script, it is
   **re-armed**: (a) `scancel 573583` while it is PENDING (nothing has run); (b) `sacct` shows it CANCELLED and
   squeue no longer lists it; (c) `runs/ext1/a2_close_job.txt` is renamed `a2_close_job.txt.superseded_A3` (kept);
   (d) `submit_a2.sh arm` from `code/<A3 commit>` submits the new A1-close job with the same dependency (afterany on
   every A1 lane job). This must finish before the last A1 lane job ends (not before the 18:21:25 EDT deadline plus the
   last element). If the old job had already started, A3's queue change is not made and A2 stands unchanged (then
   b12–b14 stay on symmetry; A3 is void).
2. **Vendor rule, per batch.** A1 and A2 run every extension batch on Intel. A3 runs **each of b12, b13 and b14
   entirely on AMD EPYC 7742** (Expanse `shared`), the platform and environment of b1–b4 (the binary's native GCC 13.3
   runtime, the Expanse Python venv of b1–b4, the b1–b4 launcher settings: 16 cores, 24 GB, 4 h per element). The
   reason for the vendor rule (finding F5: x87 long-double transcendentals differ between vendors at about 1e-16
   relative) is kept where it matters, inside a batch: no batch mixes vendors. b12–b14 have no symmetry checkpoint
   (checked at export and again at install), and after the A1 close no symmetry worker can reach them (the A1 queue's
   deadline has passed and its workers refuse claims; `queue_a2` does not contain them). Across batches, vendors are
   already mixed (b1–b4 AMD, b5–b11 Intel); the A1 smoke replay bounded the platform effect on a campaign's per-batch C8
   contribution to ≤ 1e-6 of its SE.
3. **Export** — `cluster/a3/export.sh A3_COMMIT [--early]`, run on the Mac (both sites by ssh). Normally after the A1
   close; with `--early` (user, 2026-10-12 ~14:45: "expanse can start right now?") before it, through the early gate
   below. Either way the closing job requires the A1-close snapshot to record b12–b14 with no checkpoint, claim or done
   marker in either queue, and the installation requires symmetry's planned b12–b14 trees to be untouched, so an
   Expanse copy can never be combined with symmetry work on the same batch; if either check failed, that batch's
   Expanse copy would be discarded entirely (a new decision).
   - **early gate** (`a3_tree.py gate --early`), before the A1 close: the snapshot, `queue_a2` and its staging
     directory do not exist; b12–b14 are untouched (as below) and have no claim in the A1 queue; the A1 queue has no
     failure record; and a lower bound on the time before any A1 worker can claim a b12 element by computing exceeds the
     time left to the A1 deadline. A1 workers claim strictly in queue order (b10, b11, b12, …) and start no element
     after the deadline, so every unclaimed element before the first b12 element must be claimed first, and when the
     first b12 element is claimed at most W of them are still running. Bound: (sum of their predicted costs minus the W
     largest) / (W × 2), with W = 2 × the 24 A1 lane jobs (only 15 run) and a speed factor of 2 (a symmetry worker is
     measured 1.3–1.6 times faster than the 16-core cost unit). At 14:46 EDT: 873 unclaimed elements before b12 (375
     of b10, all of b11), bound 5.8 h, 3.6 h to the deadline. The gate is evaluated again after the copy and must give
     the same answer.
     **This is a speculative start, not an exclusion guarantee.** The bound covers computing only: A1 workers skip an
     element after 3 failed attempts and continue after ordinary failures, so a systemic fast failure could advance them
     faster. Policy: (i) the gate requires a failure-free A1 queue; (ii) no tripwire is pre-implemented: the Expanse
     work runs on, and its validity is decided only by the A1-close snapshot, so the cost of the unlikely case is
     wasted compute, at most one batch's Expanse allocation (≈6k SU) per overlapped batch; A1 failure records seen
     before the close are reported to the user; (iii) overlap and discard: if the snapshot records any A1 checkpoint,
     claim or done marker on a batch of b12–b14, that batch's Expanse copy is never imported (the close refuses it) and
     is discarded entirely, and the batch is completed on symmetry from its A1 state through a separately reviewed
     procedure. Mixed-vendor data cannot arise either way:
     the close requires the snapshot to record b12–b14 untouched, and the installation requires symmetry's planned
     trees to be untouched;
   - normal gate (`a3_tree.py gate`), after the A1 close: the A1-close snapshot exists and records b12–b14 with no checkpoint, claim or
     done marker in either queue; `queue_a2/order.json` holds exactly b10 and b11 (996 elements); b12–b14 have the
     amendment's labels and seeds, their `production.json` digests equal the snapshot's, they have no `checkpoints/` or
     `merged/` directory and no claim file in either queue;
   - on Expanse the export takes the submit lock `runs/ext1/A3_SUBMIT.lock` (shared with the `a3_expanse.py` commands,
     including `stop`) before its admission checks and holds it to the end; under it, the stop barrier must be absent
     and the targets `runs/ext1/b12..b14` and the export record must not exist;
   - tar stream symmetry → Expanse; per batch the sha256 of the file manifest (sha256 and path of every file),
     computed inside `a3_tree.py manifest --digest` (which fails on any error: a traversal error, a root that is not a
     real directory, an empty tree, any entry that is neither a real directory nor a regular file, symlinks included), must be 64 hex digits and equal on both sites (remote shells run with pipefail and stop if their environment
     setup fails); the gate is rerun and must give the same answer;
   - the export record `runs/ext1/A3_export.json` on Expanse (written to a temporary file, then renamed no-clobber,
     with the stop barrier absent and the lock still the export's): the A3 commit, the gate's answer (mode, snapshot
     digest or none, `production.json` digests) and the three manifest digests; then the export removes its own lock. An interrupted export leaves the lock (inspect, then
     remove it).
4. **Expanse run** — `cluster/a3/submit_expanse.sh run` (Expanse login node; environment `env.sh` of b1–b4, then
   `cluster/a3/a3_expanse.py`). Checks: the executable digest is ffb200d4…, the code copy's `tools/production8.py` and
   `tools/campaign.py` equal the A3 commit's byte for byte, the export record exists. Per batch it submits whatever is
   missing, so a partial submission is resumed by running it again: the 498-task array of
   `cluster/a3/production8_a3.slurm` only if no array of the batch is journaled (then no `c8a3-` job of the batch may
   exist in any state other than a terminal one, the batch must be untouched (`check-expanse`) and its manifest digest
   must equal the export record), and the merge job `cluster/a3/merge8_a3.slurm` with `--dependency=afterok` on the
   array only if no merge is journaled and none exists. Elements run as `production8.py run BATCH --index I --threads
   16 --executable code/c0ffa63/bin/c8_integrate` (the manifests name the symmetry path of the same binary;
   `campaign.py` checks the given file against the planned sha256 before every invocation). The merge job runs
   `production8.py merge` and then writes the batch's file manifest `runs/ext1/<label>.expanse_manifest.txt`
   (no-clobber). Every accepted job is journaled in `runs/ext1/a3_jobs.jsonl` (fsync) as soon as sbatch answers; sbatch
   output must be a job id, and any sbatch or journal failure stops the command (a journal failure names the accepted
   job for a manual entry). Scheduler queries remove every `SQUEUE_*` variable, list all states and stop the command
   on any failure or malformed line (as `lane8.squeue_jobs`); a job counts as finished only in the terminal states
   lane8 uses (COMPLETED, CANCELLED, FAILED, TIMEOUT, NODE_FAIL, BOOT_FAIL, DEADLINE, OUT_OF_MEMORY, REVOKED; held,
   requeued or preempted jobs count as unfinished); sbatch runs with `SBATCH_*` and inherited `C8_*`
   variables removed and the pins given explicitly. Admission is serialized: `run`, `resubmit`, `merge` and `stop` hold
   the submit lock `runs/ext1/A3_SUBMIT.lock` (exclusive create, removed on exit; a lock left by a killed command is
   removed by hand after inspection) for their checks, submissions and journal writes. No throttle (as b1–b4: `shared`
   is not under the per-account node cap).
   **Recovery on Expanse.** `submit_expanse.sh resubmit LABEL INDEX...` reruns elements whose every journaled attempt
   (the array and earlier resubmissions) has exactly one accounting line in a state FAILED, TIMEOUT, NODE_FAIL or
   OUT_OF_MEMORY, with fewer than 3 such attempts (all four states count; CANCELLED or any other state is not retried
   automatically), and only while no task of the batch is pending or running (b1–b4 had two transient srun step
   failures). A checkpoint found corrupt after its element COMPLETED (by validation at merge time; not seen in b1–b4)
   has no pre-implemented repair: the batch's Expanse work halts, and a recovery procedure (quarantine with the frozen
   tool, rerun, a new manifest, withdrawal of any staged copy) is written and independently reviewed before use. A
   staged copy that fails its checks on symmetry (for example a damaged transfer) is withdrawn with `a3_tree.py
   unstage LABEL` (login node) and imported again: it takes the batch's registration `.incoming.<label>` (as a
   transfer does) for its whole duration, then refuses if the close lock exists or any part of the batch is installed
   (after the close has begun, such a recovery is a new, documented decision), moves the staged copy and its manifest
   (and a verification receipt of it, if any) to `runs/ext1_a3_import/withdrawn/<label>.<k>/`, and removes the
   registration last. Committed checkpoints are
   validated and skipped, so only missing work is computed. Resubmissions are journaled and logged in
   `runs/ext1/A3_RESUBMISSIONS.txt`. The afterok merge then never starts; it is cancelled
   while pending and `submit_expanse.sh merge LABEL` submits it by hand once the batch's array is journaled, no task
   or merge of the batch is unfinished and every planned checkpoint is present. The merge job itself first checks the
   whole batch's completeness (`lane8.checkpoints_complete`: manifests and hash-checked task plans) and exits without
   writing if any planned checkpoint is missing, so the frozen merger never starts on an incomplete batch. An element at its third failure is
   diagnosed by hand. Checkpoints are never recomputed on another site; if a batch cannot be completed on Expanse,
   moving it is a new, documented decision, and its Expanse checkpoints are then discarded entirely, never mixed with
   symmetry ones.
5. **Import** — `cluster/a3/import.sh A3_COMMIT LABEL...` (Mac), per merged batch, into symmetry's **staging**
   directory `runs/ext1_a3_import/` (nothing else reads it; never into `runs/ext1` directly, so neither queue and no lane
   can see the Expanse work before the close). Admission protocol, shared with the close job: with the close lock absent,
   the transfer is registered by creating `.incoming.<label>` (mkdir, atomic); the manifest and the batch are copied into
   the registration; the manifest digests of both sites must agree; with the close lock still absent, the batch and
   then its manifest are published by renames and the registration is removed last. The close job publishes its lock
   first and then refuses while any registration exists, so it either sees a batch fully staged or stops. A transfer
   that finds the lock, or is interrupted, leaves its registration, which stops the close until an operator inspects and
   removes it. While it reads a batch on Expanse the transfer holds the Expanse submit lock (as the `a3_expanse.py`
   commands do), so no resubmission or merge submission interleaves with it. An optional `c8x-a3check` job (sharedq, 8 cores) then validates the staged copies early (the same checks
   as the close job's `verify`, below); nothing depends on it, it writes nothing, and it refuses once the close lock
   exists (while it runs, the close refuses, being a `c8x-` job).

## Closing rule and final result

- A3 closes when all of b5–b14 are complete: `queue_a2` has all 996 elements done and b10, b11 merged, no `c8x-lane`
  job remains, and b12–b14 are merged on Expanse and staged.
- Then one job, `cluster/a3/a3_close.slurm` (defq, exclusive; named `c8x-finalize`, so that `lane8.py finalize`
  accepts it as its own job), submitted only through `cluster/a3/submit_sym.sh close` of the deployed revision (login
  node: every inherited `C8X_*` and `SBATCH_*` variable removed, `C8X_A3` set to the script's own directory; the job
  compares its own script with the copy there and refuses any other `C8X_*` variable, so exactly that revision's
  helpers run; `c8x-a3check` is submitted the same way, by `submit_sym.sh check`), in this order:
  0. `a3_close.py begin`, on every invocation (it also requires the A1-close snapshot to record b12–b14 untouched by
     A1 workers, which covers an early export): the close lock `runs/ext1/A3_CLOSE.lock` is published no-clobber FIRST and
     held to the end (an existing lock from an earlier attempt stops the job; it is removed by hand only after that job
     has ended and its log has been read); then squeue answers and lists no unfinished `c8x-` job other than this one
     (`c8x-stop` excepted, as in lane8); then no transfer or unstaging registration exists; then no stop marker exists
     (`runs/ext1/A3_STOP`, `runs/ext1/A2_CANCEL`, `runs/ext1/queue_a2/STOP`), no publication was admitted
     (`runs/ext1/A3_PUBLISH`) and no result is published; then `queue_a2` is complete and b12–b14 are staged;
  1. `lane8.py finalize` on `queue_a2` and then on `queue` (merge-only; b12–b14 still have no checkpoint on symmetry
     at this point, so the A1 queue leaves them unmerged and no A1 queue marker names Expanse work); recorded in
     `runs/ext1/A3_finalized.json` and not repeated on a rerun (step 0 is);
  2. per A3 batch: `a3_close.py verify` validates the staged copy before anything is moved: `a3_tree.py check-import`
     (the staged tree equals the Expanse manifest; every planned file equals symmetry's; additions only under
     `<campaign>/checkpoints/<file>` and `<campaign>/merged/<file>`; every campaign has `merged/audit.json`), then `production8.py merge` on the staged copy, which (all campaigns being audited) only
     re-validates every merged campaign: manifest, task plans, every checkpoint and its payload digest, coverage and
     audited outputs (`verify_campaign` compares digests, so it is platform-independent); it then publishes the receipt
     `runs/ext1/A3_verified_<label>.json` bound to the manifest digest. On a rerun after an interrupted install (some
     campaign directories already moved) the receipt for the same manifest is required instead. Then `a3_tree.py
     install` moves each campaign's `checkpoints/` and `merged/` (renames on BeeGFS) into `runs/ext1/<label>/`
     (restartable: a campaign directory already moved is accepted only if the union of the two trees still equals the
     manifest and no directory is split; afterwards the installed tree must equal the manifest file for file), and
     `production8.py merge` re-validates the installed batch (writes nothing);
  3. `a3_close.py batches`: every one of b5–b14 must have all planned checkpoints and every campaign merged (b12–b14:
     installed tree equal to the manifest); otherwise the job stops: a complete close never omits a batch;
  4. `combine8.py` b1–b4 + b5–b14 `--extension runs/ext1/extension.json --closed` with A1's `--affine`, `--exact5` and
     `--design-meta`, into the private directory `results/C8_final_A3.pending/`; `a3_close.py end` requires the closed
     K = 14 result there (14 batches, final, extension closed with b5–b14 included and none omitted) and writes
     `A3_close.json` (atomic no-clobber; on a rerun an existing record must agree in schema, batches and vendors); then
     **publication**: the marker `runs/ext1/A3_PUBLISH` is
     published no-clobber, the symmetry stop marker `runs/ext1/A3_STOP` must be absent, and the directory is renamed to
     `results/C8_final_A3/` (combine8 writes every path relative to its output directory, so the rename keeps them
     valid). If the stop marker exists the job stops and the result stays private.
- The report quotes the A3 result (registered allowance rule), the vendor of each batch (b1–b4 and b12–b14 AMD EPYC
  7742; b5–b11 Intel Gold 6148), and separately the A1 deadline result and the original b1–b4 result.
- **Stop (user instruction only; never after looking at results).** Halting is pre-implemented, a stopped close is
  not. To halt: first `a3_close.py stop` on symmetry's login node, which publishes `runs/ext1/A3_STOP` no-clobber and
  then reports the stop acknowledged only if `A3_PUBLISH` is absent. Each side publishes its marker before checking the
  other's, so either the stop is acknowledged and no close publishes (a running close stops at publication, a later one
  at `begin`), or publication was admitted first and the stop is reported as too late for the result. Then A2's
  markers on symmetry (`runs/ext1/A2_CANCEL`, and `runs/ext1/queue_a2/STOP` once the queue
  exists); on Expanse `submit_expanse.sh stop`, which publishes the durable barrier `runs/ext1/A3_STOP` under the
  submit lock (it creates `runs/ext1` if the export has not happened yet; after it returns no submission is accepted,
  merges included, every element task that starts exits without work, and `export.sh` refuses to copy or to write the
  export record),
  then `scancel` of the unfinished `c8a3-` jobs. The result rule after a stop is fixed now: the A1 rule applied on each
  batch's owning site (a batch is included if and only if all its planned checkpoints are present where it ran; it is
  then merged there and, for an Expanse batch, imported as above; omitted batches are reported with their completed
  fractions). Its implementation depends on the phase at which the stop happens (before or after the A1 close, the
  queue publication, the export, the Expanse merges), so no stopped result is published until a closing procedure
  for the actual state has been written and independently reviewed. The complete close above refuses to omit any
  batch.

## Expected cost and timeline

- Expanse: 3 × ≈5,930 core-hours ≈ 18k SU (b1–b4: 5,930 allocated core-hours per batch; yun124 has 22.08M SU, 219k
  spent, expiring 2027-09-30). b1–b4 took about 9 h on `shared`; the shared queue is busier now (≈1,080 pending jobs).
- symmetry: b10's remainder after the A1 close (about 250 elements) plus b11 (498), ≈490 worker-hours: about 11 h on
  23 nodes, 16 h on 15.
- Final result expected on 2026-10-13 (EDT), about a day earlier than under A2 alone. Expected SE ≈ 4,250 and allowance
  ≈ ±17,000, as for A2.

## Checks

- Local: `a3_tree.py` on a synthetic batch (fresh import passes; a changed planned file, an extra file, an install
  outside the close job, a wrong seed are rejected; an interrupted install resumes; a rerun after install passes; a
  manifest rewrite with different content is refused). `a3_expanse.py` and
  `a3_close.py` against stub `squeue`, `sbatch` and `sacct` commands (journaling, resumed `run`, rejection on scheduler
  failure, retry states and limits, submit lock, stop barrier, close lock, quiescence, registrations, stop/publication
  handshake, unstaging).
- Re-arm: 573583 CANCELLED in sacct; the new A1-close job pending on Dependency with the A1 lane jobs; `queue_a2`
  absent until the A1 close.
- A1 close: the job log shows the snapshot, "A2 queue_a2 (b10-b11; amendment A3) published", 996 elements, and the A1-
  close combination; A2 lanes begin work within minutes.
- Export: gate passes twice with the same answer; three manifest digests equal; export record written.
- Expanse: first element logs about 10 minutes after the arrays start ("committed" lines); sacct states.
- Import: each batch staged (registration removed); the optional `c8x-a3check` passes.
- Close: finalize outputs (b12–b14 "incomplete, 0/…: left unmerged" in the A1 queue), verify receipts, install and
  re-validation pass, all ten extension batches complete, closed K = 14 combination written.

## Review dispositions

- **Round 1** (Codex, REVISE, 5 findings; all accepted):
  - A3-01 (sbatch failure hidden inside command substitution; no resumable partial submission): submission moved to
    `a3_expanse.py`: sbatch output validated as a job id, sbatch and journal failures stop the command, `run`
    submits per batch only what the journal lacks.
  - A3-02 (inherited `SQUEUE_*` filters, pending-only listing): queries remove `SQUEUE_*`, list all states, reject any
    unfinished job, and fail closed.
  - A3-03 (retry count ignored NODE_FAIL and OUT_OF_MEMORY; CANCELLED retried): all four retried states count toward
    the limit of 3; CANCELLED and other states are not retried; every journaled attempt needs exactly one accounting
    line.
  - A3-04 (a rerun of the close skipped the exclusion check): quiescence is checked on every invocation, and the
    no-clobber close lock is held from before finalize to the end; staging and checking refuse once it exists.
  - A3-05 (no closing path after a user stop): a stopped mode (withdrawn in round 2, see A3-R2-05) (stop record from Expanse with completeness on
    the owning site, merge of complete batches whose merge was cancelled, staged record, installation of exactly the
    complete batches, reported fractions).
- **Round 2** (Codex, REVISE, 6 findings):
  - A3-R2-01 (complete close could omit an incomplete symmetry batch, K = 13): accepted; `batches` requires every
    planned checkpoint and merge of b5–b14, and `end` requires the closed K = 14 result.
  - A3-R2-02 (no durable Expanse stop barrier; unserialized admission): accepted for halting: the submit lock
    serializes `run`, `resubmit`, `merge` and `stop`; `stop` publishes `A3_STOP`, honored by submission and by every
    element task. The Expanse stop record is withdrawn with the stopped close (next item).
  - A3-R2-05 (the stopped close could not handle a stop before queue publication or export): the round-1 stopped mode is
    withdrawn rather than extended phase by phase. Halting stays pre-implemented and the result rule after a stop is
    fixed in advance (the A1 rule on each batch's owning site), but no stopped result is published until a procedure
    for the actual state is written and independently reviewed. A stop is not expected and needs a user instruction.
  - A3-R2-03 (imports and checks not coordinated with the close): accepted; registration/rename protocol for imports,
    and the close publishes its lock before querying the scheduler and the registrations; step 0 runs on every rerun.
  - A3-R2-04 (no enforced pre-install verification): accepted; the close job validates each staged copy itself before
    any rename and keeps a manifest-bound receipt for reruns; `c8x-a3check` is only an early diagnostic.
  - A3-R2-06 (quarantine records rejected by the import check): accepted, then withdrawn in round 5 (A3-R5-01); the import check accepts
    `<campaign>/checkpoints/quarantine/<file>` and merged-directory audit invalidations, and `resubmit` reruns an
    element with a COMPLETED attempt when every missing checkpoint is named in the quarantine log.
- **Round 3** (Codex, REVISE, 2 findings; both accepted):
  - A3-R3-01 (stop before the export failed: no `runs/ext1` on Expanse for the lock): the submit lock creates its
    directory first; `export.sh` refuses while the stop barrier or the submit lock exists, also when it writes the
    export record.
  - A3-R3-02 (a checkpoint repaired after the manifest was published could not be re-imported; the quarantine part
    withdrawn in round 5): `submit_expanse.sh
    quarantine` archives the published manifest before the frozen quarantine and journals it; transfers hold the
    Expanse submit lock while reading; `a3_tree.py unstage` withdraws an obsolete staged copy and its receipt before
    the close.
- **Round 4** (Codex, REVISE, 2 findings; both accepted):
  - A3-R4-01 (unstaging not serialized with the close or imports): `unstage` takes the per-batch registration for its
    whole duration and rechecks the close lock and the installed state under it.
  - A3-R4-02 (a complete close could publish after a user stop): `begin` refuses any stop marker; the result is written
    privately and published by rename only after the `A3_PUBLISH` / `A3_STOP` handshake; the stop procedure starts with
    `a3_close.py stop`.
- **Round 5** (Codex, REVISE, 4 findings):
  - A3-R5-01 (an interrupted quarantine blocks recovery) and A3-R5-04 (quarantine identity not validated): the
    pre-implemented quarantine path (rounds 2–3: the `quarantine` command, reruns of COMPLETED elements, acceptance of
    quarantine records at import) is withdrawn, as the stopped close was in round 2: a corrupt checkpoint on Expanse
    halts that batch's Expanse work until a recovery procedure is written and reviewed. `unstage` stays, for staged
    copies that fail their checks.
  - A3-R5-02 (closing record not atomic): accepted; `A3_close.json` is published atomically and an existing one must
    agree.
  - A3-R5-03 (export did not hold the Expanse lock): accepted; the export holds the submit lock from its admission
    checks to the export record, which is written atomically.
- **Change after approval (user, 2026-10-12 ~14:45, "expanse can start right now?")**: the early export gate
  (`gate --early`, `export.sh --early`) and the snapshot requirement in the close job's `begin`; to be reviewed before
  use.
- **Round 7** (Codex, REVISE, 2 findings on the early gate; both accepted):
  - A3-IR-01 (the reach bound is not an exclusion guarantee: fast failures can advance A1): the early export is stated
    as a speculative start with an explicit policy (failure-free A1 queue at the gate, hold tripwire on any A1 failure
    before the close, discard of an overlapped batch's Expanse copy and a reviewed completion on symmetry).
  - A3-IR-02 (manifest digest of an empty pipeline output could verify): the digest is computed by `manifest --digest`
    and validated as 64 hex digits; remote shells use pipefail and stop on environment failure.
- **Round 8** (Codex, REVISE, 4 findings; all accepted):
  - A3-R8-01 (manifest traversal errors and directory symlinks ignored): `tree` raises on every traversal error,
    checks the root and rejects every entry that is not a real directory or regular file.
  - A3-R8-02 (SPECIAL_EXIT and PREEMPTED counted as finished): the terminal set is lane8's.
  - A3-R8-03 (an inherited `C8X_A3` could select another revision): `submit_sym.sh` sanitizes and pins; the jobs
    compare their own script with the pinned copy and refuse other `C8X_*` variables.
  - A3-R8-04 (merge accepted after a stop): `merge` honors the stop barrier.
- **Round 9** (Codex, REVISE, 2 findings):
  - A3-R9-01 (the early-start tripwire had no execution path): the tripwire is removed rather than implemented across
    sites; it only limited wasted compute (correctness is enforced by the close-time snapshot and installation
    checks), and the worst case is stated (≈6k SU per overlapped batch, discarded).
  - A3-R9-02 (a premature manual merge could create output and block the initial submission): accepted; `merge`
    requires a journaled array and a complete batch, and the merge job checks completeness before any write.
