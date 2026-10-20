# Reviews of LRI_C8_D2_HPC_optimized (independent check of C8(2))

The code was written by OpenAI GPT-6 astra (model stated by the author, 2026-10-13), independently of the eighth-order extension that Claude Code built for the main calculation, as an
eighth-order extension of the seventh-order package of Section 28 of the note. It was delivered as
`LRI_C8_D2_HPC_optimized.zip` together with the original package `LRI_C8_D2_HPC.zip` (graph packs and earlier runs). Its numerical files (`src/`, `Makefile`, the tools pinned by a campaign plan) were not changed afterwards.
A Claude Code session added a cluster layer for Expanse and symmetry (whole-node runner, admission and seed checks, a gate
job, tests and docs; commits 300a1ca..a791a1f) and ran the pilot and the production. The reviewer in every round below was
OpenAI Codex (model gpt-6-astra, reasoning effort xhigh), each inspection in a fresh session.

| Stage | Rounds | Verdict | What changed |
|---|---|---|---|
| Port plan | 4 | APPROVED in round 4 | Rounds 1-3 (REVISE): 8 + 7 + 4 findings, all accepted. Job arrays replaced by one whole-node runner per node; production seeds reserved in the seed registry of the main C8(2) calculation; one site lock and admission check shared with the other campaigns; scheduler states such as COMPLETING handled; exhausted work indices retried; the deadline measured in wall time. |
| Code inspection 1 | 1 | REVISE, 4 findings | All fixed in 71a7844: claim tokens under a claims lock; the seed synchronisation compares (seed, source) pairs; quoted owner paths in remote shells; the plan comparison fails on any differing manifest key. |
| Code inspection 2 | 1 | REVISE, 1 finding | Fixed in a791a1f: the runtime identity refuses `LD_PRELOAD`, `LD_AUDIT` and `GLIBC_TUNABLES` and hashes absolute-path library entries. |
| Results | none | not reviewed | The result was not given a separate results review. |

What was not reviewed:
- the fix of the second inspection (a791a1f), because the inspection budget of two rounds was used up. It touches only the
  cluster layer's identity check, not the numerics. The production ran this commit.
- the numerical code itself, beyond the checks the package ships: it was delivered as is, and the port's acceptance gate
  required its numerical files to be byte-identical to the delivery (gate step AC1) and its kernel to reproduce 52 frozen
  fixture cases bit for bit against the delivered reference kernel (AC2), on both clusters.

No recommendation of any review round was overruled.

Scope of the check (note Section 31.7): the code shares with the main calculation the seventh-order kernel construction
and its precision policy, the importance sampler, the digital nets and seed hashing, the renormalization scheme and the
payloads of loops three to seven, so an error in those would be common to both.
