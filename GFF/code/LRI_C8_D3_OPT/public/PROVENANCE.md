# Provenance: LRI_C8_D3_OPT (independent check of C8(3))

## Who wrote what

| part | author | date | source |
|---|---|---|---|
| The package: native worker, graph generation and audits, analytic low-loop inputs, planner, assembly, fixed point, allocation, tests, docs, the delivered pilot | OpenAI GPT-6 astra (stated by the author, 2026-10-13; the files do not name it), given the project's seventh-order package `LRI_C7_D3_HPC` and a version of the condensed note | delivered 2026-10-09 | `LRI_C8_D3_HPC_optimized.zip`, 451,327,106 bytes, sha256 `9de3c1d85c2c5e4103cd3de84ef7f2a07a49fcfbefc9168c451e176cf0e73000` |
| Inside that zip: the base package plus a performance patch, merged by the same author | same | 2026-10-08/09 | `OPTIMIZED_PACKAGE.json`: base `LRI_C8_D3_HPC.zip` sha256 `4cf21876...`, patch `LRI_C8_D3_optimized_patch.zip` sha256 `aafee16b...`; the patch changes `Makefile`, `src/kernel.hpp` and `src/c8d3_integrate.cpp`; `baseline/` keeps the unpatched worker for the regression test |
| Cluster layer for Expanse and symmetry: `tools/submit.py`, `tools/hpc_dispatch.py` (locks, deadlines, signals, staging), `slurm/*.sh`, `slurm/sites/*`, `docs/CLUSTERS.md`, `tests/test_cluster.py`, `tests/fake_native.py`; one receipt re-check in `tools/campaign.py run_job` | Claude Code session C63d (Claude), reviewed by Codex (`REVIEWS.md`) | 2026-10-09 to 2026-10-12 | git commits after `dafa312` |
| Production `prod1` on Expanse and its records | C63d, on the user's decisions (budget about 9,000 SU on 2026-10-10; finishing the 5-job tail on 2026-10-11) | 2026-10-10/11 | `GFF/results/C8_3_check` |
| `public.mk` and `public/` (replay, docs, Slurm templates, data-bundle tool) | the drafting agent of the public release (Claude) | 2026-10-13 | new files, not part of the package |

## Git history of the package (repository `main`)

- `dafa312` (2026-10-09): the zip as received, unchanged. `inputs/free/`, `inputs/power/` and `results/` are untracked
  (git-ignored) and covered by the package's own `SHA256SUMS` / `DELIVERY_MANIFEST.json`.
- `a807244` ... `6fb5b5f`: the cluster layer and the fix rounds of Codex inspections r1-r4.
- **`d5deeb9` (2026-10-10 15:18 EDT): the production commit.** One admission change after r4 (the user's running-job
  cap counted differently), uninspected. Exported here.
- `3961865`, `6edcc9e` (2026-10-12): fix rounds 5 and 6 (admission rules only). They change `tools/submit.py`,
  `tests/test_cluster.py`, `docs/CLUSTERS.md`, `DELIVERY_MANIFEST.json` and `SHA256SUMS`; no file that the
  production pins or that the science reads. Not exported.

Science files unchanged since `dafa312`: `src/`, `baseline/`, `inputs/` (tracked and untracked), `regeneration/`,
`tools/assemble.py`, `assemble_streaming.py`, `rg.py`, `io_utils.py`, `sobol_net.py`, `allocate.py`,
`generate_graphs.py`, `prepare_low.py`, the package `Makefile`. `tools/campaign.py` changed once (commit `6e3f139`,
Codex finding R2-08: `run_job` re-checks the receipt after taking its lock and never replaces a receipted output); the
production manifest pins the changed file (sha256 `13a12b7c...`). `tools/hpc_dispatch.py` is pinned by the production's
dispatch index (sha256 `f36741f7...`, identical from `6fb5b5f` to `6edcc9e`).

## Production

- Worker: `bin/c8d3_optimized`, sha256 `e6f424c5...`, built from `d5deeb9`'s sources (unchanged since `dafa312`) with
  GCC 13.3.0, Boost 1.77 headers and GMP 6.2.1 on an AMD EPYC 7742 node; three Expanse builds (jobs 54781591,
  54783728 and 54786481 on 2026-10-09, before and after the r2-r4 fixes) produced the same binary hash. Backend `gmp350`.
- Allocation `prod1_2000.json` (sha256 `fccf8969...`): `tools/allocate.py` on the delivered pilot's graph statistics,
  2,000 core-hours of the pilot's host, 16 replicates, minimum 4,096 points (the replay reproduces it byte for byte).
- Plan job 54822480 (manifest created 2026-10-10T21:00:28Z): base seed 1546835505427890396, 1,994 jobs,
  37,121,687,552 evaluations, complete coverage verified.
- Lanes job 54823471: 6 nodes x 16 lanes x 8 threads, 2026-10-10 21:59Z to 2026-10-11 10:42Z (12:43:34); 1,989 jobs.
  Lane 67 deferred two bundles (jobs 417 and 1057-1060) at its deadline, a clean stop (srun exit 3).
- Index-only job 54838167 (a hand-written sbatch; the site layer had no role for re-indexing an existing run): a
  16-lane index over the same run with the same bundling. Lanes job 54838170 (1 node, 11:31) ran the 5 jobs.
- Assembly job 54838171 (`assemble_streaming.py --bootstrap 4096`, 46 s): `C8_result_54838171.json`
  (sha256 `58de4f97...`) and `graph_statistics_54838171.json`.
- Records copied from the Expanse campaign directory to the project on 2026-10-11 (`GFF/results/C8_3_check`, byte
  identical). The native outputs and receipts of the 1,994 jobs stay on the production cluster's scratch filesystem;
  they are not archived.

## What the export changes

- Code: `git archive d5deeb9`, minus `DELIVERY_MANIFEST.json`, `reference_study/`, `regeneration/` and
  `inputs/complete_inventory_L*.json` (the last two are hosted), and, since 2026-10-16 (author rule: one TeX note per
  direction), minus `derivation.tex`, `docs/DERIVATION.tex` and `docs/C8_3D_calculation.{tex,pdf}`, whose substance
  is in the condensed note, Section 32.7. No shipped file is modified.
- Plus 179 untracked graph payloads from the working tree (the test fixtures), byte-identical to the zip (checked
  against `SHA256SUMS`).
- `SHA256SUMS` ships unchanged. `make -f public.mk verify-data` (`public/verify_data.py`) checks every shipped file
  against it; a listed file may be absent only if it is hosted (until `fetch-data`) or named in
  `public/dropped_paths.txt` (the four notes above and `reference_study/long_range_ising_condensed.tex`).
- The package's `.gitignore` ships unchanged; it ignores `inputs/free/`, `inputs/power/`, `results/` and `bin/`, so the
  179 fixtures must be added to the public repository with `git add -f` (tracked files stay tracked; the hosted
  payloads unpacked by `fetch-data` stay ignored).
