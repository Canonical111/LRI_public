# REVIEWS: LRI_C8_HPC (C8(1), one-dimensional long-range Ising model, eighth order)

This file summarizes every independent review of the package. The raw review logs, transcripts and runner outputs
are not published, so this summary replaces them. Finding identifiers (C8-R01, A1-R2-03, ...) are the original ones.
They match the commit messages and the per-round disposition tables in `docs/EXTENSION_A1.md`, `EXTENSION_A2.md` and
`EXTENSION_A3.md`, which ship with the code.

**Setup common to all stages.** The package author and coordinator was a Claude Code session. It wrote the code, the
amendments and every fix. The reviewer was OpenAI's Codex CLI in a read-only sandbox. Every round requested model
`gpt-6-astra` at reasoning effort `xhigh`. The runner did not record which model actually served a round (its
observed-model field is empty in all 45 rounds), so the served model is "not recorded". Each code or amendment
inspection round was a fresh Codex session. It saw the plan plus every changed file against a fixed base commit. The
results review used one session (round 1), resumed for rounds 2 to 4. All reviews were static: the reviewers ran no
tests, numerics or jobs, and they did not inspect live cluster state or checkpoints. The approvals say this in their
stated limitations. The reviewed commit of each round was identified from the runner snapshot, which lists the
SHA-256 of every reviewed file. These hashes equal the files of the named commit (checked with git for every amendment
round and for code rounds 1, 8, 9 and 10). For the code inspection, the `c8-review` branch also names each round's tree.

## 1. Stages

| Stage | Dates (2026) | Reviewer | Rounds | Final verdict | Reviewed commit / plan SHA-256 | Findings |
|---|---|---|---|---|---|---|
| Code inspection of the C8 package (plan `PLAN.md`, base bbb3338 = C7 package + verified C8 inventory) | 10-02 | Codex CLI 0.158.0; gpt-6-astra, xhigh requested; served model not recorded | 10 | APPROVED r8 (1c9a6f3); after post-approval changes REVISE r9, APPROVED r10 | c0ffa63 (production code); PLAN.md 7dbf2469… | 26 (10 high, 15 medium, 1 low) |
| Amendment A1: extension batches b5–b14 on symmetry (`docs/EXTENSION_A1.md`, base 78e6a8a) | 10-10 | Codex CLI 0.162, Fast mode; gpt-6-astra, xhigh requested; served model not recorded | 12 | APPROVED r12 | 15a110e; plan 7efa851c… | 38 (8 high, 27 medium, 3 low) |
| Amendment A2: complete b10–b14 in a second wave (`docs/EXTENSION_A2.md`, base 15a110e) | 10-12 | as A1 | 9 | APPROVED r9 | 4adf719; plan 3f958f71… | 15 (7 high, 7 medium, 1 low) |
| Amendment A3: b12–b14 on Expanse (`docs/EXTENSION_A3.md`, base 4adf719) | 10-12 | as A1 | 10 | APPROVED r6 (eb25c8e); after the early-export change REVISE r7–r9, APPROVED r10 | bd13a63; plan 1cb32f78… | 27 (2 high, 25 medium): 19 before r6, 8 after |
| Results review of the K = 14 result (dossier `RESULTS_REVIEW.md`) | 10-13 | as A1 | 4 | APPROVED r4 | dossier rev 4 a5a3e5cf…; REPORT.md at 1282e37 (r1 read HEAD 9dd3a6b) | 8 (4 medium, 4 low) |

In total there were 45 rounds and 114 findings. Every finding was accepted (Section 3 gives the exceptions in how
they were resolved).

## 2. Findings and what changed

**Code inspection.** The rounds reviewed these trees (findings in brackets): r1 d9f300b (11), r2 3c29000 (4),
r3 8b5a690 (3), r4 0f4ff50 (3), r5 f57a3c1 (1), r6 b195a0c (2), r7 6c048f0 (1), r8 1c9a6f3 (0, APPROVED),
r9 5ff54ae (1), r10 c0ffa63 (0, APPROVED).
- Assembly completeness and binding (R01, R02, R06, R19, R21, R23). Fixed list of sampled loops and levels, including
  the 8→9 check. One canonical level/degree table. Exact inputs must be complete. The loop-5 input is frozen in the
  design. Loop 5 runs in one campaign only. A final combination needs the frozen batch count, and partial results are
  labelled as partial.
