# Amendment A1: extension batches of the frozen C8(1) design on symmetry (2026-10-10)

## Goal

The user asked to improve the precision of C8(1) as much as possible on symmetry's idle Intel nodes within the defq
wall-time limit (24 h per job). Starting point: `results/2026-10_expanse/REPORT.md`, four batches b1–b4 of the frozen
design `prod4_34000`, C8(1) = 8,066,723, SE 8,015, allowance ±33,000 (4 SE). Each batch has SE ≈ 16,000 and costs
≈ 5,930 allocated core-hours on Expanse (498 elements of 16 cores, longest element 1.43 h).

Acceptance: more batches of the identical frozen design are added, combined with b1–b4 by the unchanged estimator, and
the result is reported with the unchanged pre-registered allowance rule. Nothing about the numerics changes.

## What does not change

- Kernel and binary: the Expanse-built `code/c0ffa63/bin/c8_integrate`, sha256 `ffb200d4…7db8b`, byte-identical
  (checked by every `campaign.py run` via the manifest digest and by the lane job before it starts).
- Production tools for plan/run/merge: commit c0ffa63, unchanged (`production8.py`, `campaign.py`).
- Frozen design bundle `designs_frozen/prod4_34000` (design, unit, counts, expected input hashes, forbidden seeds),
  affine map `analysis/v1/full_affine8.json`, exact loop-5 input (`runs/exact8_L5/exact_L5`, degrees 14 and 12).
- Estimator, assembly (`assemble8.py`), allowance rule, lower-order checks, coverage guard.
- Every extension batch must have exactly b1's scientific configuration (the `combine8.canonical()` fields plus the
  element list); `cluster/symmetry/plan8.slurm` checks this after planning and `combine8.py` re-checks it.

## What changes

1. **More batches.** Extension batches b5–b14, seeds 80840005–80840014 (b1–b4 used 80840001–80840004; the pilot
   batch seed 80810031 and all pilot/training campaign seeds stay forbidden and are checked at planning). More batches
   are planned than can finish, so the lanes never run dry. Batches are filled in order. (b13 and b14 were added on
   2026-10-10, together with the 48 h window below, before any extension element ran.)
