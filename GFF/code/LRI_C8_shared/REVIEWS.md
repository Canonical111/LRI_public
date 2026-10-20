# Reviews of LRI_C8_shared (shared eighth-order inputs of C8(2) and C8(3))

Two Claude Code sessions wrote this folder: C62d (the C8(2) package) the inventory and payloads `inventory/inventory8_d2/`,
C63d (the C8(3) package) the order-8 assembly `assembly/`. Each checked the other's part. No raw review log ships (the
review records and the coordination notes stay in the project archive).

| Item | Reviewer | Verdict | What was checked |
|---|---|---|---|
| `assembly/` (handoff H2/H3, `HANDOFF_assembly.json` sha256 f5ff6a35..., 2026-10-03) | C62d's Claude workflow, four lenses (independent derivation of the eighth-order RG polynomial, order-7 regression against the published C7(2) assembly, numerics of the two-loop and Gamma inputs, handoff tests) | ACCEPT_WITH_MINOR; no required change | every delivered file at its sha256; the eighth-order polynomial derived twice and equal; 64 random eighth-order cases against two exact inversions (7.0e-16); order 7 reproduces C7(2) to 2 ulp; the vendored tests (30 passed) and exact_check. Minor suggestions (documentation, test bounds) were left for a later revision, which never happened. |
| `assembly/` | C63d's own workflows (builder plus three adversarial lenses, two repair rounds; fixer plus two verifiers) | ready | as recorded in `HANDOFF_assembly.json` (`verification`) |
| `inventory/inventory8_d2/` (handoff H1, pin 46341a3c...) | C62d's independent verifier (Stage 1-2 of the C8(2) plan) and C63d's gates on the published tree | passed | the eleven gates of the tree (`gates/`), plus C63d's gate records in `assembly/H1_gates/` (counts against an independent enumeration, weight sums, reproduction of the L <= 7 packs at d = 2 and d = 3) |
| both | OpenAI Codex (gpt-6-astra, xhigh) | not reviewed as such | the assembly was out of scope of the C8(2) Codex inspection (reviewed separately as above); the generator code under `inventory8_d2/src/gen/` was inspected as part of the C8(2) package (`LRI_C8_D2_HPC/gen/`, rounds 1-4, REVISE, fixed; no Codex approval, see that package's REVIEWS.md). The tree itself was published before those rounds and never changed; the generator regression re-run after each fix round (J-GEN-1, A-INV-2 on symmetry) still found the regenerated loops equal to the published inventory. |