- Input and design integrity (R03, R08, R12, R16). Input hashes must be identical across sources. The frozen pilot
  input hashes are enforced at planning and at assembly. The design bundle is written atomically with digests and
  re-verified at final assembly.
- Independence of random streams (R04, R13). Pilot and control-training seeds are forbidden in production, and a seed
  shared by two campaigns is rejected.
- Budget and work sizing (R09, R14, R17, R26). Integer allocation under the budget. Costs are in allocated core-hours
  from the measured pilot efficiency over all submission attempts. Power-mode tasks have a bounded length.
- Failure propagation (R05, R07, R10, R11, R15, R20). Long-double test output is parsed exactly as Decimal (the
  validation was rerun on Expanse and all checks passed). Failed checks give nonzero exits. The weights job derives
  every required degree from the designs and checks each child process. Deterministic campaigns are merged before
  the affine map. The weight files generated earlier were kept: all required files exist and are hash-bound in every
  campaign manifest.
- Code defects and documentation (R22, R24, R25, R18). An uninitialized variable on the assembly path; an unreachable
  assignment in the combiner; a bootstrap whose memory is now bounded by resampling only the C8 column in blocks; a
  new C8 README, with the C7 documents moved to a historical folder.
- After approval r8, running `design8` on the real pilot asked for an infeasible number of replicates. Commit 5ff54ae
  split the multiplier into replicates and a sample multiplier. It also added a QMC per-graph point floor, because
  the pilot's L7 QMC distribution at 64 points per graph was skewed. Round 9 found unbounded power tasks (R26), fixed
  in c0ffa63, which round 10 approved.

**Amendment A1.** Rounds: r1 79d348b (8), r2 769dd4a (7), r3 ad373bd (5), r4 cb86c79 (3), r5 527f72f (4),
r6 8a84105 (3), r7 2413ec0 (2), r8 91fd099 (2), r9 da0aad0 (1), r10 2ed1941 (2), r11 fa82268 (1),
r12 15a110e (0, APPROVED).
- Inclusion rule and combination integrity (A1-R7, R8, R2-01, R2-02, R2-06, R2-07, R3-01, R4-01, R4-02, R6-03). Base
  batches are bound to the frozen count and records. Every declared extension batch needs validated metadata.
  Omitted batches are checked against the combined configuration, including the shard layout, and are reported with
  their completion fractions. Campaign seeds must derive from the batch seed and differ from base and pilot seeds.
  Reused plans have their task files hash-checked.
- Lane runner ownership and recovery (A1-R1, R3–R6, R2-03–R2-05, R3-02–R3-04, R4-03, R5-04, R6-02, R7-01, R8-01,
  R10-01). Queue directories are created up front. Ownership is attempt-based, with a heartbeat and takeover. Claims
  are atomic. Merges are reconciled and retried. Abandoned work gives a nonzero exit. Markers are trusted only together
  with their audits. Signal-interrupted attempts are not counted as failures. Recovery runs only under an exclusive
  maintenance marker, with a sanitized all-state scheduler query and a fixed package job-name prefix.
- Deadline and closing (A1-R9-01, R10-02, R11-01). A merge-only finalize step runs after the wave. Every worker enforces
  an immutable deadline, rechecked after scheduler queries and again just before an element starts.
- Smoke replay comparison (A1-R2, R3-05, R5-01–R5-03, R6-01, R7-02, R8-02). Per-process exit status. The full expected
  checkpoint set is required. Long doubles are parsed exactly. Comparator bugs were fixed. The bound is on the
  estimator scale. The qualifying element set is fixed, with no environment bypass.
- User decisions folded into the revisions were inspected in later rounds: the 48-hour window and batches b13–b14
  (round-7 revision), and 7-day longq requests with a pre-registered stop at T0 + 48 h (round-9 revision).

**Amendment A2.** Rounds: r1 bea184d (3), r2 3f0e071 (3), r3 2b642f0 (1), r4 92377ad (1), r5 e191f4c (1),
r6 e42cdf8 (3), r7 b52b19f (1), r8 28d28c7 (2), r9 4adf719 (0, APPROVED).
- Preserving the A1 result (A2-R2, IR-01, IR-03, REVIEW-01, R4-01, R7-01, R8-01, R8-02). An immutable A1-close
  snapshot and a derived inclusion file. Inclusion follows A1's checkpoint-completeness rule, with claim-based wave
  attribution and a two-pass scan (checkpoints first, then claims). Publication is restartable. The A1 record is made
  whatever happens to A2. The combination verifies the snapshot. One shared job body runs both steps.
