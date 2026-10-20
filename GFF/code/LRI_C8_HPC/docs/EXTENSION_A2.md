# Amendment A2: completing the planned extension batches b10–b14

Status: written 2026-10-12 before submission; to be reviewed (fresh Codex session) before any A2 job is submitted.
Builds on `docs/EXTENSION_A1.md` (A1, Codex APPROVED r12 at 15a110e). Everything not stated here is unchanged from A1.

## Decision record and disclosure

- **User decision, 2026-10-12 ~09:00 EDT:** "finish everything", i.e. complete b10–b14, the extension batches that A1
  planned (seeds 80840010–80840014) but that the A1 wave cannot finish before its deadline. Motivation: precision.
- **This overrides one A1 rule.** A1 allows a finishing wave only for batches already in progress at closing. A2 also
  runs b11–b14, which A1 would never start. This is a user decision taken after A1 was approved, not part of A1.
- **What was visible when the decision was taken.** The interim (non-final) combinations of b1–b5, b1–b6, b1–b7 and
  b1–b8 had been computed and reported: C8 = 8,062,300 / 8,063,205 / 8,064,070 / 8,063,433 with SE 7,106 / 6,463 /
  5,976 / 5,602. The decision followed a question about the attainable precision and its cost in wall time, not about
  the central value.
- **No b10–b14 data existed.** At the decision, b10–b14 had no completed element (A1 status at 08:23 EDT: b9 259/498,
  b10 0/498 done; b11–b14 never queued for work before b10).
- **Stopping rule independent of results.** A2 fixes the target in advance: all of b10–b14, i.e. K = 14 batches. It
  closes on completion, not on a time or a value, so no outcome can influence which batches are included.

## What stays unchanged

Frozen design prod4_34000 and its estimator, assembly, allowance rule and lower-order checks; the planned batches
b10–b14 under `runs/ext1/` exactly as planned and checked under A1 (labels, seeds, configuration identical to b1);
`runs/ext1/extension.json` (not edited); the production executable (sha256 ffb200d4…, GCC 13.3 runtime libraries);
the tools 15a110e (`lane8.py`, `combine8.py`) and the frozen production code; `cluster/symmetry/lane8.slurm`,
`finalize8.slurm`, mode ht. Intel Gold 6148 nodes only (AMD nodes are left to other projects; one CPU vendor for
all extension batches, as in A1).

## What A2 adds: a sequential second wave

A2 does not overlap A1. Its single queue is published only after every A1 lane job has ended and the A1 state has been
recorded, so no A2 worker can write any batch while an A1 worker can still reach it.

1. **A1-close job.** `cluster/symmetry/submit_a2.sh arm` (login node, once) submits a debugq job `c8x-a1close` with
   `--dependency=afterany` on every A1 lane job (572737–572760). It runs `submit_a2.sh close` and then, whatever
   `close` returned, `a1_close_combine.sh` (which itself requires the snapshot); the job fails if either failed:
   - `close` runs `a1_close_snapshot.py` (retried up to 15 times at 60 s while accounting catches up), which records
     the A1 state and the A1 inclusion set (below). The A1 record is made whatever A2's fate: `A2_CANCEL` only
     suppresses publication of the A2 queue (checked before staging and again before the rename; `close` then exits
     successfully). Only if the snapshot succeeds and A2 is not cancelled does it build the A2 queue in
     `runs/ext1/queue_a2.staging` (`lane8.py queue --costs costs_b1to4_seconds16.json b10 b11 b12 b13 b14`, 2,490
     elements), check the element count and publish it by an atomic rename to `runs/ext1/queue_a2`. Workers therefore
     see either no queue or the complete one. A leftover staging directory from an interrupted build is removed and
     rebuilt (nothing reads it); `close` is restartable (an existing snapshot is only verified; an existing queue is
     kept).
   - `a1_close_combine.sh` writes the A1 result at its deadline (below).
   The job body is `cluster/symmetry/a1_close_job.sh` (both steps, unconditionally, with their combined exit status).
   If the job fails, it is rerun by hand with the same body after reading its log (`sbatch -p debugq -N 1 --exclusive
   --mem=180G -t 01:00:00 --job-name=c8x-a1close --wrap "bash .../cluster/symmetry/a1_close_job.sh"`).
2. **No deadline.** `queue_a2` has no `deadline.json`; `submit_a2.sh lanes` refuses a published queue that has one, or a
   STOP or MAINTENANCE marker. Workers exit when no element or merge needs work. b10 comes first because it is already
   about two-thirds done; b10 elements completed by A1 are re-run by A2 workers through `production8.py run`, which
   validates the committed checkpoints and skips them (no sampling is repeated), and their done markers then appear in
   `queue_a2`.
