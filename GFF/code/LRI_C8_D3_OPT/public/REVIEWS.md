# Reviews: LRI_C8_D3_OPT (independent check of C8(3))

Summary of the independent reviews. The transcripts, findings files and plan are not shipped.

## What was reviewed and what was not

- **Reviewed:** the cluster layer that C63d (Claude) added to the delivered package for Expanse and symmetry: the
  dispatcher's locks, leases, deadlines and signal handling (`tools/hpc_dispatch.py`), the admission and submission
  rules (`tools/submit.py`, `slurm/*.sh`, `slurm/sites/*`), the one change to a pinned tool (`tools/campaign.py
  run_job`), and their tests (`tests/test_cluster.py`). Scope of every round: `git diff dafa312..<head>`.
- **Not reviewed by an independent reviewer:** the delivered science code (worker, graph generation, low-loop
  inputs, assembly, fixed point), which the delivering AI (OpenAI GPT-6 astra) checked with its own tests and evidence (`verification/`,
  `tests/`), and **the production number 1600.98 +- 3.97: there was no results review.** Its checks are the replayed
  lower-order pulls (all |pull| <= 1.73), the a/b campaign split (0.64) and the comparison with the separately reviewed
  main C8(3) result (-0.40 combined standard errors; that result's results review is summarized in the main package's `REVIEWS.md`, `GFF/code/LRI_C8_D3_HPC`).

## Codex inspections of the cluster layer

Reviewer: Codex, model gpt-6-astra, reasoning effort xhigh, a fresh session each round. Builder of every fix: Claude
(C63d). All findings were accepted; no recommendation was overruled.

| round | head inspected | verdict | findings | fixed in | what changed |
|---|---|---|---|---|---|
| r1 (2026-10-09) | `f0f0cd5` | REVISE | 16 (R01-R10 high, R11-R16 medium) and one limitation | `a3b6b07` (+ `2470de1`, `704b148`) | token locks with fixed-name tombstone reclaim and token release; seed check and reservation inside the session lock; intents written before sbatch and reconciled afterwards; allow-listed plan and index arguments; queued jobs counted as running; strict squeue parsing; scheduler variables scrubbed; shared-partition billing; time validation and partition limits; grace-aware deadline; receipts checked before the deadline test; build tests only in a copy; canonical dispatch identity; array mode disabled; a controlled test environment. The limitation (assembly needs loops 3-8) went into the runbook. |
| r2 (2026-10-09) | `9583eca` | REVISE | 8 (3 high) | `6e3f139` | stale-lock reclaim only when squeue shows no active or completing allocation, sacct is terminal and a settle time has passed, with the token re-checked before publication; unresolved intents stay reserved; `--mem 0` refused; separate Expanse compute and shared classes; the account-wide running cap; node exclusions on symmetry; an environment check in every job script; **R2-08: `campaign.py run_job` re-checks the receipt after its lock and never replaces a receipted output** (a hash-pinned tool; accepted as a plan deviation, so only plans made after `6e3f139` can run, as `prod1` did) |
| r3 (2026-10-09) | `6e3f139` | REVISE | 8 (1 high) | `f7264e7` | no time-based release of intents (an operator's recorded resolve instead); one package per site and partition class instead of disjoint shares, because the main package's submitter cannot see this package's jobs; lanes only on the integration partitions; fail-fast environment files; one account value; an unknown job end defers bundles |
| r4 (2026-10-09) | `f7264e7` | REVISE | 3 medium, no high; r1-r3 fixes confirmed | `6fb5b5f` | the class handoff procedure covers Expanse shared jobs; `squeue -t all` so suspended jobs count; unresolved submissions of the main package occupy their class |
| (none) | | | | `d5deeb9` (2026-10-10) | **the production commit**: the user's 22-running-jobs cap counted only this package's queued jobs among the user's pending ones. Uninspected when production ran. |
| r5 (2026-10-12) | `d5deeb9` | REVISE | 3 (R5-01 high, R5-02 and R5-03 medium) | `3961865` | R5-01 reverts `d5deeb9`'s loosening (every non-terminal normal job of the user counts; other users' allocated jobs count for the account cap); SPECIAL_EXIT is live, not terminal; the reader of the main package's intents fails closed and validates every frame |
| r6 (2026-10-12) | `3961865` | REVISE | 1 medium (R6-01); R5-01 and R5-02 confirmed resolved | `6edcc9e` | the intent reader also reads the main package's ledger under the shared lock; any hold refuses. **Not inspected.** |

Consequences for the published result: every finding concerned admission, locking or restart safety. None touches
the integrand, the sampling, the allocation or the assembly. R5-01 means that `prod1` was admitted under a cap rule
that was looser than intended for the user's other jobs; the rule decides which jobs may run, not what they compute.
The production commit `d5deeb9` is exported; the fixes `3961865` and `6edcc9e` are not (they change only the
admission layer, which a public rerun replaces by the templates in `public/slurm/`).

## Validation runs (not reviews)

- Expanse builds 54781591, 54783728 and 54786481 (AMD EPYC 7742, 2026-10-09): all 14 steps PASS (delivery check,
  build, worker description, test copy, positive binary128 adder, native regression, point checks, optimization
  regression, dispatcher, streaming assembly, fixed point, campaign, allocation, cluster tests).
- Expanse smoke campaign `smoke1` (all loops, 16 points, 4 replicates, 772 jobs): killed by its deadline once,
  resumed, assembled (exploratory C8 = 2075 +- 396).
- symmetry: Intel test builds 572278 (one failure, the test-environment leak fixed as R16) and 572321 (all PASS); AMD
  EPYC 7543 build 573730 on `6edcc9e`, all 14 steps PASS (2026-10-12); smoke campaign `smoke_sym1`: deadline deferral,
  forced TERM stop with nothing left behind, resume and assembly (exploratory C8 = 550.8 +- 327, lower-order pulls
  <= 1.98).
- These exploratory 16-point estimates test the workflow, not the number.

## Replay added for the public release

`public/replay_check.py` (2026-10-13, not reviewed) recomputes the estimator, its standard error and every quoted
check from the stored records (`REPRODUCE.md`, section 3). It passed locally (76 PASS, 1 SKIP without the hosted pilot,
1 documented row; 79 PASS with the pilot statistics) and fails on a deliberately altered record.