- Separating the waves (A2-R3, R5-01, R6-01–R6-03). After rounds 5 and 6, A2 was made sequential. Its single queue is
  published atomically only after every A1 lane has ended and the snapshot is recorded. One stop mechanism covers the
  whole wave, and one queue handles recovery.
- Submission environment (A2-R1, IR-02). Inherited `C8X_*` and `SBATCH_*` variables are cleared, the job name is
  explicit, and submissions are checked afterwards.

**Amendment A3.** Rounds: r1 8d2df66 (5), r2 4f24314 (6), r3 46727b4 (2), r4 124e54f (2), r5 3a36737 (4),
r6 eb25c8e (0, APPROVED), r7 b9a9bf6 (2), r8 9e5ed07 (4), r9 6096b92 (2), r10 bd13a63 (0, APPROVED).
- Expanse submission and scheduler handling (A3-01–A3-03, R8-02). Journaled submission with validated job ids.
  Sanitized all-state queries that fail closed. Retry accounting over all retried states. Lane8's set of terminal
  states.
- Closing on symmetry (A3-04, R2-01, R2-03, R2-04, R4-01, R4-02, R5-02). The close is complete-only: it requires all
  of b5–b14 and K = 14. The close lock and the quiescence check apply on every run. Imports are registered. The close
  job verifies each staged copy itself, with receipts, before installing it. A stop/publication handshake. An atomic
  closing record.
- Stop barrier and locks (R2-02, R3-01, R5-03, R8-04, R9-02). A submit lock serializes run, resubmit, merge and stop.
  A durable stop marker is honored by submission and by tasks. The export holds the lock. Merges honor the stop and
  require a journaled array and a complete batch.
- Transfer integrity (R3-02, IR-02, R8-01, R8-03). Manifest digests are computed and validated in Python. Remote
  shells use pipefail. Tree traversal is strict and rejects symlinks. Symmetry submission is pinned.
- The early export (b9a9bf6, a user request after approval r6) was inspected in r7–r10. A3-IR-01 led to stating it as
  a speculative start, with a failure-free gate and a discard policy. For A3-R9-01, see Section 3.
- Withdrawn features (A3-05, R2-05, R2-06, R5-01, R5-04): the stopped close and the Expanse quarantine path; see
  Section 3.

**Results review.** Rounds: r1 dossier rev 1 (170b44d0…) with HEAD 9dd3a6b (5); r2 rev 2 (ad3dab33…) with REPORT.md
at 1bccd7c (2); r3 rev 3 (9a4fd78e…) with REPORT.md at 4fe7f05 (1); r4 rev 4 (a5a3e5cf…) with REPORT.md at 1282e37
(0, APPROVED). Rounds 1–3 identified no numerical correction to the headline estimate, round 2 confirmed that the
result file was unchanged, and round 4 found nothing outstanding. All eight findings concern wording or disclosure.
- Controls (C8-REV-01, C8-R2-01). The pole columns enter the estimate through the frozen controls. Their C8
  projection, +11,078 ± 24,734, is now reported. Finite-degree control error lies inside the allowance (through the
  R8 and R9 terms). A failure of the exact pole identity would be a framework error outside it.
- Statistics (C8-REV-02). The χ²₃₀ p-value was removed, because the columns are correlated. Σz² = 39.8 is descriptive
  only.
- Chronology (C8-REV-03, C8-R2-02, C8-R3-01). The report now states A1's deadline rule as executed, and A2's decision,
  taken after the K = 5–8 interims were visible. The b10 completion fraction is attributed to the A1 closing snapshot.
- Wording (C8-REV-04, C8-REV-05). The early-export reach bound is a scheduling estimate, not a guarantee. Seven
  batches (b5–b11) ran on Intel, not ten.

## 3. Recommendations not adopted / overruled

No finding was rejected or deferred in any stage. Every disposition file and amendment table records each of the 114
findings as accepted. Five points need stating:
- **A3 stopped-campaign close (A3-05, A3-R2-02, A3-R2-05).** A3-05 asked for a close procedure after a user stop, and
  round 1 implemented one. A3-R2-05 then showed that it could not handle a stop before queue publication or export.
  The coordinator withdrew the stopped close rather than extend it phase by phase. Halting stays implemented (A3-R2-02
  was adopted only for halting) and the result rule after a stop is fixed in advance. However, no stopped result will
  be published until a procedure for the actual state has been written and independently reviewed. Round 6 approved
  the amendment with the stopped close withdrawn. The campaign closed complete (K = 14), so this path was never needed.
