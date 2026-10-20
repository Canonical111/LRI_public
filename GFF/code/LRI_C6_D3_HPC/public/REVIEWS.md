# Reviews of the C6(3) package and result

There were three independent reviews: of the delivered code, of the plan and code for production, and of the result.
The raw logs, transcripts and reviewer artifacts are not published; this file summarizes them.
- Reviewers: Claude (Anthropic) sessions and OpenAI Codex CLI 0.158.0 with `--model gpt-6-astra --effort xhigh`.
- Every Codex review was static (read-only).
- There was no human referee.

## 1. Review of the delivered package (2026-09-28)

**Reviewers.** Three read-only Claude reviewers:
1. the d=3 kernel against the reference code;
2. the assembly and inputs against the archived d=3 derivation;
3. a map of the C6(2) review findings onto this port.

There were also runs on a project workstation (Slurm jobs 946–951).

**Verdict.** The d=3 numerics are sound; nothing critical or high was found.
- **Kernel.** The worker computes the same integrand, measure and precision fallbacks as the original code built with
  `-DSPATIAL_D=3`. This was checked line by line in all three precision tiers.
- **Graph files.** They equal the forest and rate inputs token for token.
- **Archived streams.** Replaying the eight archived production streams (385,744,896 samples) gives equal fallback
  counts, per-graph jets equal to 2.2e-13, and the published refinement-only C6(3) = 33.560840352429125 bit for bit.
- **Assembly.** It is a line-for-line copy of the archived one. B2 matches an independent 85-digit record to 1e-54.

**Findings.**
- Carried over from the C6(2) review:
  - M1: binary and inputs hashed once for all blocks;
  - M2: unverified assembly inputs;
  - M3: the block structure caps efficiency;
  - L1–L19: Slurm templates, resumability, recovery, seed hygiene, tests rewriting evidence, file modes, and others.
- New for d=3:
  - D3-1 (medium): legacy seed arithmetic could replay archived streams;
  - D3-2 (medium): `--primitive-points` would destroy the variance-based allocation;
  - D3-3 (low): no regression test of the assembly on archived data;
  - D3-4 (low): the 300-digit tier was effectively untested. 515 of 516 relative point checks pass; the exception
    (graph L6G160 at scale 1e-130, 395 digits of cancellation) is identical to the original code.
  - D3-5 (low): untested layouts and branches;
  - D3-6 (info): zero-weight graphs, and the lower-order pull gate needs care.

**Author decisions.**
- Remove `--primitive-points` and keep the frozen allocation.
- Use hashed seeds, and in legacy mode refuse every archived seed.
- Apply the C6(2) rule to the single point beyond the 300-digit tier.
- Validation: the tests, the archived-stream replay, an Expanse smoke campaign, recovery and status drills, and a
  throughput pilot.

**Overruled recommendation.** The review suggested optional per-loop multipliers (1, 4, 2, 1), worth about 18% of
CPU at equal SE. The author chose a single multiplier and kept the frozen cross-loop split (plan decision D7).

## 2. Production readiness: claudex loop (2026-09-28)

Roles: Claude (Opus 5.5) planned and built; Codex gpt-6-astra reviewed the plan and inspected the code, each time in
a fresh session.

| round | verdict | findings | what changed |
|---|---|---|---|
| plan review 1 | REVISE | R1 (medium): no campaign-level serialization of submit/resubmit; concurrent merges collide. R2 (medium): an unescaped path in the SQLite URI. | Per-campaign submission lock, concurrent-safe merge, URI-safe database open |
| plan review 2 | **APPROVED** (plan sha256 14c089fa…) | none | — |
| inspection 1 (b3bdbb0) | REVISE | R-SLURM-01: `%` in `--output`. R-LOCK-02: lock left behind after an `owner.json` failure. R-MODE-03: 0600 input files. R-DOC-04: docs claimed pending Expanse evidence. | Fix round 1 (`382e752`) |
| inspection 2 (0fef6b8) | REVISE | R-PKG-05: checksum list omitted 98 evidence files. R-VAL-06: the Expanse validation ran on the compute partition instead of the planned shared partition. R-DOC-07: sample count. | Fix round 2 (`d3fb81d`); the calibration (`73d3635`) and the whole validation redone on the shared partition (job 54510646, smoke, drills, pilot); the compute-partition runs kept as a cross-check |
| inspection 3 (1c6dfb3) | **APPROVED** | none | — |

- The production ran `1c6dfb3`. There were no uninspected edits after the approval.
- The binary built from the final sources is byte-identical to the delivered one: `e22809aa…` on a workstation and
  `2f897044…` on Expanse.
- The reviewer stated these limits:
  - the review was static, and results and binary identity were judged from the saved records;
  - the remote campaign databases were not available to it;
  - the L6G160 exception was not rederived.
- The reviewer's Codex configuration kept a write-capable MCP server enabled (the author's earlier choice), and the
  reviewer was instructed to stay read-only.

## 3. Results review of C6(3) = 33.5754 ± 0.0005 (2026-10-01)

Reviewer: Codex gpt-6-astra, review mode. Coordinator: Claude. The claim was the result after Amendment 1.

- **Round 1: REVISE**, two low findings: "Static inspection identified no defect requiring a change to C6 or its
  stated sampling allowance."
  - C6-REPORT-01: "RQMC does better than 1/N" is unsupported, because the projection scales as 1/√N.
  - C6-REPORT-02: the C4 pull is −1.09, not −1.10.
  - The reviewer confirmed:
    - 4 × SE = 0.000474… → 0.0005;
    - all eight allocations equal the frozen tables × 8192;
    - the 64 replicates, the coordinate widths and the equal weights;
    - every production hash.
- **Changes.** Both findings were accepted. A dated Errata section was appended to `CAMPAIGN.md` (the original text is
  kept), and the note's sentence was corrected. The coordinator recomputed the estimator from the merged records on
  Apple arm64: it agrees with `C6_result.json` to 1 ulp.
- **Round 2: APPROVED.** "Both prior findings are resolved by the dated errata. No material unresolved defect was
  identified. C6(3) = 33.5754 ± 0.0005 is supported within its explicitly stated empirical sampling-only scope."
- **Limits** stated by the reviewer:
  - the coordinator's recomputation was not reproduced;
  - the raw checkpoints were not re-merged;
  - the analytic compensation and the framework were not re-derived;
  - digital resolution is controlled only empirically (52 vs 60 bits);
  - the preregistration chronology and the thread-identity check rest on the written log.

The public replay (`make -f public.mk replay`) recomputes the estimator and every quoted number from the merged
records. `make -f public.mk replay-full` (not yet run) re-merges the checkpoints from the hosted tarball and would
close the second limit.

## 4. Known open points

- **Amendment 1 was post hoc.** It changed the rounding step after the result was known. Under the registered step the
  allowance is ±0.001.
- **Thread identity.** The 64- vs 16-thread identity check (141,994 binary128 promotions) is documented only in
  `CAMPAIGN.md`; its logs stayed on the cluster.
- **Scope.** The allowance is sampling-only. The analytic power-sector compensation and the finite-MOM framework are
  taken over from the reference calculation and not redone. The independent C7(3) by-product (−0.79σ) shares that
  framework.