3. **Lanes, submitted ahead of the queue.** `submit_a2.sh lanes PARTITION N [BEGIN]` submits N lane jobs of
   `cluster/symmetry/lane8_a2.slurm`. Such a job may start before the queue is published (for example on a node an
   A1 lane has just released): it waits for `queue_a2/order.json`, polling every 60 s for at most 4 h, and exits
   without work if `runs/ext1/A2_CANCEL` exists; then it runs the unchanged A1 launcher `code/symmetry/lane8.slurm`
   (tools 15a110e) on `queue_a2`. The script removes every inherited `C8X_*` and `SBATCH_*` variable, exports exactly
   `C8X_TOOLS=code/15a110e`, `C8X_QUEUE=runs/ext1/queue_a2` and `C8X_MODE=ht`, checks the resulting `C8X_*`
   environment, submits with `--export=ALL` and `--job-name=c8x-lane`, and checks each submitted job's name and
   partition with squeue (recovery and finalize recognize lane jobs by that name); `lane8_a2.slurm` refuses any other
   queue. It refuses to run inside a Slurm job. longq requests 7 days (cn053–068), defq 24 h, preq 24 h with
   `--requeue` and `--exclude=cn[043-068]` (preq-only nodes cn069–076), as in A1. Job ids are appended to
   `runs/ext1/a2_jobs_<partition>.txt`. Lanes may be added at any time while there is work (for example, to replace a
   24 h lane that ended); since A2 closes on completion, the number and timing of lanes cannot change which samples
   enter the result. Abandoned attempts of ended lanes are taken over as in A1.
4. **Initial submission:** `arm`; 15 longq lanes (they pend until the A1 longq lanes release cn053–067 after the A1
   deadline and then wait for the queue); 8 preq lanes with `BEGIN` = 2026-10-12T18:15 (cn069–076), so they hold their
   nodes for at most the A1 tail (about 1.5 h) before the queue is published.
5. **Wave-wide stop of A2.** Touch `runs/ext1/A2_CANCEL`: `close` then still records A1 (snapshot and A1-close
   combination) but publishes no queue, `lanes` submits nothing and
   waiting lane jobs exit without work. Once `queue_a2` exists, also touch `runs/ext1/queue_a2/STOP`: running workers
   finish their current element and exit. A2 has a single queue, so these two markers stop all A2 work. A stop is used
   only on the user's instruction, never after looking at results.

## The A1 record at its close

- **A1 wave untouched.** Its deadline, STOP job (572736, writes only `runs/ext1/queue/STOP`) and lanes run as
  pre-registered, and its result is recorded before A2 can write anything.
- **A1-close snapshot** (`cluster/symmetry/a1_close_snapshot.py`). Run by `close` after every A1 lane job has ended
  (squeue lists none of them in a non-terminal state and sacct gives each a terminal state). It writes, no-clobber,
  `results/C8_A1_close/a1_close_snapshot.json`: for every planned extension batch the checkpoints present and planned,
  completeness, claimed and done elements in each queue, the A1 merge state and the `production.json` digest; the A1
  lane jobs' final states; the deadline and STOP marker; and the A1 inclusion set. **The A1 inclusion set keeps A1's
  own rule**: a batch is complete when all its planned checkpoints are present (as `lane8.py finalize` decides; done
  markers are not required, so a batch whose last done marker was cut off after its final checkpoint is still
  included). The script refuses to run if `queue_a2` or its staging directory exists, so no A2 work can be counted.
  As a defence it also attributes checkpoints to a wave by claims (a worker runs an element only after publishing an
  attempt file in its own queue; claims are read after every checkpoint has been scanned) and stops if a complete batch
  has A2 claims or a batch has claims in both queues. Every A1-queue done marker must name an A1 lane job, and a batch
  with A1 done markers on every element but missing checkpoints stops the script. It also writes
  `runs/ext1/extension_A1close.json`: `extension.json` with the planned extension batches restricted to the A1
  inclusion set, bound to the snapshot by its sha256. It is restartable: with an existing snapshot it only validates
  it and rebuilds or verifies the derived file, without rescanning checkpoints. It reads only otherwise; it creates no
  queue marker.
