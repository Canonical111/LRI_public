# Reviews of LRI_C8_D2_HPC (full C8(2), note Section 31)

The package extends the seventh-order d = 2 package (LRI_C7_D2_HPC, whose root commit is the code as delivered by an AI
model in a ChatGPT session, OpenAI GPT-6 astra (model stated by the author, 2026-10-13), hardened by Claude Code and approved by Codex in round 3 at a55958f)
to eighth order. The eighth-order code, its tests and all evidence were written by Claude Code session C62d and its
subagent workflows (2026-10-03 to 2026-10-09). The reviewer in every round below was OpenAI Codex (model gpt-6-astra,
reasoning effort xhigh), each round in fresh sessions. No raw review log or transcript is shipped.

**There is no Codex approval of the code.** The user stopped the code inspection after round 4 (2026-10-06); round 5
was prepared but not run, and the pilot and the production went ahead without an APPROVED verdict.

| Stage | Rounds | Verdict | What changed |
|---|---|---|---|
| Plan | 4 | APPROVED in round 4 (plan only, static) | Rounds 1-3 (REVISE): 3 high and 9 medium, then 5 and 3 medium findings, all accepted: dependencies of the vendored tests, invalidation of completion markers, a frozen and pinned rate map, an acyclic checksum hierarchy, per-campaign cost keys, bounded merge fan-in, the calibration bootstrap, the platform contract. |
| Stage-3 checkpoint (3 parallel sessions) | 1 | REVISE, 20 findings (4 high) | All fixed (merged-run authentication, partition overrides of merges, accounting that fails closed on missing scheduler records, no submission after a failed time policy, and 16 medium/low); worker binaries byte-identical; re-validated on Expanse. |
| Stage-6 code inspection (6-8 parallel sessions per round) | 4 | REVISE in every round: 23, 16, 22 and 21 distinct findings | Four fix rounds, each validated on symmetry: gate records bound to their F1 coverage, build and input set; OpenMP team sizes controlled and observed; generator input validation; contained vendoring; runtime fingerprints enforced; cost-model numerics checked; seed registration; memory estimate of a claim; strict G-file readers. One fix changed the kernel source (round 3, Z4: refuse truncated graph files; valid inputs give the same output bit for bit; the full exact replay of all 3,773 L3-L7 kernels passed again and the double-double/77-digit gate was re-run). No default-path number changed in any round. |
| Heavy-tail question (results side) | 2 consultations | (1) the confirmations apply a warning rule and do not establish an infinite second moment; (2) "sound with caveats" | The caveats were all addressed before the result was quoted: four random primes and two random points per prime instead of two fixed primes, an error bound; nine archived controls with failing exit codes; joint resampling on a common window; a targeted test of the double-lift class; the SE wording ("estimated sampling standard error"; inflation figures are scenarios, not bounds). |
| Results | none | not reviewed | No separate Codex results review of the C8(2) production was run. The independent eighth-order code (GFF/code/LRI_C8_D2_HPC_optimized) is the external check. |

Recommendations overruled or not done, and why:
- The Stage-6 approval gate (the plan tied the pilot to Codex approval): waived by the user after round 4, because the
  later rounds found mostly hardening against misuse and no numerical defect.
- Codex's proposed tail test from checkpoint prefixes: not possible (one checkpoint row per replicate); replaced by a
  fresh nested-sampling test.
- Never run (owed after Stage 6, not needed because production stayed on symmetry): the J-EXP-1 rerun on Expanse
  (acceptance A-EXP-3; the first attempt was cut short by a Lustre failure), the zen2 `GMP_PREFIX` precision re-run on
  Expanse (so builds with `GMP_PREFIX` are not cleared for production), and the Expanse copy of the forbidden-seed log
  (seeds of fix rounds 1-4 and of the pilot and production are pending there).
- Not approved for production: the `exp1` numerics profile (inert) and the R7 rate maps.
- Deferred: undefined behaviour of the frozen-grid reader on a truncated optional grid file (production passes '-').

What was never reviewed by Codex: the fix of inspection round 4 (W1-W24; no source change; validated on symmetry), the
evidence and analysis scripts under benchmarks/, the report-caps fix aafa8a4 (not part of this release), and the public
release files (public.mk, public/).

The order-8 assembly under vendor/c8_assembly/ was written by Claude Code session C63d and reviewed by C62d's Claude
workflow (four lenses: independent derivation, order-7 regression, numerics, handoff tests): ACCEPT_WITH_MINOR, no
required change (see ../LRI_C8_shared/REVIEWS.md).
