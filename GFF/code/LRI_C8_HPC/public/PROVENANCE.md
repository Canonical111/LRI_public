# Provenance: LRI_C8_HPC (C8(1), full eighth order in one dimension)

- **Authors.** AI-generated: written by a Claude Code session (Anthropic Claude, session "C71d") on 2026-10-02 as an
  order-eight generalization of the reviewed C7(1) package `LRI_C7_HPC`. The repository is a fork of it: its first
  commits are the C7 history, from baseline c21b9e8 on. The nine-vertex generators in `gen/` were written by a subagent
  of that session. Independent reviews are by OpenAI Codex (see REVIEWS.md). The research direction, budgets and the
  decisions recorded in the amendments are the author's.
- **Source.** Git repository `LRI_C8_HPC`, branch `c8`, exported at commit 1282e37 (2026-10-13).
  - **b1-b4 production code** (SDSC Expanse, 2-3 October 2026): commit c0ffa63, Codex APPROVED at inspection round 10.
    `src/`, `gen/` and every tool except `tools/combine8.py` and `tools/lane8.py` are unchanged from c0ffa63 to
    1282e37.
  - **Extension A1** (b5-b14 on symmetry, 10-12 October): `tools/combine8.py --extension` and `tools/lane8.py` at
    15a110e, APPROVED at round 12, unchanged afterwards.
  - **Amendments A2 and A3** (12-13 October): `cluster/symmetry/*`, `cluster/a3/*` and docs, through bd13a63.
  - **Results:** commits 9dd3a6b to 1282e37 add the K = 14 result and the report, with no code change.
- **Production.** The production ran copies of these commits:
  - Expanse: `code/c0ffa63`;
  - symmetry: `code/15a110e` and the A3 tools of bd13a63.
  The binary `bin/c8_integrate` was built from `src/` with GCC 13.3.0. Its sha256 is recorded in every campaign
  manifest (`executable_sha256`), and `tools/combine8.py` requires it to be identical across batches.
- **Dates.** Code 2026-10-02 to 2026-10-03. First result (K = 4) 2026-10-03: 8066723 +- 8015, allowance 33000. Extension
  A1 2026-10-10 to 12 (A1 interim, K = 9: 8061480 +- 5300). A2 and A3 2026-10-12 to 13. Final K = 14 on 2026-10-13:
  8059767, SE 4210, allowance 17000. The Codex results review was APPROVED at round 4 on 2026-10-13.
- **Compute.** About 9x10^4 physical core-hours in all (1.4x10^5 as charged, counting hyperthreads on symmetry). The
  extension A1-A3 used 64.6x10^3 physical core-hours: 46.8x10^3 on symmetry and 17.8x10^3 on Expanse.
- **Changed for the public copy.**
  - Inherited C7 files (benchmarks/, inputs_extra/, CHANGELOG.md, docs/c7_historical/ and a stale SHA256SUMS) and the
    second copy of `reference/` are not shipped. `make -f public.mk setup` links `reference` to `../LRI_C7_HPC/reference`, which is
    byte-identical (no symlink is committed).
  - `inputs8/L8_coord.txt` ships xz-compressed in `GFF/data/C8_1/inputs8/`.
  - New files only: `public.mk`, `public/` (replay, verify, portable test, env template, README) and `REVIEWS.md`.
  - No shipped file was edited.
- **Records.** `GFF/data/C8_1` holds byte-identical copies of the merged production records, fetched read-only on
  2026-10-13 from symmetry (`<SCRATCH>/c8_hpc/`) and Expanse (`runs/tailtest_L7`; `runs/pilot8/tprodA_L7`,
  `tprodB_L7` and the pilot batch JSON on 2026-10-16). User names, cluster paths
  and node names in records and production scripts are kept, because they are bound by hashes or ran as written.