2. **Site.** symmetry Intel Xeon Gold 6148 nodes (defq; preq with `--requeue` for the preq-only nodes cn069–076).
   The Expanse binary runs with the GCC 13.3.0 runtime libraries copied from Expanse (`rtlib_gcc13.3`, via
   `LD_LIBRARY_PATH`; the binary's RPATH points at Expanse paths that do not exist on symmetry). glibc/libm and
   Python (anaconda3 2023.07: Python 3.11.4, numpy 1.24.3, scipy 1.10.1; Expanse: 3.11.5, 1.26.4, 1.11.4) differ.
   Every new batch runs entirely on Intel; b1–b4 ran on AMD EPYC. The x87 long-double transcendental instructions
   differ between vendors at about 1e-16 relative (finding F5 of the C8 work), and libm may differ at the last bit.
   These are ~10^-13 of the per-batch sampling error and cannot bias the estimate. The smoke replay (below) measures
   the actual difference.
3. **Scheduling.** `tools/lane8.py` (new): one worker per NUMA node of a whole node, working through a batch-ordered
   queue. Ownership is by numbered attempt files (`claims/<element>.<n>`), published atomically (temporary file,
   fsync, no-clobber hard link in the same directory, as `campaign.py` publishes checkpoints; flock is node-local on
   symmetry's BeeGFS and is not used). The current owner is the highest attempt; its mtime is a heartbeat refreshed
   every 5 min while it runs. A worker first resumes its own current attempts (a requeued job keeps its id), then
   walks the queue in order and, at the first element needing work, claims it, retries it (current attempt failed,
   at most 3 failures) or takes it over (current attempt stale: no heartbeat for 30 min, or squeue answered, listing
   this worker's own job as RUNNING, and the owner job is not RUNNING; a failed or implausible query never counts as
   gone). A takeover creates attempt n+1, so the old owner never resumes it. Because the walk is in queue order,
   abandoned work in an earlier batch is always recovered before new work in a later one. A signal kill records no
   failure (the attempt simply goes stale). Each element is `production8.py run BATCH --index I` of the frozen
   tools; committed checkpoints are validated and skipped, and a concurrent duplicate is published once and never
   counted twice, so re-runs and duplicates are harmless. Merging uses the same attempt scheme
   (`merge/<batch>.<n>`, `.failed`, `.ok`); every worker reconciles merges at start, after each element and before it
   exits, and exits nonzero if a merge stays unresolved. `production8.py merge` resumes (verified campaigns are
   skipped) and is deterministic and no-clobber, so a duplicate merge is harmless. Scheduling never changes samples.
4. **Combination.** `combine8.py --extension extension.json [--closed]` (new). The amendment file lists the base
   batches (label, seed and the sha256 of each base batch's `production.json`) and the planned extension batches
   (label, seed, path). Labels, seeds and paths must be distinct; the base list must have exactly the frozen design's
   batch count (4) and every base batch must be given with its recorded `production.json`. Every **planned extension
   batch whose campaigns have all planned checkpoints** must be merged and included; a planned batch may be left out
   only when some planned checkpoint is missing. This makes the inclusion rule mechanical: completion, never values.
   Without `--closed` the output is `C8_interim.json` (final = false); `--closed` (no lane running or to be run)
   publishes `C8_final.json`. Weights are 1/K for K = 4 + included extension batches; the χ² is over the K per-batch
   estimates.

## Inclusion and closing rule (fixed before submission)

- The campaign is one wave of lane jobs submitted together at T0 (user decisions 2026-10-10: use longq to run past
  24 h; request a week for safety, with a 48 h budget): 15 longq lanes (cn053–067) requesting 7 days, 1 defq lane
  (cn051) and 8 preq lanes with requeue (cn069–076) requesting 24 h. Before submission the deadline T0+48 h is
  published once in the queue (`lane8.py deadline`, immutable `deadline.json`); every worker, including a requeued
  one, checks it before each claim and starts no element after it: it finishes its current element, merges
  completed batches and exits (so no element in progress is lost to a wall-time kill). `cluster/symmetry/stop8.slurm`
  (`--begin=T0+48h`, publishes STOP) is submitted as a second mechanism. No further lanes
  are added. The wave closes when every lane job has ended (STOP, wall time, or queue exhausted); an operator STOP
  earlier than T0+48 h is used only to release nodes, never after looking at results.
- After closing, `cluster/symmetry/finalize8.slurm` (`lane8.py finalize`, merge only, exclusive maintenance access)
  merges every batch whose planned checkpoints are all present, including one whose last done marker or merge was cut
  off; it never computes samples or runs elements.
- The final result combines b1–b4 and every extension batch complete at closing. A batch left incomplete at closing
  is reported as omitted, with its completed fraction. No finishing wave is run unless the user asks for one; if run,
  it may only complete batches that were already in progress, and that is reported.
- Interim combinations may be produced during the campaign for monitoring; they never change what is run.
- The headline result is the pre-registered rule applied to the final combination:
  ceil_2sf(max(4 SE, 2|R8|+4 SE_R8, 2|R9|+4 SE_R9, half-split shift, 2|loop-5 last degree step|) + 0.01).

## Validation before production

1. Local: `make test` (pipeline test now also covers the extension combination and a lane-runner pass, including the
   rejections: missing base batch, complete-but-unmerged batch omitted, incomplete batch given, unplanned batch,
   `--partial` with `--extension`, `--closed` without `--extension`).
2. symmetry smoke replay (`cluster/symmetry/smoke8.slurm`, debugq, not production): replay b1 elements 5, 84, 9, 10,
   11, 12 (power L6 degrees 1, 5/6, 6/7, 7/8, 8/9 and QMC L8) with the Expanse binary on symmetry in two variants at
   once (one thread per core on NUMA node 0; both hardware threads on node 1), and compare every replayed checkpoint
   row with the Expanse checkpoint (`smoke_compare.py`). The expected checkpoint set is derived from the manifest
   (every part of each element's shard at every degree); each must exist in both trees with identical row identities
   and widths. Pass (revised twice, see "Smoke replay result" and round 6 below): every replay exits 0; the two modes
   agree exactly in row identities and values; max |diff|/row scale ≤ 1e-10; and the estimator-scale bound on the
   shift of each replayed campaign's C8 contribution in one batch, (w/B)·Σ_k |M[8,k]|·Σ_rows |Δ_k| (both degrees of
   a paired level; M the frozen controlled map or Jacobian), extrapolated to the whole campaign, is ≤ 1e-6 of that
   campaign's per-batch C8 SE. The job exits nonzero otherwise. The faster variant sets the lane mode.
3. Planning (`cluster/symmetry/plan8.slurm` → `plan_ext.py`, task files hash-checked): labels, seeds and paths come from `extension.json`;
   every batch (new or planned earlier) must carry exactly its amendment label and seed, all labels and batch/campaign
   seeds must be distinct, and each configuration must be identical to b1's (canonical fields plus element list).
4. Environment check after the old batches are copied: `combine8.py` of b1–b4 on symmetry (without `--extension`)
   must reproduce Expanse's `C8_final.json` C8 value and SE to 1e-9 relative.

## Resources

The wave above: 24 whole Intel nodes (40 cores each), 15 of them until the 48 h STOP (plus the last element and
merges, about 1–1.5 h) and 9 for 24 h, ≈ 936–960 node-hours. One
15-node defq job of another user has been pending on "Reservation" since 2026-10-07. AMD nodes are not used (C8(3)
production of another session is queued there). Expected yield (smoke speeds, ≈ 5 h per batch on 24 nodes): about 8
extension batches, SE ≈ 4,700, allowance ≈ ±19,000.

## Files

- `tools/lane8.py`, `tools/combine8.py` (extension), `tests/test_pipeline8.py` (extension and lane tests).
- `cluster/symmetry/`: `env_symmetry.sh`, `cpusets.py`, `lane8.slurm`, `smoke8.slurm`, `plan8.slurm`.
- symmetry: `/mnt/beegfs/zzheng1/c8_hpc/` (code/c0ffa63 from Expanse, code/symmetry, code/<this commit>,
  runs/prod4 = b1–b4 copied from Expanse, runs/ext1 = extension batches and queue, results/).

## Inspection round 1 (Codex gpt-6-astra xhigh, REVISE) and dispositions

All eight findings were accepted and fixed:
- A1-R1 (queue logs directory missing at worker start): `lane8.py queue` creates every queue directory;
  `lane8.slurm` also creates `logs/` and refuses a queue without `order.json`.
- A1-R2 (smoke could pass on failures): per-PID exit status, derived expected checkpoint set, identity/width checks,
  enforced 1e-12 threshold, nonzero exit (`smoke_compare.py`).
- A1-R3 (merge claim could block forever; no merge after a restart): attempt-based merge ownership with heartbeat,
  failure retry and takeover; reconciliation at start, after each element and before exit; nonzero exit when
  unresolved.
- A1-R4 (stolen work not recoverable): one ownership scheme for all attempts; takeover creates attempt n+1, which its
  owner can resume and others can take over again.
- A1-R5 (recovery only after all unclaimed work): a single in-order walk claims, retries or takes over at the first
  element needing work.
- A1-R6 (non-atomic claim files): atomic publish; unreadable leftovers go stale by mtime and are taken over.
- A1-R7 (base set not bound): exact frozen base count, base `production.json` digests in the amendment, distinct
  labels/seeds/paths, K = 4 + included extension batches.
- A1-R8 (reused plans not checked): `plan_ext.py` checks every batch's label and seed against the amendment and
  rejects duplicate batch or campaign seeds.
Tests: `tests/test_pipeline8.py` adds the amendment rejections (base count, duplicate label, wrong base record) and
lane ownership cases (stale attempt of another job taken over, own attempt resumed, unreadable leftover taken over,
stale merge claim taken over).

## Inspection round 2 (fresh Codex session, REVISE) and dispositions

All seven findings were accepted and fixed:
- A1-R2-01 (declared batch without metadata could be omitted): every declared extension batch must have a readable
  `production.json` with its amendment label and seed and hash-checked campaign plans; missing metadata is an error.
  A batch is incomplete only when its validated plan has missing checkpoints (`checkpoint_counts`).
- A1-R2-02 (reused plans could carry foreign campaign seeds): `plan_ext.py` checks that every campaign seed is
  production8's derivation from the declared batch seed and campaign name, and that none equals a base-batch or
  bundle-forbidden campaign seed.
- A1-R2-03 (abandoned work reported as success): a worker exits nonzero when elements are abandoned or a ready batch's
  merge is unresolved; merges in progress elsewhere are reported as pending.
- A1-R2-04 (markers trusted by name): `merge/<batch>.ok` is trusted only while every campaign still has its audit;
  `lane8.py quarantine` (the only sanctioned quarantine for queue-managed batches) runs `campaign.py quarantine` and
  moves the element's done marker and the batch's merge marker aside, so the lane recomputes and re-merges;
  `lane8.py invalidate` redoes one element.
- A1-R2-05 (signal kills counted as failures): the worker installs SIGTERM/SIGINT handlers (Slurm signals every
  process of the job at wall time, preemption or scancel) and records no failure for an attempt interrupted while
  the flag is set.
- A1-R2-06: omitted batches record present/planned checkpoints, the completed fraction and the reason.
- A1-R2-07: `combine8.canonical()` includes the production element list.
Tests add: declared-but-unplanned extension batch rejected; omitted-batch completion fraction; queue-aware
quarantine followed by recomputation and an identical re-merge.

## Inspection round 3 (fresh Codex session, REVISE) and dispositions

All five findings were accepted and fixed:
- A1-R3-01 (omitted batch with inconsistent metadata): every declared but uncombined extension batch must have
  planning metadata whose scientific configuration (`planned_configuration`, the canonical fields read from the
  manifests with hash-checked task plans) equals the combined batches', planned against the frozen bundle, with
  campaign seeds derived from its batch seed; otherwise the combination fails instead of omitting it.
- A1-R3-02 (failed merge left without a retrier): a worker retries a failed merge in the same reconciliation until it
  succeeds or MAX_FAILURES attempts failed; "pending" now means only a live attempt of another worker.
- A1-R3-03 (recovery kept exhausted budgets): `invalidate`/`quarantine` archive the element's and the batch merge's
  failure records with the done/ok markers (history kept in `invalidated/`) and publish `reset` attempts, which the
  next worker claims with a fresh retry budget.
- A1-R3-04 (racy marker invalidation): archive moves tolerate a concurrent move and use unique names.
- A1-R3-05 (smoke parsed long doubles as binary64): `smoke_compare.py` parses with `parse_float=Decimal`.
Tests add: tampered metadata of an omitted batch rejected; an abandoned element makes the worker exit 1 and is
recovered by `invalidate` (claimed as attempt 4 after the reset).

## Smoke replay result (job 572700) and revision of its row bound

The first replay (b1 elements 5, 84, 9, 10, 11, 12; both modes) completed every element and produced every expected
checkpoint with identical row identities. Power rows (L6, degrees 1 and 5–9) differ from Expanse by at most
4.7e-14 of the row scale (most 1e-18 to 1e-15). The L8 QMC rows of element 84 differ by up to 6.0e-12 of the row
scale, which failed the pre-set row bound of 1e-12. Diagnosis: (a) the 20-thread and 40-thread replays on symmetry
are bitwise identical row by row, so the result does not depend on the thread count and the difference is a
deterministic platform effect (Intel x87 transcendentals and Ubuntu glibc libm versus AMD and Rocky glibc); (b) per
checkpoint and slot, the row-sum difference is at most 1.6e-15 of sqrt(n) times the row standard deviation.
(Round 6 pointed out that row dispersion is not the estimator's sampling scale, which comes from replicate totals
after degree pairing and projection; the "15 orders below the noise" reading is withdrawn and replaced by the
estimator-scale bound below.) The large row-relative differences occur in
rows with strong internal cancellation (small values relative to the row scale). The row bound of 1e-12 was an
arbitrary pre-set number ("expected ~1e-16") that did not anticipate this amplification; it is replaced, before any
production, by a row sanity bound of 1e-10 plus an estimator-scale bound (round 6), and the modes must agree
exactly. The comparison is re-run on the same replay with the revised script.
Speed (wall seconds, one 20-core socket vs Expanse 16 EPYC cores): element 5: 186 (phys) / 173 (ht) vs 271;
element 84: 378 / 329 vs 435. Lane mode: ht. One Intel node ≈ 45–50 Expanse cores; ≈ 5 h per batch on 24 nodes.

## Inspection round 4 (fresh Codex session, REVISE) and dispositions

All three findings were accepted and fixed:
- A1-R4-01 (regrouped checkpoint layout could pass as incomplete): the canonical campaign configuration (combined
  batches, omitted batches and `plan_ext.py`) now also binds the manifest's shard list (ids, task files and their
  sha256, work units), checkpoint_tasks, chunk_points, total_work_units and samples_per_degree. These are identical
  across b1, b2, b4, b5 and b12 (checked on symmetry), so the base combination is unaffected.
- A1-R4-02 (included batches skipped the seed derivation): every combined batch (base and extension) must have campaign
  seeds derived from its batch seed, checked before inclusion and omission are decided.
- A1-R4-03 (recovery racing active workers): `lane8.py invalidate` and `quarantine` refuse to run unless squeue
  answers and lists no `c8x-lane` job of the user in any state; recovery is done only with the lanes stopped.
Tests add: a regrouped (checkpoint_tasks) omitted batch rejected; a relabelled batch whose campaign seeds are not
derived from its declared seed rejected; recovery runs against a fake empty squeue.

## Inspection round 5 (fresh Codex session, REVISE) and dispositions

All four findings were accepted and fixed:
- A1-R5-01 (comparator crashed on multipart elements: the slot mean shadowed the manifest): separate variables; the
  rerun of the comparison on replay 572700 (job 572702) had hit exactly this crash.
- A1-R5-02 (mode equality compared timings): modes are compared on row identities and exact values only.
- A1-R5-03 (statistical bound skipped for zero variance or one row): a zero-variance slot requires an exactly equal
  sum; a single-row checkpoint has no sample sd, so only the row bound applies, and the output says so.
- A1-R5-04 (worker could exit while a sibling's dead attempt was not yet stale): with nothing claimable, a worker waits
  (5 min) and rescans while unfinished elements or pending merges are held by others, until done/abandoned, STOP or a
  signal.
Tests add: comparator on a campaign with two checkpoint parts and two degrees (equal values with different timings
pass; a value beyond the row bound fails; a changed zero-variance slot fails).

## Inspection round 6 (fresh Codex session, REVISE) and dispositions

All three findings were accepted and fixed:
- A1-R6-01 (smoke statistic not on the estimator scale): replaced by the conservative bound on the shift of the
  campaign's C8 contribution in one batch, (w/B)·Σ_k |M[8,k]|·Σ_rows |Δ_k| over both degrees of a paired level, with
  M the frozen controlled map (power) or Jacobian (free/exact), extrapolated linearly from the replayed shard's work
  units to the campaign and divided by the campaign's per-batch C8 SE (2 × its SE in the b1–b4 combination); bound
  1e-6. Because it uses absolute row differences, no cancellation pattern can hide a shift. The earlier
  "15 orders below the noise" statement is withdrawn.
- A1-R6-02 (interrupted quarantine not restartable): `lane8.py quarantine` invalidates the queue state first, then
  moves the checkpoint; a rerun finds it already quarantined, re-invalidates, and invalidates the audit if an
  interruption left it in place. Recovery still requires stopped lanes.
- A1-R6-03 (reused plans' task files not hash-checked): `plan_ext.py` runs `campaign.blocks()` over every campaign of
  b1 and of every extension batch, so a missing or altered task file fails before submission.
Tests: comparator on the estimator scale (equal values with different timings pass; a value beyond the row bound
fails; a sub-row-bound offset passes against a realistic SE and fails against a tiny one; modes that disagree fail);
quarantine rerun.

## Inspection round 7 (fresh Codex session, REVISE) and dispositions

Both findings were accepted and fixed:
- A1-R7-01 (recovery did not exclude non-lane writers): `lanes_quiescent` refuses while squeue lists any job of the
  user whose name starts with `c8` (every C8 launcher on symmetry, including any standalone merge, uses such a name)
  and publishes a `MAINTENANCE` marker; lane workers neither claim, run nor merge while it exists. It is removed only
  after a successful recovery (a failed one leaves it for the operator).
- A1-R7-02 (smoke gate could pass with no elements): `smoke8.slurm` rejects an empty element list; `smoke_compare.py`
  rejects no elements or modes, fails when no checkpoint was compared, and exits 3 unless the qualifying set
  (elements 5, 84, 9, 10, 11, 12 in modes phys and ht) was compared; `C8X_SMOKE_DIAGNOSTIC=1` (tests only, never
  set by `smoke8.slurm`) reports a reduced run instead of gating it.
Tests add: recovery refused while another C8 job exists, with no marker left; comparator rejections for no element
and for a non-qualifying set.
The 48 h window and batches b13–b14 (user decision, same day) are part of this revision.

## Inspection round 8 (fresh Codex session, REVISE) and dispositions

Both findings were accepted and fixed:
- A1-R8-01 (recovery admission race): `lanes_quiescent` publishes `MAINTENANCE` first and only then requires an
  answering squeue with no `c8*` job of the user in any state, now including the job the command may run in (recovery
  is run from the login node); on refusal it removes its own marker. A worker that is already past its marker check
  belongs to a job that squeue lists, so recovery refuses; a worker starting later waits. On symmetry the
  queue-managed batches are written only by lane8 workers (merges run inside the lanes); standalone `production8.py`
  run/merge on them is not supported (`cluster/merge8.slurm` is the Expanse template and is not used here).
- A1-R8-02 (inherited diagnostic bypass): the diagnostic mode of `smoke_compare.py` is an explicit leading
  `--diagnostic` argument (no environment variable); `smoke8.slurm` never passes it and replays the fixed qualifying
  element set (its element list is no longer configurable).
Tests add: a worker started while `MAINTENANCE` exists claims nothing; recovery refused while a marker exists; an
inherited `C8X_SMOKE_DIAGNOSTIC=1` does not turn a non-qualifying comparison into a pass.

## Inspection round 9 (fresh Codex session, REVISE) and dispositions

The finding was accepted and fixed:
- A1-R9-01 (no supported finalization for a batch completed at the very end): `lane8.py finalize` (and
  `finalize8.slurm`, job name `c8x-finalize`) runs after the wave under exclusive maintenance access (the only `c8*`
  job allowed is the finalize job itself, matched by id and name); for every queued batch it derives completion from
  the hash-checked planned checkpoints, merges complete batches with the frozen `production8.py merge` (resuming an
  interrupted merge; done markers are not required), publishes `merge/<batch>.ok`, and reports incomplete batches
  with their checkpoint fraction without running anything.
Tests add: a batch with every checkpoint, no done markers and one campaign merged before the cut is merged by
finalize; an incomplete batch is reported and left; finalize refuses while a lane job exists.
Also in this revision (user decision): longq lanes request 7 days and the pre-registered STOP at T0+48 h ends the
wave (`stop8.slurm`).

## Inspection round 10 (fresh Codex session, REVISE) and dispositions

Both findings were accepted and fixed:
- A1-R10-01 (inherited squeue filters could hide writers): one scheduler query (`squeue_jobs`) removes every
  `SQUEUE_*` variable, asks for all states (`-t all`) and rejects malformed lines; exclusivity counts every
  unfinished job (any non-terminal state) of this package. While checking the live format on symmetry it turned out
  that another session's C8(3) jobs are named `c8d3-…`, so the package prefix is now exactly `c8x-` (every job of
  this package: lane, plan, smoke, recheck, stop, finalize); jobs of other packages, which write other directories,
  and the `c8x-stop` job (it only writes STOP) do not block.
- A1-R10-02 (48 h cut depended on the stop job starting): the immutable `deadline.json` in the queue is enforced by
  every worker before each claim; the scheduled stop job remains as a second mechanism.
Tests add: an inherited `SQUEUE_PARTITION` cannot hide a pending lane; a malformed answer is refused; finished jobs,
another package's jobs and the stop job do not block finalize; a passed deadline means no claim; the deadline cannot
be republished.

## Inspection round 11 (fresh Codex session, REVISE) and disposition

- A1-R11-01 (a claim could start after the deadline because the check preceded a slow scheduler query): the deadline
  and STOP are rechecked after the scheduler query, before publishing or resuming any claim, and immediately before
  launching `production8.py run`; a claim acquired across the cutoff is left unstarted. Test: the deadline passes
  while a (fake) squeue sleeps; no claim is published and nothing starts.