- **A3 Expanse quarantine path (A3-R2-06, A3-R5-01, A3-R5-04).** The quarantine support added for A3-R2-06 was found
  to be non-restartable and to leave identities unvalidated. Instead of the suggested fixes, the path was withdrawn: a
  corrupt Expanse checkpoint halts that batch's Expanse work until a reviewed recovery procedure exists. Round 6
  approved this.
- **A3 early-start tripwire (A3-R9-01).** The reviewer offered two options: implement a persistent failure watcher, or
  disable the early export. The coordinator chose neither. It removed the tripwire and kept the early export. The
  stated reason: the tripwire only limited wasted compute; correctness is enforced by the close-time snapshot and
  installation checks; and the stated worst case is about 6k SU discarded per overlapped batch. Round 10 approved
  this. The A1-close snapshot later recorded b12–b14 as untouched by A1 workers, so no Expanse copy was discarded.
- **A1 smoke threshold.** A1-R2 asked for the pre-set row bound of 1e-12 to be enforced, and it was. The first
  symmetry replay then failed it: L8 QMC rows differed from Expanse by up to 6.0e-12 of the row scale, a deterministic
  platform effect (the two thread modes agreed bitwise). Before production, the coordinator replaced the bound with a
  row bound of 1e-10 plus an estimator-scale bound of 1e-6 of the per-batch SE. Rounds 4–6 inspected the change, and
  round 6 corrected its first statistical form.
- One registered rule was overridden by the user, not by a reviewer. A1 allowed a finishing wave only for batches
  already in progress. A2 runs all of b10–b14. The user took this decision after interims of five to eight batches
  had been seen. A2 discloses it and was inspected with it, and the results review required the chronology to be
  stated (C8-REV-03).

## 4. Not reviewed

- **Code inspection.** The production code c0ffa63 is the tree approved in round 10. Commit 78e6a8a (the K = 4
  result) changes only files under `results/`. Some work ran before approval, on intermediate trees. The exact stage
  and the pilot were planned before the round-1 fixes (disposition of C8-R03). The pilot ran from code copy ce5074e
  (= commit 4666608), the tree inspected in round 1. The post-pilot job (merges, affine map, controls, preview) ran
  b195a0c, the tree of round 6. The kernel sources `src/` are identical in 4666608 and c0ffa63. `affine8.py`,
  `controls8.py`, `campaign.py` and `production8.py` are identical in b195a0c and c0ffa63. The sources contain no
  separate results review of the K = 4 result. The K = 14 results review covers the final result.
- **A1.** Approved at 15a110e, and the A1 lanes ran tools 15a110e. `tools/`, `src/`, `tests/` and `gen/` do not change
  from 15a110e to bd13a63.
- **A2.** Approved at 4adf719. The only later change to an A2 file (`cluster/symmetry/submit_a2.sh`, queue reduced to
  b10–b11) came with A3 and was inspected there.
- **A3.** The final A3 tools bd13a63 were approved: round 10 returned APPROVED, and its snapshot matches bd13a63 file
  by file. The A1-close job ran the eb25c8e copy (approved r6), whose `cluster/symmetry/` scripts are identical in
  bd13a63. The Expanse export (15:12 EDT) followed the round-10 verdict.
- **After bd13a63.** Commit 9dd3a6b adds results and records only (`results/2026-10_ext1/`). Commits 1bccd7c, 4fe7f05
  and 1282e37 change only `REPORT.md`. The results review covers all four: round 1 read HEAD 9dd3a6b, and REPORT.md
  at 1282e37 was an input of the approving round 4. Outside `results/`, the exported code tree (1282e37) is identical
  to bd13a63.
- **Limits of the results review.** The review was static. Remote checkpoints, merged replicate data and detailed
  incident logs were not inspected, and the physics framework was not validated. The reviewer read the
  condensed-note merge script but did not run it and did not compile the note. The note commit (fa71533, 11:49 EDT)
  followed the round-4 verdict, so the merged note text itself was not reviewed. The script file was last written at
  11:49, and the sources do not record whether its content changed after rev 4.

## 5. Public-edition files

The files written for this release (`public/replay8.py`, `public/verify8.py`, `public/test_tools_portable.py`, with
`public.mk` and the Slurm environment template) were added after all reviews. No second model reviewed them, and no
review artifact mentions them.
