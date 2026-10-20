# Reviews of the C8(3) calculation (LRI_C8_D3_HPC)

All reviewers were AI systems. There was no human referee. The builder and coordinator was a Claude Code session (C63d).
The reviewer was OpenAI Codex (CLI 0.158–0.162) with model gpt-6-astra at reasoning effort xhigh, in read-only review mode.
The raw logs, transcripts and review artifacts are not published; this file summarizes them.

## 1. Plan review: APPROVED in round 7

- **What was reviewed.** The implementation plan of the package (`PLAN.md`, 2,503 lines in round 1, 5,283 lines when
  approved), generalizing the C7(3) package `LRI_C7_D3_HPC@a6ce987` to eighth order, with the recon of the inherited code,
  the shared nine-vertex inventory (H1) and the shared order-8 assembly.
- **Rounds.** Rounds 1–6 REVISE with 11, 5, 3, 2, 2 and 2 findings; round 7 APPROVED (2026-10-04), bound to the plan's
  sha256 `00a25729…`. The user raised the round limit from 5 to 8 after round 5.
- **What changed.** All findings were accepted and applied. The main ones:
  - pilot subset campaigns that cannot be assembled (R01): a separate pilot_subset role, merged without assembly;
  - Gate 5 needed subgraph mask lists that the published inventory does not hold (R02);
  - a cost-model refresh path for a changed binary (R03);
  - the two-loop reference path and its five-entry overlap (R04);
  - report inputs that lost the prefix boundaries of nested samples (R06), the same-data variance correction for 8 and
    16 replicates (R07);
  - submission safety: the shared lock, ledger-before-acceptance, durable submission intents, slot accounting of
    unresolved intents (R08, R09, R17, R20–R22);
  - block balancing under both checkpoint maxima (R10) and the input-parser guards of the rate converter (R11).
- **Limitations stated by the reviewer.** Static plan review; implementation conformity, live cluster behaviour and the
  unchanged numerics were not revalidated.

## 2. Code inspection: two rounds; Stage 6 closed on the user's acceptance of the residuals

- **Round 1 (2026-10-06).** Four scopes (native worker; orchestration; assembly, statistics and delivery; inputs,
  performance and gen3), each diffed against the C7(3) base. All REVISE, 33 findings (14 high). All 33 accepted and fixed
  in one fix round, with two departures from Codex's proposed fixes (per-site budget sub-caps instead of a shared
  admission coordinator, S2-004; an append-only decision acknowledgment instead of a lock that the other session's
  writers do not honour, S4-004).
- **Round 2 (2026-10-06, the last allowed by the user).** All four scopes REVISE, 23 findings. Codex confirmed most
  round-1 fixes; nine were partial; three findings were new.
- **Decision (user, 2026-10-06): "Targeted fix, no 3rd Codex".** Fix round 2 fixed the reachable gaps (S3-R2-001..007,
  -009, S2-R2-005, S4-R2-001..003, S1-R2-01, -02, -05 and a uniqueness check for S1-R2-03). **Fix round 2 and the host's
  change of the symmetry admission cap are not Codex-reviewed.**
- **Accepted residuals** (G6 closed 2026-10-07): concurrency races outside the operating procedure (S2-R2-002, -003,
  -004 = S3-R2-008, -006); defense in depth behind working guards (S2-R2-001, S1-R2-04); S1-R2-03 beyond uniqueness; and
  three unit tests that cannot run on a real cluster site by design (they pass on the Mac). One per-block throughput
  shortfall (three of 789 blocks below 0.95) is reported, not fixed.
- **Validation of the final code (K6 a914db2)** on symmetry and Expanse: val1, val2 (order 7 bit for bit against the
  unchanged C7(3) worker on every L <= 7 kernel; `benchmarks/symmetry_2026-10-c8/stage6_a914db2/val2/`), val3, the
  bitwise L8 proof against the Stage-3 binary, cost sweeps and campaign-build checks.

## 3. Production support after Stage 6: not inspected

Added on 2026-10-08 by the builder, tested on the Mac and on symmetry, **not Codex-reviewed**: the production budget line
(`tools/budget.py`), the conservative tail rule of the design (`tools/design_fallback.py --pc`), the margin probe
(`tools/margin_probe8.py`) and the production support of `tools/production.py` and `tools/slurm_submit.py`. The worker
source `src/` did not change after Stage 6 (production binary e9b6f6c3…). The production export 4fbd1bae passed val1
(571477: 38 PASS, 19 SITE_REFUSED by design, 0 FAIL) and J-BLD (571482).

## 4. Results review: APPROVED in round 3

- **What was reviewed.** A results dossier (C8(3) = 1602.6 ± 3.9, the campaign split, the tail N-trend, the margin
  probes, the lower-order checks) against the stored result, the local copy of the production records (50 hashes matched
  symmetry), the package at 6dd4a75a and the independent package's records.
- **Round 1 (2026-10-12): REVISE.** "The stored result and campaign provenance are consistent with the inspected records.
  The uncertainty justification overstates what the diagnostics establish, and the N-trend analysis contains two
  concrete comparison errors." Findings: χ²/dof ≈ 1 does not show calibrated SEs nor exclude a diffuse rate effect
  (C8D3-R1); the a/b shift of ξ̂ was taken at unmatched N (C8D3-R2); coincident predictions at N = 32,768 were counted
  as decisions (C8D3-R3). All accepted: `ntrend.py` and both READMEs revised (package commit 8adedace), the a/b reading
  narrowed to "no concentrated discrepancy".
- **Round 2: not counted.** The reply was APPROVED with one low finding (C8D3-R4, quoted bands), but a transport failure
  left the turn unrecorded; C8D3-R4 was applied anyway.
- **Round 3 (2026-10-12): APPROVED.** "Rev 3 resolves C8D3-R1–R4. No material unresolved defects were found in the
  inspected evidence. The result stands within its stated scope: ±3.9 is a conditional, heuristic sampling allowance,
  without established confidence coverage."
- **Limitations stated by the reviewer.** Static review; remote checkpoints, promotion tables, raw tails and the archives
  were not audited; inventory and field theory not re-derived; finite variance and four-SE coverage not established.
- **Reporting rule.** 4 × SE rounded up to a multiple of 0.1 was proposed in the dossier and confirmed by the user after
  the approval ("yes use 1602.6 ± 3.9"). No allowance was registered before the production.

## 5. Recommendations not followed

- Codex's shared admission coordinator (S2-004) and shared-file lock (S4-004): replaced as stated in section 2.
- A third inspection round after fix round 2: declined by the user.

## 6. Independent check

A separately developed code (package LRI_C8_D3_OPT, by OpenAI GPT-6 astra) gives 1600.98 ± 3.97, −0.40 combined SE from this
result. It is documented with its own reviews in the `C8_3_check` folder.