- **A1 result at its deadline** (`cluster/symmetry/a1_close_combine.sh`, run by the A1-close job). It first verifies
  the saved snapshot and the exact contents of the derived file (the snapshot script in restart mode), then runs `combine8.py` of
  b1–b4 and the A1 inclusion set with `--extension runs/ext1/extension_A1close.json` (interim mode, no `--closed`,
  because A2 lanes run) into `results/C8_A1_close/combination/` (expected b1–b9). The derived file fixes the inclusion
  set, so the same command gives the same A1 result whenever it is run, and combine8 rejects any batch outside it.
  This is what A1 alone would have given; it is reported next to the A2 result. Omitted A1 batches and their fractions
  at the A1 close are taken from the snapshot.
- **If an A1-complete batch is unmerged at the A1 close** (a merge cut off; not expected: A1 lanes merge each batch as
  it completes, and b9 is merged hours before the deadline), the combination fails without writing, because
  `lane8.py finalize` refuses while any `c8x-lane` job exists. It is then rerun after the A2 close and the A1-queue
  finalize, with the same derived file, and reported as computed late, with the snapshot unchanged.
- **A1 finalize is deferred to the A2 close** for the same reason. It merges on checkpoint completeness, so it also
  sees b10–b14 complete then; their campaigns are already merged by A2 and are only verified (`production8.py merge`
  skips merged campaigns after verification).
- **Recovery.** `lane8.py invalidate` and `quarantine` still require that no `c8x-` job of the user exists. After the
  A1 close, **`queue_a2` is the only recovery queue for b10–b14**; recovery of those batches through the A1 queue is
  prohibited (its workers can no longer run after the deadline, and its done markers for b10 are not used by
  anything: the A1-queue finalize and combine8 decide from checkpoints). b5–b9 are merged and verified under A1 and
  are not in `queue_a2`; a recovery of b5–b9 after the A1 close would be a new, separately documented decision.

## Closing rule and final result

- A2 closes when `queue_a2` has every element done, b10–b14 are merged and no `c8x-lane` job remains.
- Then, in this order: `finalize8.slurm` on `queue_a2` and on `queue` (both merge-only; expected no-ops), and
  `combine8.py` b1–b4 + b5–b14 `--extension runs/ext1/extension.json --closed` with the same `--affine`, `--exact5` and
  `--design-meta` as A1, into `results/C8_final_A2/` (`C8_final.json`). By the A1 mechanical rule every complete
  planned batch is included; the expected K is 14.
- **If A2 cannot complete** (elements abandoned after 3 failed attempts, or the cluster unavailable for long), the
  operator diagnoses and repairs under the A1 recovery rules. An A2 stop is used only on the user's instruction; the
  final result then follows the A1 rule (complete batches only, omitted batches reported with their completed
  fraction), and the shortfall is reported.
- The report quotes the A2 result (registered allowance rule) and, separately, the A1 deadline result and the
  original b1–b4 Expanse result.

## Expected cost

About 1,400 worker-hours from the A1 close (about a third of b10 plus four batches at ≈325 worker-hours each; two
workers per node): about 30 h on 23 nodes, 35 h on 20 nodes or 47 h on 15 nodes, so the final result is expected on
2026-10-14. Expected final SE ≈ 4,230 and allowance ≈ ±17,000 (4 SE dominates, as for b1–b8).

## Checks before and after submission

- Before: `submit_a2.sh arm` prints the A1-close job id; `queue_a2` does not exist; every A2 lane job shows
  `c8x-lane` and its partition.
- At the A1 close: the A1-close job log shows the snapshot (inclusion set, fractions), the published queue (2,490
  elements; `lane8.py status --queue runs/ext1/queue_a2` with b10 first) and the A1-close combination.
- About 10 minutes later: worker logs `worker_<job>_*` exist in `runs/ext1/queue_a2/logs` (not in the A1 queue's
  logs) and show b10 elements, those completed by A1 finishing in seconds (validated checkpoints skipped).

## Inspection round 1 (fresh Codex session, gpt-6-astra xhigh, REVISE) and dispositions

All three findings were accepted and fixed:
- A2-R1 (an inherited `C8X_QUEUE`, `C8X_TOOLS` or `C8X_MODE` could redirect A2 jobs, since `--export=ALL,VAR=value`
  does not reliably override an exported value): `submit_a2.sh` unsets every inherited `C8X_*`, exports the three
  pins, checks the `C8X_*` environment and submits with `--export=ALL`; the post-submission check confirms that worker
  logs appear in `queue_a2/logs` only.
- A2-R2 (the A1 deadline result was not preserved if it had to wait until after the A2 close, when combine8 would
  require b10–b14): an immutable A1-close snapshot (`a1_close_snapshot.py`) and a derived extension file restricted to
  the A1 inclusion set; the A1-close combination uses that file, so it is reproducible at any later time.
