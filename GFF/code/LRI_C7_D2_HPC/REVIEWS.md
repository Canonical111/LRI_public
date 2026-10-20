# Reviews of LRI_C7_D2_HPC (full C7(2), note Section 28)

The package was written by OpenAI GPT-6 astra (model stated by the author, 2026-10-13), in a ChatGPT session and delivered on 2026-09-30 as an
optimized, restartable reimplementation of that model's earlier two-dimensional seventh-order calculation, which it
carries unchanged under `reference/`. A Claude Code session (C62d) committed it unchanged as git commit `fb64c47`, built
and tested it on the production cluster, and ran the production with it on 2026-09-30. Three reviews followed. No raw
review log or transcript is shipped.

| Stage | Reviewer | Rounds | Verdict | What changed |
|---|---|---|---|---|
| Code review of the delivered package (`fb64c47`), 2026-09-30, in parallel with the production | Claude Code multi-agent workflow (72 agents: kernel, sampler, assembly, orchestration, inputs and tests, cluster use; every finding checked by independent refute and impact verifiers; a completeness critic) | 1 | Numerics sound; no critical or high finding; 4 medium and 21 low findings; GO for the running production | Nothing in the code that ran. The production was judged with manual lower-order pulls, as the review asked (finding M2). |
| Results review of the production, 2026-10-01 | OpenAI Codex (model gpt-6-astra, reasoning effort xhigh), claudex-loop review mode, on a dossier of the result | 1 of 5 | APPROVED, no findings | Nothing. Codex rebuilt all 1,275,008 task rows of the 2,048 checkpoints with Decimal arithmetic (1,094,688,178,176 samples, no gap or overlap), checked the hashes of all 20 groups and of the 3,511 packed kernels against the reference files, reconstructed C7 = -3876.126092794993 with sampling SE 0.524449669095692 and every pull, and found no sign of heavy tails (largest standardized replicate deviations 2.72 and 2.88 in the dominant groups). It called +-2.1 "defensible as an empirical four-SE allowance, not a certified error bound". |
| Fix loop on the package, 2026-10-01/02 (`fb64c47` -> code `3cef517`, evidence `a55958f`) | Plan and code: Claude Code (C62d and a builder subagent); plan review and code inspection: OpenAI Codex (gpt-6-astra, xhigh), each inspection in a fresh session; host review: Claude Code workflow (42 agents) | plan 4, inspections 3 | Plan APPROVED in round 4; host review 1 medium and 27 low; inspections REVISE (5 findings), REVISE (2 findings), APPROVED in round 3 | Job-handling layer (status, recovery, guarded submission with a lock, resumable merge), opt-in allocation flags, lower-order pulls in the result, build records, tests. **Not part of this release**: the production ran `fb64c47`, and the revised tools refuse campaigns planned by `fb64c47`. Its only change to `src/` is one line that lets the kernel compile with Boost 1.66; with Boost 1.77 the binaries of both commits are byte-identical to the production binaries (checked four times on the production cluster). |

Findings of the code review that were not acted on for the production, and why:
- M1 (the power sector takes 55-62% of the CPU for under 1% of the variance) and M3 (the 44 primitive classes get a flat
  allocation): the production had already been planned with the delivered defaults when the review reported; changing the
  allocation would only have saved cost, not changed the estimator. The review estimated SE 0.45-0.5 instead of about 0.7
  for the same cost; the production reached 0.52.
- M2 (the emitted lower-order checks carry no pull and compare C6 with the old archived value 362.3489 +- 0.153): the
  record `C7_result.json` keeps that block as written (it is hash-bound); the note's pulls are computed against the C6(2)
  production and are recomputed by `make -f public.mk replay`.
- M4 and the 21 low findings concern throughput and orchestration; the fix loop addressed them in code that is not shipped.

Deviations in the fix loop: one acceptance criterion assumed the delivered kernel fails with Boost 1.86; the host found
that the failure seen on one cluster came from the system Boost 1.66 (the Boost 1.86 module there sets no include path),
so the criterion could not be met as written and the documentation was corrected instead. The builder used a deferred
signal handler instead of `pthread_sigmask`, which a child process would inherit. Deferred test-strength items (HR17,
HR19-HR23, HR25, HR27, HR28) remain open in that unshipped revision.

What was never reviewed:
- the graph construction, the local mass subtraction and the renormalization argument, which this package inherits from
  the earlier calculation (its method note is merged into note Section 28); the reviews checked the software against that
  construction, and the note's checks (three-loop analytic value, lower orders) share it;
- the native kernel beyond reading and the package's own bitwise and point checks (no reviewer built it; the coordinator
  ran the builds and tests on the clusters);
- the bootstrap regeneration (the results review inspected the stored bootstrap; `make -f public.mk replay` now regenerates
  it).