- A2-R3 (recovery through one queue leaves stale done markers in the other): after the A1 close, `queue_a2` is the
  only recovery queue for b10–b14; recovery through the A1 queue is prohibited; nothing reads the A1 queue's b10 done
  markers.

## Inspection round 2 (fresh Codex session, REVISE) and dispositions

All three findings were accepted and fixed:
- A2-IR-01 (a delayed snapshot could count A2-completed batches as A1's): the A1 inclusion set is derived from A1-queue
  done markers attributed to A1 lane jobs (plus complete checkpoints), never from checkpoint completeness alone.
  Dry run on live data (debugq job 573561, all writes redirected to scratch): inclusion b5–b8 at 08:59 EDT, b9 at
  0.689, b10–b14 at 0; no file written under runs/ or results/.
- A2-IR-02 (an inherited `SBATCH_JOB_NAME` could rename lane jobs, hiding them from recovery and finalize):
  `submit_a2.sh` unsets every `SBATCH_*`, passes `--job-name=c8x-lane`, refuses to run inside a job and verifies each
  submitted job's name and partition.
- A2-IR-03 (snapshot and derived file published separately; an interruption would block forever): restartable
  publication from the saved snapshot, with verification of an existing derived file.

## Inspection round 3 (fresh Codex session, REVISE) and disposition

- A2-REVIEW-01 (a batch whose final checkpoint was committed but whose done marker was cut off would be excluded,
  although A1's checkpoint-based rule includes it): accepted. Inclusion is now A1's checkpoint-completeness rule,
  with wave attribution by claims (no claim in `queue_a2`), and a barrier that stops the snapshot if any batch has
  claims in both queues.

## Inspection round 4 (fresh Codex session, REVISE) and disposition

- A2-R4-01 (claims read before checkpoints were scanned: an A2 checkpoint written during a delayed scan could be
  attributed to A1): accepted. Two passes: checkpoints of every batch first, then claims and done markers. A claim
  always precedes the checkpoints of its element, so every checkpoint observed in pass 1 that A2 wrote has its claim
  in the pass-2 listing.

## Inspection round 5 (fresh Codex session, REVISE) and disposition

- A2-R5-01 (queue position does not bound when A2 reaches b10: fast failures could move A2 workers through b11–b14
  and into b10 while A1 still owns claims there, after which no snapshot could be published): accepted. b10 is no
  longer in `queue_a2`; it is in `queue_a2b`, which can be created only after the A1-close snapshot is published and
  verified, and whose existence stops the snapshot script. `lane8_a2.slurm` runs the unchanged A1 launcher on
  `queue_a2` and then on `queue_a2b` when it exists.

## Inspection round 6 (fresh Codex session, REVISE) and dispositions

All three findings were accepted. They all came from running A2 next to a live A1 queue that also lists b10–b14, so the
design was changed instead of patched: A2 is now sequential.
- A2-R6-01 (fast failures could advance A1 into b11 while A2 already owned b11 claims): A2's queue is published only
  after every A1 lane job has ended and the A1 snapshot is recorded; A2 lane jobs that start earlier wait for it.
- A2-R6-02 (a STOP in one A2 queue did not stop the other): A2 has one queue; `runs/ext1/A2_CANCEL` (before and while
  waiting) and `queue_a2/STOP` (once published) stop all A2 work.
- A2-R6-03 (the b10 queue was created non-atomically while lanes ran): the queue is built in a staging directory and
  published by an atomic rename; an interrupted build is discarded and rebuilt.

## Inspection round 7 (fresh Codex session, REVISE) and disposition

- A2-R7-01 (`A2_CANCEL` also suppressed the A1 snapshot and the A1-close combination): accepted. `close` always makes
  the A1 record; `A2_CANCEL` only skips publishing the A2 queue (before staging, and before the rename with the
  staging directory removed) and `close` then succeeds. The A1-close job runs the combination whatever `close`
  returned; the combination itself requires the snapshot.

## Inspection round 8 (fresh Codex session, REVISE) and dispositions

Both findings were accepted:
- A2-R8-01 (the combination checked only that the snapshot files exist): `a1_close_combine.sh` first runs the snapshot
  script in restart mode, which verifies the snapshot (schema, extension.json digest) and that the derived file equals
  the one rebuilt from the snapshot, and refuses otherwise.
- A2-R8-02 (the documented manual rerun used `close && combine`): one shared job body, `a1_close_job.sh`, runs both
  steps unconditionally with the combined status; `arm` and the documented rerun both use it.
